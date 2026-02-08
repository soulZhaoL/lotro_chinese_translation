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
    text_id: number;
    part: number;
    source_text: string | null;
    translated_text: string | null;
    status: number;
    edit_count: number;
    updated_at: string;
    created_at: string;
  };
  claims: Array<{ id: number; user_id: number; claimed_at: string }>;
  locks: Array<{ id: number; user_id: number; locked_at: string; expires_at: string; released_at: string | null }>;
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
          `/texts/by-textid?fid=${encodeURIComponent(fid)}&text_id=${textId}`
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
        <Descriptions.Item label="TextId">{detail.text.text_id}</Descriptions.Item>
        <Descriptions.Item label="Part">{detail.text.part}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusMeta[detail.text.status]?.color || "default"}>
            {statusMeta[detail.text.status]?.label || "-"}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="更新时间">{formatDateTime(detail.text.updated_at)}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{formatDateTime(detail.text.created_at)}</Descriptions.Item>
        <Descriptions.Item label="变更次数">{detail.text.edit_count}</Descriptions.Item>
      </Descriptions>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} sm={24} md={12} lg={12} xl={12} xxl={12} style={{ minWidth: 0 }}>
          <Typography.Title level={5}>原文</Typography.Title>
          <Input.TextArea value={detail.text.source_text || ""} rows={24} readOnly style={{ width: "100%" }} />
        </Col>
        <Col xs={24} sm={24} md={12} lg={12} xl={12} xxl={12} style={{ minWidth: 0 }}>
          <Typography.Title level={5}>译文</Typography.Title>
          <Input.TextArea value={detail.text.translated_text || ""} rows={24} readOnly style={{ width: "100%" }} />
        </Col>
      </Row>
    </div>
  );
}
