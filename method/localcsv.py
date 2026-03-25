#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
本地CSV生成图片模块
"""

import os
import sys
import pandas as pd

# 将项目根目录添加到路径，以便导入 core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_csv(csv_path):
    """
    加载CSV文件
    :param csv_path: CSV文件路径
    :return: DataFrame
    """
    if not os.path.exists(csv_path):
        print(f"错误：文件不存在 {csv_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        print(f"加载CSV：{csv_path}")
        print(f"数据量：{len(df)} 行")
        return df
    except Exception as e:
        print(f"读取失败：{str(e)}")
        return pd.DataFrame()


def generate_from_csv(csv_path, save_dir=None):
    """
    从CSV文件生成表格图片
    :param csv_path: CSV文件路径
    :param save_dir: 图片保存目录
    :return: 保存的图片路径
    """
    df = load_csv(csv_path)
    if df.empty:
        return None
    
    # 导入core中的保存函数
    from core import save_table_image, get_timestamp
    
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        timestamp = get_timestamp()
        save_path = os.path.join(save_dir, f"DAC成绩表_{timestamp}.png")
        result = save_table_image(df, save_path)
        print(f"图片已保存：{result}")
        return result
    else:
        print("未指定保存目录，跳过图片生成")
        return None


def main():
    if len(sys.argv) < 2:
        print("用法：python localcsv.py <csv文件路径> [保存目录]")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    save_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    generate_from_csv(csv_path, save_dir)


if __name__ == "__main__":
    main()