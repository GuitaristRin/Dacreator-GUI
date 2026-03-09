import os
import sys
import re
import tempfile
import subprocess
import time
import json
import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    print("错误：需要requests库。请运行 'pip install requests' 安装。")
    sys.exit(1)

# GitHub仓库信息
OWNER = "GuitaristRin"
REPO = "Dacreator-GUI"
LOCAL_FILE = "Player_ID.dat"
LOG_FILE = "update_log.txt"  # 日志文件名
CACHE_FILE = "update_cache.json"
BRANCHES = ["main", "master"]

# 备用镜像源（按优先级排序）
GITHUB_MIRRORS = [
    "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file}",
    "https://cdn.jsdelivr.net/gh/{owner}/{repo}@{branch}/{file}",
    "https://ghproxy.com/https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file}",
    "https://hub.fastgit.xyz/{owner}/{repo}/raw/{branch}/{file}",
    "https://raw.staticdn.net/{owner}/{repo}/{branch}/{file}"
]

class UpdateLogger:
    """日志管理类"""
    def __init__(self, log_file=LOG_FILE):
        self.log_file = Path(log_file)
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """确保日志文件存在"""
        if not self.log_file.exists():
            self.log_file.touch()
    
    def get_last_update_time(self):
        """获取上次更新时间"""
        if not self.log_file.exists():
            return None
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 从最后一行往前找更新时间
                for line in reversed(lines):
                    if line.startswith('更新时间：'):
                        return line.strip().replace('更新时间：', '')
                return None
        except Exception as e:
            print(f"读取日志文件时出错：{e}")
            return None
    
    def log_update(self, local_version, remote_version, status, details=""):
        """记录更新操作
        status: '检查'、'更新成功'、'更新失败'、'取消更新'、'已是最新'
        """
        try:
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{current_time}] "
            log_entry += f"本地版本：{local_version} | "
            log_entry += f"远程版本：{remote_version} | "
            log_entry += f"状态：{status}"
            if details:
                log_entry += f" | 详情：{details}"
            log_entry += "\n"
            
            # 同时记录一个专门的"更新时间"行
            if status in ['更新成功', '检查']:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            else:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                    
        except Exception as e:
            print(f"写入日志时出错：{e}")
    
    def show_last_update(self):
        """显示上次更新时间"""
        last_time = self.get_last_update_time()
        if last_time:
            # 从日志中提取更详细的上次更新信息
            last_update_info = self.get_last_update_info()
            print(f"📅 上次更新时间：{last_time}")
            if last_update_info:
                print(f"📋 上次更新详情：{last_update_info}")
        else:
            print("📅 这是首次运行更新程序")
        print("-" * 50)
    
    def get_last_update_info(self):
        """获取上次更新的详细信息"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if '更新时间：' not in line and ('更新成功' in line or '检查' in line):
                        return line.strip()
                return None
        except:
            return None

def create_session_with_retries():
    """创建带重试机制的requests session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # 总重试次数
        backoff_factor=1,  # 重试间隔：1, 2, 4秒
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.timeout = (5, 15)  # (连接超时, 读取超时)
    return session

def get_github_version_with_mirrors(logger=None):
    """使用多个镜像源尝试获取GitHub版本"""
    session = create_session_with_retries()
    
    for branch in BRANCHES:
        for mirror_template in GITHUB_MIRRORS:
            url = mirror_template.format(
                owner=OWNER, 
                repo=REPO, 
                branch=branch, 
                file="Player_ID.dat"
            )
            
            print(f"尝试从 {url} 获取版本信息...")
            
            try:
                # 使用较短的超时时间，快速失败
                resp = session.get(url, timeout=(3, 5))
                if resp.status_code == 200:
                    content = resp.text
                    version_pattern = re.compile(r'^\s*VERSION\s*=\s*([\d\.]+)\s*$', re.IGNORECASE | re.MULTILINE)
                    match = version_pattern.search(content)
                    if match:
                        version = match.group(1)
                        print(f"✓ 成功从 {url} 获取版本信息")
                        if logger:
                            logger.log_update("未知", version, "检查", f"从镜像源获取成功：{url}")
                        return version
                    else:
                        print(f"  ⚠ 文件内容中未找到VERSION")
                elif resp.status_code == 404:
                    print(f"  ⚠ 文件不存在 (404)")
                else:
                    print(f"  ⚠ 返回状态码: {resp.status_code}")
            except requests.exceptions.Timeout:
                print(f"  ⚠ 连接超时")
            except requests.exceptions.ConnectionError:
                print(f"  ⚠ 连接失败")
            except Exception as e:
                print(f"  ⚠ 其他错误: {str(e)[:50]}")
            
            # 短暂延迟，避免请求过快
            time.sleep(0.5)
    
    print("\n❌ 所有镜像源都尝试失败，无法获取GitHub版本信息。")
    if logger:
        logger.log_update("未知", "未知", "检查失败", "所有镜像源都无法访问")
    return None

