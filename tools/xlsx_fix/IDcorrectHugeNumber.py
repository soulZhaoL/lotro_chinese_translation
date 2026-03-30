import pandas as pd
import re
import os
import openpyxl
import gc # 强力释放内存
from pathlib import Path

# ==========================================
# 1. 核心逻辑层 (100% 像素级搬运 V16 IDcorrect.py)
# ==========================================

def _find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "config" / "lotro.yaml").exists() or (candidate / ".git").exists():
            return candidate
    raise RuntimeError("无法自动定位项目根目录")

def has_chinese(text):
    if not isinstance(text, str): return False
    return len(re.findall(r'[\u4e00-\u9fa5]', text)) > 0 #

def get_id_from_part(text):
    match = re.search(r'(\d+)', str(text))
    return match.group(1) if match else "" #

def extract_val_flexible(text):
    s = str(text).strip()
    brackets = re.findall(r'\[(.*?)\]', s)
    if brackets:
        for b in reversed(brackets):
            if has_chinese(b): return b #
        return brackets[-1] #
    clean = re.sub(r'^\d+[:\s\d\-]*', '', s).strip()
    return clean.replace('[', '').replace(']', '').strip() #

def process_logic(text_data, translation_orig):
    """V16 核心模糊匹配逻辑，一行不改"""
    c_val = str(text_data) if pd.notna(text_data) else "" #
    d_val = str(translation_orig) if pd.notna(translation_orig) else "" #
    
    if not c_val.strip(): return d_val #

    exact_map = {}
    fuzzy_list = []
    
    d_parts = d_val.split('|||') #
    for p in d_parts:
        pid = get_id_from_part(p)
        content = extract_val_flexible(p)
        if pid and has_chinese(content): #
            exact_map[pid] = content
            fuzzy_list.append((pid, content)) #
            
    c_parts = c_val.split('|||') #
    final_result = []
    
    for cp in c_parts:
        c_id = get_id_from_part(cp)
        start = cp.find('[')
        end = cp.rfind(']')
        target_content = None
        
        if c_id in exact_map:
            target_content = exact_map[c_id] #
        elif c_id:
            for f_id, f_content in fuzzy_list:
                # V16 的内鬼抓捕逻辑：位数差2以内
                if (f_id in c_id or c_id in f_id) and abs(len(f_id) - len(c_id)) <= 2: #
                    target_content = f_content
                    break
        
        if target_content and start != -1 and end != -1:
            final_result.append(f"{cp[:start+1]}{target_content}{cp[end:]}") #
        else:
            final_result.append(cp) #
            
    return '|||'.join(final_result) #

# ==========================================
# 2. 执行层 (分块处理，防止内存溢出)
# ==========================================

def run_v46_chunked():
    project_root = _find_project_root(Path(__file__).resolve().parent)
    # input_path = project_root / "tools/xlsx_fix/test.xlsx"
    # output_path = project_root / "tools/xlsx_fix/test修复.xlsx"

    input_path = project_root / "work_text/U46.1.xlsx"
    output_path = project_root / "work_text/U46.1_修复.xlsx"
    
    print("🚀 启动 V46：保持 V16 原始逻辑，采用分段处理模式...")
    
    # 步骤 1：先用 Pandas 读取数据（Pandas 处理 30 万行纯文本比 openpyxl 省内存）
    # 如果内存还是紧巴巴，可以加上 chunksize 参数
    df = pd.read_excel(input_path)
    total_rows = len(df)
    print(f"📊 数据读取完毕，共 {total_rows} 行。开始分段处理...")

    # 确认列名
    c_col = 'text_data'
    d_col = 'translation'
    
    # 步骤 2：循环处理
    chunk_size = 5000
    for i in range(0, total_rows, chunk_size):
        end_idx = min(i + chunk_size, total_rows)
        
        # 针对当前分段执行 V16 逻辑
        df.loc[i:end_idx, d_col] = df.loc[i:end_idx].apply(
            lambda x: process_logic(x[c_col], x[d_col]), axis=1
        )
        
        print(f"⏳ 已完成 {end_idx}/{total_rows} 行...")
        
        # 强制垃圾回收
        gc.collect()

    # 步骤 3：最终输出
    print("💾 正在执行最后保存，请耐心等候（约 1-3 分钟）...")
    df.to_excel(output_path, index=False)
    print(f"✅ 处理完成！结果已存至: {output_path}")

if __name__ == "__main__":
    run_v46_chunked()
