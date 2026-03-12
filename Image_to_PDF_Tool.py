"""
图片转PDF工具 - 极简丝滑版 (PyQt5)
功能：将多张图片合并转换为一个PDF文件
版本：2.3 (优化布局版)
"""

import os
import sys
from PIL import Image
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QFileDialog, QMessageBox,
    QLabel, QFrame, QSlider, QLineEdit, QAbstractItemView, QDesktopWidget,
    QProgressDialog, QComboBox, QDialog, QCheckBox, QGroupBox, QSplitter,
    QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, QPoint, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPixmap, QDragEnterEvent, QDropEvent


class ModernButton(QPushButton):
    """现代风格按钮 - 支持悬停、点击动画"""
    def __init__(self, text, parent=None, bg_color="#4CAF50", hover_color="#45a049"):
        super().__init__(text, parent)
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.default_style = f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 6px;
                font: bold 9pt "Microsoft YaHei";
                padding: 6px 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(hover_color)};
            }}
        """
        self.setStyleSheet(self.default_style)
        self.setCursor(Qt.PointingHandCursor)

    def darken_color(self, color):
        """加深颜色"""
        color = QColor(color)
        h, s, v, _ = color.getHsv()
        return QColor.fromHsv(h, s, min(255, v - 30)).name()


class ModernLineEdit(QLineEdit):
    """现代风格输入框"""
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 5px 8px;
                font: 9pt "Microsoft YaHei";
                background-color: white;
                selection-background-color: #2196F3;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)


class ModernSlider(QWidget):
    """现代风格滑块"""
    def __init__(self, parent=None, min_val=0, max_val=100, default_val=95):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(default_val)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #e0e0e0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                border: none;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #1976D2;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
                border-radius: 2px;
            }
        """)

        self.value_label = QLabel(f"{default_val}%")
        self.value_label.setStyleSheet("""
            QLabel {
                color: #2196F3;
                font: 9pt "Microsoft YaHei";
                min-width: 40px;
            }
        """)

        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)

        self.setLayout(layout)

        # 连接信号
        self.slider.valueChanged.connect(lambda v: self.value_label.setText(f"{v}%"))

    def value(self):
        return self.slider.value()

    def setValue(self, value):
        self.slider.setValue(value)


