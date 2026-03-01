// 文本编辑页面。
import { Button, Card, Input, Row, Col, Switch, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../../../api";
import { parseStoredListState } from "../storage";
import type { ListStateSnapshot, TextDetailByTextIdResponse } from "../types";

export default function TextEdit() {
  const params = useParams();
  const fid = params.fid || "";
  const textId = Number(params.textId);
  const [detail, setDetail] = useState<TextDetailByTextIdResponse | null>(null);
  const [translated, setTranslated] = useState("");
  const [reason, setReason] = useState("");
  const [markCompleted, setMarkCompleted] = useState(false);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const listState = useMemo(() => {
    const state = location.state as { listState?: ListStateSnapshot } | null;
    return state?.listState || parseStoredListState();
  }, [location.state]);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await apiFetch<TextDetailByTextIdResponse>(
          `/texts/by-textid?fid=${encodeURIComponent(fid)}&textId=${textId}`
        );
        setDetail(response);
        setTranslated(response.text.translatedText || "");
      } catch (error) {
        message.error(getErrorMessage(error, "加载失败"));
      }
    };
    if (fid && Number.isFinite(textId)) {
      void load();
    }
  }, [fid, textId]);

  const handleSave = async () => {
    try {
      if (saving || !detail) {
        return;
      }
      setSaving(true);
      await apiFetch(`/texts/${detail.text.id}/translate`, {
        method: "PUT",
        body: JSON.stringify({ translatedText: translated, reason, isCompleted: markCompleted }),
      });
      message.success("保存成功");
      navigate("/texts", { state: { refresh: true, listState } });
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
      <Typography.Paragraph>
        FID: {detail.text.fid} / TextId: {detail.text.textId} / Part: {detail.text.part}
      </Typography.Paragraph>
      <Row gutter={16}>
        <Col xs={24} sm={24} md={12} lg={12} xl={12} xxl={12} style={{ minWidth: 0 }}>
          <Card title="原文">
            <Input.TextArea
              value={detail.text.sourceText || ""}
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
