// 维护模式页面。
import { Button, Result, Typography } from "antd";

type MaintenanceProps = {
  message?: string;
};

export default function Maintenance({ message }: MaintenanceProps) {
  const description = message?.trim() || "系统维护中，请稍后再试";

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        background: "linear-gradient(135deg, #f5f7fa 0%, #e4ecf7 100%)",
      }}
    >
      <Result
        status="warning"
        title="系统维护中"
        subTitle={
          <Typography.Paragraph style={{ marginBottom: 0 }}>{description}</Typography.Paragraph>
        }
        extra={
          <Button type="primary" onClick={() => window.location.reload()}>
            刷新重试
          </Button>
        }
      />
    </div>
  );
}