class ConvertThread(QThread):
    """转换线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, image_paths, quality, page_size):
        super().__init__()
        self.image_paths = image_paths
        self.quality = quality
        self.page_size = page_size

    def run(self):
        try:
            images = []
            for i, img_path in enumerate(self.image_paths):
                img = Image.open(img_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 根据页面大小调整 - 使用标准PDF大小
                if self.page_size != "原始大小":
                    img = self.resize_image(img, self.page_size)

                images.append(img)
                self.progress.emit(i + 1)

            self.finished.emit(images)
        except Exception as e:
            self.error.emit(str(e))

    def resize_image(self, img, page_size):
        """调整图片大小 - 标准PDF大小"""
        # 标准PDF页面尺寸（点，1点 = 1/72英寸）
        sizes = {
            "A4": (595, 842),
            "A3": (842, 1191),
            "Letter": (612, 792)
        }

        if page_size in sizes:
            target_size = sizes[page_size]

            # 计算缩放比例，保持宽高比
            img_ratio = img.width / img.height
            target_ratio = target_size[0] / target_size[1]

            if img_ratio > target_ratio:
                # 图片更宽，按宽度缩放
                new_width = target_size[0]
                new_height = int(new_width / img_ratio)
            else:
                # 图片更高，按高度缩放
                new_height = target_size[1]
                new_width = int(new_height * img_ratio)

            # 缩放图片
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 创建标准大小的白色背景
            new_img = Image.new('RGB', target_size, (255, 255, 255))

            # 将图片居中粘贴
            paste_x = (target_size[0] - new_width) // 2
            paste_y = (target_size[1] - new_height) // 2
            new_img.paste(img, (paste_x, paste_y))

            return new_img

        return img


class ImageToPDF(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.history = []
        self.redo_stack = []
        self.settings = QSettings('YourCompany', 'ImageToPDF')
        self.init_ui()
        self.load_settings()
        self.setAcceptDrops(True)
        self.add_to_history()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("图片转PDF工具")
        self.setGeometry(100, 100, 1000, 700)  # 稍微加宽窗口
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 中心窗口部件
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet("""
            #CentralWidget {
                background-color: #fafafa;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)
        self.setCentralWidget(central_widget)

        # 主布局 - 使用垂直布局，但不使用滚动区域
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建自定义标题栏
        self.create_title_bar(main_layout)

        # 内容容器 - 直接使用固定高度的布局
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 10, 15, 10)
        content_layout.setSpacing(8)

        # 创建各个部分
        self.create_header(content_layout)
        self.create_main_content(content_layout)
        self.create_convert_button(content_layout)
        self.create_status_bar(content_layout)

        main_layout.addWidget(content_widget)

        # 居中显示
        self.center_window()

    def create_title_bar(self, parent_layout):
        """创建自定义标题栏"""
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setStyleSheet("""
            #TitleBar {
                background-color: white;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        title_bar.setFixedHeight(35)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(12, 0, 8, 0)

        # 标题和图标
        title_layout = QHBoxLayout()
        title_icon = QLabel("🖼️")
        title_icon.setStyleSheet("font-size: 14px;")
        title_layout.addWidget(title_icon)

        title = QLabel("图片转PDF工具")
        title.setStyleSheet("""
            QLabel {
                color: #333333;
                font: 10pt "Microsoft YaHei";
                font-weight: bold;
            }
        """)
        title_layout.addWidget(title)
        layout.addLayout(title_layout)

        layout.addStretch()

        # 窗口控制按钮
        self.min_btn = QPushButton("─")
        self.max_btn = QPushButton("□")
        self.close_btn = QPushButton("✕")

        for btn in [self.min_btn, self.max_btn, self.close_btn]:
            btn.setFixedSize(28, 28)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #666666;
                    border: none;
                    font-size: 13px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border-radius: 14px;
                }
            """)
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)

        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(self.close)

        # 特殊处理关闭按钮悬停
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f44336;
                color: white;
                border-radius: 14px;
            }
        """)

        parent_layout.addWidget(title_bar)

        # 添加窗口拖动功能
        self.drag_pos = None
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move

    def toggle_maximize(self):
        """切换最大化/还原"""
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("□")
        else:
            self.showMaximized()
            self.max_btn.setText("❐")

    def title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos()
            event.accept()

    def title_bar_mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(self.pos() + event.globalPos() - self.drag_pos)
            self.drag_pos = event.globalPos()
            event.accept()

    def create_header(self, parent_layout):
        """创建头部 - 高度减小"""
        header_widget = QWidget()
        header_widget.setFixedHeight(50)

        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(5, 0, 5, 0)

        # 左侧标题
        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        main_title = QLabel("图片转PDF")
        main_title.setStyleSheet("""
            QLabel {
                color: #333333;
                font: bold 16pt "Microsoft YaHei";
            }
        """)
        title_layout.addWidget(main_title)

        subtitle = QLabel("轻松将多张图片合并为PDF文件")
        subtitle.setStyleSheet("""
            QLabel {
                color: #999999;
                font: 8pt "Microsoft YaHei";
            }
        """)
        title_layout.addWidget(subtitle)

        layout.addLayout(title_layout)
        layout.addStretch()

        # 右侧统计信息
        stats_widget = QWidget()
        stats_widget.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-radius: 16px;
                padding: 4px;
            }
        """)
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(12, 4, 12, 4)

        stats_icon = QLabel("📊")
        stats_icon.setStyleSheet("font-size: 14px;")
        stats_layout.addWidget(stats_icon)

        self.stats_label = QLabel("0 张图片 | 0 MB")
        self.stats_label.setStyleSheet("color: #666666; font: 9pt 'Microsoft YaHei';")
        stats_layout.addWidget(self.stats_label)

        layout.addWidget(stats_widget)

        parent_layout.addWidget(header_widget)

    def create_main_content(self, parent_layout):
        """创建主要内容区域 - 使用固定比例"""
        # 使用QSplitter实现可调整大小的分栏
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
            }
            QSplitter::handle:hover {
                background-color: #2196F3;
            }
        """)

        # 左侧面板
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 右侧面板
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置初始比例 - 调整比例让右侧更大
        splitter.setSizes([200, 750])

        parent_layout.addWidget(splitter, 1)  # 添加拉伸因子

    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        panel.setMinimumWidth(160)
        panel.setMaximumWidth(220)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 5, 0)
        layout.setSpacing(8)

        # 文件操作组
        file_group = QGroupBox("文件操作")
        file_group.setStyleSheet("""
            QGroupBox {
                font: bold 10pt "Microsoft YaHei";
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(4)
        file_layout.setContentsMargins(6, 8, 6, 6)

        # 按钮配置
        file_buttons = [
            ("📁 添加图片", self.add_images, "#4CAF50", "#45a049"),
            ("🗑️ 清空", self.clear_list, "#f44336", "#da190b"),
            ("❌ 删除选中", self.delete_selected, "#ff9800", "#e68900"),
        ]

        for text, func, bg, hover in file_buttons:
            btn = ModernButton(text, bg_color=bg, hover_color=hover)
            btn.clicked.connect(func)
            file_layout.addWidget(btn)

        layout.addWidget(file_group)

        # 排序操作组
        sort_group = QGroupBox("排序操作")
        sort_group.setStyleSheet("""
            QGroupBox {
                font: bold 10pt "Microsoft YaHei";
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        sort_layout = QVBoxLayout(sort_group)
        sort_layout.setSpacing(4)
        sort_layout.setContentsMargins(6, 8, 6, 6)

        sort_buttons = [
            ("⬆️ 上移", self.move_up, "#2196F3", "#1976D2"),
            ("⬇️ 下移", self.move_down, "#2196F3", "#1976D2"),
            ("🔄 撤销", self.undo, "#9C27B0", "#7B1FA2"),
            ("↩️ 重做", self.redo, "#9C27B0", "#7B1FA2"),
        ]

        for text, func, bg, hover in sort_buttons:
            btn = ModernButton(text, bg_color=bg, hover_color=hover)
            btn.clicked.connect(func)
            sort_layout.addWidget(btn)

        layout.addWidget(sort_group)

        # 工具组
        tool_group = QGroupBox("工具")
        tool_group.setStyleSheet("""
            QGroupBox {
                font: bold 10pt "Microsoft YaHei";
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        tool_layout = QVBoxLayout(tool_group)
        tool_layout.setSpacing(4)
        tool_layout.setContentsMargins(6, 8, 6, 6)

        tool_buttons = [
            ("✏️ 批量重命名", self.batch_rename, "#607D8B", "#455A64"),
            ("🔄 重启", self.restart_program, "#9C27B0", "#7B1FA2"),
        ]

        for text, func, bg, hover in tool_buttons:
            btn = ModernButton(text, bg_color=bg, hover_color=hover)
            btn.clicked.connect(func)
            tool_layout.addWidget(btn)

        layout.addWidget(tool_group)
        layout.addStretch()

        return panel

    def create_right_panel(self):
        """创建右侧面板 - 优化布局"""
        panel = QWidget()

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(8)

        # 图片列表区域 - 给更多空间
        list_group = QGroupBox("图片列表")
        list_group.setStyleSheet("""
            QGroupBox {
                font: bold 10pt "Microsoft YaHei";
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(6, 8, 6, 6)

        # 列表控件
        self.listbox = QListWidget()
        self.listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.listbox.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 4px;
                font: 9pt "Microsoft YaHei";
                outline: none;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #f0f0f0;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)

        # 启用拖拽
        self.listbox.setAcceptDrops(True)
        self.listbox.setDragEnabled(True)
        self.listbox.setDefaultDropAction(Qt.MoveAction)

        list_layout.addWidget(self.listbox)

        # 快捷键提示
        shortcut_label = QLabel("💡 快捷键: Ctrl+A全选 | Ctrl+I反选 | Delete删除 | Ctrl+Z撤销")
        shortcut_label.setStyleSheet("""
            QLabel {
                color: #999999;
                font: 8pt "Microsoft YaHei";
                padding: 4px;
                background-color: #f9f9f9;
                border-radius: 4px;
            }
        """)
        list_layout.addWidget(shortcut_label)

        layout.addWidget(list_group, 2)  # 给列表更多空间

        # PDF设置区域 - 使用网格布局节省空间
        settings_group = QGroupBox("PDF设置")
        settings_group.setStyleSheet("""
            QGroupBox {
                font: bold 10pt "Microsoft YaHei";
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        settings_layout = QGridLayout(settings_group)
        settings_layout.setVerticalSpacing(6)
        settings_layout.setHorizontalSpacing(8)
        settings_layout.setContentsMargins(8, 8, 8, 8)

        # 文件名设置
        name_label = QLabel("文件名:")
        name_label.setStyleSheet("color: #666666; font: 9pt 'Microsoft YaHei';")
        settings_layout.addWidget(name_label, 0, 0)

        self.pdf_name = ModernLineEdit(placeholder="我的图片.pdf")
        settings_layout.addWidget(self.pdf_name, 0, 1)

        # 质量设置
        quality_label = QLabel("质量:")
        quality_label.setStyleSheet("color: #666666; font: 9pt 'Microsoft YaHei';")
        settings_layout.addWidget(quality_label, 1, 0)

        self.quality = ModernSlider(default_val=95)
        settings_layout.addWidget(self.quality, 1, 1)

        # 页面大小设置
        size_label = QLabel("页面大小:")
        size_label.setStyleSheet("color: #666666; font: 9pt 'Microsoft YaHei';")
        settings_layout.addWidget(size_label, 2, 0)

        self.page_size = QComboBox()
        self.page_size.addItems(["原始大小", "A4", "A3", "Letter"])
        self.page_size.setStyleSheet("""
            QComboBox {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 4px;
                font: 9pt "Microsoft YaHei";
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        settings_layout.addWidget(self.page_size, 2, 1)

        # 自动打开选项
        self.auto_open = QCheckBox("转换后自动打开文件夹")
        self.auto_open.setStyleSheet("""
            QCheckBox {
                color: #666666;
                font: 9pt "Microsoft YaHei";
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 2px solid #e0e0e0;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
        """)
        settings_layout.addWidget(self.auto_open, 3, 0, 1, 2)

        layout.addWidget(settings_group, 1)

        # 预览区域 - 固定高度
        preview_group = QGroupBox("图片预览")
        preview_group.setStyleSheet("""
            QGroupBox {
                font: bold 10pt "Microsoft YaHei";
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(6, 8, 6, 6)

        self.preview_label = QLabel()
        self.preview_label.setFixedHeight(90)  # 固定预览高度
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border-radius: 6px;
                border: 1px dashed #e0e0e0;
                color: #999999;
                font: 9pt "Microsoft YaHei";
            }
        """)
        self.preview_label.setText("👆 选择图片查看预览")

        preview_layout.addWidget(self.preview_label)

        layout.addWidget(preview_group, 1)

        # 连接选择变化信号
        self.listbox.itemSelectionChanged.connect(self.preview_selected_image)

        return panel

    def create_convert_button(self, parent_layout):
        """创建转换按钮 - 固定高度，确保可见"""
        btn_widget = QWidget()
        btn_widget.setFixedHeight(60)

        layout = QHBoxLayout(btn_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧信息
        info_widget = QWidget()
        info_widget.setStyleSheet("""
            QWidget {
                background-color: #E3F2FD;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(8, 4, 8, 4)

        info_icon = QLabel("ℹ️")
        info_icon.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(info_icon)

        self.info_label = QLabel("就绪")
        self.info_label.setStyleSheet("color: #1976D2; font: 9pt 'Microsoft YaHei';")
        info_layout.addWidget(self.info_label)

        layout.addWidget(info_widget)

        layout.addStretch()

        # 转换按钮
        self.convert_btn = QPushButton("📄 开始转换")
        self.convert_btn.setFixedSize(140, 40)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 20px;
                font: bold 11pt "Microsoft YaHei";
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.convert_btn.setCursor(Qt.PointingHandCursor)
        self.convert_btn.clicked.connect(self.convert_to_pdf)

        layout.addWidget(self.convert_btn)

        parent_layout.addWidget(btn_widget)

    def create_status_bar(self, parent_layout):
        """创建状态栏"""
        status_widget = QWidget()
        status_widget.setFixedHeight(32)
        status_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #e0e0e0;
            }
        """)

        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(12, 0, 12, 0)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font: 9pt "Microsoft YaHei";
            }
        """)
        layout.addWidget(self.status_dot)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font: 9pt "Microsoft YaHei";
            }
        """)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 版本信息
        version_label = QLabel("v2.3 (优化布局版)")
        version_label.setStyleSheet("color: #CCCCCC; font: 8pt 'Microsoft YaHei';")
        layout.addWidget(version_label)

        parent_layout.addWidget(status_widget)

    def center_window(self):
        """居中显示窗口"""
        screen = QDesktopWidget().availableGeometry()
        window = self.frameGeometry()
        window.moveCenter(screen.center())
        self.move(window.topLeft())

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """拖拽放置事件"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}

        added_count = 0
        for file in files:
            if os.path.splitext(file)[1].lower() in image_extensions:
                if file not in self.image_paths:
                    self.image_paths.append(file)
                    self.listbox.addItem(os.path.basename(file))
                    added_count += 1

        if added_count > 0:
            self.update_stats()
            self.add_to_history()
            self.status_label.setText(f"已添加 {added_count} 张图片")

    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_A:  # Ctrl+A 全选
                self.listbox.selectAll()
            elif event.key() == Qt.Key_I:  # Ctrl+I 反选
                for i in range(self.listbox.count()):
                    item = self.listbox.item(i)
                    item.setSelected(not item.isSelected())
            elif event.key() == Qt.Key_Z:  # Ctrl+Z 撤销
                self.undo()
            elif event.key() == Qt.Key_Y:  # Ctrl+Y 重做
                self.redo()
        elif event.key() == Qt.Key_Delete:
            self.delete_selected()
        elif event.key() == Qt.Key_Escape:
            self.listbox.clearSelection()

    def add_images(self):
        """添加图片"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )

        added_count = 0
        for file in files:
            if file not in self.image_paths:
                self.image_paths.append(file)
                self.listbox.addItem(os.path.basename(file))
                added_count += 1

        if added_count > 0:
            self.update_stats()
            self.add_to_history()
            self.status_label.setText(f"已添加 {added_count} 张图片")

    def clear_list(self):
        """清空列表"""
        if self.image_paths:
            reply = QMessageBox.question(
                self,
                "确认清空",
                "确定要清空列表吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.image_paths.clear()
                self.listbox.clear()
                self.update_stats()
                self.add_to_history()
                self.status_label.setText("列表已清空")
                self.preview_label.setText("👆 选择图片查看预览")

    def delete_selected(self):
        """删除选中项"""
        selected = self.listbox.selectedItems()
        if selected:
            # 从后往前删除，避免索引变化
            rows = sorted([self.listbox.row(item) for item in selected], reverse=True)
            for row in rows:
                del self.image_paths[row]
                self.listbox.takeItem(row)

            self.update_stats()
            self.add_to_history()
            self.status_label.setText(f"已删除 {len(selected)} 张图片")

            if not self.image_paths:
                self.preview_label.setText("👆 选择图片查看预览")

    def move_up(self):
        """上移选中项"""
        selected = self.listbox.selectedItems()
        if selected and self.listbox.row(selected[0]) > 0:
            # 对选中的项目排序
            rows = sorted([self.listbox.row(item) for item in selected])

            for row in rows:
                if row > 0:
                    # 交换数据
                    self.image_paths[row], self.image_paths[row-1] = \
                        self.image_paths[row-1], self.image_paths[row]

                    # 更新列表显示
                    item = self.listbox.takeItem(row)
                    self.listbox.insertItem(row-1, item)
                    item.setSelected(True)

            self.add_to_history()

    def move_down(self):
        """下移选中项"""
        selected = self.listbox.selectedItems()
        if selected and self.listbox.row(selected[-1]) < len(self.image_paths) - 1:
            # 对选中的项目排序（从大到小）
            rows = sorted([self.listbox.row(item) for item in selected], reverse=True)

            for row in rows:
                if row < len(self.image_paths) - 1:
                    # 交换数据
                    self.image_paths[row], self.image_paths[row+1] = \
                        self.image_paths[row+1], self.image_paths[row]

                    # 更新列表显示
                    item = self.listbox.takeItem(row)
                    self.listbox.insertItem(row+1, item)
                    item.setSelected(True)

            self.add_to_history()

    def update_stats(self):
        """更新统计信息"""
        count = len(self.image_paths)
        if count > 0:
            total_size = sum(os.path.getsize(f) for f in self.image_paths) / (1024 * 1024)
            self.stats_label.setText(f"{count} 张图片 | {total_size:.2f} MB")
            self.info_label.setText(f"准备转换 {count} 张图片")
        else:
            self.stats_label.setText("0 张图片 | 0 MB")
            self.info_label.setText("就绪")

    def add_to_history(self):
        """添加当前状态到历史记录"""
        self.history.append(self.image_paths.copy())
        self.redo_stack.clear()

        # 限制历史记录大小
        if len(self.history) > 20:
            self.history.pop(0)

    def undo(self):
        """撤销"""
        if len(self.history) > 1:
            self.redo_stack.append(self.history.pop())
            self.image_paths = self.history[-1].copy()
            self.refresh_list()
            self.status_label.setText("已撤销")

    def redo(self):
        """重做"""
        if self.redo_stack:
            self.history.append(self.redo_stack.pop())
            self.image_paths = self.history[-1].copy()
            self.refresh_list()
            self.status_label.setText("已重做")

    def refresh_list(self):
        """刷新列表显示"""
        self.listbox.clear()
        for path in self.image_paths:
            self.listbox.addItem(os.path.basename(path))
        self.update_stats()

    def preview_selected_image(self):
        """预览选中的图片"""
        selected = self.listbox.selectedItems()
        if len(selected) == 1:
            row = self.listbox.row(selected[0])
            img_path = self.image_paths[row]

            # 使用PIL加载并缩放图片
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                # 获取预览区域大小
                preview_size = self.preview_label.size()
                if preview_size.width() > 0 and preview_size.height() > 0:
                    # 缩放以适应预览区域，保持宽高比
                    scaled_pixmap = pixmap.scaled(
                        preview_size.width() - 10,
                        preview_size.height() - 10,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.preview_label.setPixmap(scaled_pixmap)
                    self.preview_label.setText("")
        else:
            self.preview_label.setText("👆 选择图片查看预览")
            self.preview_label.setPixmap(QPixmap())

    def batch_rename(self):
        """批量重命名列表中的文件（仅显示名称，不实际重命名文件）"""
        if not self.image_paths:
            QMessageBox.warning(self, "提示", "列表为空")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("批量重命名")
        dialog.setFixedSize(380, 180)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # 设置样式
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("批量重命名显示名称")
        title.setStyleSheet("font: bold 11pt 'Microsoft YaHei'; color: #333333;")
        layout.addWidget(title)

        # 说明
        desc = QLabel("修改列表中显示的文件名（不会实际重命名原文件）")
        desc.setStyleSheet("color: #999999; font: 8pt 'Microsoft YaHei';")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 前缀输入
        prefix_layout = QHBoxLayout()
        prefix_label = QLabel("前缀:")
        prefix_label.setFixedWidth(40)
        prefix_label.setStyleSheet("color: #666666; font: 9pt 'Microsoft YaHei';")
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("例如：风景_")
        self.prefix_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 5px;
                font: 9pt "Microsoft YaHei";
            }
        """)
        prefix_layout.addWidget(prefix_label)
        prefix_layout.addWidget(self.prefix_input)
        layout.addLayout(prefix_layout)

        # 起始数字
        start_layout = QHBoxLayout()
        start_label = QLabel("起始:")
        start_label.setFixedWidth(40)
        start_label.setStyleSheet("color: #666666; font: 9pt 'Microsoft YaHei';")
        self.start_input = QLineEdit()
        self.start_input.setText("1")
        self.start_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 5px;
                font: 9pt "Microsoft YaHei";
            }
        """)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_input)
        layout.addLayout(start_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        ok_btn = QPushButton("应用")
        ok_btn.setFixedSize(90, 32)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font: bold 9pt "Microsoft YaHei";
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(90, 32)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #666666;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                font: 9pt "Microsoft YaHei";
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)

        ok_btn.clicked.connect(lambda: self.apply_batch_rename(dialog))
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dialog.exec_()

    def apply_batch_rename(self, dialog):
        """应用批量重命名"""
        try:
            prefix = self.prefix_input.text()
            start = int(self.start_input.text())

            # 保存原始文件路径
            old_paths = self.image_paths.copy()

            # 更新列表显示
            self.listbox.clear()
            for i, path in enumerate(old_paths):
                ext = os.path.splitext(path)[1]
                new_name = f"{prefix}{start + i}{ext}"
                self.listbox.addItem(new_name)

            # 保持文件路径不变，只改变显示名称
            self.image_paths = old_paths

            dialog.accept()
            self.add_to_history()
            self.status_label.setText("显示名称已更新")
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的数字")

    def restart_program(self):
        """重启程序"""
        reply = QMessageBox.question(
            self,
            "确认重启",
            "确定要重启程序吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.save_settings()
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)

    def load_settings(self):
        """加载设置"""
        # 恢复上次的PDF名称
        last_name = self.settings.value('pdf_name', '我的图片.pdf')
        self.pdf_name.setText(last_name)

        # 恢复质量设置
        last_quality = int(self.settings.value('quality', 95))
        self.quality.setValue(last_quality)

        # 恢复页面大小
        last_page_size = self.settings.value('page_size', '原始大小')
        index = self.page_size.findText(last_page_size)
        if index >= 0:
            self.page_size.setCurrentIndex(index)

        # 恢复自动打开设置
        auto_open = self.settings.value('auto_open', 'false')
        self.auto_open.setChecked(auto_open == 'true')

        # 恢复上次的图片列表
        last_images = self.settings.value('image_paths', [])
        if last_images:
            if isinstance(last_images, str):
                last_images = [last_images]
            for img_path in last_images:
                if os.path.exists(img_path):
                    self.image_paths.append(img_path)
                    self.listbox.addItem(os.path.basename(img_path))
            self.update_stats()

    def save_settings(self):
        """保存设置"""
        self.settings.setValue('pdf_name', self.pdf_name.text())
        self.settings.setValue('quality', self.quality.value())
        self.settings.setValue('page_size', self.page_size.currentText())
        self.settings.setValue('auto_open', 'true' if self.auto_open.isChecked() else 'false')
        self.settings.setValue('image_paths', self.image_paths)

    def closeEvent(self, event):
        """重写关闭事件，保存设置"""
        self.save_settings()
        event.accept()

    def convert_to_pdf(self):
        """转换为PDF"""
        if not self.image_paths:
            QMessageBox.warning(self, "提示", "请先添加图片")
            return

        # 获取文件名
        pdf_name = self.pdf_name.text()
        if not pdf_name:
            pdf_name = "我的图片.pdf"

        if not pdf_name.lower().endswith('.pdf'):
            pdf_name += '.pdf'

        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存PDF",
            pdf_name,
            "PDF文件 (*.pdf)"
        )

        if not file_path:
            return

        try:
            self.status_label.setText("转换中...")
            self.status_dot.setStyleSheet("color: #FF9800;")
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("⏳ 转换中...")

            # 创建进度对话框
            progress = QProgressDialog("正在转换图片...", "取消", 0, len(self.image_paths), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.setStyleSheet("""
                QProgressDialog {
                    background-color: white;
                    border-radius: 12px;
                    padding: 8px;
                }
                QProgressBar {
                    border: 2px solid #e0e0e0;
                    border-radius: 5px;
                    text-align: center;
                    height: 18px;
                }
                QProgressBar::chunk {
                    background-color: #2196F3;
                    border-radius: 3px;
                }
                QLabel {
                    font: 9pt "Microsoft YaHei";
                    color: #333333;
                }
                QPushButton {
                    background-color: #f5f5f5;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    padding: 4px 12px;
                    font: 9pt "Microsoft YaHei";
                }
            """)

            # 创建转换线程
            self.convert_thread = ConvertThread(
                self.image_paths,
                self.quality.value(),
                self.page_size.currentText()
            )
            self.convert_thread.progress.connect(progress.setValue)
            self.convert_thread.finished.connect(lambda images: self.on_convert_finished(images, file_path, progress))
            self.convert_thread.error.connect(lambda e: self.on_convert_error(e, progress))
            self.convert_thread.start()

        except Exception as e:
            self.on_convert_error(str(e), None)

    def on_convert_finished(self, images, file_path, progress):
        """转换完成处理"""
        try:
            progress.setLabelText("正在生成PDF...")
            progress.setMaximum(0)  # 不确定模式

            # 保存PDF
            quality = self.quality.value()
            images[0].save(
                file_path,
                save_all=True,
                append_images=images[1:],
                quality=quality
            )

            progress.close()

            self.status_label.setText("转换完成！")
            self.status_dot.setStyleSheet("color: #4CAF50;")
            self.convert_btn.setEnabled(True)
            self.convert_btn.setText("📄 开始转换")

            if self.auto_open.isChecked():
                # 打开所在文件夹
                if sys.platform == 'win32':
                    os.startfile(os.path.dirname(file_path))
                elif sys.platform == 'darwin':  # macOS
                    os.system(f'open "{os.path.dirname(file_path)}"')
                else:  # Linux
                    os.system(f'xdg-open "{os.path.dirname(file_path)}"')
            else:
                reply = QMessageBox.question(
                    self,
                    "完成",
                    "转换成功！是否打开所在文件夹？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    if sys.platform == 'win32':
                        os.startfile(os.path.dirname(file_path))
                    elif sys.platform == 'darwin':
                        os.system(f'open "{os.path.dirname(file_path)}"')
                    else:
                        os.system(f'xdg-open "{os.path.dirname(file_path)}"')

        except Exception as e:
            self.on_convert_error(str(e), progress)

    def on_convert_error(self, error_msg, progress):
        """转换错误处理"""
        if progress:
            progress.close()

        self.status_label.setText("转换失败")
        self.status_dot.setStyleSheet("color: #f44336;")
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("📄 开始转换")
        QMessageBox.critical(self, "错误", f"转换失败：{error_msg}")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))

    # 设置应用样式
    app.setStyle('Fusion')

    window = ImageToPDF()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()