import type { ProFormInstance } from "@ant-design/pro-form";
import { Button, Space } from "antd";
import type { MutableRefObject, ReactNode } from "react";

import { getToken } from "../../../api";
import { getAppConfig } from "../../../config";
import type { QueryParams } from "../types";

function normalizeString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function normalizeStatus(value: unknown): number | undefined {
  if (value === undefined || value === null || value === "") {
    return undefined;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function normalizeClaimed(value: unknown): string | undefined {
  if (value === undefined || value === null || value === "") {
    return undefined;
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (value === "true" || value === "false") {
    return value;
  }
  return undefined;
}

function normalizeDateTime(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  return value ? value : undefined;
}

function normalizeRange(range: unknown): { updatedFrom?: string; updatedTo?: string } {
  if (!Array.isArray(range)) {
    return {};
  }
  return {
    updatedFrom: normalizeDateTime(range[0]),
    updatedTo: normalizeDateTime(range[1]),
  };
}

export function normalizeQueryParams(raw: Partial<QueryParams> & { uptTime?: [string, string] }): QueryParams {
  const range = normalizeRange(raw.uptTime);
  return {
    fid: normalizeString(raw.fid),
    textId: normalizeString(raw.textId),
    status: normalizeStatus(raw.status),
    sourceKeyword: normalizeString(raw.sourceKeyword),
    translatedKeyword: normalizeString(raw.translatedKeyword),
    updatedFrom: normalizeDateTime(raw.updatedFrom) || range.updatedFrom,
    updatedTo: normalizeDateTime(raw.updatedTo) || range.updatedTo,
    claimer: normalizeString(raw.claimer),
    claimed: normalizeClaimed(raw.claimed),
  };
}

export function hasAnyFilter(params: QueryParams): boolean {
  return Object.values(params).some((value) => value !== undefined && value !== null && value !== "");
}

export function buildDownloadQuery(params: QueryParams): URLSearchParams {
  const query = new URLSearchParams();
  if (params.fid) {
    query.set("fid", params.fid);
  }
  if (params.textId) {
    query.set("textId", params.textId);
  }
  if (params.status !== undefined) {
    query.set("status", String(params.status));
  }
  if (params.sourceKeyword) {
    query.set("sourceKeyword", params.sourceKeyword);
  }
  if (params.translatedKeyword) {
    query.set("translatedKeyword", params.translatedKeyword);
  }
  if (params.updatedFrom) {
    query.set("updatedFrom", params.updatedFrom);
  }
  if (params.updatedTo) {
    query.set("updatedTo", params.updatedTo);
  }
  if (params.claimer) {
    query.set("claimer", params.claimer);
  }
  if (params.claimed !== undefined) {
    query.set("claimed", String(params.claimed));
  }
  return query;
}

export function resolveSearchParams(
  formRef: MutableRefObject<ProFormInstance<QueryParams> | undefined>,
  parentSearch: QueryParams
): QueryParams {
  const formValues = formRef.current?.getFieldsValue?.() || {};
  return normalizeQueryParams({
    ...parentSearch,
    ...(formValues as Partial<QueryParams>),
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

async function downloadByPath(path: string, fallbackName: string): Promise<DownloadFileResult> {
  const config = getAppConfig();
  if (config.useMock) {
    return "mock_unsupported";
  }
  const apiBase = config.apiBaseUrl;
  if (!apiBase) {
    throw new Error("缺少 apiBaseUrl");
  }
  const token = getToken();
  if (!token) {
    throw new Error("未登录或登录已失效");
  }

  const response = await fetch(`${apiBase}${path}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
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
  const blob = await response.blob();
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
  return downloadByPath("/texts/template", "text_template.xlsx");
}

export async function downloadFilteredFile(search: QueryParams): Promise<DownloadFileResult> {
  const query = buildDownloadQuery(search);
  return downloadByPath(`/texts/download?${query.toString()}`, "text_export.xlsx");
}

type SearchActionBarProps = {
  dom: ReactNode[];
  uploading: boolean;
  onDownloadFiltered: () => void;
  onDownloadTemplate: () => void;
  onUpload: () => void;
};

export function SearchActionBar({
  dom,
  uploading,
  onDownloadFiltered,
  onDownloadTemplate,
  onUpload,
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
        <Button onClick={onDownloadFiltered}>导出</Button>
        <Button onClick={onDownloadTemplate}>下载模板</Button>
        <Button type="primary" loading={uploading} onClick={onUpload}>
          上传译文
        </Button>
      </Space>
    </div>
  );
}
