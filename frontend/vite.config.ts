import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const packageJsonPath = resolve(__dirname, "package.json");
const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf-8")) as {
  version?: string;
};
const appVersion = String(process.env.VITE_APP_VERSION || packageJson.version || "N/A");

export default defineConfig({
  plugins: [react()],
  base: "./",
  define: {
    __APP_VERSION__: JSON.stringify(appVersion)
  },
  build: {
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react-dom") || id.includes("node_modules/react/") || id.includes("node_modules/scheduler")) {
            return "framework";
          }
          if (id.includes("node_modules/lucide-react")) {
            return "icons";
          }
        }
      }
    }
  },
  server: {
    port: 5173,
    host: "127.0.0.1"
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts"
  }
});
