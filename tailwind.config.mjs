/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx,md,mdx}'],
  theme: {
    extend: {
      colors: {
        // Juniper Jing / Lovart 调色板（2026-05-16 对齐 Lovart 设计稿）
        ink: '#0a0908',           // 深黑底（Lovart 主背景）
        parchment: '#e6dcc6',     // 旧羊皮纸
        verdigris: '#5a7a6a',     // 风化铜绿
        ochre: '#b89568',         // 做旧赭石
        slate: '#3a3d40',         // 石板灰
        brass: '#8d6e3a',         // 黄铜
        goldleaf: '#d4b98a',      // 主品牌金（Lovart 暖金，从 #c9a35a 调亮）
        candle: '#f4d68a',        // 烛火光
        crimson: '#7a2b2b',       // 圣血红
        junipergold: '#e8d9bd',   // 最亮品牌金（hero 标题 / wordmark）
        juniperdeep: '#0a0908',   // 品牌深黑底（同 ink）
      },
      fontFamily: {
        // 西文 = Cinzel / EB Garamond; 中文 = 楷体 (Kaiti)
        display: ['Cinzel', 'Trajan Pro', 'STKaiti', 'KaiTi', '楷体', 'serif'],
        body: ['EB Garamond', 'Garamond', 'STKaiti', 'KaiTi', 'BiauKai', '楷体', 'serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'fresco': "url('/textures/cracked-fresco.jpg')",
      },
    },
  },
  plugins: [],
};
