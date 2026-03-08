#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DACreator 搜索爬虫模块
通过用户名搜索获取成绩（无排名）
可作为独立CLI运行，也可被GUI导入
"""

import json
import pandas as pd
from typing import List, Dict, Optional

# 复用原 spider 的配置和基础类
from spider import CONFIG, ArcadeZoneCrawler


class ArcadeZoneSearchCrawler(ArcadeZoneCrawler):
    """
    通过用户名搜索获取成绩的爬虫（结果不含全国排名）
    继承原爬虫的基础方法
    """
    
    def __init__(self, username: str = None, season: int = None, callback=None):
        """初始化搜索爬虫"""
        super().__init__(username, season, callback)
        self._log("初始化搜索爬虫")

    def _search_request(self, payload: dict) -> Optional[dict]:
        """带重试的搜索请求 - 修复编码问题"""
        self.stats["total_requests"] += 1
        
        for retry in range(CONFIG["max_retry"]):
            try:
                response = self.session.post(
                    url=self.api_url,
                    headers=self.headers,
                    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    timeout=CONFIG["timeout"]
                )
                response.raise_for_status()
                self.stats["successful_requests"] += 1
                return response.json()
            except Exception as e:
                self.stats["failed_requests"] += 1
                self._log(f"搜索请求失败（第{retry+1}次）：{e}", "warning")
                if retry == CONFIG["max_retry"] - 1:
                    self._log("搜索请求最终失败", "error")
                    return None

    def search_by_name(self, name: str, course_id: Optional[int] = None) -> List[Dict]:
        """
        在指定赛道搜索用户的所有成绩
        返回记录列表，不包含排名信息
        """
        all_records = []
        page = 1

        while True:
            payload = {
                "page": page,
                "name": name,
                "season": self.season
            }
            if course_id is not None:
                payload["course"] = course_id

            data = self._search_request(payload)
            if not data:
                break

            page_records = self._parse_search_result(data)
            all_records.extend(page_records)

            pagination = data.get("pagination", {})
            if page >= pagination.get("last_page", 1):
                break
            page += 1

        return all_records

    def _parse_search_result(self, data: dict) -> List[dict]:
        """解析搜索结果，不包含排名信息"""
        result = []
        rank_list = data.get("list", [])
        car_styles_map = data.get("carStyles", {})

        for item in rank_list:
            course_id = item.get("course_id")
            course_name = CONFIG["course_name_map"].get(course_id, "未知赛道")
            direction = CONFIG["course_direction_map"].get(course_id, "未知方向")

            car_id = str(item.get("style_car_id", ""))
            car_name = car_styles_map.get(car_id, "未知车型")

            goal_time_ms = item.get("goal_time", 0)
            time_str = self._parse_time(goal_time_ms)
            play_time = item.get("play_dt", "").split(" ")[0]

            # 复用等级判断
            time_eval = self._judge_rank(course_name, direction, goal_time_ms)
            
            if self.callback:
                self.callback(f"赛道 {course_name}({direction}) 成绩：{time_str} → {time_eval}")

            record = {
                "コース": course_name,
                "ルート": direction,
                "タイム": time_str,
                "タイム評価": time_eval,
                "記録車種": car_name,
                "記録日": play_time
                # 没有“全国順位”
            }
            result.append(record)
            self.stats["total_records"] += 1

        return result

    def search_all_courses(self, name: str) -> List[Dict]:
        """遍历所有赛道，用搜索方式获取用户在每个赛道的成绩"""
        target_courses = CONFIG["target_courses"]
        all_records = []
        
        self._log(f"开始搜索用户 {name} 在所有赛道的成绩")
        
        for i, cid in enumerate(target_courses):
            progress = int((i + 1) / len(target_courses) * 100)
            if self.callback:
                self.callback(f"正在搜索第 {i+1}/{len(target_courses)} 个赛道", "info", progress)
            
            records = self.search_by_name(name, course_id=cid)
            if records:
                self._log(f"赛道 {cid} 找到 {len(records)} 条记录")
                all_records.extend(records)
            
        return all_records

    def search(self) -> pd.DataFrame:
        """执行搜索"""
        records = self.search_all_courses(self.target_username)
        
        if not records:
            self._log(f"未找到用户 {self.target_username} 的任何成绩", "warning")
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        self._log(f"搜索完成！共找到 {len(records)} 条记录")
        self._log(f"统计：总请求 {self.stats['total_requests']}，成功 {self.stats['successful_requests']}，失败 {self.stats['failed_requests']}")
        
        return df


# 对外暴露的函数
def crawl_data_by_search(username: str = None, season: int = None, callback=None) -> pd.DataFrame:
    """
    通过用户名搜索爬取成绩（无排名）
    :param username: 用户名，为None时从配置文件读取
    :param season: 赛季，为None时从配置文件读取
    :param callback: 回调函数，用于GUI进度显示
    :return: DataFrame
    """
    try:
        crawler = ArcadeZoneSearchCrawler(username, season, callback)
        df = crawler.search()
        return df
    except Exception as e:
        if callback:
            callback(f"搜索爬虫执行失败：{str(e)}", "error")
        else:
            print(f"❌ 搜索爬虫执行失败：{str(e)}")
        return pd.DataFrame()


# CLI入口
if __name__ == "__main__":
    print("=" * 60)
    print("DACreator 搜索模块 - 命令行版本")
    print("=" * 60)
    
    try:
        df = crawl_data_by_search()
        if not df.empty:
            print("\n📊 成绩预览：")
            print(df.to_string(index=False))
            
            # 保存CSV
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DAC成绩表_{timestamp}_无排名.csv"
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\n✅ 数据已保存至：{filename}")
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 程序出错：{str(e)}")
    
    input("\n按回车键退出...")