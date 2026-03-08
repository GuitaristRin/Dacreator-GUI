#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DACreator 核心爬虫模块
用于爬取ArcadeZone的计时赛成绩
可作为独立CLI运行，也可被GUI导入
"""

import json
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

# 配置信息
CONFIG = {
    "base_web_url": "https://arcadezone.cn/ranking#timetrial",
    "api_url": "https://arcadezone.cn/ranking/timetrial",
    "season": 5,  # 默认值，会被配置文件覆盖
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://arcadezone.cn/ranking#timetrial",
        "Origin": "https://arcadezone.cn",
    },
    "player_id_path": "Player_ID.dat",
    "standard_time_path": "./assets/rank.csv",  # 标准等级时间库路径
    "timeout": 30,
    "max_retry": 3,
    "course_name_map": {
        0: "秋名湖", 2: "秋名湖", 4: "妙義", 6: "妙義", 8: "赤城", 10: "赤城",
        12: "秋名", 14: "秋名", 16: "伊吕波坂", 18: "伊吕波坂", 20: "筑波", 22: "筑波",
        24: "八方原", 26: "八方原", 28: "长尾", 30: "长尾", 32: "椿线", 34: "椿线",
        36: "碓冰", 38: "碓冰", 40: "定峰", 42: "定峰", 44: "土坂", 46: "土坂",
        48: "秋名雪", 50: "秋名雪", 52: "箱根", 54: "箱根", 56: "枫树线", 58: "枫树线",
        60: "七曲", 62: "七曲", 64: "群馬赛车场", 66: "群馬赛车场", 68: "小田原", 70: "小田原",
        72: "筑波雪", 74: "筑波雪", 76: "矢矩", 78: "矢矩", 80: "土坂雪", 82: "土坂雪",
        84: "真鹤", 86: "真鹤", 88: "碓冰雪", 90: "碓冰雪", 92: "秋名雨", 94: "秋名雨"
    },
    "course_direction_map": {
        0: "逆时针", 2: "顺时针", 4: "下坡", 6: "上坡", 8: "下坡", 10: "上坡",
        12: "下坡", 14: "上坡", 16: "下坡", 18: "逆行", 20: "去路", 22: "归路",
        24: "去路", 26: "归路", 28: "下坡", 30: "上坡", 32: "下坡", 34: "上坡",
        36: "逆时针", 38: "顺时针", 40: "下坡", 42: "上坡", 44: "去路", 46: "归路",
        48: "下坡", 50: "上坡", 52: "下坡", 54: "上坡", 56: "下坡", 58: "上坡",
        60: "下坡", 62: "上坡", 64: "去路", 66: "归路", 68: "顺行", 70: "逆行",
        72: "去路", 74: "归路", 76: "下坡", 78: "上坡", 80: "去路", 82: "归路",
        84: "顺行", 86: "逆行", 88: "逆时针", 90: "顺时针", 92: "下坡", 94: "上坡"
    },
    "rank_priority": ["LEGEND", "MASTER+", "MASTER", "PROFESSIONAL", "EXPERT", "SPECIALIST", "REGULAR"],
    # 需要爬取的赛道ID列表
    "target_courses": [
        0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30,
        32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60,
        62, 64, 66, 68, 70, 72, 74, 76, 78, 80, 82, 84, 86, 88, 90, 92, 94
    ]
}

class ArcadeZoneCrawler:
    """ArcadeZone爬虫核心类"""
    
    def __init__(self, username: str = None, season: int = None, callback=None):
        """
        初始化爬虫
        :param username: 用户名，如果为None则从配置文件读取
        :param season: 赛季，如果为None则从配置文件读取
        :param callback: 回调函数，用于GUI进度显示
        """
        self.headers = CONFIG["headers"].copy()
        self.api_url = CONFIG["api_url"]
        self.base_web_url = CONFIG["base_web_url"]
        self.callback = callback
        
        # 加载配置
        if season is not None:
            self.season = season
        else:
            self.season = self._load_season()
            
        if username is not None:
            self.target_username = username
        else:
            self.target_username = self._load_target_username()
            
        self.standard_times = self._load_standard_times()
        self.session = requests.Session()
        self._get_csrf_token()
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_records": 0
        }

    def _log(self, message: str, level: str = "info"):
        """日志回调"""
        if self.callback:
            self.callback(message, level)
        else:
            print(f"[{level.upper()}] {message}")

    def _load_season(self) -> int:
        """从配置文件加载赛季"""
        default_season = CONFIG["season"]
        try:
            with open(CONFIG["player_id_path"], "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line.startswith("SEASON = "):
                    season = int(line.split("=")[1].strip())
                    self._log(f"加载赛季配置：第 {season} 赛季")
                    return season
            self._log(f"使用默认赛季：第 {default_season} 赛季", "warning")
            return default_season
        except Exception as e:
            self._log(f"读取赛季配置失败，使用默认值：{e}", "warning")
            return default_season

    def _load_target_username(self) -> str:
        """从配置文件加载目标用户名"""
        try:
            with open(CONFIG["player_id_path"], "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line.startswith("ID = "):
                    username = line.split("=")[1].strip()
                    self._log(f"加载目标用户：{username}")
                    return username
            raise ValueError("配置文件中未找到 ID 行")
        except FileNotFoundError:
            raise Exception(f"未找到配置文件：{CONFIG['player_id_path']}")
        except Exception as e:
            raise Exception(f"读取配置文件失败：{str(e)}")

    def _load_standard_times(self) -> pd.DataFrame:
        """加载等级标准库"""
        try:
            df = pd.read_csv(CONFIG["standard_time_path"], encoding="utf-8-sig")
            required_cols = ["Course", "Direction"] + CONFIG["rank_priority"]
            for col in required_cols:
                if col not in df.columns:
                    raise Exception(f"标准库缺少必填列：{col}")
            for rank in CONFIG["rank_priority"]:
                df[rank] = df[rank].fillna("99'99\"999")
            self._log(f"加载等级标准库，共{len(df)}条赛道标准")
            return df
        except FileNotFoundError:
            raise Exception(f"未找到等级标准库：{CONFIG['standard_time_path']}")
        except Exception as e:
            raise Exception(f"读取等级标准库失败：{str(e)}")

    def _get_csrf_token(self):
        """获取CSRF Token"""
        try:
            response = self.session.get(
                self.base_web_url,
                headers=self.headers,
                timeout=CONFIG["timeout"]
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_meta = soup.find("meta", attrs={"name": "csrf-token"})
            if csrf_meta:
                csrf_token = csrf_meta.get("content")
                self.headers["X-CSRF-TOKEN"] = csrf_token
                self._log("获取CSRF Token成功")
            else:
                raise Exception("网页中未找到CSRF Token")
        except Exception as e:
            raise Exception(f"获取CSRF Token失败：{str(e)}")

    def _str_time_to_ms(self, time_str: str) -> int:
        """时间字符串转毫秒"""
        try:
            if ":" in time_str and "." in time_str:
                minute, rest = time_str.split(":")
                second, ms = rest.split(".")
                return int(minute)*60000 + int(second)*1000 + int(ms)
            elif "'" in time_str and "\"" in time_str:
                minute, rest = time_str.split("'")
                second, ms = rest.split("\"")
                return int(minute)*60000 + int(second)*1000 + int(ms)
            else:
                return 99999999
        except:
            return 99999999

    def _judge_rank(self, course: str, direction: str, score_ms: int) -> str:
        """判断等级"""
        mask = (self.standard_times["Course"] == course) & (self.standard_times["Direction"] == direction)
        if not mask.any():
            self._log(f"未找到{course}-{direction}的等级标准", "warning")
            return "未知评价"
        
        standard_row = self.standard_times[mask].iloc[0]
        for rank in CONFIG["rank_priority"]:
            standard_ms = self._str_time_to_ms(str(standard_row[rank]))
            if score_ms <= standard_ms:
                return rank
        return "ROOKIE"

    def _request_api(self, page: int, course_id: int) -> Optional[Dict]:
        """请求API"""
        payload = {
            "page": page,
            "season": self.season,
            "course": course_id
        }
        
        self.stats["total_requests"] += 1
        
        for retry in range(CONFIG["max_retry"]):
            try:
                response = self.session.post(
                    url=self.api_url,
                    headers=self.headers,
                    data=json.dumps(payload, ensure_ascii=False),
                    timeout=CONFIG["timeout"]
                )
                response.raise_for_status()
                self.stats["successful_requests"] += 1
                return response.json()
            except requests.exceptions.RequestException as e:
                self.stats["failed_requests"] += 1
                if retry == CONFIG["max_retry"] - 1:
                    self._log(f"赛道{course_id}第{page}页请求失败", "error")
                    return None
                continue

    def _parse_time(self, ms: int) -> str:
        """毫秒转时间字符串"""
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{minutes}:{seconds:02d}.{millis:03d}"

    def _parse_rank_data(self, data: Dict, course_id: int, current_page: int) -> List[Dict]:
        """解析排名数据"""
        result = []
        rank_list = data.get("list", [])
        car_styles_map = data.get("carStyles", {})
        course_name = CONFIG["course_name_map"].get(course_id, "未知赛道")
        direction = CONFIG["course_direction_map"].get(course_id, "未知方向")
        per_page = data.get("pagination", {}).get("per_page", 15)

        for idx, item in enumerate(rank_list):
            user_info = item.get("userinfo", {})
            username = user_info.get("username", "")
            if username != self.target_username:
                continue

            national_rank = (current_page - 1) * per_page + idx + 1
            car_id = str(item.get("style_car_id", ""))
            car_name = car_styles_map.get(car_id, "未知车型")
            goal_time_ms = item.get("goal_time", 0)
            time_str = self._parse_time(goal_time_ms)
            play_time = item.get("play_dt", "").split(" ")[0]

            time_eval = self._judge_rank(course_name, direction, goal_time_ms)
            self._log(f"赛道 {course_name}({direction}) 成绩：{time_str} → {time_eval}")

            rank_info = {
                "コース": course_name,
                "ルート": direction,
                "タイム": time_str,
                "タイム評価": time_eval,
                "記録車種": car_name,
                "全国順位": str(national_rank),
                "記録日": play_time
            }
            result.append(rank_info)
            self.stats["total_records"] += 1
        
        return result

    def crawl_course(self, course_id: int) -> List[Dict]:
        """爬取单个赛道"""
        course_name = CONFIG["course_name_map"].get(course_id, "未知赛道")
        direction = CONFIG["course_direction_map"].get(course_id, "未知方向")
        self._log(f"开始爬取赛道 {course_id} ({course_name} {direction})")
        
        all_matched_data = []
        first_page_data = self._request_api(page=1, course_id=course_id)
        
        if not first_page_data:
            return all_matched_data

        page1_data = self._parse_rank_data(first_page_data, course_id, current_page=1)
        all_matched_data.extend(page1_data)

        total_pages = first_page_data.get("pagination", {}).get("last_page", 1)
        self._log(f"赛道 {course_id} 总页数：{total_pages}")

        for page in range(2, total_pages + 1):
            page_data = self._request_api(page=page, course_id=course_id)
            if not page_data:
                continue
            matched_data = self._parse_rank_data(page_data, course_id, current_page=page)
            all_matched_data.extend(matched_data)

        self._log(f"赛道 {course_id} 完成，找到 {len(all_matched_data)} 条记录")
        return all_matched_data

    def crawl_all(self, course_list: List[int] = None) -> pd.DataFrame:
        """
        爬取所有赛道
        :param course_list: 赛道ID列表，为None时使用默认列表
        :return: DataFrame
        """
        if course_list is None:
            course_list = CONFIG["target_courses"]
        
        self._log(f"开始爬取所有赛道，共 {len(course_list)} 个")
        final_result = []
        
        for i, course_id in enumerate(course_list):
            progress = int((i + 1) / len(course_list) * 100)
            if self.callback:
                self.callback(f"正在爬取第 {i+1}/{len(course_list)} 个赛道", "info", progress)
            
            data = self.crawl_course(course_id)
            final_result.extend(data)

        if not final_result:
            self._log(f"未找到用户 {self.target_username} 的任何成绩", "warning")
            return pd.DataFrame()

        csv_columns = ["コース", "ルート", "タイム", "タイム評価", "記録車種", "全国順位", "記録日"]
        df = pd.DataFrame(final_result)[csv_columns]
        
        self._log(f"爬取完成！共找到 {len(final_result)} 条记录")
        self._log(f"统计：总请求 {self.stats['total_requests']}，成功 {self.stats['successful_requests']}，失败 {self.stats['failed_requests']}")
        
        return df

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats


# 对外暴露的函数
def crawl_data(username: str = None, season: int = None, callback=None) -> pd.DataFrame:
    """
    爬取用户成绩
    :param username: 用户名，为None时从配置文件读取
    :param season: 赛季，为None时从配置文件读取
    :param callback: 回调函数，用于GUI进度显示
    :return: DataFrame
    """
    try:
        crawler = ArcadeZoneCrawler(username, season, callback)
        df = crawler.crawl_all()
        return df
    except Exception as e:
        if callback:
            callback(f"爬虫执行失败：{str(e)}", "error")
        else:
            print(f"❌ 爬虫执行失败：{str(e)}")
        return pd.DataFrame()


# CLI入口
if __name__ == "__main__":
    print("=" * 60)
    print("DACreator 爬虫模块 - 命令行版本")
    print("=" * 60)
    
    try:
        df = crawl_data()
        if not df.empty:
            print("\n📊 成绩预览：")
            print(df.to_string(index=False))
            
            # 保存CSV
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DAC成绩表_{timestamp}.csv"
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\n✅ 数据已保存至：{filename}")
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 程序出错：{str(e)}")
    
    input("\n按回车键退出...")