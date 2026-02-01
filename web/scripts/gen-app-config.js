import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const apiBaseUrl = process.env.APP_API_BASE_URL;
const useMockRaw = process.env.APP_USE_MOCK;

if (useMockRaw === undefined) {
  throw new Error("缺少环境变量: APP_USE_MOCK");
}

const useMock = useMockRaw === "true";

if (!useMock && !apiBaseUrl) {
  throw new Error("APP_API_BASE_URL 为空，且 APP_USE_MOCK=false");
}

const config = {
  apiBaseUrl: apiBaseUrl || "",
  useMock,
};

const outputPath = path.join(__dirname, "..", "public", "app-config.json");
fs.writeFileSync(outputPath, JSON.stringify(config, null, 2));
console.log("[INFO] 已生成 app-config.json:", config);
