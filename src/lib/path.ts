// 给所有静态资源/内链加上 Astro 的 base 前缀。
// 部署到 GitHub Pages 的 project page 时（base = '/lumen-records/'），
// 写死的 '/foo' 路径在浏览器里会指向根（404）。统一过这个函数。

export const BASE_URL = import.meta.env.BASE_URL; // '/lumen-records/' 末尾带斜杠

/**
 * 把 '/foo/bar' 或 'foo/bar' 转换成 '<base>foo/bar'。
 * 外链（http://、https://、//）原样返回。
 */
export function withBase(p: string): string {
  if (!p) return p;
  if (p.startsWith('http://') || p.startsWith('https://') || p.startsWith('//')) return p;
  const normalized = p.startsWith('/') ? p.slice(1) : p;
  return `${BASE_URL}${normalized}`;
}
