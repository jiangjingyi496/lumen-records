import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import { writeFile, mkdir } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = dirname(fileURLToPath(import.meta.url));
const pExecFile = promisify(execFile);

// 仅 dev mode 下注册的 LRC 保存端点。生产构建静态站不需要此能力。
const lrcSaverPlugin = {
  name: 'lrc-saver-dev',
  configureServer(server) {
    server.middlewares.use('/api/save-lrc', async (req, res) => {
      if (req.method !== 'POST') {
        res.statusCode = 405;
        return res.end('Method Not Allowed');
      }
      let raw = '';
      req.on('data', (c) => (raw += c));
      req.on('end', async () => {
        try {
          const { slug, filename, content } = JSON.parse(raw);
          if (!/^[a-z0-9-]+$/.test(slug) || !/^[a-z0-9-]+\.lrc$/.test(filename)) {
            res.statusCode = 400;
            res.setHeader('Content-Type', 'application/json');
            return res.end(JSON.stringify({ ok: false, error: 'invalid slug or filename' }));
          }
          if (typeof content !== 'string' || content.length > 1_000_000) {
            res.statusCode = 400;
            res.setHeader('Content-Type', 'application/json');
            return res.end(JSON.stringify({ ok: false, error: 'invalid content' }));
          }
          const filepath = resolve(projectRoot, 'public/lrc', slug, filename);
          await mkdir(dirname(filepath), { recursive: true });
          await writeFile(filepath, content, 'utf-8');
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ ok: true, path: filepath }));
        } catch (e) {
          res.statusCode = 500;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ ok: false, error: String(e) }));
        }
      });
    });
  },
};

// 第二个 dev-only 端点: 一键 git add+commit+push 把调过的 LRC 推到 GitHub Pages.
// 走 execFile (非 shell) 避开注入风险; 仅在本地 (127.0.0.1) 监听, 外网不可达.
const publishPlugin = {
  name: 'publish-dev',
  configureServer(server) {
    server.middlewares.use('/api/publish', async (req, res) => {
      if (req.method !== 'POST') {
        res.statusCode = 405;
        return res.end('Method Not Allowed');
      }
      const send = (status, obj) => {
        res.statusCode = status;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(obj));
      };

      const cwd = projectRoot;
      const git = async (...args) => {
        const { stdout, stderr } = await pExecFile('git', args, { cwd, maxBuffer: 4 * 1024 * 1024 });
        return { stdout: stdout.trim(), stderr: stderr.trim() };
      };

      try {
        // 1. 是否有可推送的改动 (仅看 lrc + lyrics-raw, 不扫其他文件)
        const { stdout: status } = await git('status', '--porcelain', '--', 'public/lrc', 'lyrics-raw');
        if (!status) {
          return send(200, { ok: true, msg: '没有需要发布的改动', changed: [] });
        }
        // git status --porcelain 每行: "XY path", X/Y 各 1 字符, 跟 1 空格分开.
        // 但 status 字符为空格时, git 可能省略到 "M path"。统一用 regex 拆。
        const changed = status
          .split('\n')
          .map((l) => l.replace(/^[\sMARC?!ADUT]{1,2}\s+/, ''))
          .filter(Boolean);

        // 2. stage
        await git('add', '--', 'public/lrc', 'lyrics-raw');

        // 3. commit
        const ts = new Date().toLocaleString('sv', { timeZone: 'Asia/Shanghai' }).slice(0, 16);
        const msg = `Tuned lyrics — ${ts}\n\n${changed.map((f) => '- ' + f).join('\n')}`;
        await git('commit', '-m', msg);

        // 4. push
        const { stdout: pushOut, stderr: pushErr } = await git('push', 'origin', 'main');

        return send(200, {
          ok: true,
          msg: '已推送到 GitHub,GitHub Actions 正在部署,约 1 分钟后线上生效。',
          changed,
          push: pushOut || pushErr,
        });
      } catch (e) {
        const detail = e?.stderr || e?.stdout || e?.message || String(e);
        return send(500, { ok: false, error: detail });
      }
    });
  },
};

// 部署目标判定:
//   - DEPLOY_TARGET=zeabur  → 部署到 Zeabur 子域 (根路径)
//   - 其他 / 未设           → 默认 GitHub Pages 项目页 (/lumen-records/)
const isZeabur = process.env.DEPLOY_TARGET === 'zeabur';

export default defineConfig({
  site: isZeabur
    ? (process.env.PUBLIC_SITE_URL || 'https://lumen-records.zeabur.app')
    : 'https://jiangjingyi496.github.io',
  base: isZeabur ? '/' : '/lumen-records/',
  integrations: [tailwind()],
  vite: {
    plugins: [lrcSaverPlugin, publishPlugin],
  },
});
