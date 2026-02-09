// 前端入口渲染。
import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, message } from "antd";
import zhCN from "antd/locale/zh_CN";

import App from "./App";
import { loadAppConfig } from "./config";
import { fetchMaintenanceState } from "./maintenance";
import "antd/dist/reset.css";
import "./pro_layout_overrides.css";

const root = ReactDOM.createRoot(document.getElementById("root")!);

const renderApp = () => {
  root.render(
    <React.StrictMode>
      <ConfigProvider locale={zhCN}>
        <App />
      </ConfigProvider>
    </React.StrictMode>
  );
};

void (async () => {
  try {
    await loadAppConfig();
    await fetchMaintenanceState();
    renderApp();
  } catch (error) {
    root.render(
      <React.StrictMode>
        <ConfigProvider locale={zhCN}>
          <div style={{ padding: 24 }}>
            前端配置加载失败，请检查 .env 的 VITE_* 配置
          </div>
        </ConfigProvider>
      </React.StrictMode>
    );
    message.error((error as Error).message || "前端配置加载失败");
  }
})();
