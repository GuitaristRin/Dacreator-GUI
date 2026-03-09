#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DACreator GUI 完整版
- 支持 Windows 深色/浅色主题自动跟随
- 流畅的动画效果
- 使用 Emoji 替代图标
- 本地微软雅黑字体
- 对接爬虫核心模块
- 实时进度显示
- 多语言支持 (从assets/lang/动态加载)
- 集成更新功能
- 历史记录数据库
"""

import sys
import os
import subprocess
import site
import logging
import time
import json
import glob
import tempfile
from typing import List, Optional, Dict
from datetime import datetime
import threading
import database

# 依赖列表
REQUIRED_PACKAGES = [
    'PyQt5',
    'pandas',
    'requests',
    'beautifulsoup4',
    'pillow'
]

PYPI_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def is_in_virtualenv() -> bool:
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )


def get_venv_python() -> str:
    if sys.platform == "win32":
        return os.path.join("venv", "Scripts", "python.exe")
    else:
        return os.path.join("venv", "bin", "python")


def create_activation_script():
    if sys.platform == "win32":
        with open("run_gui.bat", "w", encoding="utf-8") as f:
            f.write("""@echo off
chcp 65001 > nul
echo 正在激活虚拟环境...
call venv\\Scripts\\activate.bat
echo 启动 DACreator GUI...
python dacreator_gui.py --venv-activated
pause
""")
        print("✅ 已创建 run_gui.bat，下次请双击此文件运行")


def ensure_virtualenv_and_dependencies():
    if "--venv-activated" in sys.argv:
        print("✅ 已在虚拟环境中，继续启动...")
        return True

    venv_python = get_venv_python()
    venv_exists = os.path.exists(venv_python)

    print("\n" + "="*60)
    print("DACreator 环境检查")
    print("="*60)

    if not venv_exists:
        print("📦 未检测到虚拟环境，正在创建 venv ...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            print("✅ 虚拟环境创建成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ 创建虚拟环境失败：{e}")
            input("\n按回车键退出...")
            sys.exit(1)

        print("\n📥 正在安装依赖，请稍候...")
        print(f"镜像源：{PYPI_MIRROR}")
        pip_cmd = [venv_python, '-m', 'pip', 'install', '-i', PYPI_MIRROR] + REQUIRED_PACKAGES
        try:
            subprocess.run(pip_cmd, check=True)
            print("✅ 依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败：{e}")
            input("\n按回车键退出...")
            sys.exit(1)

        create_activation_script()

        print("\n" + "="*60)
        print("✅ 虚拟环境已准备就绪！")
        print("请双击 run_gui.bat 来启动程序")
        print("="*60)
        input("\n按回车键退出...")
        sys.exit(0)

    if not is_in_virtualenv():
        print("⚠️  当前未在虚拟环境中")
        print("\n请使用以下方式启动程序：")
        print("1. 双击 run_gui.bat（推荐）")
        print("2. 或手动激活虚拟环境后运行：")
        if sys.platform == "win32":
            print("   venv\\Scripts\\activate")
            print("   python dacreator_gui.py --venv-activated")
        
        if not os.path.exists("run_gui.bat"):
            create_activation_script()
        
        input("\n按回车键退出...")
        sys.exit(0)

    print("✅ 已在虚拟环境中，检查依赖完整性...")
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            if pkg == 'PyQt5':
                __import__('PyQt5')
            else:
                __import__(pkg.replace('-', '_'))
        except ImportError:
            print(f"  缺失：{pkg}")
            missing.append(pkg)

    if missing:
        print(f"\n📥 检测到缺失依赖：{missing}，正在安装...")
        pip_cmd = [sys.executable, '-m', 'pip', 'install', '-i', PYPI_MIRROR] + missing
        try:
            subprocess.run(pip_cmd, check=True)
            print("✅ 依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败：{e}")
            input("\n按回车键退出...")
            sys.exit(1)
    else:
        print("✅ 所有依赖已安装")

    print("="*60 + "\n")
    return True


# 导入 PyQt5
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QListWidget, QListWidgetItem, QStackedWidget, QLabel, QPushButton,
        QComboBox, QFormLayout, QLineEdit, QSpinBox, QTextEdit, QMessageBox,
        QGraphicsOpacityEffect, QFrame, QSizePolicy, QProgressBar, QFileDialog,
        QTableWidget, QTableWidgetItem, QHeaderView
    )
    from PyQt5.QtCore import (
        Qt, QSettings, QSize, pyqtSignal, QPropertyAnimation, 
        QEasingCurve, QRect, QTimer, QPoint, QThread
    )
    from PyQt5.QtGui import (
        QIcon, QPixmap, QFont, QFontDatabase, QColor, QPalette, 
        QLinearGradient, QBrush, QTextCursor
    )
except ImportError as e:
    print(f"❌ 导入 PyQt5 失败：{e}")
    input("\n按回车键退出...")
    sys.exit(1)

# 导入核心模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from spider import crawl_data
    from spider_search import crawl_data_by_search
    from core import save_table_image, CONFIG as CORE_CONFIG
    import update  # 导入更新模块
except ImportError as e:
    print(f"❌ 导入核心模块失败：{e}")
    print("请确保 spider.py, spider_search.py, core.py, update.py 在同一目录下")
    input("\n按回车键退出...")
    sys.exit(1)


class LanguageManager:
    """语言管理器，从lang目录动态加载语言文件"""
    
    def __init__(self):
        self.current_lang_code = None
        self.translations: Dict[str, str] = {}
        self.available_languages: Dict[str, str] = {}  # code -> display_name
        self.lang_dir = os.path.join("assets", "lang")
        
        # 扫描可用语言
        self.scan_languages()
        
        # 如果没有找到任何语言文件，报错退出
        if not self.available_languages:
            error_msg = "❌ 错误：未找到语言文件！\n\n请在 assets/lang 目录下放置语言文件，例如：\n- simp_chi.lang (简体中文)\n- trad_chi.lang (繁体中文)\n- us_en.lang (英文)"
            print(error_msg)
            QMessageBox.critical(None, "语言文件缺失", error_msg)
            sys.exit(1)
    
    def scan_languages(self) -> None:
        """扫描lang目录下所有.lang文件，读取语言信息"""
        self.available_languages.clear()
        
        if not os.path.exists(self.lang_dir):
            os.makedirs(self.lang_dir, exist_ok=True)
            return
        
        # 查找所有.lang文件
        lang_files = glob.glob(os.path.join(self.lang_dir, "*.lang"))
        
        for lang_file in lang_files:
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and "=" in line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            if key.strip() == "LANG":
                                lang_code = os.path.splitext(os.path.basename(lang_file))[0]
                                display_name = value.strip().strip('"')
                                self.available_languages[lang_code] = display_name
                                break
            except Exception as e:
                print(f"⚠️ 读取语言文件失败 {lang_file}: {e}")
    
    def load_language(self, lang_code: str) -> bool:
        """
        加载指定语言文件
        :param lang_code: 语言代码 (如: simp_chi, trad_chi, us_en)
        :return: 是否加载成功
        """
        lang_file = os.path.join(self.lang_dir, f"{lang_code}.lang")
        if not os.path.exists(lang_file):
            print(f"❌ 语言文件不存在：{lang_file}")
            return False
        
        self.translations.clear()
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        self.translations[key.strip()] = value.strip().strip('"')
            
            # 验证是否包含LANG标识
            if "LANG" in self.translations:
                self.current_lang_code = lang_code
                print(f"✅ 已加载语言：{self.translations['LANG']}")
                return True
            else:
                print(f"❌ 语言文件格式错误：缺少LANG标识")
                return False
                
        except Exception as e:
            print(f"❌ 加载语言文件失败：{e}")
            return False
    
    def get(self, key: str, default: str = None) -> str:
        """
        获取翻译文本
        :param key: 翻译键名
        :param default: 默认值
        :return: 翻译后的文本
        """
        return self.translations.get(key, default if default is not None else key)
    
    def get_language_display_names(self) -> List[str]:
        """获取所有可用语言的显示名称列表"""
        return list(self.available_languages.values())
    
    def get_lang_code_by_display_name(self, display_name: str) -> str:
        """根据显示名称获取语言代码"""
        for code, name in self.available_languages.items():
            if name == display_name:
                return code
        # 如果没有找到，返回第一个可用的语言代码
        if self.available_languages:
            return list(self.available_languages.keys())[0]
        return None
    
    def get_display_name_by_code(self, lang_code: str) -> str:
        """根据语言代码获取显示名称"""
        return self.available_languages.get(lang_code, list(self.available_languages.values())[0] if self.available_languages else "Unknown")


class ThemeManager:
    """主题管理器，支持深色/浅色主题"""
    
    LIGHT_THEME = {
        "bg_primary": "#f5f5f5",
        "bg_secondary": "#ffffff",
        "bg_sidebar": "#2c3e50",
        "bg_sidebar_hover": "#3d566e",
        "bg_sidebar_selected": "#34495e",
        "text_primary": "#2c3e50",
        "text_secondary": "#7f8c8d",
        "text_light": "#ecf0f1",
        "border": "#bdc3c7",
        "accent": "#3498db",
        "accent_hover": "#5dade2",
        "success": "#27ae60",
        "success_hover": "#2ecc71",
        "warning": "#f39c12",
        "error": "#e74c3c"
    }
    
    DARK_THEME = {
        "bg_primary": "#1e1e1e",
        "bg_secondary": "#2d2d2d",
        "bg_sidebar": "#1a1a1a",
        "bg_sidebar_hover": "#2a2a2a",
        "bg_sidebar_selected": "#333333",
        "text_primary": "#ffffff",
        "text_secondary": "#b0b0b0",
        "text_light": "#ffffff",
        "border": "#404040",
        "accent": "#3498db",
        "accent_hover": "#5dade2",
        "success": "#27ae60",
        "success_hover": "#2ecc71",
        "warning": "#f39c12",
        "error": "#e74c3c"
    }
    
    @staticmethod
    def detect_windows_theme():
        """检测 Windows 深色/浅色主题"""
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if value == 1 else "dark"
            except:
                pass
        return "light"  # 默认浅色
    
    @staticmethod
    def get_current_theme():
        """获取当前主题"""
        theme_name = ThemeManager.detect_windows_theme()
        return ThemeManager.LIGHT_THEME if theme_name == "light" else ThemeManager.DARK_THEME


class FontManager:
    """字体管理器，加载本地微软雅黑字体"""
    
    @staticmethod
    def load_fonts():
        """加载assets/font目录下的字体"""
        font_dir = os.path.join("assets", "font")
        if not os.path.exists(font_dir):
            print(f"⚠️ 字体目录不存在：{font_dir}")
            return False
        
        loaded_fonts = []
        for font_file in ["msyhbd.ttc", "YuGothB.ttc", "consolab.ttf"]:
            font_path = os.path.join(font_dir, font_file)
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    loaded_fonts.append(font_file)
                    print(f"✅ 加载字体：{font_file}")
        
        if loaded_fonts:
            print(f"✅ 已加载 {len(loaded_fonts)} 个字体")
            return True
        else:
            print("⚠️ 未找到本地字体文件，将使用系统默认字体")
            return False
    
    @staticmethod
    def get_font(size: int = 12, weight: int = QFont.Normal):
        """获取微软雅黑字体"""
        font = QFont("Microsoft YaHei", size)
        font.setWeight(weight)
        font.setStyleHint(QFont.SansSerif)
        return font


class WorkerThread(QThread):
    """工作线程，避免界面卡顿"""
    progress = pyqtSignal(str, str, int)  # 消息, 级别, 进度
    finished = pyqtSignal(object, float)  # DataFrame, 耗时
    error = pyqtSignal(str)
    
    def __init__(self, mode, username, season, save_dir):
        super().__init__()
        self.mode = mode
        self.username = username
        self.season = season
        self.save_dir = save_dir
        
    def run(self):
        try:
            start_time = time.time()
            
            # 定义回调函数
            def callback(msg, level="info", progress=None):
                self.progress.emit(msg, level, progress if progress else -1)
            
            # 根据模式执行
            if self.mode == 0:  # 爬取模式
                self.progress.emit("开始爬取数据...", "info", 0)
                df = crawl_data(self.username, self.season, callback)
            elif self.mode == 1:  # 搜索模式
                self.progress.emit("开始搜索数据...", "info", 0)
                df = crawl_data_by_search(self.username, self.season, callback)
            else:  # 本地CSV模式
                self.progress.emit("请选择CSV文件", "info", -1)
                return
            
            if df.empty:
                self.error.emit("未获取到任何数据")
                return
            
            # 保存图片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DAC成绩表_{timestamp}.png"
            save_path = os.path.join(self.save_dir, filename)
            
            self.progress.emit("开始生成图片...", "info", 50)
            save_table_image(df, save_path, callback)
            
            elapsed = time.time() - start_time
            self.finished.emit(df, elapsed)
            
        except Exception as e:
            self.error.emit(str(e))


class UpdateCheckThread(QThread):
    """版本检测线程（使用镜像源）"""
    progress = pyqtSignal(str)          # 日志消息
    check_finished = pyqtSignal(dict)   # 版本信息
    check_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.local_version = None

    def run(self):
        try:
            self.progress.emit("开始检查更新...")
            
            # 获取本地版本
            try:
                self.local_version = update.get_local_version()
                self.progress.emit(f"本地版本：{self.local_version}")
            except SystemExit as e:
                self.check_error.emit(f"获取本地版本失败：请确保 Player_ID.dat 文件中包含 VERSION = x.x.x 行")
                return

            # 获取远程版本（使用镜像源）
            self.progress.emit("正在获取远程版本信息...")
            remote_version = update.get_github_version_with_mirrors(None)  # 传入 None 忽略日志
            if not remote_version:
                self.check_error.emit("无法获取远程版本信息，请检查网络连接。")
                return

            self.progress.emit(f"远程版本：{remote_version}")

            # 比较版本
            cmp = update.compare_versions(self.local_version, remote_version)
            if cmp >= 0:
                self.progress.emit("✅ 当前已是最新版本。")
                self.check_finished.emit({
                    'has_update': False,
                    'local_version': self.local_version,
                    'remote_version': remote_version
                })
                return

            # 获取 release 信息
            self.progress.emit("发现新版本！正在获取更新详情...")
            release_body, download_url = update.get_latest_release_info_with_mirrors(None)

            if not download_url:
                self.check_error.emit("无法获取下载链接。")
                return

            self.progress.emit("获取更新详情成功。")
            self.check_finished.emit({
                'has_update': True,
                'local_version': self.local_version,
                'remote_version': remote_version,
                'release_notes': release_body or "（无更新说明）",
                'download_url': download_url
            })

        except Exception as e:
            self.check_error.emit(f"检查更新时发生错误：{str(e)}")


class UpdateDownloadThread(QThread):
    """下载更新线程"""
    progress = pyqtSignal(str)      # 日志消息
    download_progress = pyqtSignal(int)  # 下载百分比
    download_finished = pyqtSignal(str)  # 下载完成，返回本地路径
    download_error = pyqtSignal(str)

    def __init__(self, download_url, remote_version):
        super().__init__()
        self.download_url = download_url
        self.remote_version = remote_version

    def run(self):
        try:
            self.progress.emit("开始下载更新包...")
            temp_dir = tempfile.gettempdir()
            file_name = self.download_url.split('/')[-1].split('?')[0]
            dest_path = os.path.join(temp_dir, f"DACreator_{self.remote_version}_{file_name}")

            success = self.download_file_with_progress(self.download_url, dest_path)

            if success:
                self.progress.emit(f"✅ 下载完成：{dest_path}")
                self.download_finished.emit(dest_path)
            else:
                self.download_error.emit("下载失败")

        except Exception as e:
            self.download_error.emit(f"下载异常：{str(e)}")

    def download_file_with_progress(self, url, dest_path):
        """带进度报告的下载（支持断点续传）"""
        session = update.create_session_with_retries()
        resume_header = {}
        existing_size = 0
        if os.path.exists(dest_path):
            existing_size = os.path.getsize(dest_path)
            resume_header = {'Range': f'bytes={existing_size}-'}
            self.progress.emit(f"发现已下载部分：{existing_size} 字节，尝试断点续传...")

        try:
            with session.get(url, stream=True, timeout=30, headers=resume_header) as r:
                if r.status_code == 416:
                    self.progress.emit("文件已完整下载")
                    return True
                r.raise_for_status()
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
                                self.download_progress.emit(percent)
                                self.progress.emit(f"下载进度：{percent}%")
            return True
        except Exception as e:
            self.progress.emit(f"下载出错：{str(e)}")
            return False


class AnimatedSidebar(QWidget):
    """带动画效果的侧边栏"""
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.expanded_width = 200
        self.collapsed_width = 70
        self.setFixedWidth(self.expanded_width)
        
        # 动画
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.valueChanged.connect(self.on_width_changed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 折叠按钮
        self.toggle_btn = QPushButton("  ☰  折叠")
        self.toggle_btn.setFont(FontManager.get_font(15))
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 15px 15px;
                border: none;
            }
        """)
        layout.addWidget(self.toggle_btn)
        
        # 列表项
        self.list_widget = QListWidget()
        self.list_widget.setFont(FontManager.get_font(15))
        self.list_widget.setIconSize(QSize(24, 24))
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_widget.setWordWrap(False)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        
        layout.addWidget(self.list_widget)
        
        self.expanded = True
        self.update_theme()
    
    def add_item(self, emoji, text):
        """添加导航项"""
        item = QListWidgetItem(f"{emoji}  {text}")
        item.setData(Qt.UserRole, emoji)
        item.setData(Qt.UserRole + 1, text)
        item.setSizeHint(QSize(self.expanded_width - 30, 60))
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.list_widget.addItem(item)
        return item
    
    def toggle(self):
        """切换折叠/展开状态"""
        self.expanded = not self.expanded
        target_width = self.expanded_width if self.expanded else self.collapsed_width
        
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        self.animation.start()
        
        if self.expanded:
            self.toggle_btn.setText("  ☰  折叠")
        else:
            self.toggle_btn.setText(" ☰")
        
        self.toggled.emit(self.expanded)
    
    def on_width_changed(self, width):
        """宽度变化时的处理"""
        self.setFixedWidth(width)
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            emoji = item.data(Qt.UserRole)
            full_text = item.data(Qt.UserRole + 1)
            
            if width < 100:
                item.setText(emoji)
                item.setTextAlignment(Qt.AlignCenter)
                item.setSizeHint(QSize(width - 20, 60))
            else:
                item.setText(f"{emoji}  {full_text}")
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item.setSizeHint(QSize(width - 30, 60))
    
    def update_theme(self):
        """更新主题样式"""
        theme = ThemeManager.get_current_theme()
        self.setStyleSheet(f"""
            #sidebar {{
                background-color: {theme['bg_sidebar']};
                border-right: 1px solid {theme['border']};
            }}
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
                color: {theme['text_light']};
                font-size: 16px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }}
            QListWidget::item {{
                padding: 0px;
                margin: 0px;
                border-left: 4px solid transparent;
            }}
            QListWidget::item:selected {{
                background-color: {theme['bg_sidebar_selected']};
                border-left: 4px solid {theme['accent']};
            }}
            QListWidget::item:hover {{
                background-color: {theme['bg_sidebar_hover']};
            }}
            QListWidget::item:!selected {{
                border: none;
            }}
            QListWidget::item:selected:!active {{
                border: none;
            }}
            QPushButton {{
                padding: 15px;
                color: {theme['text_light']};
                background-color: {theme['bg_sidebar_selected']};
                border: none;
                text-align: left;
                font-size: 15px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }}
            QPushButton:hover {{
                background-color: {theme['bg_sidebar_hover']};
            }}
        """)


