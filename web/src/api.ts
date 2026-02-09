// API 访问封装与鉴权。
import { getAppConfig } from "./config";
import { setMaintenanceState } from "./maintenance";

const TOKEN_KEY = "lotro_token";
const USER_NAME_KEY = "lotro_user_name";

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export function setUserName(name: string) {
  window.localStorage.setItem(USER_NAME_KEY, name);
}

export function getUserName(): string {
  return window.localStorage.getItem(USER_NAME_KEY) || "游客";
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const config = getAppConfig();
  const useMockFlag = config.useMock;
  const apiBase = useMockFlag ? "/api" : config.apiBaseUrl;
  if (!useMockFlag && !apiBase) {
    throw new Error("缺少 apiBaseUrl");
  }
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers,
  });

  let payload: any = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (payload && typeof payload === "object" && "success" in payload && "code" in payload) {
    if (payload.code !== "0000") {
      if (payload.code === "MAINTENANCE") {
        setMaintenanceState({
          enabled: true,
          message: typeof payload.message === "string" ? payload.message : undefined,
        });
      }
      throw new Error(payload.message || "请求失败");
    }
    return payload.data as T;
  }

  if (!response.ok) {
    if (response.status === 503) {
      setMaintenanceState({ enabled: true });
    }
    const text = payload ? JSON.stringify(payload) : await response.text();
    throw new Error(text || `请求失败: ${response.status}`);
  }

  return payload as T;
}
