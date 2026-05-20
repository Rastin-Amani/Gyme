import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
    plugins: [tailwindcss()],
    build: {
        outDir: 'app/static',
        emptyOutDir: false,
        rollupOptions: {
            input: 'app/static/main.js',
            output: {
                // This controls the CSS output
                assetFileNames: 'app.css',
                // This controls the JS output
                entryFileNames: 'app.js',
            },
        },
    },
});
