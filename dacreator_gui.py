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
"""

import sys
import os
import subprocess
import site
import logging
import time
import json
from typing import List, Optional
from datetime import datetime
import threading

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
        QGraphicsOpacityEffect, QFrame, QSizePolicy, QProgressBar, QFileDialog
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
except ImportError as e:
    print(f"❌ 导入核心模块失败：{e}")
    print("请确保 spider.py, spider_search.py, core.py 在同一目录下")
    input("\n按回车键退出...")
    sys.exit(1)


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
    def get_font(size: int = 12, weight: int = QFont.Normal):  # 默认从11改为12
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
        self.toggle_btn.setFont(FontManager.get_font(15))  # 从14改为15
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
        self.list_widget.setFont(FontManager.get_font(15))  # 从14改为15
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
                font-size: 16px;  /* 从15改为16 */
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
                font-size: 15px;  /* 从14改为15 */
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
        self.setWindowTitle("DACreator - 头文字D激斗成绩表生成器")
        self.setMinimumSize(1200, 800)
        
        # 加载设置
        self.settings = QSettings("DACreator", "DACreator")
        
        # 加载本地字体
        FontManager.load_fonts()
        
        # 设置应用字体
        app_font = FontManager.get_font(12)  # 从11改为12
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
        
        # 添加导航项
        self.sidebar.add_item("🏠", "主页")
        self.sidebar.add_item("⚙️", "设置")
        self.sidebar.add_item("ℹ️", "关于")
        
        # 创建页面
        self.home_page = self.create_home_page()
        self.settings_page = self.create_settings_page()
        self.about_page = self.create_about_page()
        
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.addWidget(self.about_page)
        
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
        
        title_label = QLabel("DACreator")
        title_label.setFont(FontManager.get_font(32, QFont.Bold))
        header_layout.addWidget(title_label)
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
        mode_layout.addWidget(QLabel("📋 选择模式:"))
        self.func_combo = QComboBox()
        self.func_combo.addItems([
            "🌐 爬取模式（含排名）",
            "🔍 搜索模式（无排名）",
            "📁 本地CSV生成图片"
        ])
        self.func_combo.setFont(FontManager.get_font(13))  # 从12改为13
        self.func_combo.setMinimumWidth(300)
        self.func_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.func_combo)
        mode_layout.addStretch()
        func_layout.addLayout(mode_layout)
        
        # CSV文件选择容器
        self.csv_container = QWidget()
        csv_layout = QHBoxLayout(self.csv_container)
        csv_layout.setContentsMargins(0, 0, 0, 0)
        
        csv_layout.addWidget(QLabel("📄 CSV文件:"))
        self.csv_path_edit = QLineEdit()
        self.csv_path_edit.setPlaceholderText("请选择CSV文件...")
        self.csv_path_edit.setReadOnly(True)
        csv_layout.addWidget(self.csv_path_edit)
        self.csv_btn = QPushButton("浏览...")
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
        self.log_text.setFont(FontManager.get_font(11))  # 从10改为11
        progress_layout.addWidget(self.log_text)
        
        layout.addWidget(progress_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 开始生成")
        self.start_btn.setFont(FontManager.get_font(15, QFont.Bold))  # 从14改为15
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setMinimumWidth(200)
        self.start_btn.clicked.connect(self.on_start_clicked)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setFont(FontManager.get_font(15, QFont.Bold))  # 从14改为15
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setMinimumWidth(150)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        return page
    
    def create_settings_page(self):
        """创建设置页"""
        page = FadeWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("⚙️ 设置")
        title.setFont(FontManager.get_font(28, QFont.Bold))
        title.setStyleSheet("margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 表单
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # ID
        self.id_edit = QLineEdit()
        self.id_edit.setText(self.settings.value("id", ""))
        self.id_edit.setPlaceholderText("例如：小明小红")
        self.id_edit.setMinimumWidth(300)
        form_layout.addRow(self.create_label("👤 ID:"), self.id_edit)
        
        # 地区
        self.region_edit = QLineEdit()
        self.region_edit.setText(self.settings.value("region", ""))
        self.region_edit.setPlaceholderText("例如：関東")
        form_layout.addRow(self.create_label("🗺️ 地区:"), self.region_edit)
        
        # 城市
        self.city_edit = QLineEdit()
        self.city_edit.setText(self.settings.value("city", ""))
        self.city_edit.setPlaceholderText("例如：東京")
        form_layout.addRow(self.create_label("🏙️ 城市:"), self.city_edit)
        
        # 店铺名
        self.store_edit = QLineEdit()
        self.store_edit.setText(self.settings.value("store", ""))
        self.store_edit.setPlaceholderText("例如：ゲームセンター")
        form_layout.addRow(self.create_label("🏪 店铺名:"), self.store_edit)
        
        # 赛季
        self.season_spin = QSpinBox()
        self.season_spin.setRange(1, 10)
        self.season_spin.setValue(int(self.settings.value("season", 5)))
        form_layout.addRow(self.create_label("📅 赛季:"), self.season_spin)
        
        # 回合（预留）
        self.round_spin = QSpinBox()
        self.round_spin.setRange(1, 10)
        self.round_spin.setValue(int(self.settings.value("round", 1)))
        form_layout.addRow(self.create_label("🔄 回合:"), self.round_spin)
        
        # 语言（预留）
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["中文", "English", "日本語"])
        self.lang_combo.setCurrentText(self.settings.value("language", "中文"))
        form_layout.addRow(self.create_label("🌐 语言（开发中）:"), self.lang_combo)
        
        layout.addWidget(form_widget)
        layout.addStretch()
        
        # 保存按钮
        save_btn = QPushButton("💾 保存设置")
        save_btn.setFont(FontManager.get_font(15, QFont.Bold))  # 从14改为15
        save_btn.setMinimumHeight(50)
        save_btn.setMinimumWidth(250)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        
        return page
    
    def create_about_page(self):
        """创建关于页"""
        page = FadeWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # 标题
        title = QLabel("ℹ️ 关于")
        title.setFont(FontManager.get_font(28, QFont.Bold))
        title.setStyleSheet("margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 大图标
        icon_label = QLabel("🏎️ DACreator")
        icon_label.setFont(FontManager.get_font(36, QFont.Bold))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # 关于文本
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setMinimumHeight(400)
        about_text.setFrameStyle(QFrame.NoFrame)
        about_text.setFont(FontManager.get_font(12))  # 从11改为12
        
        about_content = """
        <div style='font-family: "Microsoft YaHei", "微软雅黑", sans-serif; line-height: 1.8; font-size: 13px;'>  <!-- 从12px改为13px -->
            <h2 style='color: #2c3e50; margin-bottom: 10px;'>DACreator 成绩表生成工具</h2>
            <p style='color: #7f8c8d;'>版本 2.0.0 (GUI版)</p>
            <p style='margin: 20px 0;'>
                为头文字D：激斗设计的爬虫工具，可自动抓取ArcadeZone的计时赛成绩并生成可视化表格。
            </p>
            
            <h3 style='color: #2c3e50; margin-top: 30px; margin-bottom: 15px;'>👨‍💻 开发者</h3>
            <ul style='list-style-type: none; padding: 0;'>
                <li style='margin-bottom: 10px;'>🎯 核心开发：Takahashi_Rinta</li>
                <li style='margin-bottom: 10px;'>🎨 GUI设计：JustNacho</li>
                <li style='margin-bottom: 10px;'>🙏 特别感谢：ArcadeZone社区</li>
            </ul>
            
            <h3 style='color: #2c3e50; margin-top: 30px; margin-bottom: 15px;'>📚 依赖库</h3>
            <ul style='list-style-type: none; padding: 0;'>
                <li style='margin-bottom: 8px;'>• PyQt5 - GUI框架</li>
                <li style='margin-bottom: 8px;'>• pandas - 数据处理</li>
                <li style='margin-bottom: 8px;'>• requests - 网络请求</li>
                <li style='margin-bottom: 8px;'>• beautifulsoup4 - HTML解析</li>
                <li style='margin-bottom: 8px;'>• pillow - 图片处理</li>
            </ul>
            
            <p style='color: #7f8c8d; margin-top: 30px;'>
                本项目遵循 MIT 开源协议，仅供学习交流，严禁商业用途。<br>
                GitHub: <a href='https://github.com/GuitaristRin/DACreator'>https://github.com/GuitaristRin/DACreator-GUI</a>
            </p>
        </div>
        """
        about_text.setHtml(about_content)
        layout.addWidget(about_text)
        
        layout.addStretch()
        return page
    
    def create_label(self, text):
        """创建带 Emoji 的标签"""
        label = QLabel(text)
        label.setFont(FontManager.get_font(13))  # 从12改为13
        return label
    
    def on_mode_changed(self, index):
        """模式改变时的处理"""
        # 模式2（本地CSV）显示文件选择容器
        self.csv_container.setVisible(index == 2)
    
    def select_csv_file(self):
        """选择CSV文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择CSV文件", "", "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        if file_path:
            self.csv_path_edit.setText(file_path)
    
    def on_page_changed(self, index):
        """页面切换动画"""
        current_page = self.stacked_widget.currentWidget()
        if current_page and hasattr(current_page, 'fade_out'):
            current_page.fade_out()
        
        QTimer.singleShot(300, lambda: self.stacked_widget.setCurrentIndex(index))
        
        new_page = self.stacked_widget.widget(index)
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
                QMessageBox.warning(self, "提示", "请选择CSV文件")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "提示", "CSV文件不存在")
                return
        
        # 选择保存目录
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
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
                QMessageBox.warning(self, "提示", "请在设置页面配置您的ID")
                self.sidebar.list_widget.setCurrentRow(1)
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
            self.log(f"📁 加载CSV：{csv_path}")
            self.log(f"📊 数据量：{len(df)} 行")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DAC成绩表_{timestamp}.png"
            save_path = os.path.join(save_dir, filename)
            
            self.log("🎨 开始生成图片...")
            self.progress_bar.setValue(30)
            
            # 定义回调函数
            def callback(msg, level="info", progress=None):
                self.log(msg, level)
                if progress is not None and progress > 0:
                    self.progress_bar.setValue(progress)
            
            save_table_image(df, save_path, callback)
            
            self.progress_bar.setValue(100)
            self.log(f"✅ 图片已保存：{save_path}")
            
            QMessageBox.information(self, "完成", f"图片已保存至：\n{save_path}")
            
        except Exception as e:
            self.log(f"❌ 处理失败：{str(e)}", "error")
            QMessageBox.critical(self, "错误", f"处理失败：{str(e)}")
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
            self.log("⏹️ 任务已停止", "warning")
            
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
        time_str = f"{minutes}分{seconds:.1f}秒" if minutes > 0 else f"{seconds:.1f}秒"
        
        self.log(f"✅ 任务完成！共处理 {len(df)} 条记录，耗时 {time_str}", "success")
        self.progress_bar.setValue(100)
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.func_combo.setEnabled(True)
        
        QMessageBox.information(self, "完成", f"任务完成！\n记录数：{len(df)}\n耗时：{time_str}")
        
        # 3秒后隐藏进度条
        QTimer.singleShot(3000, lambda: self.progress_bar.setVisible(False))
    
    def on_task_error(self, error_msg):
        """任务错误"""
        self.log(f"❌ 错误：{error_msg}", "error")
        self.progress_bar.setVisible(False)
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.func_combo.setEnabled(True)
        
        QMessageBox.critical(self, "错误", f"执行失败：{error_msg}")
    
    def log(self, message, level="info"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            prefix = "❌"
        elif level == "warning":
            prefix = "⚠️"
        elif level == "success":
            prefix = "✅"
        else:
            prefix = "📌"
        
        self.log_text.append(f"[{timestamp}] {prefix} {message}")
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
        self.settings.setValue("language", self.lang_combo.currentText())
        
        QMessageBox.information(self, "保存成功", "设置已保存")
    
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
                font-size: 13px;  /* 从12px改为13px */
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }}
            /* 下拉菜单样式 - 修复深色模式 */
            QComboBox {{
                background-color: {theme['bg_secondary']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;  /* 从12px改为13px */
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
            /* 下拉列表样式 */
            QComboBox QAbstractItemView {{
                background-color: {theme['bg_secondary']};
                color: {theme['text_primary']};
                border: 1px solid {theme['border']};
                selection-background-color: {theme['accent']};
                selection-color: white;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;  /* 从12px改为13px */
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
                font-size: 13px;  /* 从12px改为13px */
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
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    setup_logging()
    main()
