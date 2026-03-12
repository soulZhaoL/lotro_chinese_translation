// 前端运行时配置加载。
export type AppConfig = {
  apiBaseUrl: string;
  useMock: boolean;
};

let cachedConfig: AppConfig | null = null;

function parseApiBaseUrl(rawValue: unknown): string {
  if (typeof rawValue !== "string") {
    throw new Error("前端配置缺少 VITE_API_BASE_URL");
  }
  const value = rawValue.trim();
  if (!value) {
    throw new Error("前端配置 VITE_API_BASE_URL 不能为空");
  }
  return value.replace(/\/+$/, "");
}

function resolveConfig(): AppConfig {
  const useMock = import.meta.env.MODE === "mock";
  const isDev = import.meta.env.DEV;

  if (useMock && !isDev) {
    throw new Error("前端配置无效: 生产构建禁止启用 Mock（--mode mock 仅限开发环境）");
  }

  const apiBaseUrl = useMock ? "" : parseApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

  return {
    apiBaseUrl,
    useMock,
  };
}

export async function loadAppConfig(): Promise<AppConfig> {
  if (cachedConfig) {
    return cachedConfig;
  }
  cachedConfig = resolveConfig();
  return cachedConfig;
}

export function getAppConfig(): AppConfig {
  if (!cachedConfig) {
    throw new Error("前端配置未初始化");
  }
  return cachedConfig;
}
