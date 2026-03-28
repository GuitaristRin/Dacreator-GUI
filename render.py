#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
render.py - 赛车游戏玩家战绩卡生成器
基于 template.png 模板，将数据填入精确位置
"""

import os
import sys
import random
import configparser
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_player_config() -> Dict[str, str]:
    """读取 Player_ID.dat 配置文件。"""
    config_path = "Player_ID.dat"
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return {}

    data = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                data[key.strip()] = value.strip()
    return data

# 导入数据获取函数
try:
    from method.search import crawl_data_by_search
    from method.round import get_round_info
    from method.pride import get_pride_info
    from method.team import get_team_info
except ImportError as e:
    print(f"❌ 导入数据模块失败: {e}")
    sys.exit(1)

# ==================== 统一配置区 ====================
class Config:
    """所有配置集中管理"""
    
    # 模板路径
    TEMPLATE_PATH = os.path.join("./assets/render", "template.png")
    
    # 图片资源路径
    RANK_IMG_DIR = os.path.join("./assets", "rank")
    TEAM_IMG_DIR = os.path.join("./assets", "team")
    PRIDE_IMG_DIR = os.path.join("./assets", "pride")
    
    # 字体路径
    FONT_YU_GOTHIC = os.path.join("./assets/font", "YuGothB.ttc")    # Yu Gothic 字体
    FONT_MSYH_BOLD = os.path.join("./assets/font", "msyhbd.ttc")      # 微软雅黑粗体
    FONT_MSYH_REGULAR = os.path.join("./assets/font", "msyh.ttc")     # 微软雅黑常规体
    
    # 颜色定义
    COLOR_HIGHLIGHT_BLUE = (0, 80, 255)   # #0050FF
    COLOR_BLACK = (0, 0, 0)
    COLOR_GRAY = (100, 100, 100)          # #646464
    COLOR_WHITE = (255, 255, 255)
    
    # 模板区域定义（基于 template.png 的精确坐标）
    # 顶部标题栏
    TITLE_AREA = (40, 40, 1560, 180)
    
    # 左列区域
    LEFT_AREA = (40, 180, 760, 1160)
    
    # 左1: 玩家ID栏
    PLAYER_ID_AREA = (35, 250, 760, 325)
    # 左2: 地区+城市栏
    LOCATION_AREA = (35, 420, 760, 415)
    # 左3: 店铺名栏
    STORE_AREA = (35, 545, 760, 505)
    # 左4: 计时赛记录区
    RECORDS_AREA = (40, 580, 760, 1160)
    
    # 右列区域
    RIGHT_AREA = (760, 180, 1560, 1160)
    
    # 右1: 赛季回合栏
    SEASON_ROUND_AREA = (700, 210, 1560, 325)
    # 右2: 回合分数栏（只保留数值）
    SCORE_ONLY_AREA = (760, 395, 1560, 490)
    # 右3: 所属车队栏（只保留数值）
    TEAM_ONLY_AREA = (760, 510, 1560, 570)
    # 右4: 荣誉徽章+车队总分+固定logo区
    HONOR_AREA = (760, 505, 1560, 1160)
    
    # 计时赛记录配置
    RECORD_START_X_OFFSET = 60          # 记录整体向右偏移量
    RECORD_START_Y_OFFSET = 40          # 第一条记录距单元格顶部距离
    RECORD_VERTICAL_SPACING = 38        # 记录间垂直间距
    BADGE_WIDTH = 220                   # 等级徽章宽度
    BADGE_HEIGHT = 56                   # 等级徽章高度
    BADGE_LEFT_MARGIN = 30              # 徽章距左边缘距离
    BADGE_TEXT_GAP = 20                 # 徽章与赛道名间距
    TRACK_NAME_FONT_SIZE = 28           # 赛道名字号
    TIME_FONT_SIZE = 28                 # 时间字号
    TIME_OFFSET_FROM_TRACK = 5          # 时间与赛道名的水平间距
    
    # 字体大小配置
    PLAYER_ID_FONT_SIZE = 72            # 玩家ID字号
    LOCATION_FONT_SIZE = 48             # 地区+城市字号
    STORE_FONT_SIZE = 48                # 店铺名字号
    SEASON_FONT_SIZE = 72               # 赛季回合字号
    SCORE_ONLY_FONT_SIZE = 56           # 回合分数数值字号
    TEAM_ONLY_FONT_SIZE = 56            # 所属车队数值字号
    
    # 右2/右3单元格配置
    SCORE_ONLY_RIGHT_MARGIN = 60        # 右侧数值距右边缘
    TEAM_ONLY_RIGHT_MARGIN = 60         # 右侧数值距右边缘
    
    # 荣誉区配置（加大徽章尺寸）
    BADGE_WIDTH_HONOR = 340             # 荣誉徽章宽度
    BADGE_HEIGHT_HONOR = 204            # 荣誉徽章高度（保持5:3比例）
    BADGE_HORIZONTAL_GAP = 100          # 两枚徽章水平间距
    BADGE_TEXT_VERTICAL_OFFSET = 35     # 徽章下方文字垂直偏移
    
    # 车队分数配置
    TEAM_SCORE_VALUE_FONT_SIZE = 48     # 车队分数数值字号
    TEAM_SCORE_X_OFFSET = 60             # 车队分数水平偏移（正数向右）
    TEAM_SCORE_Y_OFFSET = 105             # 车队分数垂直偏移（正数向下）
    
    # 名声分数配置
    PRIDE_SCORE_FONT_SIZE = 38          # 名声分数数值字号
    PRIDE_SCORE_X_OFFSET = 0            # 名声分数水平偏移（正数向右）
    PRIDE_SCORE_Y_OFFSET = -10            # 名声分数垂直偏移（正数向下）
    
    # 等级映射
    RANK_ORDER = ["ROOKIE", "REGULAR", "SPECIALIST", "EXPERT",
                  "PROFESSIONAL", "MASTER", "MASTER+", "LEGEND"]
    
    RANK_IMAGE_MAP = {r: f"{r.lower()}.png" for r in RANK_ORDER}
    RANK_IMAGE_MAP["MASTER+"] = "masterp.png"
    
    # 车队等级图片映射
    TEAM_IMAGE_MAP = {
        "OPEN": "open.png",
        "BASIC": "basic.png",
        "BRONZE": "bronze.png",
        "SILVER": "silver.png",
        "GOLD": "gold.png",
        "PLATINUM": "platinum.png",
        "MASTER": "master.png"
    }
    
    @classmethod
    def get_pride_image(cls, score: int) -> str:
        """根据名声分数返回对应的图片路径"""
        if score < 100:
            return os.path.join(cls.PRIDE_IMG_DIR, "pride1.png")
        elif score < 1000:
            return os.path.join(cls.PRIDE_IMG_DIR, "pride2.png")
        else:
            return os.path.join(cls.PRIDE_IMG_DIR, "pride3.png")


# ==================== 辅助函数 ====================

def load_player_config() -> Dict[str, str]:
    """读取 Player_ID.dat 配置文件。"""
    config_path = "Player_ID.dat"
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)

    data = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                data[key.strip()] = value.strip()
    return data


def get_rank_value(rank_name: str) -> int:
    """返回等级数值。"""
    try:
        return Config.RANK_ORDER.index(rank_name)
    except ValueError:
        return -1


def select_top_records(df, limit: int = 5) -> List[Dict]:
    """从 DataFrame 中挑选 top N 条记录。"""
    if df.empty:
        return []

    df = df.copy()
    df['rank_val'] = df['タイム評価'].apply(get_rank_value)
    df_sorted = df.sort_values(by=['rank_val', 'タイム'], ascending=[False, True])

    grouped = {}
    for _, row in df_sorted.iterrows():
        rank = row['タイム評価']
        if rank not in grouped:
            grouped[rank] = []
        grouped[rank].append(row)

    selected = []
    remaining = limit
    for rank in reversed(Config.RANK_ORDER):
        if rank not in grouped:
            continue
        items = grouped[rank]
        if len(items) <= remaining:
            selected.extend(items)
            remaining -= len(items)
        else:
            selected.extend(random.sample(items, remaining))
            remaining = 0
            break
        if remaining == 0:
            break

    result = []
    for row in selected:
        course = row.get('コース', '')
        route = row.get('ルート', '')
        track_name = f"{course} {route}" if route else course
        result.append({
            'track': track_name,
            'time': row.get('タイム', ''),
            'rank': row.get('タイム評価', ''),
        })
    return result


def load_and_resize_image(path: str, target_width: int = None, target_height: int = None, keep_ratio: bool = True) -> Optional[Image.Image]:
    """加载图片并缩放到指定尺寸，可选择是否保持宽高比。"""
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    
    if target_width and target_height:
        if keep_ratio:
            # 保持宽高比，缩放至不超过目标尺寸
            ratio = min(target_width / w, target_height / h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            return img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    elif target_width:
        ratio = target_width / w
        new_h = int(h * ratio)
        return img.resize((target_width, new_h), Image.Resampling.LANCZOS)
    elif target_height:
        ratio = target_height / h
        new_w = int(w * ratio)
        return img.resize((new_w, target_height), Image.Resampling.LANCZOS)
    return img


def parse_round_info(info_str: str) -> Tuple[int, int]:
    """解析回合信息，返回 (分数, 排名)"""
    import re
    score_match = re.search(r'回合分数[：:]\s*(\d+)', info_str)
    rank_match = re.search(r'排名[：:]\s*(\d+)', info_str)
    score = int(score_match.group(1)) if score_match else 0
    rank = int(rank_match.group(1)) if rank_match else 0
    return score, rank


def parse_pride_info(info_str: str) -> Tuple[int, int]:
    """解析名声信息，返回 (名声值, 排名)"""
    import re
    val_match = re.search(r'名声值[：:]\s*(\d+)', info_str)
    rank_match = re.search(r'排名[：:]\s*(\d+)', info_str)
    value = int(val_match.group(1)) if val_match else 0
    rank = int(rank_match.group(1)) if rank_match else 0
    return value, rank


def parse_team_info(info_str: str) -> Tuple[int, str, int]:
    """解析车队信息，返回 (分数, 等级名称, 排名)"""
    import re
    score_match = re.search(r'车队分数[：:]\s*(\d+)', info_str)
    level_match = re.search(r'联赛等级[：:]\s*([A-Z+]+)', info_str)
    rank_match = re.search(r'排名[：:]\s*(\d+)', info_str)
    score = int(score_match.group(1)) if score_match else 0
    level = level_match.group(1) if level_match else "OPEN"
    rank = int(rank_match.group(1)) if rank_match else 0
    return score, level, rank


# ==================== 主渲染类 ====================

class TemplateRenderer:
    """基于模板图的战绩卡渲染器"""
    
    def __init__(self):
        """加载模板和字体"""
        if not os.path.exists(Config.TEMPLATE_PATH):
            print(f"❌ 模板文件不存在: {Config.TEMPLATE_PATH}")
            sys.exit(1)
        
        self.image = Image.open(Config.TEMPLATE_PATH).convert("RGBA")
        self.draw = ImageDraw.Draw(self.image)
        
        # 加载字体
        self.fonts = self._load_fonts()
    
    def _load_fonts(self) -> Dict:
        """加载所有字体"""
        fonts = {}
        font_configs = {
            'player_id': (Config.FONT_YU_GOTHIC, Config.PLAYER_ID_FONT_SIZE),
            'location': (Config.FONT_MSYH_BOLD, Config.LOCATION_FONT_SIZE),
            'store': (Config.FONT_MSYH_BOLD, Config.STORE_FONT_SIZE),
            'track': (Config.FONT_MSYH_BOLD, Config.TRACK_NAME_FONT_SIZE),
            'time': (Config.FONT_MSYH_BOLD, Config.TIME_FONT_SIZE),
            'season': (Config.FONT_YU_GOTHIC, Config.SEASON_FONT_SIZE),
            'score_only': (Config.FONT_MSYH_BOLD, Config.SCORE_ONLY_FONT_SIZE),
            'team_only': (Config.FONT_MSYH_BOLD, Config.TEAM_ONLY_FONT_SIZE),
            'team_score_value': (Config.FONT_MSYH_BOLD, Config.TEAM_SCORE_VALUE_FONT_SIZE),
            'pride_score': (Config.FONT_MSYH_BOLD, Config.PRIDE_SCORE_FONT_SIZE),
        }
        
        for key, (font_path, size) in font_configs.items():
            try:
                fonts[key] = ImageFont.truetype(font_path, size)
            except Exception as e:
                print(f"⚠️ 字体加载失败 {font_path}: {e}")
                fonts[key] = ImageFont.load_default()
        
        return fonts
    
    def draw_text_with_stroke(self, x: int, y: int, text: str, font_key: str, 
                               fill_color: Tuple, stroke_color: Tuple, stroke_width: int = 2,
                               anchor: str = "lt"):
        """绘制带描边的文字"""
        # 绘制描边（多层偏移）
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx != 0 or dy != 0:
                    self.draw.text((x + dx, y + dy), text, fill=stroke_color, 
                                  font=self.fonts[font_key], anchor=anchor)
        # 绘制主文字
        self.draw.text((x, y), text, fill=fill_color, font=self.fonts[font_key], anchor=anchor)
    
    def draw_text_in_area_with_stroke(self, area: Tuple[int, int, int, int], text: str, 
                                       font_key: str, fill_color: Tuple, stroke_color: Tuple,
                                       stroke_width: int = 2, align: str = "center"):
        """在指定区域内绘制带描边的文字"""
        x1, y1, x2, y2 = area
        width = x2 - x1
        height = y2 - y1
        
        bbox = self.draw.textbbox((0, 0), text, font=self.fonts[font_key])
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if align == "center":
            x = x1 + (width - text_width) // 2
            y = y1 + (height - text_height) // 2
        elif align == "left":
            x = x1
            y = y1 + (height - text_height) // 2
        elif align == "right":
            x = x2 - text_width
            y = y1 + (height - text_height) // 2
        
        self.draw_text_with_stroke(x, y, text, font_key, fill_color, stroke_color, stroke_width)
    
    def draw_text_aligned_with_stroke(self, x: int, y: int, text: str, font_key: str,
                                       fill_color: Tuple, stroke_color: Tuple, 
                                       stroke_width: int = 2, anchor: str = "lt"):
        """在指定坐标绘制带描边的文字"""
        self.draw_text_with_stroke(x, y, text, font_key, fill_color, stroke_color, stroke_width, anchor)
    
    def paste_image_centered(self, img: Image.Image, area: Tuple[int, int, int, int]):
        """将图片居中粘贴到指定区域"""
        x1, y1, x2, y2 = area
        img_x = x1 + (x2 - x1 - img.width) // 2
        img_y = y1 + (y2 - y1 - img.height) // 2
        self.image.paste(img, (img_x, img_y), mask=img if img.mode == 'RGBA' else None)
    
    def render(self, data: Dict):
        """主渲染流程"""
        
        # ========== 1. 顶部标题栏（固定内容，不需要从数据获取）==========
        
        # ========== 2. 左列区域 ==========
        
        # 2.1 玩家ID（白色填充，黑色描边，Yu Gothic字体）
        self.draw_text_in_area_with_stroke(Config.PLAYER_ID_AREA, data['user']['id'], 
                                           'player_id', Config.COLOR_WHITE, Config.COLOR_BLACK, 3, "center")
        
        # 2.2 地区+城市（白色填充，黑色描边，微软雅黑）
        location_parts = data['user']['locale'].split('・') if '・' in data['user']['locale'] else [data['user']['locale'], data['user']['city']]
        if len(location_parts) >= 2:
            location_text = f"{location_parts[0]}   {location_parts[1]}"
        else:
            location_text = f"{data['user']['locale']}   {data['user']['city']}"
        
        self.draw_text_in_area_with_stroke(Config.LOCATION_AREA, location_text, 
                                           'location', Config.COLOR_WHITE, Config.COLOR_BLACK, 2, "center")
        
        # 2.3 店铺名（白色填充，黑色描边，微软雅黑）
        self.draw_text_in_area_with_stroke(Config.STORE_AREA, data['user']['store'], 
                                           'store', Config.COLOR_WHITE, Config.COLOR_BLACK, 2, "center")
        
        # 2.4 计时赛记录
        self._render_records(data['records'])
        
        # ========== 3. 右列区域 ==========
        
        # 3.1 赛季回合（白色填充，黑色描边，Yu Gothic字体）
        season_text = f"SEASON {data['season']} ROUND {data['round']}"
        self.draw_text_in_area_with_stroke(Config.SEASON_ROUND_AREA, season_text, 
                                           'season', Config.COLOR_WHITE, Config.COLOR_BLACK, 3, "center")
        
        # 3.2 回合分数（只保留数值，白色填充，黑色描边）
        self._render_score_only(data['round_score'])
        
        # 3.3 所属车队（只保留数值，白色填充，黑色描边）
        self._render_team_only(data['team']['name'])
        
        # 3.4 荣誉区（徽章+车队总分+logo）
        self._render_honor_area(data['team']['level'], data['team']['score'], data['pride_value'])
    
    def _render_records(self, records: List[Dict]):
        """渲染计时赛记录列表（时间跟在赛道名后面）"""
        x1, y1, x2, y2 = Config.RECORDS_AREA
        start_x = x1 + Config.RECORD_START_X_OFFSET
        start_y = y1 + Config.RECORD_START_Y_OFFSET
        
        for i, record in enumerate(records[:5]):
            record_y = start_y + i * (Config.BADGE_HEIGHT + Config.RECORD_VERTICAL_SPACING)
            
            # 绘制等级徽章
            badge_path = os.path.join(Config.RANK_IMG_DIR, 
                                      Config.RANK_IMAGE_MAP.get(record['rank'], ''))
            badge_img = load_and_resize_image(badge_path, 
                                              target_width=Config.BADGE_WIDTH, 
                                              target_height=Config.BADGE_HEIGHT)
            if badge_img:
                badge_x = start_x
                badge_y = record_y
                self.image.paste(badge_img, (badge_x, badge_y), mask=badge_img)
                text_x = badge_x + Config.BADGE_WIDTH + Config.BADGE_TEXT_GAP
            else:
                text_x = start_x
            
            # 赛道名 + 时间（放在同一行）
            track_text = record['track'][:25]
            time_text = record['time']
            full_text = f"{track_text}  {time_text}"
            
            # 垂直居中对齐徽章
            text_y = record_y + (Config.BADGE_HEIGHT // 2) - 15
            self.draw_text_aligned_with_stroke(text_x, text_y, full_text, 'track',
                                               Config.COLOR_BLACK, Config.COLOR_WHITE, 1, "lt")
    
    def _render_score_only(self, round_score: int):
        """渲染回合分数（只显示数值，右对齐，白色填充+黑色描边）"""
        x1, y1, x2, y2 = Config.SCORE_ONLY_AREA
        value_text = f"{round_score} pts"
        
        bbox = self.draw.textbbox((0, 0), value_text, font=self.fonts['score_only'])
        value_width = bbox[2] - bbox[0]
        value_x = x2 - Config.SCORE_ONLY_RIGHT_MARGIN - value_width
        value_y = y1 + (y2 - y1 - (bbox[3] - bbox[1])) // 2
        
        self.draw_text_aligned_with_stroke(value_x, value_y, value_text, 'score_only',
                                           Config.COLOR_WHITE, Config.COLOR_BLACK, 2, "lt")
    
    def _render_team_only(self, team_name: str):
        """渲染所属车队（只显示数值，右对齐，白色填充+黑色描边）"""
        x1, y1, x2, y2 = Config.TEAM_ONLY_AREA
        value_text = team_name
        
        bbox = self.draw.textbbox((0, 0), value_text, font=self.fonts['team_only'])
        value_width = bbox[2] - bbox[0]
        value_x = x2 - Config.TEAM_ONLY_RIGHT_MARGIN - value_width
        value_y = y1 + (y2 - y1 - (bbox[3] - bbox[1])) // 2
        
        self.draw_text_aligned_with_stroke(value_x, value_y, value_text, 'team_only',
                                           Config.COLOR_WHITE, Config.COLOR_BLACK, 2, "lt")
    
    def _render_honor_area(self, team_level: str, team_score: int, pride_value: int):
        """渲染右4单元格（荣誉徽章 + 车队总分 + logo）"""
        x1, y1, x2, y2 = Config.HONOR_AREA
        area_height = y2 - y1
        
        # 徽章区高度占70%
        badge_area_height = int(area_height * 0.7)
        
        # ========== 上半区：徽章区 ==========
        # 计算两枚徽章的整体宽度
        total_badge_width = Config.BADGE_WIDTH_HONOR * 2 + Config.BADGE_HORIZONTAL_GAP
        start_x = x1 + (x2 - x1 - total_badge_width) // 2
        
        # 车队等级徽章
        team_badge_path = os.path.join(Config.TEAM_IMG_DIR, 
                                       Config.TEAM_IMAGE_MAP.get(team_level.upper(), "open.png"))
        team_badge = load_and_resize_image(team_badge_path, 
                                           target_width=Config.BADGE_WIDTH_HONOR,
                                           target_height=Config.BADGE_HEIGHT_HONOR,
                                           keep_ratio=True)
        if team_badge:
            team_badge_x = start_x
            team_badge_y = y1 + (badge_area_height - team_badge.height) // 2
            self.image.paste(team_badge, (team_badge_x, team_badge_y), 
                           mask=team_badge if team_badge.mode == 'RGBA' else None)
            
            # 只显示车队分数数值，不显示标签（白色填充+黑色描边）
            value_x = team_badge_x + team_badge.width // 2 + Config.TEAM_SCORE_X_OFFSET
            value_y = team_badge_y + team_badge.height + Config.BADGE_TEXT_VERTICAL_OFFSET + Config.TEAM_SCORE_Y_OFFSET
            self.draw_text_aligned_with_stroke(value_x, value_y, f"{team_score} pts", 'team_score_value',
                                               Config.COLOR_WHITE, Config.COLOR_BLACK, 2, "mt")
        
        # 名声徽章
        pride_img_path = Config.get_pride_image(pride_value)
        pride_badge = load_and_resize_image(pride_img_path,
                                            target_width=Config.BADGE_WIDTH_HONOR,
                                            target_height=Config.BADGE_HEIGHT_HONOR,
                                            keep_ratio=True)
        if pride_badge:
            pride_badge_x = start_x + Config.BADGE_WIDTH_HONOR + Config.BADGE_HORIZONTAL_GAP
            pride_badge_y = y1 + (badge_area_height - pride_badge.height) // 2
            self.image.paste(pride_badge, (pride_badge_x, pride_badge_y),
                           mask=pride_badge if pride_badge.mode == 'RGBA' else None)
            
            # 在名声徽章上绘制分数（白色填充+黑色描边）
            temp_draw = ImageDraw.Draw(pride_badge)
            try:
                temp_font = ImageFont.truetype(Config.FONT_MSYH_BOLD, Config.PRIDE_SCORE_FONT_SIZE)
            except:
                temp_font = ImageFont.load_default()
            score_text = str(pride_value)
            bbox = temp_draw.textbbox((0, 0), score_text, font=temp_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (pride_badge.width - text_width) // 2 + Config.PRIDE_SCORE_X_OFFSET
            text_y = (pride_badge.height - text_height) // 2 + Config.PRIDE_SCORE_Y_OFFSET
            
            # 绘制描边
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx != 0 or dy != 0:
                        temp_draw.text((text_x + dx, text_y + dy), score_text, 
                                      fill=Config.COLOR_BLACK, font=temp_font)
            # 绘制主文字
            temp_draw.text((text_x, text_y), score_text, fill=Config.COLOR_WHITE, font=temp_font)
            
            # 重新粘贴
            self.image.paste(pride_badge, (pride_badge_x, pride_badge_y),
                           mask=pride_badge if pride_badge.mode == 'RGBA' else None)
    
    def save(self, output_path: str):
        """保存图片"""
        self.image.save(output_path, "PNG")
        print(f"✅ 战绩卡已保存: {output_path}")


# ==================== 主流程 ====================

def main():
    print("🎮 开始生成赛车游戏玩家战绩卡...")
    
    # 1. 读取配置
    config = load_player_config()
    user_id = config.get('ID', '未知')
    team_name = config.get('TEAM', '未知')
    store = config.get('STORE', '未知')
    locale = config.get('LOCALE', '未知')
    city = config.get('CITY', '未知')
    season = config.get('SEASON', '?')
    round_num = config.get('ROUND', '?')
    
    # 2. 获取计时赛记录
    print("📡 正在获取计时赛记录...")
    try:
        df = crawl_data_by_search()
        if df.empty:
            print("⚠️ 未获取到任何计时赛记录")
            records = []
        else:
            records = select_top_records(df, limit=5)
            print(f"✅ 已选取 {len(records)} 条高等级记录")
    except Exception as e:
        print(f"❌ 获取计时赛记录失败: {e}")
        records = []
    
    # 3. 获取回合数据
    print("📡 获取回合分数...")
    try:
        round_info = get_round_info()
        round_score, round_rank = parse_round_info(round_info)
        print(f"✅ 回合分数: {round_score}")
    except Exception as e:
        print(f"❌ 获取回合数据失败: {e}")
        round_score = 0
    
    # 4. 获取名声数据
    print("📡 获取名声分数...")
    try:
        pride_info = get_pride_info()
        pride_val, pride_rank = parse_pride_info(pride_info)
        print(f"✅ 名声分数: {pride_val}")
    except Exception as e:
        print(f"❌ 获取名声数据失败: {e}")
        pride_val = 0
    
    # 5. 获取车队数据
    print("📡 获取车队信息...")
    try:
        team_info = get_team_info()
        team_score, team_level, team_rank = parse_team_info(team_info)
        print(f"✅ 车队分数: {team_score}, 等级: {team_level}")
    except Exception as e:
        print(f"❌ 获取车队信息失败: {e}")
        team_score, team_level = 0, "OPEN"
    
    # 6. 组装数据
    data = {
        'user': {
            'id': user_id,
            'store': store,
            'locale': locale,
            'city': city,
        },
        'records': records,
        'season': season,
        'round': round_num,
        'round_score': round_score,
        'pride_value': pride_val,
        'team': {
            'name': team_name,
            'score': team_score,
            'level': team_level,
        }
    }
    
    # 7. 渲染图片
    renderer = TemplateRenderer()
    renderer.render(data)
    
    output_file = f"race_card_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    renderer.save(output_file)
    print("🎉 战绩卡生成完成！")


if __name__ == "__main__":
    main()
