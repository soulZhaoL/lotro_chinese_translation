// 维护模式状态管理。
import { getAppConfig } from "./config";

type MaintenanceState = {
  enabled: boolean;
  message: string;
  checked: boolean;
};

const DEFAULT_MESSAGE = "系统维护中，请稍后再试";

let state: MaintenanceState = {
  enabled: false,
  message: DEFAULT_MESSAGE,
  checked: false,
};

const listeners = new Set<(nextState: MaintenanceState) => void>();

function notify() {
  listeners.forEach((listener) => listener(state));
}

export function getMaintenanceState(): MaintenanceState {
  return state;
}

export function setMaintenanceState(next: Partial<MaintenanceState>) {
  state = {
    ...state,
    ...next,
    message: next.message ?? state.message ?? DEFAULT_MESSAGE,
    checked: next.checked ?? true,
  };
  notify();
}

export function subscribeMaintenance(listener: (nextState: MaintenanceState) => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export async function fetchMaintenanceState(): Promise<MaintenanceState> {
  try {
    const config = getAppConfig();
    const apiBase = config.useMock ? "/api" : config.apiBaseUrl;
    const response = await fetch(`${apiBase}/health`);
    const payload = await response.json().catch(() => null);

    if (payload && typeof payload === "object" && payload.success && payload.data) {
      const maintenance = payload.data.maintenance;
      if (maintenance && typeof maintenance === "object") {
        const enabled = Boolean(maintenance.enabled);
        const message =
          typeof maintenance.message === "string" && maintenance.message.trim()
            ? maintenance.message
            : DEFAULT_MESSAGE;
        setMaintenanceState({ enabled, message });
        return state;
      }
    }
  } catch {
    // 忽略维护探测失败，保持默认状态。
  }

  setMaintenanceState({ enabled: false });
  return state;
}
