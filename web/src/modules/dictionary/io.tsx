import type { ProFormInstance } from "@ant-design/pro-form";
import { Button, Space } from "antd";
import type { MutableRefObject, ReactNode } from "react";

import { getToken, redirectToLogin } from "../../api";
import { getAppConfig } from "../../config";
import type { DictionaryFilters } from "./types";

function normalizeString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

export function normalizeQueryParams(raw: Partial<DictionaryFilters>): DictionaryFilters {
  return {
    termKey: normalizeString(raw.termKey),
    termValue: normalizeString(raw.termValue),
    category: normalizeString(raw.category),
  };
}

export function buildDownloadQuery(params: DictionaryFilters): URLSearchParams {
  const query = new URLSearchParams();
  if (params.termKey) {
    query.set("termKey", params.termKey);
  }
  if (params.termValue) {
    query.set("termValue", params.termValue);
  }
  if (params.category) {
    query.set("category", params.category);
  }
  return query;
}

export function resolveSearchParams(
  formRef: MutableRefObject<ProFormInstance<DictionaryFilters> | undefined>,
  currentSearch: DictionaryFilters
): DictionaryFilters {
  const formValues = formRef.current?.getFieldsValue?.() || {};
  return normalizeQueryParams({
    ...currentSearch,
    ...(formValues as Partial<DictionaryFilters>),
  });
}

function parseContentDispositionFileName(contentDisposition: string | null, fallbackName: string): string {
  if (!contentDisposition) {
    return fallbackName;
  }

  const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (filenameStarMatch?.[1]) {
    try {
      return decodeURIComponent(filenameStarMatch[1]);
    } catch {
      return filenameStarMatch[1];
    }
  }

  const filenameMatch = contentDisposition.match(/filename=\"?([^\";]+)\"?/i);
  if (filenameMatch?.[1]) {
    return filenameMatch[1];
  }

  return fallbackName;
}

export type DownloadFileResult = "downloaded" | "mock_unsupported";

export type DownloadProgressStage = "preparing" | "transferring";

export type DownloadProgressSnapshot = {
  stage: DownloadProgressStage;
  loadedBytes: number;
  totalBytes: number | null;
  percent: number | null;
};

type DownloadProgressHandler = (snapshot: DownloadProgressSnapshot) => void;

type DownloadOptions = {
  onProgress?: DownloadProgressHandler;
};

export function formatDownloadProgressText(baseLabel: string, snapshot: DownloadProgressSnapshot): string {
  if (snapshot.stage === "preparing") {
    return `${baseLabel}生成中...`;
  }
  if (snapshot.percent !== null) {
    return `${baseLabel}传输中 ${snapshot.percent}%`;
  }
  const receivedMb = (snapshot.loadedBytes / (1024 * 1024)).toFixed(1);
  return `${baseLabel}传输中 ${receivedMb}MB`;
}

function parseContentLength(headerValue: string | null): number | null {
  if (!headerValue) {
    return null;
  }
  const parsed = Number(headerValue);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

function calcProgressPercent(loadedBytes: number, totalBytes: number | null): number | null {
  if (!totalBytes || totalBytes <= 0) {
    return null;
  }
  const ratio = (loadedBytes / totalBytes) * 100;
  return Math.floor(Math.max(0, Math.min(100, ratio)));
}

async function downloadByPath(path: string, fallbackName: string, options?: DownloadOptions): Promise<DownloadFileResult> {
  const onProgress = options?.onProgress;
  const config = getAppConfig();
  if (config.useMock) {
    return "mock_unsupported";
  }
  if (!config.apiBaseUrl) {
    throw new Error("缺少 apiBaseUrl");
  }

  const token = getToken();
  if (!token) {
    throw new Error("未登录或登录已失效");
  }

  onProgress?.({
    stage: "preparing",
    loadedBytes: 0,
    totalBytes: null,
    percent: null,
  });

  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      redirectToLogin();
    }
    let errorMessage = "下载失败";
    try {
      const payload = await response.json();
      if (payload && typeof payload.message === "string") {
        errorMessage = payload.message;
      }
    } catch {
      errorMessage = "下载失败";
    }
    throw new Error(errorMessage);
  }

  const fileName = parseContentDispositionFileName(response.headers.get("Content-Disposition"), fallbackName);
  const totalBytes = parseContentLength(response.headers.get("Content-Length"));
  let loadedBytes = 0;
  onProgress?.({
    stage: "transferring",
    loadedBytes,
    totalBytes,
    percent: calcProgressPercent(loadedBytes, totalBytes),
  });

  let blob: Blob;
  if (response.body) {
    const reader = response.body.getReader();
    const chunks: BlobPart[] = [];
    let lastEmitMs = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      if (!value) {
        continue;
      }
      chunks.push(value as BlobPart);
      loadedBytes += value.length;
      const now = Date.now();
      if (now - lastEmitMs >= 120) {
        lastEmitMs = now;
        onProgress?.({
          stage: "transferring",
          loadedBytes,
          totalBytes,
          percent: calcProgressPercent(loadedBytes, totalBytes),
        });
      }
    }
    blob = new Blob(chunks);
  } else {
    blob = await response.blob();
    loadedBytes = blob.size;
  }

  onProgress?.({
    stage: "transferring",
    loadedBytes,
    totalBytes: totalBytes ?? blob.size,
    percent: 100,
  });

  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
  return "downloaded";
}

export async function downloadTemplateFile(): Promise<DownloadFileResult> {
  return downloadByPath("/dictionary/template", "dictionary_template.xlsx");
}

export async function downloadFilteredFile(
  search: DictionaryFilters,
  options?: DownloadOptions
): Promise<DownloadFileResult> {
  const query = buildDownloadQuery(search);
  return downloadByPath(`/dictionary/download?${query.toString()}`, "dictionary_export.xlsx", options);
}

type SearchActionBarProps = {
  dom: ReactNode[];
  downloadingFiltered: boolean;
  filteredDownloadText: string;
  uploading: boolean;
  creating: boolean;
  onDownloadFiltered: () => void;
  onDownloadTemplate: () => void;
  onUpload: () => void;
  onCreate: () => void;
};

export function SearchActionBar({
  dom,
  downloadingFiltered,
  filteredDownloadText,
  uploading,
  creating,
  onDownloadFiltered,
  onDownloadTemplate,
  onUpload,
  onCreate,
}: SearchActionBarProps) {
  return (
    <div
      style={{
        width: "100%",
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        gap: 8,
      }}
    >
      <Space wrap size={8}>
        {dom}
      </Space>
      <Space wrap size={8}>
        <Button loading={downloadingFiltered} onClick={onDownloadFiltered}>
          {filteredDownloadText}
        </Button>
        <Button onClick={onDownloadTemplate}>下载模板</Button>
        <Button loading={uploading} onClick={onUpload}>
          导入
        </Button>
        <Button type="primary" loading={creating} onClick={onCreate}>
          新增
        </Button>
      </Space>
    </div>
  );
}
