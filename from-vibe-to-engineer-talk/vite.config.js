import { defineConfig } from 'vite';

// base передається з CLI у publish-gh-pages (--base=/AI-work-place/from-vibe-to-engineer-talk/).
// slides.md імпортується як ?raw і вбудовується в бандл, тож fetch/CORS/шлях не залежать від base.
export default defineConfig({
  build: {
    outDir: 'dist',
  },
});
