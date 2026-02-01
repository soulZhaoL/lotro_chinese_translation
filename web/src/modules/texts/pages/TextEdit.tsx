// 文本编辑页面。
import { Button, Card, Input, Row, Col, Switch, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../../../api";

interface TextDetailResponse {
  text: {
    id: number;
    fid: string;
    part: string;
    source_text: string | null;
    translated_text: string | null;
    status: number;
  };
}

export default function TextEdit() {
  const params = useParams();
  const textId = Number(params.id);
  const [detail, setDetail] = useState<TextDetailResponse | null>(null);
  const [translated, setTranslated] = useState("");
  const [reason, setReason] = useState("");
  const [markCompleted, setMarkCompleted] = useState(false);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const load = async () => {
      try {
        const response = await apiFetch<TextDetailResponse>(`/texts/${textId}`);
        setDetail(response);
        setTranslated(response.text.translated_text || "");
      } catch (error) {
        message.error(getErrorMessage(error, "加载失败"));
      }
    };
    if (Number.isFinite(textId)) {
      void load();
    }
  }, [textId]);

  const handleSave = async () => {
    try {
      if (saving) {
        return;
      }
      setSaving(true);
      await apiFetch(`/texts/${textId}/translate`, {
        method: "PUT",
        body: JSON.stringify({ translated_text: translated, reason, is_completed: markCompleted }),
      });
      message.success("保存成功");
      navigate("/texts", { state: { refresh: true } });
    } catch (error) {
      message.error(getErrorMessage(error, "保存失败"));
    } finally {
      setSaving(false);
    }
  };

  if (!detail) {
    return <Typography.Text>加载中...</Typography.Text>;
  }

  return (
    <div>
      <Row gutter={16}>
        <Col xs={24} sm={24} md={12} lg={12} xl={12} xxl={12} style={{ minWidth: 0 }}>
          <Card title="原文">
            <Input.TextArea
              value={detail.text.source_text || ""}
              rows={24}
              readOnly
              style={{ width: "100%" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={24} md={12} lg={12} xl={12} xxl={12} style={{ minWidth: 0 }}>
          <Card title="译文">
            <Input.TextArea
              value={translated}
              onChange={(event) => setTranslated(event.target.value)}
              rows={24}
              style={{ width: "100%" }}
            />
            <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <span>是否已完成</span>
              <Switch checked={markCompleted} onChange={setMarkCompleted} />
            </div>
            <Input
              style={{ marginTop: 12 }}
              placeholder="更新原因（可选）"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
            <Button type="primary" style={{ marginTop: 12 }} onClick={handleSave} loading={saving}>
              保存
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
