import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
    plugins: [tailwindcss()],
    build: {
        outDir: 'app/static/css',
        emptyOutDir: false, // keep other static files
        rollupOptions: {
            input: 'app/static/app.css', // Tailwind entry CSS
            output: {
                assetFileNames: 'app.css', // force predictable name
            },
        },
    },
});
