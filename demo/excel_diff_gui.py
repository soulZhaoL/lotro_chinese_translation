import os
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd


# ----------------------------
# 读取与规范化
# ----------------------------
def read_excel_keep_str(path: str, sheet_name=None) -> pd.DataFrame:
    """
    读取 Excel 并确保返回 DataFrame。
    - sheet_name 为 None 时：默认取第一张 sheet
    - 如果 pandas 返回 dict（读到了多张）：取第一张
    """
    x = pd.read_excel(path, sheet_name=sheet_name, dtype=str)

    if isinstance(x, dict):
        if not x:
            raise ValueError("Excel里没有可读取的sheet")
        first_name = next(iter(x.keys()))
        df = x[first_name]
    else:
        df = x

    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    return df


def normalize_series(s: pd.Series) -> pd.Series:
    s = s.astype("string")
    s = s.str.strip()
    s = s.replace({"": pd.NA})
    return s


def normalize_split_part(s: pd.Series) -> pd.Series:
    """
    split_part 规范化：
    - 读入为字符串后 strip
    - 如果是 "1.0" 这种来自Excel的数字字符串，尽量转成 "1"
    - 空 -> NA
    """
    s = normalize_series(s)

    def _fix(x):
        if x is pd.NA or x is None:
            return pd.NA
        t = str(x).strip()
        if t == "":
            return pd.NA
        if t.endswith(".0") and t.replace(".", "", 1).isdigit():
            t2 = t[:-2]
            if t2.isdigit():
                return t2
        return t

    return s.map(_fix).astype("string")


