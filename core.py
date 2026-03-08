#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DACreator 核心功能模块
生成可视化表格图片
可作为独立CLI运行，也可被GUI导入
"""

import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import platform
import sys
from typing import Optional
from datetime import datetime
import time

# 全局配置
CONFIG = {
    "font_size": 12,
    "header_height": 40,
    "row_height": 30,
    "col_widths": [80, 60, 80, 100, 280, 90, 80],
    "bg_color": (255, 255, 255),
    "header_color": (44, 62, 80),
    "header_text_color": (255, 255, 255),
    "row_even_color": (245, 245, 245),
    "row_odd_color": (255, 255, 255),
    "text_color": (0, 0, 0),
    "border_color": (200, 200, 200),
    "scale": 2,
    
    "rank_img_root": r"./assets/rank",
    "rank_img_scale": 0.8,
    "rank_mapping": {
        "ROOKIE": "rookie.png",
        "REGULAR": "regular.png",
        "SPECIALIST": "specialist.png",
        "EXPERT": "expert.png",
        "PROFESSIONAL": "professional.png",
        "MASTER": "master.png",
        "MASTER+": "masterp.png",
        "LEGEND": "legend.png"
    },
    
    "font_root": r"./assets/font",
    "font_files": {
        "header": "YuGothB.ttc",
        "special_cols": "consolab.ttf",
        "normal_cols": "msyhbd.ttc"
    },
    "special_col_names": ["タイム", "記録日"],
}


def format_time(seconds: float) -> str:
    """格式化时间为 分'秒"毫秒 格式"""
    minutes = int(seconds // 60)
    seconds_remainder = seconds % 60
    whole_seconds = int(seconds_remainder)
    milliseconds = int((seconds_remainder - whole_seconds) * 1000)
    
    if minutes > 0:
        return f"{minutes}'{whole_seconds:02d}\"{milliseconds:03d}"
    else:
        return f"{whole_seconds}\"{milliseconds:03d}"


def get_timestamp() -> str:
    """获取当前时间戳，格式：YYYYMMDD_HHMMSS"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_rank_image(rank_text: str, target_height: int) -> Optional[Image.Image]:
    """加载等级图片"""
    rank_text_upper = rank_text.strip().upper()
    if rank_text_upper not in CONFIG["rank_mapping"]:
        return None
    
    img_name = CONFIG["rank_mapping"][rank_text_upper]
    img_path = os.path.join(CONFIG["rank_img_root"], img_name)
    if not os.path.exists(img_path):
        print(f"⚠️ 等级图片不存在：{img_path}")
        return None
    
    img = Image.open(img_path).convert("RGBA")
    original_w, original_h = img.size
    final_row_height = CONFIG["row_height"] * CONFIG["rank_img_scale"]
    scale_ratio = final_row_height / original_h
    new_w = int(original_w * scale_ratio * CONFIG["scale"])
    new_h = int(original_h * scale_ratio * CONFIG["scale"])
    
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    return img_resized


def load_font(font_type: str, size: int = None) -> ImageFont.FreeTypeFont:
    """加载字体"""
    if size is None:
        size = CONFIG["font_size"] * CONFIG["scale"]
    else:
        size = size * CONFIG["scale"]
    
    font_file = CONFIG["font_files"][font_type]
    font_path = os.path.join(CONFIG["font_root"], font_file)
    
    if not os.path.exists(font_path):
        print(f"❌ 内置字体文件缺失：{font_path}")
        # 使用默认字体
        return ImageFont.load_default()
    
    try:
        if font_file.endswith(".ttc"):
            font = ImageFont.truetype(font_path, size, index=0)
        else:
            font = ImageFont.truetype(font_path, size)
        return font
    except Exception as e:
        print(f"❌ 加载字体失败：{font_path}，{str(e)}")
        return ImageFont.load_default()


def create_table_image(df: pd.DataFrame, callback=None) -> Image.Image:
    """
    创建表格图片（兼容有无排名列两种情况）
    :param df: DataFrame
    :param callback: 进度回调函数
    :return: PIL Image
    """
    if callback:
        callback("开始创建表格图片...", "info", 0)
    
    # 加载字体
    header_font = load_font("header", 14)
    special_font = load_font("special_cols", 12)
    normal_font = load_font("normal_cols", 12)
    
    # 根据实际列数调整列宽
    actual_cols = len(df.columns)
    if actual_cols == 6:  # 无排名列
        col_widths = CONFIG["col_widths"][:5] + [CONFIG["col_widths"][6]]
    else:  # 7列（含排名）
        col_widths = CONFIG["col_widths"]
    
    total_width = (sum(col_widths) + 20) * CONFIG["scale"]
    total_height = (CONFIG["header_height"] + (len(df) * CONFIG["row_height"]) + 20) * CONFIG["scale"]
    
    if callback:
        callback(f"创建画布 {total_width//CONFIG['scale']}x{total_height//CONFIG['scale']}", "info", 10)
    
    img = Image.new("RGB", (total_width, total_height), CONFIG["bg_color"])
    draw = ImageDraw.Draw(img)
    
    # 绘制表头
    x = 10 * CONFIG["scale"]
    y = 10 * CONFIG["scale"]
    draw.rectangle(
        [x, y, total_width - 10 * CONFIG["scale"], y + CONFIG["header_height"] * CONFIG["scale"]],
        fill=CONFIG["header_color"],
        outline=CONFIG["border_color"]
    )
    headers = df.columns.tolist()
    for i, header in enumerate(headers):
        draw.text(
            (x + 5 * CONFIG["scale"], y + (CONFIG["header_height"] * CONFIG["scale"]) / 2 - (CONFIG["font_size"] * CONFIG["scale"]) / 2),
            header,
            fill=CONFIG["header_text_color"],
            font=header_font
        )
        x += col_widths[i] * CONFIG["scale"]
    
    if callback:
        callback("表头绘制完成", "info", 20)
    
    # 绘制数据行
    y += CONFIG["header_height"] * CONFIG["scale"]
    eval_col_idx = headers.index("タイム評価") if "タイム評価" in headers else -1
    
    total_rows = len(df)
    for idx, (_, row) in enumerate(df.iterrows()):
        # 更新进度
        if callback and idx % 10 == 0:
            progress = 20 + int((idx / total_rows) * 70)
            callback(f"正在绘制第 {idx+1}/{total_rows} 行", "info", progress)
        
        row_bg = CONFIG["row_even_color"] if idx % 2 == 0 else CONFIG["row_odd_color"]
        draw.rectangle(
            [10 * CONFIG["scale"], y, total_width - 10 * CONFIG["scale"], y + CONFIG["row_height"] * CONFIG["scale"]],
            fill=row_bg,
            outline=CONFIG["border_color"]
        )
        
        x = 10 * CONFIG["scale"]
        for i, col in enumerate(headers):
            text = str(row[col]) if pd.notna(row[col]) else ""
            
            if i == eval_col_idx:
                rank_img = load_rank_image(text, 0)
                if rank_img:
                    img_x = x + (col_widths[i] * CONFIG["scale"] - rank_img.width) // 2
                    img_y = y + (CONFIG["row_height"] * CONFIG["scale"] - rank_img.height) // 2
                    img.paste(rank_img, (img_x, img_y), mask=rank_img)
                else:
                    draw.text(
                        (x + 5 * CONFIG["scale"], y + (CONFIG["row_height"] * CONFIG["scale"]) / 2 - (CONFIG["font_size"] * CONFIG["scale"]) / 2),
                        text,
                        fill=CONFIG["text_color"],
                        font=normal_font
                    )
            elif col in CONFIG["special_col_names"]:
                draw.text(
                    (x + 5 * CONFIG["scale"], y + (CONFIG["row_height"] * CONFIG["scale"]) / 2 - (CONFIG["font_size"] * CONFIG["scale"]) / 2),
                    text,
                    fill=CONFIG["text_color"],
                    font=special_font
                )
            else:
                draw.text(
                    (x + 5 * CONFIG["scale"], y + (CONFIG["row_height"] * CONFIG["scale"]) / 2 - (CONFIG["font_size"] * CONFIG["scale"]) / 2),
                    text,
                    fill=CONFIG["text_color"],
                    font=normal_font
                )
            
            x += col_widths[i] * CONFIG["scale"]
        y += CONFIG["row_height"] * CONFIG["scale"]
    
    if callback:
        callback("缩小图片...", "info", 90)
    
    # 缩小回正常尺寸
    img = img.resize(
        (total_width // CONFIG["scale"], total_height // CONFIG["scale"]),
        Image.Resampling.LANCZOS
    )
    
    if callback:
        callback("图片生成完成", "success", 100)
    
    return img


def save_table_image(df: pd.DataFrame, save_path: str = None, callback=None) -> str:
    """
    保存表格图片
    :param df: DataFrame
    :param save_path: 保存路径，为None时自动生成
    :param callback: 回调函数
    :return: 保存路径
    """
    if save_path is None:
        timestamp = get_timestamp()
        save_path = f"DAC成绩表_{timestamp}.png"
    
    if callback:
        callback(f"开始生成图片：{save_path}", "info", 0)
    
    start_time = time.time()
    img = create_table_image(df, callback)
    img.save(save_path, "PNG", dpi=(300, 300))
    
    elapsed = time.time() - start_time
    if callback:
        callback(f"图片已保存：{save_path}，耗时 {format_time(elapsed)}", "success", 100)
    
    return save_path


# 兼容旧的CLI函数
def create_table_image_cli(df: pd.DataFrame) -> Image.Image:
    """兼容CLI的旧函数"""
    return create_table_image(df)


# CLI入口
if __name__ == "__main__":
    print("=" * 60)
    print("DACreator 核心模块 - 命令行版本")
    print("=" * 60)
    
    # 简单的CLI测试
    if len(sys.argv) > 1 and sys.argv[1].endswith('.csv'):
        csv_path = sys.argv[1]
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            print(f"📁 加载CSV：{csv_path}")
            print(f"📊 数据量：{len(df)} 行")
            
            save_path = save_table_image(df)
            print(f"✅ 图片已保存：{save_path}")
        except Exception as e:
            print(f"❌ 处理失败：{str(e)}")
    else:
        print("用法：python core.py <csv文件路径>")
        print("示例：python core.py 成绩表.csv")
    
    print()