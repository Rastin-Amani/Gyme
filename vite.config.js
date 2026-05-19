import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: "static",
    emptyOutDir: false,
    rollupOptions: {
      input: {
        app: "frontend/js/app.js",
        style: "frontend/css/app.css",
      },
    },
  },
});