# ----------------------------
# 核心比较逻辑：按 (fid, split_part) 为唯一键
# 输出：单sheet：fid, split_part, change_type, old_text_data, new_text_data
# ----------------------------
def compare_excels_triple(
    old_path,
    new_path,
    out_path,
    old_sheet=None,
    new_sheet=None,
    progress_cb=None,
    log_cb=None,
):
    def log(msg):
        if log_cb:
            log_cb(msg)

    def progress(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    progress(1, "读取Excel中...")
    log(f"旧Excel: {old_path}")
    log(f"新Excel: {new_path}")
    log(f"输出: {out_path}")
    log(f"旧sheet: {old_sheet if old_sheet else '(默认)'}")
    log(f"新sheet: {new_sheet if new_sheet else '(默认)'}")

    old_df = read_excel_keep_str(old_path, sheet_name=old_sheet if old_sheet else None)
    new_df = read_excel_keep_str(new_path, sheet_name=new_sheet if new_sheet else None)

    required_cols = {"fid", "split_part", "text_data"}
    if not required_cols.issubset(old_df.columns):
        raise ValueError(f"旧表缺少列：{required_cols - set(old_df.columns)}；现有列：{list(old_df.columns)}")
    if not required_cols.issubset(new_df.columns):
        raise ValueError(f"新表缺少列：{required_cols - set(new_df.columns)}；现有列：{list(new_df.columns)}")

    progress(10, "规范化数据...")

    old = old_df[["fid", "split_part", "text_data"]].copy()
    new = new_df[["fid", "split_part", "text_data"]].copy()

    old["fid"] = normalize_series(old["fid"])
    new["fid"] = normalize_series(new["fid"])

    old["split_part"] = normalize_split_part(old["split_part"])
    new["split_part"] = normalize_split_part(new["split_part"])

    old["text_data"] = normalize_series(old["text_data"])
    new["text_data"] = normalize_series(new["text_data"])

    # 键必须存在：fid 与 split_part 不能为空
    old = old[old["fid"].notna() & old["split_part"].notna()]
    new = new[new["fid"].notna() & new["split_part"].notna()]

    log(f"旧表行数(去除 fid/split_part 空): {len(old)}")
    log(f"新表行数(去除 fid/split_part 空): {len(new)}")

    # 检查唯一性：同一个 (fid, split_part) 不应出现多行
    progress(20, "检查键唯一性...")
    old_dups = old.duplicated(subset=["fid", "split_part"], keep=False)
    new_dups = new.duplicated(subset=["fid", "split_part"], keep=False)

    if old_dups.any():
        sample = old.loc[old_dups, ["fid", "split_part"]].drop_duplicates().head(10)
        raise ValueError(
            "旧表中发现重复键 (fid, split_part)，无法保证唯一标识。\n"
            f"示例(最多10条)：\n{sample.to_string(index=False)}"
        )

    if new_dups.any():
        sample = new.loc[new_dups, ["fid", "split_part"]].drop_duplicates().head(10)
        raise ValueError(
            "新表中发现重复键 (fid, split_part)，无法保证唯一标识。\n"
            f"示例(最多10条)：\n{sample.to_string(index=False)}"
        )

    progress(35, "计算新增/删除/修改...")

    old_k = old.rename(columns={"text_data": "old_text_data"})
    new_k = new.rename(columns={"text_data": "new_text_data"})

    merged = old_k.merge(
        new_k,
        on=["fid", "split_part"],
        how="outer",
        indicator=True,
    )

    # 新增
    added = merged[merged["_merge"] == "right_only"].copy()
    added["change_type"] = "新增"
    added["old_text_data"] = pd.NA

    # 删除
    deleted = merged[merged["_merge"] == "left_only"].copy()
    deleted["change_type"] = "删除"
    deleted["new_text_data"] = pd.NA

    # 修改（两边都有但 text_data 不同；NA 也参与比较）
    both = merged[merged["_merge"] == "both"].copy()
    modified = both[both["old_text_data"].fillna("<NA>") != both["new_text_data"].fillna("<NA>")].copy()
    modified["change_type"] = "修改"

    out = pd.concat([added, modified, deleted], ignore_index=True)
    out = out[["fid", "split_part", "change_type", "old_text_data", "new_text_data"]].copy()

    # ----------------------------
    # 输出排序要求：
    # 1) change_type：新增 -> 修改 -> 删除
    # 2) 每种类型内部：fid 升序，再 split_part 升序
    # 且 fid/split_part 可能是数字字符串，需要按“数值”排序更符合预期
    # ----------------------------
    progress(70, "排序输出结果...")

    order_map = {"新增": 0, "修改": 1, "删除": 2}
    out["_type_order"] = out["change_type"].map(order_map).fillna(99).astype(int)

    out["_fid_num"] = pd.to_numeric(out["fid"], errors="coerce")
    out["_sp_num"] = pd.to_numeric(out["split_part"], errors="coerce")

    out = out.sort_values(
        by=["_type_order", "_fid_num", "fid", "_sp_num", "split_part"],
        ascending=[True, True, True, True, True],
        kind="stable",
        na_position="last",
    ).drop(columns=["_type_order", "_fid_num", "_sp_num"])

    log(f"新增: {len(added)}")
    log(f"修改: {len(modified)}")
    log(f"删除: {len(deleted)}")
    log(f"合计输出行数: {len(out)}")

    progress(85, "写出结果Excel...")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        out.to_excel(writer, index=False, sheet_name="diff")

    progress(100, "完成")
    log("完成：已生成结果Excel。")


# ----------------------------
# GUI
# ----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel差异对比 (fid, split_part, text_data)")
        self.geometry("900x600")

        self.old_path = tk.StringVar()
        self.new_path = tk.StringVar()
        self.out_path = tk.StringVar()

        self.old_sheet = tk.StringVar()
        self.new_sheet = tk.StringVar()

        self._build_ui()
        self.worker = None

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        frm_paths = ttk.LabelFrame(self, text="文件路径")
        frm_paths.pack(fill="x", **pad)

        ttk.Label(frm_paths, text="旧Excel：").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm_paths, textvariable=self.old_path).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(frm_paths, text="选择...", command=self.pick_old).grid(row=0, column=2, **pad)

        ttk.Label(frm_paths, text="新Excel：").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frm_paths, textvariable=self.new_path).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(frm_paths, text="选择...", command=self.pick_new).grid(row=1, column=2, **pad)

        ttk.Label(frm_paths, text="输出Excel：").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(frm_paths, textvariable=self.out_path).grid(row=2, column=1, sticky="ew", **pad)
        ttk.Button(frm_paths, text="选择...", command=self.pick_out).grid(row=2, column=2, **pad)

        frm_paths.columnconfigure(1, weight=1)

        frm_opts = ttk.LabelFrame(self, text="参数")
        frm_opts.pack(fill="x", **pad)

        ttk.Label(frm_opts, text="旧sheet(可选)：").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm_opts, textvariable=self.old_sheet).grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(frm_opts, text="新sheet(可选)：").grid(row=0, column=2, sticky="w", **pad)
        ttk.Entry(frm_opts, textvariable=self.new_sheet).grid(row=0, column=3, sticky="ew", **pad)

        frm_opts.columnconfigure(1, weight=1)
        frm_opts.columnconfigure(3, weight=1)

        frm_run = ttk.Frame(self)
        frm_run.pack(fill="x", **pad)

        self.btn_run = ttk.Button(frm_run, text="开始对比", command=self.on_run)
        self.btn_run.pack(side="left")

        self.btn_clear = ttk.Button(frm_run, text="清空日志", command=self.clear_log)
        self.btn_clear.pack(side="left", padx=10)

        self.prog_msg = tk.StringVar(value="等待开始")
        ttk.Label(frm_run, textvariable=self.prog_msg).pack(side="left", padx=10)

        self.prog = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.prog.pack(fill="x", padx=10, pady=4)

        frm_log = ttk.LabelFrame(self, text="日志")
        frm_log.pack(fill="both", expand=True, **pad)

        self.txt = tk.Text(frm_log, wrap="word")
        self.txt.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frm_log, command=self.txt.yview)
        scrollbar.pack(side="right", fill="y")
        self.txt.configure(yscrollcommand=scrollbar.set)

    def log(self, msg: str):
        self.txt.insert("end", msg + "\n")
        self.txt.see("end")

    def clear_log(self):
        self.txt.delete("1.0", "end")

    def set_progress(self, pct: int, msg: str):
        self.prog["value"] = max(0, min(100, pct))
        self.prog_msg.set(msg)

    def pick_old(self):
        p = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if p:
            self.old_path.set(p)
            if not self.out_path.get():
                base = os.path.splitext(os.path.basename(p))[0]
                self.out_path.set(os.path.join(os.path.dirname(p), f"{base}_diff.xlsx"))

    def pick_new(self):
        p = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if p:
            self.new_path.set(p)

    def pick_out(self):
        p = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
        )
        if p:
            self.out_path.set(p)

    def on_run(self):
        old_path = self.old_path.get().strip()
        new_path = self.new_path.get().strip()
        out_path = self.out_path.get().strip()

        if not old_path or not os.path.exists(old_path):
            messagebox.showerror("错误", "请选择有效的旧Excel路径")
            return
        if not new_path or not os.path.exists(new_path):
            messagebox.showerror("错误", "请选择有效的新Excel路径")
            return
        if not out_path:
            messagebox.showerror("错误", "请选择输出Excel路径")
            return

        old_sheet = self.old_sheet.get().strip() or None
        new_sheet = self.new_sheet.get().strip() or None

        self.set_progress(0, "开始...")
        self.log("========================================")
        self.log("启动任务...")

        self.btn_run.configure(state="disabled")

        def ui_progress(pct, msg):
            self.after(0, lambda: self.set_progress(pct, msg))

        def ui_log(msg):
            self.after(0, lambda: self.log(msg))

        def worker():
            try:
                compare_excels_triple(
                    old_path=old_path,
                    new_path=new_path,
                    out_path=out_path,
                    old_sheet=old_sheet,
                    new_sheet=new_sheet,
                    progress_cb=ui_progress,
                    log_cb=ui_log,
                )
                self.after(0, lambda: messagebox.showinfo("完成", f"已输出：\n{out_path}"))
            except Exception as e:
                tb = traceback.format_exc()
                self.after(0, lambda: self.log(tb))
                self.after(0, lambda: messagebox.showerror("失败", f"{e}\n\n详情见日志"))
            finally:
                self.after(0, lambda: self.btn_run.configure(state="normal"))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
