// 翻译页与锁定操作。
import { Button, Card, Divider, Input, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../api";

interface TextDetail {
  text: {
    id: number;
    fid: string;
    part: string;
    source_text: string | null;
    translated_text: string | null;
    status: number;
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
  const [locking, setLocking] = useState(false);
  const [releasing, setReleasing] = useState(false);

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
        setLocking(true);
        const response = await apiFetch<{ lock_id: number }>("/locks", {
          method: "POST",
          body: JSON.stringify({ text_id: textId }),
        });
        setLockId(response.lock_id);
      } catch (error) {
        message.error(getErrorMessage(error, "锁定失败"));
      } finally {
        setLocking(false);
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
    try {
      setReleasing(true);
      await apiFetch(`/locks/${lockId}`, { method: "DELETE" });
      setLockId(null);
      message.success("锁定已释放");
    } catch (error) {
      message.error(getErrorMessage(error, "释放失败"));
    } finally {
      setReleasing(false);
    }
  };

  if (!detail) {
    return <Typography.Text>加载中...</Typography.Text>;
  }

  return (
    <div>
      <Typography.Title level={4}>翻译</Typography.Title>
      <Typography.Paragraph>FID: {detail.text.fid} / Part: {detail.text.part}</Typography.Paragraph>
      <Button onClick={release} disabled={!lockId || locking} loading={releasing}>
        释放锁定
      </Button>
      <Divider />
      <Card title="原文" style={{ marginBottom: 16 }}>
        <Typography.Paragraph>{detail.text.source_text || "-"}</Typography.Paragraph>
      </Card>
      <Card title="译文">
        <Input.TextArea value={translated} onChange={(event) => setTranslated(event.target.value)} rows={6} />
      </Card>
    </div>
  );
}
