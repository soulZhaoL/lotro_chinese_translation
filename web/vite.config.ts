// Vite 构建配置。
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

type MaintenanceConfig = {
  enabled: boolean;
  message: string;
  allowPaths: string[];
};

function stripInlineComment(raw: string): string {
  let inSingleQuote = false;
  let inDoubleQuote = false;
  for (let idx = 0; idx < raw.length; idx += 1) {
    const ch = raw[idx];
    if (ch === "'" && !inDoubleQuote) {
      inSingleQuote = !inSingleQuote;
      continue;
    }
    if (ch === '"' && !inSingleQuote) {
      inDoubleQuote = !inDoubleQuote;
      continue;
    }
    if (!inSingleQuote && !inDoubleQuote && ch === "#") {
      return raw.slice(0, idx).trimEnd();
    }
  }
  return raw.trimEnd();
}

function parseYamlBool(value: string, field: string): boolean {
  const normalized = value.trim().toLowerCase();
  if (normalized === "true" || normalized === "yes" || normalized === "y" || normalized === "1") {
    return true;
  }
  if (normalized === "false" || normalized === "no" || normalized === "n" || normalized === "0") {
    return false;
  }
  throw new Error(`lotro.yaml 解析失败: ${field} 期望 bool`);
}

function parseYamlString(rawValue: string, field: string): string {
  const value = stripInlineComment(rawValue).trim();
  if (!value) {
    throw new Error(`lotro.yaml 解析失败: ${field} 不能为空`);
  }
  const quote = value[0];
  if (quote !== '"' && quote !== "'") {
    return value;
  }
  if (value.length < 2 || value[value.length - 1] !== quote) {
    throw new Error(`lotro.yaml 解析失败: ${field} 引号不闭合`);
  }
  const inner = value.slice(1, -1);
  if (quote === "'") {
    return inner.replaceAll("''", "'");
  }
  return inner.replaceAll('\\"', '"').replaceAll("\\\\", "\\");
}

function parseMaintenanceFromLotroYaml(content: string): MaintenanceConfig {
  const lines = content.split(/\r?\n/);
  const startIndex = lines.findIndex((line) => line.trim() === "maintenance:");
  if (startIndex < 0) {
    throw new Error("lotro.yaml 解析失败: 缺少 maintenance 分组");
  }

  let enabled: boolean | null = null;
  let message: string | null = null;
  let allowPaths: string[] | null = null;

  let idx = startIndex + 1;
  while (idx < lines.length) {
    const line = lines[idx];
    idx += 1;
    if (!line.trim()) {
      continue;
    }
    if (/^[^\s].*:\s*$/.test(line)) {
      break;
    }
    if (!/^\s+/.test(line)) {
      continue;
    }

    const trimmed = line.trim();
    if (trimmed.startsWith("enabled:")) {
      enabled = parseYamlBool(trimmed.slice("enabled:".length), "maintenance.enabled");
      continue;
    }
    if (trimmed.startsWith("message:")) {
      message = parseYamlString(trimmed.slice("message:".length), "maintenance.message");
      continue;
    }
    if (trimmed === "allow_paths:" || trimmed.startsWith("allow_paths:")) {
      if (trimmed !== "allow_paths:") {
        throw new Error("lotro.yaml 解析失败: maintenance.allow_paths 必须为 YAML 列表");
      }
      allowPaths = [];
      while (idx < lines.length) {
        const itemLine = lines[idx];
        if (!itemLine.trim()) {
          idx += 1;
          continue;
        }
        if (/^[^\s].*:\s*$/.test(itemLine)) {
          break;
        }
        if (!/^\s+-\s+/.test(itemLine)) {
          break;
        }
        const rawItemValue = itemLine.replace(/^\s+-\s+/, "");
        allowPaths.push(parseYamlString(rawItemValue, "maintenance.allow_paths[]"));
        idx += 1;
      }
      continue;
    }
  }

  if (enabled === null) {
    throw new Error("lotro.yaml 解析失败: 缺少 maintenance.enabled");
  }
  if (message === null) {
    throw new Error("lotro.yaml 解析失败: 缺少 maintenance.message");
  }
  if (allowPaths === null) {
    throw new Error("lotro.yaml 解析失败: 缺少 maintenance.allow_paths");
  }

  return { enabled, message, allowPaths };
}

function buildMaintenanceMockMiddleware(configPath: string) {
  let cached: MaintenanceConfig | null = null;
  let cachedMtimeMs: number | null = null;

  const loadConfig = (): MaintenanceConfig => {
    const stat = fs.statSync(configPath);
    if (cached && cachedMtimeMs === stat.mtimeMs) {
      return cached;
    }
    const content = fs.readFileSync(configPath, "utf-8");
    cached = parseMaintenanceFromLotroYaml(content);
    cachedMtimeMs = stat.mtimeMs;
    return cached;
  };

  // 启动即校验，避免“假装运行”。
  loadConfig();

  const isAllowed = (requestPath: string, allowPaths: string[]) => {
    for (const item of allowPaths) {
      if (requestPath === item || requestPath.startsWith(`${item}/`)) {
        return true;
      }
    }
    return false;
  };

  const stripMockPrefix = (requestPath: string) => {
    if (requestPath === "/api") {
      return "/";
    }
    if (requestPath.startsWith("/api/")) {
      return requestPath.slice("/api".length);
    }
    return requestPath;
  };

  return (req: any, res: any, next: any) => {
    const url = typeof req.url === "string" ? req.url : "";
    const pathname = url.split("?")[0] || "/";
    if (!pathname.startsWith("/api")) {
      next();
      return;
    }

    const state = loadConfig();
    const upstreamPath = stripMockPrefix(pathname);

    if (req.method === "GET" && upstreamPath === "/health") {
      res.statusCode = 200;
      res.setHeader("Content-Type", "application/json; charset=utf-8");
      res.end(
        JSON.stringify({
          success: true,
          statusCode: 200,
          code: "0000",
          message: "操作成功",
          data: { status: "ok", maintenance: { enabled: state.enabled, message: state.message } },
        }),
      );
      return;
    }

    if (state.enabled && !isAllowed(upstreamPath, state.allowPaths)) {
      res.statusCode = 503;
      res.setHeader("Content-Type", "application/json; charset=utf-8");
      res.end(
        JSON.stringify({
          success: false,
          statusCode: 503,
          code: "MAINTENANCE",
          message: state.message,
          data: { maintenance: { enabled: true, message: state.message } },
        }),
      );
      return;
    }

    next();
  };
}

