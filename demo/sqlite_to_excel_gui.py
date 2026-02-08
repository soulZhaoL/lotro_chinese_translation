import os
import sqlite3
import threading
import traceback
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DEFAULT_MAX_LEN = 25000
SPLIT_DELIMITER = "|||"

DEFAULT_SPLIT_PART_COL = "split_part"
DEFAULT_FID_COL = "fid"


def _split_to_new_rows_with_part(
    df: pd.DataFrame,
    col: str,
    fid_col: str = DEFAULT_FID_COL,
    part_col: str = DEFAULT_SPLIT_PART_COL,
    max_len: int = DEFAULT_MAX_LEN,
) -> pd.DataFrame:
    """
    在拆分 col 的同时，新增/填充 part_col：
    - 若该行未拆分：part_col = 0
    - 若该行拆分成 N 段：对应新行 part_col = 1..N
    以 fid_col 作为“同一fid”的依据；若不存在 fid_col，则退化为按原始行序号作为键。
    """
    if col not in df.columns:
        # 仍然确保 part_col 存在
        if part_col not in df.columns:
            df = df.copy()
            df[part_col] = 0
        return df

    cols = list(df.columns)
    if part_col not in cols:
        cols.append(part_col)

    has_fid = fid_col in df.columns
    out_rows = []

    for idx, row in df.iterrows():
        val = row[col]

        # 用于“同一 fid”的标识（如果没有 fid 列就用 idx）
        _key = row[fid_col] if has_fid else idx

        # 空值/NaN：不拆分
        if pd.isna(val):
            r = row.to_dict()
            r[part_col] = 0
            out_rows.append(r)
            continue

        s = str(val)

        # 不超长：不拆分
        if len(s) <= max_len:
            r = row.to_dict()
            r[part_col] = 0
            out_rows.append(r)
            continue

        # 需要拆分：按分隔符切，再按 max_len 聚合成块
        segments = s.split(SPLIT_DELIMITER)

        chunks = []
        current_chunk = []
        current_length = 0

        for segment in segments:
            seg_len_with_delim = len(segment) + len(SPLIT_DELIMITER)

            if current_chunk:
                if current_length + seg_len_with_delim <= max_len:
                    current_chunk.append(segment)
                    current_length += seg_len_with_delim
                else:
                    chunks.append(SPLIT_DELIMITER.join(current_chunk) + SPLIT_DELIMITER)
                    current_chunk = [segment]
                    current_length = seg_len_with_delim
            else:
                current_chunk = [segment]
                current_length = seg_len_with_delim

        if current_chunk:
            if s.endswith(SPLIT_DELIMITER):
                chunks.append(SPLIT_DELIMITER.join(current_chunk) + SPLIT_DELIMITER)
            else:
                chunks.append(SPLIT_DELIMITER.join(current_chunk))

        base = row.to_dict()
        # 拆分后的行：part_col = 1..N
        for i, ch in enumerate(chunks, start=1):
            r = dict(base)
            r[col] = ch
            r[part_col] = i
            out_rows.append(r)

    return pd.DataFrame(out_rows, columns=cols)


