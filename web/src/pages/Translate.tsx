// 翻译页与锁定操作。
import { Button, Card, Divider, Input, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { apiFetch } from "../api";

interface TextDetail {
  text: {
    id: number;
    fid: string;
    part: string;
    source_text: string;
    translated_text: string | null;
    status: string;
  };
  claims: Array<{ id: number; user_id: number; claimed_at: string }>;
  locks: Array<{ id: number; user_id: number; locked_at: string; expires_at: string; released_at: string | null }>;
}

export default function Translate() {
  const params = useParams();
  const textId = Number(params.id);
  const [detail, setDetail] = useState<TextDetail | null>(null);
  const [lockId, setLockId] = useState<number | null>(null);
  const [translated, setTranslated] = useState("");

  useEffect(() => {
    const load = async () => {
      const response = await apiFetch<TextDetail>(`/texts/${textId}`);
      setDetail(response);
      setTranslated(response.text.translated_text || "");
    };
    void load();
  }, [textId]);

  useEffect(() => {
    const lock = async () => {
      try {
        const response = await apiFetch<{ lock_id: number }>("/locks", {
          method: "POST",
          body: JSON.stringify({ text_id: textId }),
        });
        setLockId(response.lock_id);
      } catch (error) {
        message.error((error as Error).message);
      }
    };
    if (Number.isFinite(textId)) {
      void lock();
    }
  }, [textId]);

  const release = async () => {
    if (!lockId) {
      message.warning("当前没有可释放的锁");
      return;
    }
    await apiFetch(`/locks/${lockId}`, { method: "DELETE" });
    setLockId(null);
    message.success("锁定已释放");
  };

  if (!detail) {
    return <Typography.Text>加载中...</Typography.Text>;
  }

  return (
    <div>
      <Typography.Title level={4}>翻译</Typography.Title>
      <Typography.Paragraph>FID: {detail.text.fid} / Part: {detail.text.part}</Typography.Paragraph>
      <Button onClick={release} disabled={!lockId}>
        释放锁定
      </Button>
      <Divider />
      <Card title="原文" style={{ marginBottom: 16 }}>
        <Typography.Paragraph>{detail.text.source_text}</Typography.Paragraph>
      </Card>
      <Card title="译文">
        <Input.TextArea value={translated} onChange={(event) => setTranslated(event.target.value)} rows={6} />
      </Card>
    </div>
  );
}
