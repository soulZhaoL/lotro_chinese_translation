// 前端运行时配置加载。
export type AppConfig = {
  apiBaseUrl: string;
  useMock: boolean;
};

let cachedConfig: AppConfig | null = null;

function validateConfig(payload: any): AppConfig {
  if (!payload || typeof payload !== "object") {
    throw new Error("前端配置加载失败: 配置内容无效");
  }
  if (typeof payload.apiBaseUrl !== "string") {
    throw new Error("前端配置缺少 apiBaseUrl");
  }
  if (typeof payload.useMock !== "boolean") {
    throw new Error("前端配置缺少 useMock");
  }
  if (!payload.useMock && !payload.apiBaseUrl) {
    throw new Error("前端配置 apiBaseUrl 不能为空");
  }
  return {
    apiBaseUrl: payload.apiBaseUrl,
    useMock: payload.useMock,
  };
}

export async function loadAppConfig(): Promise<AppConfig> {
  if (cachedConfig) {
    return cachedConfig;
  }
  const useMockRaw = import.meta.env.VITE_USE_MOCK;
  if (useMockRaw === undefined) {
    throw new Error("前端配置缺少 VITE_USE_MOCK");
  }
  const apiBaseUrlRaw = import.meta.env.VITE_API_BASE_URL;
  if (apiBaseUrlRaw === undefined) {
    throw new Error("前端配置缺少 VITE_API_BASE_URL");
  }
  const payload = {
    apiBaseUrl: apiBaseUrlRaw,
    useMock: useMockRaw === "true",
  };
  cachedConfig = validateConfig(payload);
  return cachedConfig;
}

export function getAppConfig(): AppConfig {
  if (!cachedConfig) {
    throw new Error("前端配置未初始化");
  }
  return cachedConfig;
}
