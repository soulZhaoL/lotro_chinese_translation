import { Tag } from "antd";
import type { CSSProperties, ReactNode } from "react";

type PrettyTagProps = {
  color?: string;
  children?: ReactNode;
  emptyText?: ReactNode;
  style?: CSSProperties;
};

export default function PrettyTag({ color, children, emptyText = "-", style }: PrettyTagProps) {
  if (children === null || children === undefined || children === "") {
    return <>{emptyText}</>;
  }

  return (
    <Tag
      color={color || "default"}
      style={{
        borderRadius: 999,
        paddingInline: 10,
        fontWeight: 500,
        ...style,
      }}
    >
      {children}
    </Tag>
  );
}
