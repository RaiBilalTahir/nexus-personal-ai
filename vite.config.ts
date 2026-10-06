import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'disable-hosted-hmr-client',
      transformIndexHtml: {
        order: 'post',
        handler(html) {
          return html.replace(/<script[^>]+src=["']\/@vite\/client["'][^>]*><\/script>/g, '');
        },
      },
    },
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
});
