// 文本详情页面。
import { Descriptions, Input, Row, Col, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../../../api";
import { formatDateTime } from "../../../utils/datetime";

interface TextDetailResponse {
  text: {
    id: number;
    fid: string;
    textId: number;
    part: number;
    sourceText: string | null;
    translatedText: string | null;
    status: number;
    editCount: number;
    uptTime: string;
    crtTime: string;
  };
  claims: Array<{ id: number; userId: number; claimedAt: string }>;
  locks: Array<{ id: number; userId: number; lockedAt: string; expiresAt: string; releasedAt: string | null }>;
}

const statusMeta: Record<number, { label: string; color: string }> = {
  1: { label: "新增", color: "default" },
  2: { label: "修改", color: "processing" },
  3: { label: "已完成", color: "success" },
};

export default function TextDetail() {
  const params = useParams();
  const fid = params.fid || "";
  const textId = Number(params.textId);
  const [detail, setDetail] = useState<TextDetailResponse | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await apiFetch<TextDetailResponse>(
          `/texts/by-textid?fid=${encodeURIComponent(fid)}&textId=${textId}`
        );
        setDetail(response);
      } catch (error) {
        message.error(getErrorMessage(error, "加载失败"));
      }
    };
    if (fid && Number.isFinite(textId)) {
      void load();
    }
  }, [fid, textId]);

  if (!detail) {
    return <Typography.Text>加载中...</Typography.Text>;
  }

  return (
    <div>
      <Descriptions bordered size="small" column={{ xs: 1, sm: 2, md: 2, lg: 4, xl: 4, xxl: 4 }}>
        <Descriptions.Item label="FID">{detail.text.fid}</Descriptions.Item>
        <Descriptions.Item label="TextId">{detail.text.textId}</Descriptions.Item>
        <Descriptions.Item label="Part">{detail.text.part}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusMeta[detail.text.status]?.color || "default"}>
            {statusMeta[detail.text.status]?.label || "-"}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="更新时间">{formatDateTime(detail.text.uptTime)}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{formatDateTime(detail.text.crtTime)}</Descriptions.Item>
        <Descriptions.Item label="变更次数">{detail.text.editCount}</Descriptions.Item>
      </Descriptions>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} sm={24} md={12} lg={12} xl={12} xxl={12} style={{ minWidth: 0 }}>
          <Typography.Title level={5}>原文</Typography.Title>
          <Input.TextArea value={detail.text.sourceText || ""} rows={24} readOnly style={{ width: "100%" }} />
        </Col>
        <Col xs={24} sm={24} md={12} lg={12} xl={12} xxl={12} style={{ minWidth: 0 }}>
          <Typography.Title level={5}>译文</Typography.Title>
          <Input.TextArea value={detail.text.translatedText || ""} rows={24} readOnly style={{ width: "100%" }} />
        </Col>
      </Row>
    </div>
  );
}