def get_latest_release_info_with_mirrors(logger=None):
    """使用多个镜像源尝试获取release信息"""
    session = create_session_with_retries()
    
    # GitHub API的镜像源
    api_mirrors = [
        f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest",
        f"https://hub.fastgit.xyz/{OWNER}/{REPO}/releases/latest",
        f"https://ghproxy.com/https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    ]
    
    for api_url in api_mirrors:
        print(f"尝试从 {api_url} 获取release信息...")
        
        try:
            resp = session.get(api_url, timeout=(3, 5))
            if resp.status_code == 200:
                data = resp.json()
                body = data.get('body', '（无描述）').strip()
                
                # 获取下载链接，可能需要转换镜像
                assets = data.get('assets', [])
                if not assets:
                    print("  ⚠ 没有可下载的文件")
                    continue
                
                # 优先选择exe/msi文件
                download_url = None
                for asset in assets:
                    name = asset['name'].lower()
                    if name.endswith('.exe') or name.endswith('.msi'):
                        download_url = asset['browser_download_url']
                        break
                
                if not download_url:
                    download_url = assets[0]['browser_download_url']
                
                # 如果是GitHub官方链接，尝试转换为镜像链接
                if 'github.com' in download_url:
                    download_url = convert_to_mirror_url(download_url)
                
                print(f"✓ 成功获取release信息")
                if logger:
                    logger.log_update("未知", "未知", "检查", f"获取release信息成功")
                return body, download_url
            else:
                print(f"  ⚠ 返回状态码: {resp.status_code}")
        except Exception as e:
            print(f"  ⚠ 获取失败: {str(e)[:50]}")
        
        time.sleep(0.5)
    
    print("\n❌ 无法获取release信息。")
    if logger:
        logger.log_update("未知", "未知", "检查失败", "无法获取release信息")
    return None, None

def convert_to_mirror_url(original_url):
    """将GitHub官方下载链接转换为镜像链接"""
    if 'ghproxy.com' in original_url:
        return original_url
    
    # 检查是否包含特定模式
    if 'github.com' in original_url and '/releases/download/' in original_url:
        # 使用ghproxy作为代理
        return f"https://ghproxy.com/{original_url}"
    
    return original_url

def get_local_version():
    """从同目录下的Player_ID.dat读取版本号"""
    local_path = Path(LOCAL_FILE)
    if not local_path.exists():
        print(f"错误：本地文件 {LOCAL_FILE} 不存在。")
        sys.exit(1)

    version_pattern = re.compile(r'^\s*VERSION\s*=\s*([\d\.]+)\s*$', re.IGNORECASE)
    with open(local_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = version_pattern.match(line)
            if match:
                return match.group(1)
    print(f"错误：在 {LOCAL_FILE} 中未找到 VERSION 定义。")
    sys.exit(1)

def compare_versions(v1, v2):
    """
    比较两个版本号字符串（如'2.0.1'）。
    返回：
        -1 如果 v1 < v2
        0  如果 v1 == v2
        1  如果 v1 > v2
    """
    if not v2:  # 如果获取不到GitHub版本，认为没有更新
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

def download_file_with_resume(url, dest_path, logger=None, local_ver=None, remote_ver=None):
    """支持断点续传的下载"""
    session = create_session_with_retries()
    
    # 获取文件大小（如果存在）
    resume_header = {}
    if os.path.exists(dest_path):
        existing_size = os.path.getsize(dest_path)
        resume_header = {'Range': f'bytes={existing_size}-'}
        print(f"发现已下载部分：{existing_size} 字节，尝试断点续传...")
    else:
        existing_size = 0
    
    try:
        with session.get(url, stream=True, timeout=30, headers=resume_header) as r:
            if r.status_code == 416:  # Range Not Satisfiable，文件已完整
                print("文件已完整下载")
                if logger and local_ver and remote_ver:
                    logger.log_update(local_ver, remote_ver, "更新成功", "文件已存在，无需重复下载")
                return True
            
            r.raise_for_status()
            
            # 获取总大小
            total_size = int(r.headers.get('content-length', 0)) + existing_size
            
            mode = 'ab' if existing_size > 0 else 'wb'
            with open(dest_path, mode) as f:
                downloaded = existing_size
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            percent = downloaded * 100 // total_size
                            print(f"\r下载进度：{percent}% ({downloaded}/{total_size} 字节)", end='', flush=True)
            print()  # 换行
        
        if logger and local_ver and remote_ver:
            logger.log_update(local_ver, remote_ver, "更新成功", f"下载完成：{dest_path}")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"\n下载失败：{error_msg}")
        if logger and local_ver and remote_ver:
            logger.log_update(local_ver, remote_ver, "更新失败", f"下载失败：{error_msg}")
        return False

def load_cache():
    """加载缓存信息"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"last_check": None, "github_version": None, "release_info": None}

def save_cache(cache_data):
    """保存缓存信息"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except:
        pass

def main():
    # 初始化日志
    logger = UpdateLogger()
    
    print("=" * 50)
    print("更新检查程序")
    print("=" * 50)
    
    # 显示上次更新时间
    logger.show_last_update()
    
    # 获取本地版本
    local_ver = get_local_version()
    print(f"本地版本：{local_ver}")
    
    # 获取GitHub版本（使用镜像源）
    print("\n尝试获取远程版本信息...")
    github_ver = get_github_version_with_mirrors(logger)
    
    if not github_ver:
        print("\n⚠ 无法获取远程版本信息，跳过更新检查。")
        
        # 尝试使用缓存
        cache = load_cache()
        if cache.get("github_version"):
            print("使用缓存版本信息...")
            github_ver = cache["github_version"]
        else:
            logger.log_update(local_ver, "未知", "检查失败", "无法获取远程版本信息")
            input("按回车键退出...")
            return
    
    # 更新缓存
    cache = load_cache()
    cache["github_version"] = github_ver
    cache["last_check"] = datetime.datetime.now().isoformat()
    save_cache(cache)
    
    print(f"远程版本：{github_ver}")
    
    # 比较版本
    cmp = compare_versions(local_ver, github_ver)
    if cmp >= 0:
        print("\n✅ 当前已是最新版本。")
        logger.log_update(local_ver, github_ver, "已是最新")
        input("按回车键退出...")
        return
    
    # 获取release信息
    print("\n发现新版本！正在获取更新信息...")
    release_body, download_url = get_latest_release_info_with_mirrors(logger)
    
    if not release_body:
        print("⚠ 无法获取详细更新信息，但仍然可以尝试更新。")
        answer = input("是否继续更新？(y/N): ").strip().lower()
        if answer != 'y':
            print("已取消更新。")
            logger.log_update(local_ver, github_ver, "取消更新", "用户取消")
            return
    else:
        print("\n📋 最新版本描述：")
        print("-" * 40)
        print(release_body)
        print("-" * 40)
        if download_url:
            print(f"下载链接：{download_url}")
        
        answer = input("\n是否下载并安装更新？(y/N): ").strip().lower()
        if answer != 'y':
            print("已取消更新。")
            logger.log_update(local_ver, github_ver, "取消更新", "用户取消")
            input("按回车键退出...")
            return
    
    if not download_url:
        print("错误：无法获取下载链接。")
        logger.log_update(local_ver, github_ver, "更新失败", "无法获取下载链接")
        input("按回车键退出...")
        return
    
    # 下载安装包
    print("\n开始下载安装包...")
    temp_dir = tempfile.gettempdir()
    file_name = download_url.split('/')[-1].split('?')[0]  # 处理带参数的URL
    dest_path = os.path.join(temp_dir, f"{REPO}_{github_ver}_{file_name}")
    
    if not download_file_with_resume(download_url, dest_path, logger, local_ver, github_ver):
        print("下载失败，更新终止。")
        input("按回车键退出...")
        return
    
    print(f"\n✅ 安装包已下载到：{dest_path}")
    
    # 启动安装程序
    try:
        if sys.platform.startswith('win'):
            os.startfile(dest_path)
        else:
            if sys.platform == 'darwin':
                subprocess.run(['open', dest_path])
            else:
                subprocess.run(['xdg-open', dest_path])
        print("安装程序已启动，请按照指引完成安装。")
        logger.log_update(local_ver, github_ver, "更新成功", f"安装程序已启动：{dest_path}")
    except Exception as e:
        error_msg = str(e)
        print(f"无法启动安装程序：{error_msg}")
        print(f"请手动运行安装包：{dest_path}")
        logger.log_update(local_ver, github_ver, "更新成功", f"下载完成但无法自动启动：{error_msg}")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()