#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
独立更新模块 - 支持命令行调用
用法：
    python update.py --check                 # 检查更新
    python update.py --download <url>        # 下载文件
    python update.py --version                # 显示当前版本
"""

import os
import sys
import re
import json
import tempfile
import argparse
import time
import datetime
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# ---------- 配置 ----------
OWNER = "GuitaristRin"
REPO = "Dacreator-GUI"
LOCAL_FILE = "Player_ID.dat"
BRANCHES = ["main", "master"]

GITHUB_MIRRORS = [
    "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file}",
    "https://cdn.jsdelivr.net/gh/{owner}/{repo}@{branch}/{file}",
    "https://ghproxy.com/https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file}",
    "https://hub.fastgit.xyz/{owner}/{repo}/raw/{branch}/{file}",
    "https://raw.staticdn.net/{owner}/{repo}/{branch}/{file}"
]

# ---------- 工具函数 ----------
def create_session_with_retries():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.timeout = (5, 15)
    return session

def get_local_version():
    """从 Player_ID.dat 读取本地版本"""
    local_path = Path(LOCAL_FILE)
    if not local_path.exists():
        return None
    version_pattern = re.compile(r'^\s*VERSION\s*=\s*([\d\.]+)\s*$', re.IGNORECASE)
    with open(local_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = version_pattern.match(line)
            if match:
                return match.group(1)
    return None

def get_github_version_with_mirrors():
    """从镜像源获取远程版本"""
    session = create_session_with_retries()
    for branch in BRANCHES:
        for mirror in GITHUB_MIRRORS:
            url = mirror.format(owner=OWNER, repo=REPO, branch=branch, file="Player_ID.dat")
            try:
                resp = session.get(url, timeout=(3, 5))
                if resp.status_code == 200:
                    content = resp.text
                    match = re.search(r'^\s*VERSION\s*=\s*([\d\.]+)', content, re.IGNORECASE | re.MULTILINE)
                    if match:
                        return match.group(1)
            except:
                continue
            time.sleep(0.5)
    return None

def get_latest_release_info_with_mirrors():
    """从镜像源获取最新 release 信息"""
    session = create_session_with_retries()
    api_mirrors = [
        f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest",
        f"https://hub.fastgit.xyz/{OWNER}/{REPO}/releases/latest",
        f"https://ghproxy.com/https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    ]
    for api_url in api_mirrors:
        try:
            resp = session.get(api_url, timeout=(3, 5))
            if resp.status_code == 200:
                data = resp.json()
                body = data.get('body', '').strip()
                assets = data.get('assets', [])
                download_url = None
                for asset in assets:
                    name = asset['name'].lower()
                    if name.endswith('.exe') or name.endswith('.msi'):
                        download_url = asset['browser_download_url']
                        break
                if not download_url and assets:
                    download_url = assets[0]['browser_download_url']
                if download_url and 'github.com' in download_url:
                    download_url = f"https://ghproxy.com/{download_url}"
                return body, download_url
        except:
            continue
        time.sleep(0.5)
    return None, None

def compare_versions(v1, v2):
    if not v2:
        return 0
    def normalize(v):
        parts = [int(x) for x in v.split('.')]
        while len(parts) < 3:
            parts.append(0)
        return parts[:3]
    v1_parts = normalize(v1)
    v2_parts = normalize(v2)
    for i in range(3):
        if v1_parts[i] < v2_parts[i]:
            return -1
        elif v1_parts[i] > v2_parts[i]:
            return 1
    return 0

def download_file(url, dest_path=None):
    """下载文件，支持断点续传，返回下载路径"""
    session = create_session_with_retries()
    if dest_path is None:
        file_name = url.split('/')[-1].split('?')[0]
        dest_path = os.path.join(tempfile.gettempdir(), file_name)

    resume_header = {}
    existing_size = 0
    if os.path.exists(dest_path):
        existing_size = os.path.getsize(dest_path)
        resume_header = {'Range': f'bytes={existing_size}-'}

    try:
        with session.get(url, stream=True, timeout=30, headers=resume_header) as r:
            if r.status_code == 416:  # 文件已完整
                return dest_path
            r.raise_for_status()
            mode = 'ab' if existing_size > 0 else 'wb'
            with open(dest_path, mode) as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return dest_path
    except Exception:
        return None

# ---------- 命令行入口 ----------
def main():
    parser = argparse.ArgumentParser(description="DACreator 更新模块")
    parser.add_argument('--check', action='store_true', help='检查更新')
    parser.add_argument('--download', metavar='URL', help='下载指定 URL 的文件')
    parser.add_argument('--version', action='store_true', help='显示本地版本')
    args = parser.parse_args()

    output = {}

    if args.version:
        local_ver = get_local_version()
        output['local_version'] = local_ver
        print(json.dumps(output, ensure_ascii=False))
        return

    if args.check:
        local_ver = get_local_version()
        remote_ver = get_github_version_with_mirrors()
        if not remote_ver:
            output['error'] = '无法获取远程版本'
        else:
            cmp = compare_versions(local_ver, remote_ver)
            output['local_version'] = local_ver
            output['remote_version'] = remote_ver
            output['has_update'] = (cmp < 0)
            if output['has_update']:
                release_body, download_url = get_latest_release_info_with_mirrors()
                output['release_notes'] = release_body
                output['download_url'] = download_url
        print(json.dumps(output, ensure_ascii=False))
        return

    if args.download:
        url = args.download
        path = download_file(url)
        if path:
            output['download_path'] = path
        else:
            output['error'] = '下载失败'
        print(json.dumps(output, ensure_ascii=False))
        return

    parser.print_help()

if __name__ == '__main__':
    main()