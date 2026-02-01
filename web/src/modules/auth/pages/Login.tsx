// 登录页面。
import { Button, Card, Form, Input, Typography, message } from "antd";
import { useState } from "react";

import { apiFetch, getErrorMessage, setToken, setUserName } from "../../../api";

const { Title } = Typography;

interface LoginResponse {
  token: string;
  user: {
    id: number;
    username: string;
    is_guest: boolean;
  };
  roles: string[];
  permissions: string[];
}

interface LoginProps {
  onLogin: () => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    try {
      if (submitting) {
        return;
      }
      setSubmitting(true);
      const values = await form.validateFields();
      const result = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(values),
      });
      setToken(result.token);
      setUserName(result.user.username);
      message.success("登录成功");
      onLogin();
    } catch (error) {
      message.error(getErrorMessage(error, "登录失败"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", padding: 48 }}>
      <Card style={{ width: 360 }}>
        <Title level={3}>登录</Title>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={submitting}>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
}
