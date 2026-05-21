import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
    base: '/static/', // <-- This tells Vite to add "/static/" to the URLs in your CSS
    plugins: [tailwindcss()],
    build: {
        outDir: 'app/static',
        emptyOutDir: false,
        rollupOptions: {
            input: 'app/static/main.js',
            output: {
                // Control JS output
                entryFileNames: 'app.js',
                // Control Asset output conditionally
                assetFileNames: (assetInfo) => {
                    // If it's a CSS file, name it app.css
                    if (assetInfo.name && assetInfo.name.endsWith('.css')) {
                        return 'app.css';
                    }
                    // For fonts, images, etc., put them in an assets folder with their original extension
                    return 'assets/[name]-[hash][extname]';
                },
            },
        },
    },
});