class FadeWidget(QWidget):
    """带动画效果的淡入淡出控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutCubic)
    
    def fade_in(self):
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.start()
    
    def fade_out(self):
        self.fade_animation.setStartValue(1)
        self.fade_animation.setEndValue(0)
        self.fade_animation.start()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 加载设置
        self.settings = QSettings("DACreator", "DACreator")
        
        # 初始化语言管理器
        self.lang_manager = LanguageManager()
        
        # 从设置加载上次使用的语言，如果没有则使用第一个可用语言
        saved_lang_display = self.settings.value("language", "")
        if saved_lang_display and saved_lang_display in self.lang_manager.get_language_display_names():
            saved_lang_code = self.lang_manager.get_lang_code_by_display_name(saved_lang_display)
        else:
            # 使用第一个可用语言
            first_lang_code = list(self.lang_manager.available_languages.keys())[0]
            saved_lang_code = first_lang_code
            saved_lang_display = self.lang_manager.get_display_name_by_code(first_lang_code)
        
        self.lang_manager.load_language(saved_lang_code)
        
        self.setWindowTitle(self.lang_manager.get("window_title", "DACreator-GUI"))
        self.setMinimumSize(1200, 800)
        
        # 加载本地字体
        FontManager.load_fonts()
        
        # 设置应用字体
        app_font = FontManager.get_font(12)
        QApplication.setFont(app_font)
        
        # 中心控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧侧边栏
        self.sidebar = AnimatedSidebar()
        main_layout.addWidget(self.sidebar)
        
        # 右侧堆叠页面
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, 1)
        
        # 更新侧边栏菜单项
        self.update_sidebar_texts()
        
        # 创建页面
        self.home_page = self.create_home_page()
        self.records_page = self.create_records_page()
        self.version_page = self.create_version_page()
        self.settings_page = self.create_settings_page()
        self.about_page = self.create_about_page()
        
        self.stacked_widget.addWidget(self.home_page)      # 索引 0
        self.stacked_widget.addWidget(self.records_page)   # 索引 1
        self.stacked_widget.addWidget(self.version_page)   # 索引 2
        self.stacked_widget.addWidget(self.settings_page)  # 索引 3
        self.stacked_widget.addWidget(self.about_page)     # 索引 4
        
        # 信号连接
        self.sidebar.list_widget.currentRowChanged.connect(self.on_page_changed)
        self.sidebar.toggled.connect(self.on_sidebar_toggled)
        
        # 主题监控
        self.theme_timer = QTimer()
        self.theme_timer.timeout.connect(self.check_theme_change)
        self.theme_timer.start(5000)
        self.current_theme = "light"
        
        # 工作线程
        self.worker = None
        self.update_check_thread = None
        self.download_thread = None
        self.latest_download_url = None
        self.latest_remote_version = None
        
        # 默认选中主页
        self.sidebar.list_widget.setCurrentRow(0)
        
        # 应用初始主题
        self.apply_theme()
    
    def create_home_page(self):
        """创建主页"""
        page = FadeWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)
        
        # 顶部图标和标题
        header_layout = QHBoxLayout()
        icon_label = QLabel("🏎️")
        icon_label.setFont(FontManager.get_font(48))
        header_layout.addWidget(icon_label)
        
        self.home_title_label = QLabel(self.lang_manager.get("home_title", "DACreator"))
        self.home_title_label.setFont(FontManager.get_font(32, QFont.Bold))
        header_layout.addWidget(self.home_title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 功能选择区域
        func_group = QFrame()
        func_group.setFrameStyle(QFrame.StyledPanel)
        func_group.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 20px;
            }
        """)
        func_layout = QVBoxLayout(func_group)
        
        # 模式选择
        mode_layout = QHBoxLayout()
        self.mode_label = QLabel(self.lang_manager.get("home_mode_select", "选择模式") + ":")
        mode_layout.addWidget(self.mode_label)
        
        self.func_combo = QComboBox()
        self.update_mode_combo()
        self.func_combo.setFont(FontManager.get_font(13))
        self.func_combo.setMinimumWidth(300)
        self.func_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.func_combo)
        mode_layout.addStretch()
        func_layout.addLayout(mode_layout)
        
        # CSV文件选择容器
        self.csv_container = QWidget()
        csv_layout = QHBoxLayout(self.csv_container)
        csv_layout.setContentsMargins(0, 0, 0, 0)
        
        self.csv_label = QLabel(self.lang_manager.get("home_csv_file", "CSV文件") + ":")
        csv_layout.addWidget(self.csv_label)
        
        self.csv_path_edit = QLineEdit()
        self.csv_path_edit.setPlaceholderText(self.lang_manager.get("home_csv_placeholder", "请选择CSV文件..."))
        self.csv_path_edit.setReadOnly(True)
        csv_layout.addWidget(self.csv_path_edit)
        
        self.csv_btn = QPushButton(self.lang_manager.get("home_browse", "浏览..."))
        self.csv_btn.clicked.connect(self.select_csv_file)
        csv_layout.addWidget(self.csv_btn)
        
        self.csv_container.setVisible(False)
        func_layout.addWidget(self.csv_container)
        
        layout.addWidget(func_group)
        
        # 进度显示区域
        progress_group = QFrame()
        progress_group.setFrameStyle(QFrame.StyledPanel)
        progress_group.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 20px;
            }
        """)
        progress_layout = QVBoxLayout(progress_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(20)
        progress_layout.addWidget(self.progress_bar)
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        self.log_text.setFont(FontManager.get_font(11))
        progress_layout.addWidget(self.log_text)
        
        layout.addWidget(progress_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 " + self.lang_manager.get("home_start", "开始生成"))
        self.start_btn.setFont(FontManager.get_font(15, QFont.Bold))
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setMinimumWidth(200)
        self.start_btn.clicked.connect(self.on_start_clicked)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ " + self.lang_manager.get("home_stop", "停止"))
        self.stop_btn.setFont(FontManager.get_font(15, QFont.Bold))
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setMinimumWidth(150)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        return page
    
    def create_records_page(self):
        """创建记录页"""
        page = FadeWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel(self.lang_manager.get("menu_records", "数据"))
        title.setFont(FontManager.get_font(24, QFont.Bold))
        layout.addWidget(title)
        
        # 筛选控件
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel(self.lang_manager.get("filter_course", "赛道") + ":"))
        self.course_filter = QComboBox()
        self.course_filter.addItem(self.lang_manager.get("filter_all", "全部"))
        # 从数据库获取所有赛道列表
        try:
            courses = database.get_distinct_courses()
            self.course_filter.addItems(courses)
        except:
            pass
        self.course_filter.currentTextChanged.connect(self.refresh_records_table)
        filter_layout.addWidget(self.course_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # 表格
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(7)
        self.records_table.setHorizontalHeaderLabels([
            self.lang_manager.get("record_course", "赛道"),
            self.lang_manager.get("record_direction", "方向"),
            self.lang_manager.get("record_time", "时间"),
            self.lang_manager.get("record_rank", "等级"),
            self.lang_manager.get("record_car", "车型"),
            self.lang_manager.get("record_date", "记录日期"),
            self.lang_manager.get("record_created", "录入时间")
        ])
        self.records_table.horizontalHeader().setStretchLastSection(True)
        self.records_table.setAlternatingRowColors(True)
        layout.addWidget(self.records_table)
        
        # 刷新按钮
        refresh_btn = QPushButton(self.lang_manager.get("refresh", "刷新"))
        refresh_btn.clicked.connect(self.refresh_records_table)
        layout.addWidget(refresh_btn, alignment=Qt.AlignRight)
        
        # 初始加载
        self.refresh_records_table()
        
        return page

    def refresh_records_table(self):
        """刷新记录表格"""
        course = self.course_filter.currentText()
        if course == self.lang_manager.get("filter_all", "全部"):
            course = None
        records = database.get_history(course=course, limit=200)
        self.records_table.setRowCount(len(records))
        for i, rec in enumerate(records):
            self.records_table.setItem(i, 0, QTableWidgetItem(rec['course']))
            self.records_table.setItem(i, 1, QTableWidgetItem(rec['direction']))
            self.records_table.setItem(i, 2, QTableWidgetItem(rec['time_str']))
            self.records_table.setItem(i, 3, QTableWidgetItem(rec['rank']))
            self.records_table.setItem(i, 4, QTableWidgetItem(rec['car']))
            self.records_table.setItem(i, 5, QTableWidgetItem(rec['record_date']))
            # 格式化创建时间
            try:
                created = datetime.fromisoformat(rec['created_at']).strftime("%Y-%m-%d %H:%M")
            except:
                created = rec['created_at']
            self.records_table.setItem(i, 6, QTableWidgetItem(created))
        self.records_table.resizeColumnsToContents()
    
    def create_version_page(self):
        """创建版本页（集成更新功能）"""
        page = FadeWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        # 标题
        self.version_title = QLabel(self.lang_manager.get("version_title", "版本信息"))
        self.version_title.setFont(FontManager.get_font(28, QFont.Bold))
        layout.addWidget(self.version_title)

        # 当前版本显示
        version_info_widget = QWidget()
        version_layout = QHBoxLayout(version_info_widget)
        version_layout.setContentsMargins(0, 0, 0, 0)

        self.version_current_label = QLabel(self.lang_manager.get("version_current", "当前版本") + ":")
        self.version_current_label.setFont(FontManager.get_font(14))
        version_layout.addWidget(self.version_current_label)

        self.current_version_value = QLabel("v2.0.0")
        self.current_version_value.setFont(FontManager.get_font(16, QFont.Bold))
        version_layout.addWidget(self.current_version_value)
        version_layout.addStretch()
        layout.addWidget(version_info_widget)

        # 日志显示框（类似主页）
        self.update_log_text = QTextEdit()
        self.update_log_text.setReadOnly(True)
        self.update_log_text.setMinimumHeight(300)
        self.update_log_text.setFont(FontManager.get_font(11))
        self.update_log_text.setPlaceholderText(self.lang_manager.get("version_check_update", "检查更新") + "...")
        layout.addWidget(self.update_log_text)

        # 按钮区域（左右对称）
        btn_layout = QHBoxLayout()

        self.check_update_btn = QPushButton("🔍 " + self.lang_manager.get("version_check_update", "检查更新"))
        self.check_update_btn.setFont(FontManager.get_font(14))
        self.check_update_btn.setMinimumHeight(40)
        self.check_update_btn.setMinimumWidth(150)
        self.check_update_btn.clicked.connect(self.on_check_update_clicked)
        btn_layout.addWidget(self.check_update_btn)

        self.install_update_btn = QPushButton("⬇️ " + self.lang_manager.get("version_perform_update", "安装更新"))
        self.install_update_btn.setFont(FontManager.get_font(14))
        self.install_update_btn.setMinimumHeight(40)
        self.install_update_btn.setMinimumWidth(150)
        self.install_update_btn.setEnabled(False)  # 初始禁用
        self.install_update_btn.clicked.connect(self.on_install_update_clicked)
        btn_layout.addWidget(self.install_update_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        # 初始化版本显示
        try:
            local_ver = update.get_local_version()
            self.current_version_value.setText(f"v{local_ver}")
        except:
            self.current_version_value.setText("未知")

        return page
    
    def create_settings_page(self):
        """创建设置页"""
        page = FadeWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        # 标题
        self.settings_title = QLabel(self.lang_manager.get("settings_title", "设置"))
        self.settings_title.setFont(FontManager.get_font(28, QFont.Bold))
        self.settings_title.setStyleSheet("margin-bottom: 20px;")
        layout.addWidget(self.settings_title)
        
        # 表单
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # ID
        self.id_edit = QLineEdit()
        self.id_edit.setText(self.settings.value("id", ""))
        self.id_edit.setPlaceholderText(self.lang_manager.get("settings_id_placeholder", "例如：高橋リンタ"))
        self.id_edit.setMinimumWidth(300)
        form_layout.addRow(self.create_label("👤 " + self.lang_manager.get("settings_id", "ID") + ":"), self.id_edit)
        
        # 地区
        self.region_edit = QLineEdit()
        self.region_edit.setText(self.settings.value("region", ""))
        self.region_edit.setPlaceholderText(self.lang_manager.get("settings_region_placeholder", "例如：関東"))
        form_layout.addRow(self.create_label("🗺️ " + self.lang_manager.get("settings_region", "地区") + ":"), self.region_edit)
        
        # 城市
        self.city_edit = QLineEdit()
        self.city_edit.setText(self.settings.value("city", ""))
        self.city_edit.setPlaceholderText(self.lang_manager.get("settings_city_placeholder", "例如：東京"))
        form_layout.addRow(self.create_label("🏙️ " + self.lang_manager.get("settings_city", "城市") + ":"), self.city_edit)
        
        # 店铺名
        self.store_edit = QLineEdit()
        self.store_edit.setText(self.settings.value("store", ""))
        self.store_edit.setPlaceholderText(self.lang_manager.get("settings_store_placeholder", "例如：ゲームセンター"))
        form_layout.addRow(self.create_label("🏪 " + self.lang_manager.get("settings_store", "店铺") + ":"), self.store_edit)
        
        # 赛季
        self.season_spin = QSpinBox()
        self.season_spin.setRange(1, 10)
        self.season_spin.setValue(int(self.settings.value("season", 5)))
        form_layout.addRow(self.create_label("📅 " + self.lang_manager.get("settings_season", "赛季") + ":"), self.season_spin)
        
        # 回合（预留）
        self.round_spin = QSpinBox()
        self.round_spin.setRange(1, 10)
        self.round_spin.setValue(int(self.settings.value("round", 1)))
        form_layout.addRow(self.create_label("🔄 " + self.lang_manager.get("settings_round", "回合") + ":"), self.round_spin)
        
        # 语言 - 动态填充可用的语言
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(self.lang_manager.get_language_display_names())
        current_display = self.lang_manager.get_display_name_by_code(self.lang_manager.current_lang_code)
        self.lang_combo.setCurrentText(current_display)
        self.lang_combo.currentTextChanged.connect(self.on_language_changed)
        form_layout.addRow(self.create_label("🌐 " + self.lang_manager.get("settings_language", "语言") + ":"), self.lang_combo)
        
        layout.addWidget(form_widget)
        layout.addStretch()
        
        # 保存按钮
        self.save_btn = QPushButton("💾 " + self.lang_manager.get("settings_save", "保存设置"))
        self.save_btn.setFont(FontManager.get_font(15, QFont.Bold))
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setMinimumWidth(250)
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn, alignment=Qt.AlignCenter)
        
        return page
    
    def create_about_page(self):
        """创建关于页"""
        page = FadeWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        # 标题
        self.about_title = QLabel(self.lang_manager.get("about_title", "关于"))
        self.about_title.setFont(FontManager.get_font(28, QFont.Bold))
        self.about_title.setStyleSheet("margin-bottom: 20px;")
        layout.addWidget(self.about_title)
        
        # 大图标
        icon_label = QLabel("🏎️")
        icon_label.setFont(FontManager.get_font(64))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # 关于内容 - 使用纯文本并保留换行
        about_content = self.lang_manager.get("about_content", "")
        
        # 如果内容为空，显示默认信息
        if not about_content:
            about_content = """DACreator 成绩表生成工具
