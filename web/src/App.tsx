// 应用布局与路由入口。
import { BookOutlined, FileTextOutlined } from "@ant-design/icons";
import { PageContainer, ProLayout } from "@ant-design/pro-components";
import { Avatar, Button, Space } from "antd";
import { useState } from "react";
import { BrowserRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { clearToken, getToken, getUserName } from "./api";
import Login from "./modules/auth/pages/Login";
import Dictionary from "./modules/dictionary/pages/Dictionary";
import TextChanges from "./modules/texts/pages/TextChanges";
import TextDetail from "./modules/texts/pages/TextDetail";
import TextEdit from "./modules/texts/pages/TextEdit";
import TextsList from "./modules/texts/pages/TextsList";

const menuItems = [
  {
    path: "/texts",
    name: "文本管理",
    icon: <FileTextOutlined />,
    routes: [
      { path: "/texts/:fid/:textId", name: "文本详情", hideInMenu: true },
      { path: "/texts/:fid/:textId/edit", name: "翻译编辑", hideInMenu: true },
      { path: "/texts/:fid/:textId/changes", name: "更新记录", hideInMenu: true },
    ],
  },
  {
    path: "/dictionary",
    name: "词典管理",
    icon: <BookOutlined />,
  },
];

interface AppLayoutProps {
  onLogout: () => void;
}

function AppLayout({ onLogout }: AppLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const userName = getUserName();
  const pathname = location.pathname;
  const isEditPage = /^\/texts\/[^/]+\/\d+\/edit$/.test(pathname);
  const isChangesPage = /^\/texts\/[^/]+\/\d+\/changes$/.test(pathname);
  const isDetailPage = /^\/texts\/[^/]+\/\d+$/.test(pathname);

  return (
    <ProLayout
      title="LOTRO 汉化平台"
      logo="/icon.ico"
      layout="mix"
      location={{ pathname: location.pathname }}
      route={{ path: "/", routes: menuItems }}
      token={{
        pageContainer: {
          paddingInlinePageContainerContent: 8,
          paddingBlockPageContainerContent: 12,
        },
      }}
      menuItemRender={(item, dom) => (
        <span onClick={() => item.path && navigate(item.path)}>{dom}</span>
      )}
      breadcrumbRender={(routers) => {
        if (isEditPage) {
          return [
            { path: "/texts", breadcrumbName: "文本管理" },
            { path: pathname, breadcrumbName: "翻译编辑" },
          ];
        }
        if (isChangesPage) {
          return [
            { path: "/texts", breadcrumbName: "文本管理" },
            { path: pathname, breadcrumbName: "更新记录" },
          ];
        }
        if (isDetailPage) {
          return [
            { path: "/texts", breadcrumbName: "文本管理" },
            { path: pathname, breadcrumbName: "文本详情" },
          ];
        }
        return routers;
      }}
      rightContentRender={() => (
        <Space size="middle">
          <Avatar src="/avatar.gif" size="small" />
          <span>{userName}</span>
          <Button onClick={onLogout}>退出</Button>
        </Space>
      )}
    >
      <PageContainer>
        <Routes>
          <Route path="/texts" element={<TextsList />} />
          <Route path="/texts/:fid/:textId" element={<TextDetail />} />
          <Route path="/texts/:fid/:textId/edit" element={<TextEdit />} />
          <Route path="/texts/:fid/:textId/changes" element={<TextChanges />} />
          <Route path="/dictionary" element={<Dictionary />} />
          <Route path="*" element={<TextsList />} />
        </Routes>
      </PageContainer>
    </ProLayout>
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
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppLayout onLogout={handleLogout} />
    </BrowserRouter>
  );
}
