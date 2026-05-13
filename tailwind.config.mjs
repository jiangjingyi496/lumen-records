/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx,md,mdx}'],
  theme: {
    extend: {
      colors: {
        // Lumen / gregorian.de 调色板
        ink: '#0b0a08',           // 烛光底色（接近纯黑但带点暖意）
        parchment: '#e6dcc6',     // 旧羊皮纸
        verdigris: '#5a7a6a',     // 风化铜绿
        ochre: '#b89568',         // 做旧赭石
        slate: '#3a3d40',         // 石板灰
        brass: '#8d6e3a',         // 黄铜
        goldleaf: '#c9a35a',      // 黯金
        candle: '#f4d68a',        // 烛火光
        crimson: '#7a2b2b',       // 圣血红（强调用）
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