type MockHandler = {
  url: string | RegExp;
  method?: string;
  statusCode?: number;
  timeout?: number;
  response?: any;
  rawResponse?: any;
};

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseQuery(url: string): Record<string, string> {
  const parsed = new URL(url, "http://localhost");
  const result: Record<string, string> = {};
  for (const [key, value] of parsed.searchParams.entries()) {
    result[key] = value;
  }
  return result;
}

async function readJsonBody(req: any): Promise<any> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  if (chunks.length === 0) {
    return {};
  }
  const text = Buffer.concat(chunks).toString("utf-8").trim();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

function isMethodMatch(handlerMethod: unknown, reqMethod: unknown): boolean {
  const req = typeof reqMethod === "string" ? reqMethod.toUpperCase() : "GET";
  if (!handlerMethod) {
    return true;
  }
  if (typeof handlerMethod !== "string") {
    return false;
  }
  return handlerMethod.toUpperCase() === req;
}

function isUrlMatch(handlerUrl: unknown, pathname: string): handlerUrl is string | RegExp {
  if (typeof handlerUrl === "string") {
    return handlerUrl === pathname;
  }
  if (handlerUrl instanceof RegExp) {
    return handlerUrl.test(pathname);
  }
  return false;
}

function buildLocalMockPlugin(mockDir: string) {
  let cachedHandlers: MockHandler[] | null = null;
  let loading: Promise<MockHandler[]> | null = null;

  const listMockEntryFiles = () => {
    const entries = fs.readdirSync(mockDir, { withFileTypes: true });
    return entries
      .filter((entry) => entry.isFile() && entry.name.endsWith(".ts") && entry.name !== "rules.ts")
      .map((entry) => path.join(mockDir, entry.name));
  };

  return {
    name: "lotro:local-mock",
    configureServer(server: any) {
      const reload = () => {
        cachedHandlers = null;
        loading = null;
      };

      server.watcher.on("change", (file: string) => {
        if (file.startsWith(mockDir)) {
          reload();
        }
      });
      server.watcher.on("add", (file: string) => {
        if (file.startsWith(mockDir)) {
          reload();
        }
      });
      server.watcher.on("unlink", (file: string) => {
        if (file.startsWith(mockDir)) {
          reload();
        }
      });

      const loadHandlers = async (): Promise<MockHandler[]> => {
        if (cachedHandlers) {
          return cachedHandlers;
        }
        if (!loading) {
          loading = (async () => {
            const files = listMockEntryFiles();
            const all: MockHandler[] = [];
            for (const file of files) {
              const mod = await server.ssrLoadModule(file);
              const handlers = mod?.default;
              if (!handlers) {
                continue;
              }
              if (!Array.isArray(handlers)) {
                throw new Error(`Mock 文件默认导出必须为数组: ${file}`);
              }
              for (const handler of handlers) {
                all.push(handler as MockHandler);
              }
            }
            cachedHandlers = all;
            return all;
          })();
        }
        return loading;
      };

      server.middlewares.use(async (req: any, res: any, next: any) => {
        const url = typeof req.url === "string" ? req.url : "";
        const pathname = url.split("?")[0] || "/";
        if (!pathname.startsWith("/api")) {
          next();
          return;
        }

        const handlers = await loadHandlers();
        const match = handlers.find(
          (handler) => isMethodMatch(handler.method, req.method) && isUrlMatch(handler.url, pathname),
        );
        if (!match) {
          next();
          return;
        }

        if (typeof match.timeout === "number" && match.timeout > 0) {
          await sleep(match.timeout);
        }

        if (typeof match.rawResponse === "function") {
          await match.rawResponse(req, res);
          return;
        }

        const body = (req.method || "GET").toUpperCase() === "GET" ? {} : await readJsonBody(req);
        const query = parseQuery(url);

        const ctx = { url, body, query, headers: req.headers || {} };
        const responseValue =
          typeof match.response === "function" ? await match.response(ctx) : (match.response ?? {});

        res.statusCode = match.statusCode || 200;
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(JSON.stringify(responseValue));
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const isDev = mode === "development";
  const useMock = isDev && env.VITE_USE_MOCK === "true";

  const plugins = [react()];
  if (useMock) {
    const webDir = path.dirname(fileURLToPath(import.meta.url));
    const configPath = path.resolve(webDir, "..", "config", "lotro.yaml");
    const mockDir = path.resolve(webDir, "mock");

    plugins.push({
      name: "lotro:maintenance-mock",
      configureServer(server) {
        server.middlewares.use(buildMaintenanceMockMiddleware(configPath));
      },
    });

    plugins.push(buildLocalMockPlugin(mockDir));
  }

  return {
    plugins,
    server: {
      port: 5173,
    },
  };
});