版本 2.0.0 (GUI版)

为头文字D：激斗设计的爬虫工具，可自动抓取ArcadeZone的计时赛成绩并生成可视化表格。

开发者
核心开发：TakahashiRinta
GUI设计：JustNacho
特别感谢：ArcadeZone社区

依赖库
PyQt5 - GUI框架
pandas - 数据处理
requests - 网络请求
beautifulsoup4 - HTML解析
pillow - 图片处理

本项目遵循 MIT 开源协议，仅供学习交流，严禁商业用途。

GitHub: https://github.com/GuitaristRin/DACreator-GUI"""
        
        self.about_text = QTextEdit()
        self.about_text.setReadOnly(True)
        self.about_text.setMinimumHeight(400)
        self.about_text.setFrameStyle(QFrame.NoFrame)
        self.about_text.setFont(FontManager.get_font(12))
        
        # 直接设置纯文本，保留原有换行
        self.about_text.setPlainText(about_content)
        layout.addWidget(self.about_text)
        
        layout.addStretch()
        return page
    
    def create_label(self, text):
        """创建带 Emoji 的标签"""
        label = QLabel(text)
        label.setFont(FontManager.get_font(13))
        return label
    
    def update_sidebar_texts(self):
        """更新侧边栏菜单项文本"""
        # 清除现有项
        self.sidebar.list_widget.clear()
        
        # 按顺序添加菜单项：主页、数据、版本、设置、关于
        menu_items = [
            ("🏠", self.lang_manager.get("menu_home", "主页")),
            ("📋", self.lang_manager.get("menu_records", "数据")),
            ("📦", self.lang_manager.get("menu_version", "版本")),
            ("⚙️", self.lang_manager.get("menu_settings", "设置")),
            ("ℹ️", self.lang_manager.get("menu_about", "关于"))
        ]
        
        for emoji, text in menu_items:
            self.sidebar.add_item(emoji, text)
        
        # 恢复选中状态
        if self.sidebar.list_widget.count() > 0:
            self.sidebar.list_widget.setCurrentRow(0)
    
    def update_mode_combo(self):
        """更新模式下拉框选项"""
        current_index = self.func_combo.currentIndex()
        self.func_combo.clear()
        self.func_combo.addItems([
            "🌐 " + self.lang_manager.get("home_mode_crawl", "爬取模式（含排名）"),
            "🔍 " + self.lang_manager.get("home_mode_search", "搜索模式（无排名）"),
            "📁 " + self.lang_manager.get("home_mode_local", "本地CSV模式")
        ])
        if 0 <= current_index < self.func_combo.count():
            self.func_combo.setCurrentIndex(current_index)
    
    def update_ui_texts(self):
        """更新所有界面文本"""
        # 更新窗口标题
        self.setWindowTitle(self.lang_manager.get("window_title", "DACreator-GUI"))
        
        # 更新侧边栏菜单项
        self.update_sidebar_texts()
        
        # 更新主页文本
        self.home_title_label.setText(self.lang_manager.get("home_title", "DACreator"))
        self.mode_label.setText(self.lang_manager.get("home_mode_select", "选择模式") + ":")
        self.csv_label.setText(self.lang_manager.get("home_csv_file", "CSV文件") + ":")
        self.csv_path_edit.setPlaceholderText(self.lang_manager.get("home_csv_placeholder", "请选择CSV文件..."))
        self.csv_btn.setText(self.lang_manager.get("home_browse", "浏览..."))
        self.start_btn.setText("🚀 " + self.lang_manager.get("home_start", "开始生成"))
        self.stop_btn.setText("⏹️ " + self.lang_manager.get("home_stop", "停止"))
        self.update_mode_combo()
        
        # 更新设置页文本
        self.settings_title.setText(self.lang_manager.get("settings_title", "设置"))
        self.id_edit.setPlaceholderText(self.lang_manager.get("settings_id_placeholder", "例如：高橋リンタ"))
        self.region_edit.setPlaceholderText(self.lang_manager.get("settings_region_placeholder", "例如：関東"))
        self.city_edit.setPlaceholderText(self.lang_manager.get("settings_city_placeholder", "例如：東京"))
        self.store_edit.setPlaceholderText(self.lang_manager.get("settings_store_placeholder", "例如：ゲームセンター"))
        self.save_btn.setText("💾 " + self.lang_manager.get("settings_save", "保存设置"))
        
        # 更新版本页文本
        self.version_title.setText(self.lang_manager.get("version_title", "版本信息"))
        self.version_current_label.setText(self.lang_manager.get("version_current", "当前版本") + ":")
        self.check_update_btn.setText("🔍 " + self.lang_manager.get("version_check_update", "检查更新"))
        self.install_update_btn.setText("⬇️ " + self.lang_manager.get("version_perform_update", "安装更新"))
        self.update_log_text.setPlaceholderText(self.lang_manager.get("version_check_update", "检查更新") + "...")
        
        # 更新关于页文本
        self.about_title.setText(self.lang_manager.get("about_title", "关于"))
        about_content = self.lang_manager.get("about_content", "")
        if about_content:
            self.about_text.setPlainText(about_content)
    
    def on_language_changed(self, display_name):
        """语言改变时的处理"""
        # 获取语言代码
        lang_code = self.lang_manager.get_lang_code_by_display_name(display_name)
        
        # 加载新语言
        if lang_code and self.lang_manager.load_language(lang_code):
            # 更新界面文本
            self.update_ui_texts()
            
            # 保存设置
            self.settings.setValue("language", display_name)
            
            # 提示用户
            QMessageBox.information(self, 
                                   self.lang_manager.get("common_success", "成功"),
                                   self.lang_manager.get("settings_save_success", "设置已保存"))
            
            # 重新应用主题（确保文字颜色正确）
            self.apply_theme()
    
    def on_mode_changed(self, index):
        """模式改变时的处理"""
        # 模式2（本地CSV）显示文件选择容器
        self.csv_container.setVisible(index == 2)
    
    def select_csv_file(self):
        """选择CSV文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.lang_manager.get("home_csv_file", "CSV文件"), "", "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        if file_path:
            self.csv_path_edit.setText(file_path)
    
    def on_page_changed(self, index):
        """页面切换动画"""
        # 直接映射：0->主页, 1->数据, 2->版本, 3->设置, 4->关于
        target_index = index
        
        current_page = self.stacked_widget.currentWidget()
        if current_page and hasattr(current_page, 'fade_out'):
            current_page.fade_out()
        
        QTimer.singleShot(300, lambda: self.stacked_widget.setCurrentIndex(target_index))
        
        new_page = self.stacked_widget.widget(target_index)
        if hasattr(new_page, 'fade_in'):
            QTimer.singleShot(300, new_page.fade_in)
    
    def on_sidebar_toggled(self, expanded):
        """侧边栏折叠状态变化"""
        pass
    
    def on_start_clicked(self):
        """开始生成按钮点击事件"""
        mode = self.func_combo.currentIndex()
        
        # 验证输入
        if mode == 2:  # 本地CSV模式
            csv_path = self.csv_path_edit.text().strip()
            if not csv_path:
                QMessageBox.warning(self, 
                                   self.lang_manager.get("common_warning", "提示"),
                                   self.lang_manager.get("msg_select_csv", "请选择CSV文件"))
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, 
                                   self.lang_manager.get("common_warning", "提示"),
                                   self.lang_manager.get("msg_csv_not_exists", "CSV文件不存在"))
                return
        
        # 选择保存目录
        save_dir = QFileDialog.getExistingDirectory(self, self.lang_manager.get("home_start", "开始生成"))
        if not save_dir:
            return
        
        # 清空日志
        self.log_text.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 禁用按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.func_combo.setEnabled(False)
        
        if mode == 2:  # 本地CSV模式
            self.process_local_csv(csv_path, save_dir)
        else:
            # 检查ID
            user_id = self.id_edit.text().strip()
            if not user_id:
                QMessageBox.warning(self, 
                                   self.lang_manager.get("common_warning", "提示"),
                                   self.lang_manager.get("msg_configure_id", "请在设置页面配置您的ID"))
                self.sidebar.list_widget.setCurrentRow(3)  # 跳转到设置页
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.func_combo.setEnabled(True)
                self.progress_bar.setVisible(False)
                return
            
            # 启动工作线程
            self.worker = WorkerThread(
                mode, user_id, self.season_spin.value(), save_dir
            )
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_task_finished)
            self.worker.error.connect(self.on_task_error)
            self.worker.start()
    
    def process_local_csv(self, csv_path, save_dir):
        """处理本地CSV文件"""
        try:
            import pandas as pd
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            self.log(f"📁 {self.lang_manager.get('home_csv_file', 'CSV文件')}：{csv_path}")
            self.log(f"📊 {self.lang_manager.get('msg_records_count', '记录数')}：{len(df)} {self.lang_manager.get('common_complete', '条')}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DAC成绩表_{timestamp}.png"
            save_path = os.path.join(save_dir, filename)
            
            self.log("🎨 " + self.lang_manager.get("home_start", "开始生成") + "...")
            self.progress_bar.setValue(30)
            
            # 定义回调函数
            def callback(msg, level="info", progress=None):
                self.log(msg, level)
                if progress is not None and progress > 0:
                    self.progress_bar.setValue(progress)
            
            save_table_image(df, save_path, callback)
            
            self.progress_bar.setValue(100)
            self.log(f"✅ {self.lang_manager.get('msg_image_saved', '图片已保存')}：{save_path}")

            try:
                database.insert_records(df, "csv")
                self.log(f"💾 数据已保存到历史数据库", "success")
            except Exception as e:
                self.log(f"⚠️ 保存到数据库失败：{str(e)}", "warning")
            
            QMessageBox.information(self, 
                                   self.lang_manager.get("common_complete", "完成"),
                                   f"{self.lang_manager.get('msg_image_saved', '图片已保存')}：\n{save_path}")
            
        except Exception as e:
            self.log(f"❌ {self.lang_manager.get('common_error', '错误')}：{str(e)}", "error")
            QMessageBox.critical(self, 
                                self.lang_manager.get("common_error", "错误"),
                                f"{self.lang_manager.get('common_error', '错误')}：{str(e)}")
        finally:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.func_combo.setEnabled(True)
            QTimer.singleShot(3000, lambda: self.progress_bar.setVisible(False))
    
    def on_stop_clicked(self):
        """停止按钮点击事件"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.log("⏹️ " + self.lang_manager.get("home_stop", "停止"), "warning")
            
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.func_combo.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def on_progress(self, message, level, progress):
        """进度更新"""
        self.log(message, level)
        if progress >= 0:
            self.progress_bar.setValue(progress)
    
    def on_task_finished(self, df, elapsed):
        """任务完成"""
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        time_str = f"{minutes}{self.lang_manager.get('common_minutes', '分')}{seconds:.1f}{self.lang_manager.get('common_seconds', '秒')}" if minutes > 0 else f"{seconds:.1f}{self.lang_manager.get('common_seconds', '秒')}"
        
        self.log(f"✅ {self.lang_manager.get('msg_task_complete', '任务完成')} {self.lang_manager.get('msg_records_count', '记录数')}：{len(df)}，{self.lang_manager.get('msg_time_elapsed', '耗时')}：{time_str}", "success")
        self.progress_bar.setValue(100)

        try:
            source = "crawl" if self.mode == 0 else "search" if self.mode == 1 else "csv"
            database.insert_records(df, source)
            self.log(f"💾 数据已保存到历史数据库", "success")
        except Exception as e:
            self.log(f"⚠️ 保存到数据库失败：{str(e)}", "warning")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.func_combo.setEnabled(True)
        
        QMessageBox.information(self, 
                               self.lang_manager.get("common_complete", "完成"),
                               f"{self.lang_manager.get('msg_task_complete', '任务完成')}\n{self.lang_manager.get('msg_records_count', '记录数')}：{len(df)}\n{self.lang_manager.get('msg_time_elapsed', '耗时')}：{time_str}")
        
        # 3秒后隐藏进度条
        QTimer.singleShot(3000, lambda: self.progress_bar.setVisible(False))
    
    def on_task_error(self, error_msg):
        """任务错误"""
        self.log(f"❌ {self.lang_manager.get('common_error', '错误')}：{error_msg}", "error")
        self.progress_bar.setVisible(False)
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.func_combo.setEnabled(True)
        
        QMessageBox.critical(self, 
                            self.lang_manager.get("common_error", "错误"),
                            f"{self.lang_manager.get('common_error', '错误')}：{error_msg}")
    
    def on_check_update_clicked(self):
        """点击检查更新按钮"""
        self.update_log_text.clear()
        self.update_log_text.append(self.lang_manager.get("version_checking", "正在检查更新") + "...")
        self.install_update_btn.setEnabled(False)
        self.check_update_btn.setEnabled(False)

        # 启动检测线程
        self.update_check_thread = UpdateCheckThread()
        self.update_check_thread.progress.connect(self.on_update_progress)
        self.update_check_thread.check_finished.connect(self.on_update_check_finished)
        self.update_check_thread.check_error.connect(self.on_update_check_error)
        self.update_check_thread.start()

    def on_update_progress(self, message):
        """更新过程中的日志"""
        self.update_log_text.append(message)
        cursor = self.update_log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.update_log_text.setTextCursor(cursor)

    def on_update_check_finished(self, info):
        """版本检测完成"""
        self.check_update_btn.setEnabled(True)
        if info['has_update']:
            self.update_log_text.append(f"🎉 发现新版本 {info['remote_version']}！")
            self.update_log_text.append("更新说明：")
            self.update_log_text.append(info['release_notes'])
            # 保存下载信息
            self.latest_download_url = info['download_url']
            self.latest_remote_version = info['remote_version']
            self.install_update_btn.setEnabled(True)
        else:
            self.update_log_text.append("✅ 已是最新版本。")
            self.install_update_btn.setEnabled(False)

    def on_update_check_error(self, error_msg):
        """检测出错"""
        self.check_update_btn.setEnabled(True)
        self.update_log_text.append(f"❌ {error_msg}")
        self.install_update_btn.setEnabled(False)

    def on_install_update_clicked(self):
        """点击安装更新按钮"""
        if not hasattr(self, 'latest_download_url') or not self.latest_download_url:
            QMessageBox.warning(self, 
                               self.lang_manager.get("common_warning", "提示"),
                               self.lang_manager.get("version_check_failed", "请先检查更新"))
            return

        # 确认对话框
        reply = QMessageBox.question(self,
                                    self.lang_manager.get("update_confirm_title", "确认更新"),
                                    self.lang_manager.get("update_confirm_message", "确定要下载并安装最新版本吗？"),
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # 禁用按钮，防止重复点击
        self.install_update_btn.setEnabled(False)
        self.check_update_btn.setEnabled(False)
        self.update_log_text.append("开始下载更新...")

        # 启动下载线程
        self.download_thread = UpdateDownloadThread(self.latest_download_url, self.latest_remote_version)
        self.download_thread.progress.connect(self.on_update_progress)
        self.download_thread.download_progress.connect(self.on_download_progress)
        self.download_thread.download_finished.connect(self.on_download_finished)
        self.download_thread.download_error.connect(self.on_download_error)
        self.download_thread.start()

    def on_download_progress(self, percent):
        """下载进度更新（可以用于进度条，此处仅输出日志）"""
        self.update_log_text.append(f"下载进度：{percent}%")

    def on_download_finished(self, file_path):
        """下载完成"""
        self.update_log_text.append(f"✅ 下载完成：{file_path}")
        self.check_update_btn.setEnabled(True)

        # 启动安装程序
        try:
            if sys.platform.startswith('win'):
                os.startfile(file_path)
            else:
                if sys.platform == 'darwin':
                    subprocess.run(['open', file_path])
                else:
                    subprocess.run(['xdg-open', file_path])
            self.update_log_text.append("安装程序已启动，请按照指引完成安装。")
        except Exception as e:
            self.update_log_text.append(f"❌ 无法启动安装程序：{str(e)}")
            self.update_log_text.append(f"请手动运行安装包：{file_path}")

        # 保持安装更新按钮可用（如果失败可以重试，但这里简单处理为可用）
        self.install_update_btn.setEnabled(True)

    def on_download_error(self, error_msg):
        """下载错误"""
        self.update_log_text.append(f"❌ {error_msg}")
        self.check_update_btn.setEnabled(True)
        self.install_update_btn.setEnabled(True)  # 允许重试
    
    def log(self, message, level="info"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        level_map = {
            "error": ("❌", "log_error"),
            "warning": ("⚠️", "log_warning"),
            "success": ("✅", "log_success"),
            "info": ("📌", "log_info")
        }
        
        emoji, level_key = level_map.get(level, ("📌", "log_info"))
        level_text = self.lang_manager.get(level_key, level)
        
        self.log_text.append(f"[{timestamp}] {emoji} [{level_text}] {message}")
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
    
    def save_settings(self):
        """保存设置"""
        self.settings.setValue("id", self.id_edit.text())
        self.settings.setValue("region", self.region_edit.text())
        self.settings.setValue("city", self.city_edit.text())
        self.settings.setValue("store", self.store_edit.text())
        self.settings.setValue("season", self.season_spin.value())
        self.settings.setValue("round", self.round_spin.value())
        
        QMessageBox.information(self, 
                               self.lang_manager.get("common_success", "成功"),
                               self.lang_manager.get("settings_save_success", "设置已保存"))
    
    def check_theme_change(self):
        """检查系统主题变化"""
        theme_name = ThemeManager.detect_windows_theme()
        if theme_name != self.current_theme:
            self.current_theme = theme_name
            self.apply_theme()
    
    def apply_theme(self):
        """应用主题"""
        theme = ThemeManager.get_current_theme()
        
        # 更新侧边栏
        self.sidebar.update_theme()
        
        # 更新主窗口样式
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['bg_primary']};
            }}
            QWidget {{
                background-color: {theme['bg_primary']};
                color: {theme['text_primary']};
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }}
            QStackedWidget {{
                background-color: {theme['bg_primary']};
            }}
            QLabel {{
                color: {theme['text_primary']};
            }}
            QLineEdit, QSpinBox, QTextEdit {{
                background-color: {theme['bg_secondary']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                border-radius: 5px;
                padding: 10px;
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }}
            QComboBox {{
                background-color: {theme['bg_secondary']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                min-height: 20px;
            }}
            QComboBox:hover {{
                border: 1px solid {theme['accent']};
            }}
            QComboBox:focus {{
                border: 2px solid {theme['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {theme['text_secondary']};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme['bg_secondary']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                selection-background-color: {theme['accent']};
                selection-color: white;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px;
                min-height: 25px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {theme['accent_hover']};
                color: white;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {theme['accent']};
                color: white;
            }}
            
            QPushButton {{
                background-color: {theme['accent']};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {theme['accent']};
            }}
            QPushButton:disabled {{
                background-color: {theme['border']};
                color: {theme['text_secondary']};
            }}
            QProgressBar {{
                border: 1px solid {theme['border']};
                border-radius: 5px;
                text-align: center;
                font-size: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {theme['success']};
                border-radius: 5px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {theme['bg_secondary']};
                border: 1px solid {theme['border']};
            }}
            QFormLayout {{
                color: {theme['text_primary']};
            }}
            QMessageBox {{
                background-color: {theme['bg_secondary']};
            }}
        """)


def main():
    """主函数"""
    if not ensure_virtualenv_and_dependencies():
        return

    database.init_db()
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    setup_logging()
    main()