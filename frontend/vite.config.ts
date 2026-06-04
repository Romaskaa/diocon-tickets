import path from "path";
import { fileURLToPath } from "url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// https://vite.dev
export default defineConfig({
  //Указываем, где искать .env (на уровень выше)
  envDir: path.resolve(__dirname, ".."),

  plugins: [react(), tailwindcss(), viteSingleFile()],

  //Разрешаем обращаться к файлам выше папки frontend
  server: {
    fs: {
      allow: [
        path.resolve(__dirname, ".."), // разрешаем корень всего проекта
        path.resolve(__dirname),      
      ],
    },
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