def export_sqlite_to_excel(
    db_path: str,
    output_dir: str,
    mode: str = "single",
    single_output_file: str | None = None,
    split_columns: tuple = ("text_data",),
    max_cell_len: int = DEFAULT_MAX_LEN,
    fid_col: str = DEFAULT_FID_COL,
    split_part_col: str = DEFAULT_SPLIT_PART_COL,
    log_fn=None,
):
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"找不到数据库文件：{db_path}")

    os.makedirs(output_dir, exist_ok=True)

    if single_output_file is None:
        base = os.path.splitext(os.path.basename(db_path))[0]
        single_output_file = os.path.join(output_dir, f"{base}_export.xlsx")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()

    if not tables:
        conn.close()
        raise ValueError("数据库中没有任何表。")

    log(f"检测到的表：{tables}")
    log(f"拆分分隔符：{SPLIT_DELIMITER}")
    log(f"单元格最长：{max_cell_len}")
    log(f"fid 列：{fid_col}（若表不存在则退化为行号）")
    log(f"拆分标记列：{split_part_col}")

    def _load_and_process_table(table: str) -> pd.DataFrame:
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)

        # 先确保 split_part_col 存在（避免没拆分时列缺失）
        if split_part_col not in df.columns:
            df[split_part_col] = 0

        # 先拆分（拆分函数里会把 NaN 保留为 part=0 的行）
        for col in split_columns:
            df = _split_to_new_rows_with_part(
                df,
                col=col,
                fid_col=fid_col,
                part_col=split_part_col,
                max_len=max_cell_len,
            )

        # 需求：如果某个 fid 的 text_data 为空，则不输出这行
        # 解释：仅当表里存在 fid_col 且存在 text_data 列时过滤；否则不处理
        target_col = "text_data"
        if fid_col in df.columns and target_col in df.columns:
            # 认为“空”的标准：NaN/None 或 转成字符串后 strip 为空
            mask_empty = df[target_col].isna() | (df[target_col].astype(str).str.strip() == "")
            df = df.loc[~mask_empty].copy()

        return df

    try:
        if mode == "multiple":
            for table in tables:
                log(f"处理表：{table}")
                df = _load_and_process_table(table)
                safe_table_name = table.replace("/", "_").replace("\\", "_").replace(":", "_")
                output_file = os.path.join(output_dir, f"{safe_table_name}.xlsx")
                df.to_excel(output_file, index=False)
                log(f"已导出：{output_file}")

        elif mode == "single":
            log(f"导出为单文件：{single_output_file}")
            with pd.ExcelWriter(single_output_file, engine="openpyxl") as writer:
                for table in tables:
                    log(f"处理表：{table}")
                    df = _load_and_process_table(table)
                    sheet_name = table[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    log(f"已写入 sheet：{sheet_name}")
            log("单文件导出完成。")

        else:
            raise ValueError("mode 只能为 'multiple' 或 'single'")
    finally:
        conn.close()
        log("完成并关闭数据库连接。")

    return single_output_file


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SQLite 导出 Excel（自动拆分超长文本）")
        self.geometry("820x600")
        self.minsize(760, 540)

        self.db_path_var = tk.StringVar()
        self.out_dir_var = tk.StringVar()
        self.out_dir_var.set(os.path.abspath("./out"))

        self.split_cols_var = tk.StringVar(value="text_data")

        # 新增：可调最大长度
        self.max_len_var = tk.StringVar(value=str(DEFAULT_MAX_LEN))

        # 新增：fid 列名可配（默认 fid）
        self.fid_col_var = tk.StringVar(value=DEFAULT_FID_COL)

        # 新增：拆分标记列名可配
        self.split_part_col_var = tk.StringVar(value=DEFAULT_SPLIT_PART_COL)

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, **pad)

        # DB 选择
        row1 = ttk.Frame(frm)
        row1.pack(fill="x", **pad)
        ttk.Label(row1, text="SQLite 数据库文件（.db/.sqlite）:").pack(anchor="w")
        r1b = ttk.Frame(row1)
        r1b.pack(fill="x", pady=6)
        ttk.Entry(r1b, textvariable=self.db_path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(r1b, text="选择 DB 文件", command=self.choose_db).pack(side="left", padx=8)

        # 输出目录选择
        row2 = ttk.Frame(frm)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="输出目录:").pack(anchor="w")
        r2b = ttk.Frame(row2)
        r2b.pack(fill="x", pady=6)
        ttk.Entry(r2b, textvariable=self.out_dir_var).pack(side="left", fill="x", expand=True)
        ttk.Button(r2b, text="选择输出目录", command=self.choose_out_dir).pack(side="left", padx=8)

        # 拆分列
        row3 = ttk.Frame(frm)
        row3.pack(fill="x", **pad)
        ttk.Label(row3, text="需要拆分的列名（逗号分隔，例如 text_data,content）:").pack(anchor="w")
        ttk.Entry(row3, textvariable=self.split_cols_var).pack(fill="x", pady=6)

        # 新增：最大长度、fid列、part列
        row4 = ttk.Frame(frm)
        row4.pack(fill="x", **pad)

        ttk.Label(row4, text="单元格最大长度:").grid(row=0, column=0, sticky="w")
        ttk.Entry(row4, textvariable=self.max_len_var, width=12).grid(row=0, column=1, sticky="w", padx=(8, 18))

        ttk.Label(row4, text="fid 列名:").grid(row=0, column=2, sticky="w")
        ttk.Entry(row4, textvariable=self.fid_col_var, width=18).grid(row=0, column=3, sticky="w", padx=(8, 18))

        ttk.Label(row4, text="拆分序号列名:").grid(row=0, column=4, sticky="w")
        ttk.Entry(row4, textvariable=self.split_part_col_var, width=18).grid(row=0, column=5, sticky="w", padx=(8, 0))

        row4.grid_columnconfigure(6, weight=1)

        # 固定参数提示
        row5 = ttk.Frame(frm)
        row5.pack(fill="x", **pad)
        ttk.Label(
            row5,
            text=f"固定规则：分隔符 = '{SPLIT_DELIMITER}'；导出模式 = 单文件多 sheet；拆分后新增列：split_part(可改名)",
            foreground="#444"
        ).pack(anchor="w")

        # 开始按钮
        row6 = ttk.Frame(frm)
        row6.pack(fill="x", **pad)
        self.run_btn = ttk.Button(row6, text="开始导出", command=self.on_run)
        self.run_btn.pack(side="left")
        ttk.Button(row6, text="打开输出目录", command=self.open_out_dir).pack(side="left", padx=8)

        # 日志
        row7 = ttk.Frame(frm)
        row7.pack(fill="both", expand=True, **pad)
        ttk.Label(row7, text="日志:").pack(anchor="w")
        self.log_text = tk.Text(row7, height=16, wrap="word")
        self.log_text.pack(fill="both", expand=True, pady=6)
        self.log_text.configure(state="disabled")

    def log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def choose_db(self):
        path = filedialog.askopenfilename(
            title="选择 SQLite 数据库文件",
            filetypes=[
                ("SQLite DB", "*.db *.sqlite *.sqlite3"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.db_path_var.set(path)

    def choose_out_dir(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.out_dir_var.set(path)

    def open_out_dir(self):
        out_dir = self.out_dir_var.get().strip()
        if not out_dir:
            messagebox.showwarning("提示", "请先选择输出目录。")
            return
        os.makedirs(out_dir, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(out_dir)  # type: ignore[attr-defined]
            elif os.name == "posix":
                import subprocess
                if "darwin" in os.sys.platform:
                    subprocess.Popen(["open", out_dir])
                else:
                    subprocess.Popen(["xdg-open", out_dir])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录：{e}")

    def on_run(self):
        db_path = self.db_path_var.get().strip()
        out_dir = self.out_dir_var.get().strip()
        split_cols_raw = self.split_cols_var.get().strip()
        fid_col = self.fid_col_var.get().strip() or DEFAULT_FID_COL
        split_part_col = self.split_part_col_var.get().strip() or DEFAULT_SPLIT_PART_COL

        if not db_path:
            messagebox.showwarning("提示", "请选择 DB 文件。")
            return
        if not out_dir:
            messagebox.showwarning("提示", "请选择输出目录。")
            return

        # 解析 max_len
        try:
            max_len = int(self.max_len_var.get().strip())
            if max_len <= 0:
                raise ValueError()
        except Exception:
            messagebox.showwarning("提示", "单元格最大长度必须是正整数。")
            return

        split_columns = tuple([c.strip() for c in split_cols_raw.split(",") if c.strip()]) or ("text_data",)

        self.run_btn.configure(state="disabled")
        self.log("开始导出...")
        self.log(f"DB: {db_path}")
        self.log(f"输出目录: {out_dir}")
        self.log(f"拆分列: {split_columns}")
        self.log(f"单元格最大长度: {max_len}")
        self.log(f"fid 列: {fid_col}")
        self.log(f"拆分序号列: {split_part_col}")

        def worker():
            try:
                xlsx = export_sqlite_to_excel(
                    db_path=db_path,
                    output_dir=out_dir,
                    mode="single",
                    split_columns=split_columns,
                    max_cell_len=max_len,
                    fid_col=fid_col,
                    split_part_col=split_part_col,
                    log_fn=self._threadsafe_log,
                )
                self._threadsafe_log(f"完成！输出文件：{xlsx}")
                self._threadsafe_done(ok=True)
            except Exception:
                self._threadsafe_log("发生错误：")
                self._threadsafe_log(traceback.format_exc())
                self._threadsafe_done(ok=False)

        threading.Thread(target=worker, daemon=True).start()

    def _threadsafe_log(self, msg: str):
        self.after(0, lambda: self.log(msg))

    def _threadsafe_done(self, ok: bool):
        def done():
            self.run_btn.configure(state="normal")
            if ok:
                messagebox.showinfo("完成", "导出完成。")
            else:
                messagebox.showerror("失败", "导出失败，请查看日志。")
        self.after(0, done)


if __name__ == "__main__":
    # 依赖：pandas、openpyxl
    App().mainloop()
