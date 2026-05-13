import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import { writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = dirname(fileURLToPath(import.meta.url));

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

export default defineConfig({
  site: 'https://jiangjingyi496.github.io',
  base: '/lumen-records/',
  integrations: [tailwind()],
  vite: {
    plugins: [lrcSaverPlugin],
  },
});
