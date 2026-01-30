// Vite 构建配置。
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { viteMockServe } from "vite-plugin-mock";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const useMock = env.VITE_USE_MOCK === "true";

  return {
    plugins: [
      react(),
      viteMockServe({
        mockPath: "mock",
        localEnabled: useMock,
        prodEnabled: false,
      }),
    ],
    server: {
      port: 5173,
    },
  };
});
