// 应用布局与路由入口。
import { Layout, Menu, Button } from "antd";
import { useState } from "react";
import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router-dom";

import { clearToken, getToken } from "./api";
import Dictionary from "./pages/Dictionary";
import Login from "./pages/Login";
import TextsList from "./pages/TextsList";
import Translate from "./pages/Translate";

const { Header, Content, Sider } = Layout;

function AppLayout() {
  const location = useLocation();
  const topSelectedKey = "/home";
  const sideSelectedKey = location.pathname.startsWith("/dictionary")
    ? "/dictionary"
    : "/texts";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <div style={{ color: "#fff", fontWeight: 600 }}>LOTRO 汉化</div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[topSelectedKey]}
          items={[
            { key: "/home", label: <Link to="/texts">工作台</Link> },
          ]}
        />
      </Header>
      <Layout>
        <Sider width={200} style={{ background: "#fff" }}>
          <Menu
            mode="inline"
            selectedKeys={[sideSelectedKey]}
            style={{ height: "100%" }}
            items={[
              { key: "/texts", label: <Link to="/texts">主文本</Link> },
              { key: "/dictionary", label: <Link to="/dictionary">词典</Link> },
            ]}
          />
        </Sider>
        <Content style={{ padding: 24 }}>
          <Routes>
            <Route path="/texts" element={<TextsList />} />
            <Route path="/texts/:id/translate" element={<Translate />} />
            <Route path="/dictionary" element={<Dictionary />} />
            <Route path="*" element={<TextsList />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getToken()));

  const handleLogout = () => {
    clearToken();
    setAuthenticated(false);
  };

  if (!authenticated) {
    return <Login onLogin={() => setAuthenticated(true)} />;
  }

  return (
    <BrowserRouter>
      <div style={{ position: "fixed", top: 12, right: 16, zIndex: 1000 }}>
        <Button onClick={handleLogout}>退出</Button>
      </div>
      <AppLayout />
    </BrowserRouter>
  );
}
