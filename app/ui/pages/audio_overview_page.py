from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QProgressBar, QFrame, QScrollArea,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QSplitter, QGroupBox, QDialog, QSlider, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPropertyAnimation, QEasingCurve, Property, QSize, QThread, QRunnable, QThreadPool
from PySide6.QtGui import QFont, QIcon, QPainter, QColor, QPen, QBrush, QLinearGradient, QCursor
import os
import logging
import random
import math
from datetime import datetime

from app.core.audio_overview import AudioOverviewController, AudioOverviewConfig, DialogLine
from utils.tts_handler import TTS_ENGINE_EDGE, TTS_ENGINE_GEMINI
from app.ui.styles.design_system import Colors


class AIExplanationPopup(QDialog):
    """AI解释弹窗 - 优雅的毛玻璃风格，支持拖拽和滚动"""
    
    def __init__(self, text: str, action: str = "explain", api_client=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.action = action  # "explain" or "translate"
        self.api_client = api_client
        self._response_text = ""
        self._drag_pos = None  # 用于窗口拖拽
        
        # 使用 Qt.Tool 窗口标志，允许窗口可拖拽移动
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(480, 320)
        self.setMaximumSize(650, 700)  # 增大最大尺寸
        
        self._init_ui()
        self._start_ai_request()
    
    def _init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容容器 - 带阴影和圆角
        container = QFrame()
        container.setObjectName("popupContainer")
        container.setStyleSheet("""
            #popupContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(45, 45, 65, 0.98),
                    stop:0.5 rgba(35, 35, 55, 0.98),
                    stop:1 rgba(28, 28, 48, 0.98));
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 16px;
            }
        """)
        
        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 100))
        container.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # 标题行 - 渐变背景
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(245, 158, 11, 0.2),
                    stop:1 transparent);
                border-radius: 10px;
                padding: 8px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 8, 8)
        
        # 图标
        icon_label = QLabel("🤖" if self.action == "explain" else "🌐")
        icon_label.setStyleSheet("font-size: 24px; background: transparent;")
        header_layout.addWidget(icon_label)
        
        # 标题和副标题
        title_container = QVBoxLayout()
        title_container.setSpacing(2)
        title_text = "AI 智能解释" if self.action == "explain" else "AI 翻译"
        title = QLabel(title_text)
        title.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 16px; font-weight: bold; background: transparent;")
        title_container.addWidget(title)
        
        subtitle = QLabel("基于 DeepSeek 驱动")
        subtitle.setStyleSheet("color: #6B7280; font-size: 11px; background: transparent;")
        title_container.addWidget(subtitle)
        header_layout.addLayout(title_container)
        
        header_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                color: #9CA3AF;
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: {Colors.PRIMARY_LIGHT};
                color: {Colors.PRIMARY};
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header_frame)
        
        # 原文卡片
        source_frame = QFrame()
        source_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        source_layout = QVBoxLayout(source_frame)
        source_layout.setContentsMargins(12, 10, 12, 10)
        
        source_title = QLabel("📝 原文")
        source_title.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: bold;")
        source_layout.addWidget(source_title)
        
        source_text = QLabel(f'"{self.text[:120]}{"..." if len(self.text) > 120 else ""}"')
        source_text.setWordWrap(True)
        source_text.setStyleSheet("color: #D1D5DB; font-size: 13px; font-style: italic; line-height: 1.5;")
        source_layout.addWidget(source_text)
        
        layout.addWidget(source_frame)
        
        # 响应区域 - 使用 QScrollArea 支持滚动
        response_frame = QFrame()
        response_frame.setStyleSheet("""
            QFrame {
                background: rgba(16, 185, 129, 0.08);
                border: 1px solid rgba(16, 185, 129, 0.15);
                border-radius: 10px;
            }
        """)
        response_layout = QVBoxLayout(response_frame)
        response_layout.setContentsMargins(12, 10, 12, 10)
        response_layout.setSpacing(8)
        
        response_title = QLabel("✨ 回答")
        response_title.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
        response_layout.addWidget(response_title)
        
        # 可滚动的响应内容区域
        response_scroll = QScrollArea()
        response_scroll.setWidgetResizable(True)
        response_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        response_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 6px;
                border-radius: 3px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(16, 185, 129, 0.5);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(16, 185, 129, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        # 响应内容容器
        response_container = QWidget()
        response_container.setStyleSheet("background: transparent;")
        response_container_layout = QVBoxLayout(response_container)
        response_container_layout.setContentsMargins(0, 0, 4, 0)
        
        self.response_label = QLabel("⏳ 正在思考中...")
        self.response_label.setWordWrap(True)
        self.response_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.response_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.response_label.setStyleSheet("""
            QLabel {
                color: #E5E7EB;
                font-size: 14px;
                line-height: 1.7;
                padding: 4px 0;
                background: transparent;
            }
            QLabel::selection {
                background: {Colors.PRIMARY};
                color: white;
            }
        """)
        response_container_layout.addWidget(self.response_label)
        response_container_layout.addStretch()
        
        response_scroll.setWidget(response_container)
        response_layout.addWidget(response_scroll, 1)
        
        layout.addWidget(response_frame, 1)
        
        # 底部按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # 复制按钮
        self.copy_btn = QPushButton("📋 复制结果")
        self.copy_btn.setEnabled(False)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: {Colors.PRIMARY_LIGHT};
                color: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: {Colors.PRIMARY_LIGHTER};
                border-color: {Colors.PRIMARY};
            }
            QPushButton:disabled {
                background: rgba(255,255,255,0.05);
                color: #6B7280;
                border-color: rgba(255,255,255,0.1);
            }
        """)
        self.copy_btn.clicked.connect(self._copy_response)
        btn_layout.addWidget(self.copy_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(container)
    
    def _start_ai_request(self):
        """发起AI请求"""
        if not self.api_client:
            self.response_label.setText("❌ 未配置API客户端")
            return
        
        # 构建提示词
        if self.action == "explain":
            prompt = f"请用简洁易懂的语言解释以下内容，直接给出解释即可：\n\n{self.text}"
        else:
            prompt = f"请翻译以下内容，只需给出翻译结果：\n\n{self.text}"
        
        # 连接信号
        self.api_client.chat_stream_chunk.connect(self._on_chunk)
        self.api_client.chat_stream_finished.connect(self._on_finished)
        self.api_client.chat_response_error.connect(self._on_error)
        
        # 获取适合文本任务的provider和model
        # 优先使用 DeepSeek 或其他文本模型，避免音频专用模型
        from app.core.config import ConfigManager
        config = ConfigManager()
        
        # 优先级：DeepSeek > DashScope > OpenAI > Google (非音频模型)
        preferred_providers = ["DeepSeek", "DashScope", "OpenAI", "Groq", "SiliconFlow", "OpenRouter"]
        
        provider = None
        model = None
        
        # 首先尝试获取用户配置的默认文本模型
        for prov in preferred_providers:
            prov_model = config.get(f"default_models.{prov}.default", "")
            if prov_model and "audio" not in prov_model.lower() and "voice" not in prov_model.lower():
                provider = prov
                model = prov_model
                break
        
        # 如果没有找到配置的模型，尝试从API获取
        if not provider or not model:
            for prov in preferred_providers:
                models = self.api_client.get_models_for_provider(prov)
                if models:
                    # 过滤掉音频相关模型
                    text_models = [m for m in models if "audio" not in m.lower() and "voice" not in m.lower() and "tts" not in m.lower()]
                    if text_models:
                        provider = prov
                        model = text_models[0]
                        break
        
        if provider and model:
            logging.info(f"AI解释使用: {provider}/{model}")
            self.api_client.start_chat_request_async(provider, model, prompt, history=[])
        else:
            self.response_label.setText("❌ 请先在设置中配置文本类AI模型")
    
    def _on_chunk(self, chunk):
        """接收流式响应"""
        if self._response_text == "":
            self.response_label.setText("")  # 清除加载提示
        self._response_text += chunk
        self.response_label.setText(self._response_text)
    
    def _on_finished(self):
        """响应完成"""
        self.copy_btn.setEnabled(True)
        # 断开信号
        try:
            self.api_client.chat_stream_chunk.disconnect(self._on_chunk)
            self.api_client.chat_stream_finished.disconnect(self._on_finished)
            self.api_client.chat_response_error.disconnect(self._on_error)
        except:
            pass
    
    def _on_error(self, error):
        """处理错误"""
        self.response_label.setText(f"❌ 请求失败: {error}")
        try:
            self.api_client.chat_stream_chunk.disconnect(self._on_chunk)
            self.api_client.chat_stream_finished.disconnect(self._on_finished)
            self.api_client.chat_response_error.disconnect(self._on_error)
        except:
            pass
    
    def _copy_response(self):
        """复制响应到剪贴板"""
        from PySide6.QtWidgets import QApplication
        if self._response_text:
            QApplication.clipboard().setText(self._response_text)
            self.copy_btn.setText("✓ 已复制")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 复制结果"))
    
    def mousePressEvent(self, event):
        """鼠标按下 - 记录拖拽起点"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动 - 拖拽窗口"""
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放 - 结束拖拽"""
        self._drag_pos = None
        event.accept()


from app.ui.components.waveform_widget import WaveformWidget


class AudioPlayerDialog(QDialog):
    """炫酷的音频播放器弹窗 - 带波形动画和脚本滚动"""
    
    def __init__(self, audio_path: str, script_lines: list, tts_handler=None, api_client=None, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self.script_lines = script_lines  # [{"role": "A", "text": "..."}, ...]
        self.tts_handler = tts_handler
        self.api_client = api_client  # 用于AI解释功能
        self._is_playing = False
        self._current_line_index = 0
        
        # 音频时长和进度追踪
        self._total_duration = 0  # 总时长（秒）
        self._elapsed_time = 0    # 已播放时间（秒）
        self._line_durations = [] # 每行的时长（秒）
        
        self.setWindowTitle("🎧 播客播放器")
        self.setMinimumSize(700, 550)
        self.resize(750, 600)  # 默认尺寸更大
        # 非模态窗口 - 允许与原界面交互
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setModal(False)  # 非模态
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e1e2e, stop:0.5 #1a1a2e, stop:1 #16213e);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
        """)
        
        self._init_ui()
        self._get_audio_duration()
        self._setup_timers()
        self._setup_slider_seek()
        
        # 自动播放 - 延迟100ms等待UI渲染完成
        QTimer.singleShot(100, self._play)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)
        
        # 顶部标题栏 - 带关闭按钮，可拖拽
        header_widget = QFrame()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # 图标和标题
        title = QLabel("🎙️ Audio Overview")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.PRIMARY}; background: transparent;")
        header_layout.addWidget(title)
        
        # 副标题
        subtitle = QLabel("播客式音频播放")
        subtitle.setStyleSheet("color: #6B7280; font-size: 13px; margin-left: 12px; background: transparent;")
        header_layout.addWidget(subtitle)
        
        header_layout.addStretch()
        
        # 关闭按钮 - 更优雅的样式
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #9CA3AF;
                border: none;
                border-radius: 18px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: {Colors.PRIMARY_LIGHT};
                color: {Colors.PRIMARY};
            }
        """)
        close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(close_btn)
        
        # 使标题栏可拖拽窗口
        header_widget.mousePressEvent = self._header_mouse_press
        header_widget.mouseMoveEvent = self._header_mouse_move
        
        layout.addWidget(header_widget)
        
        # 波形动画 - 更高更醒目
        self.waveform = WaveformWidget()
        self.waveform.setFixedHeight(60)
        layout.addWidget(self.waveform)
        
        # 脚本滚动区域
        script_frame = QFrame()
        script_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        script_layout = QVBoxLayout(script_frame)
        script_layout.setContentsMargins(12, 12, 12, 12)
        
        self.script_scroll = QScrollArea()
        self.script_scroll.setWidgetResizable(True)
        self.script_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: {Colors.PRIMARY};
                border-radius: 3px;
                min-height: 20px;
            }
        """)
        
        self.script_container = QWidget()
        self.script_container.setStyleSheet("background: transparent;")
        self.script_lines_layout = QVBoxLayout(self.script_container)
        self.script_lines_layout.setSpacing(8)
        self.script_lines_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加脚本行
        self.line_labels = []
        for i, line in enumerate(self.script_lines):
            line_widget = self._create_script_line_widget(line, i == 0)
            self.script_lines_layout.addWidget(line_widget)
            self.line_labels.append(line_widget)
        
        self.script_lines_layout.addStretch()
        self.script_scroll.setWidget(self.script_container)
        script_layout.addWidget(self.script_scroll)
        
        layout.addWidget(script_frame, 1)
        
        # 简约单行控制栏 (ElevenLabs Style)
        control_frame = QFrame()
        control_frame.setObjectName("controlFrame")
        control_frame.setStyleSheet("""
            #controlFrame {
                background: rgba(30, 41, 59, 0.5);
                border-top: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(20, 10, 20, 10)
        control_layout.setSpacing(12)
        
        # 按钮样式
        BTN_STYLE = """
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(245, 158, 11, 0.1);
                color: #FBBF24;
                border-color: rgba(245, 158, 11, 0.4);
            }
        """
        
        # 后退 10s
        self.back_btn = QPushButton("↺")
        self.back_btn.setFixedSize(32, 32)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setStyleSheet(BTN_STYLE)
        self.back_btn.clicked.connect(self._skip_backward)
        control_layout.addWidget(self.back_btn)
        
        # 播放/暂停
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(42, 42)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 21px;
                font-size: 16px;
                padding-left: 2px;
            }
            QPushButton:hover {
                background: {Colors.PRIMARY_HOVER};
            }
        """)
        play_shadow = QGraphicsDropShadowEffect()
        play_shadow.setBlurRadius(12)
        play_shadow.setXOffset(0)
        play_shadow.setYOffset(2)
        play_shadow.setColor(QColor(245, 158, 11, 80))
        self.play_btn.setGraphicsEffect(play_shadow)
        self.play_btn.clicked.connect(self._toggle_play)
        control_layout.addWidget(self.play_btn)
        
        # 前进 10s
        self.forward_btn = QPushButton("↻")
        self.forward_btn.setFixedSize(32, 32)
        self.forward_btn.setCursor(Qt.PointingHandCursor)
        self.forward_btn.setStyleSheet(BTN_STYLE)
        self.forward_btn.clicked.connect(self._skip_forward)
        control_layout.addWidget(self.forward_btn)
        
        control_layout.addSpacing(10)
        
        # 时间与进度
        TIME_STYLE = "color: #94A3B8; font-size: 11px; font-family: 'Segoe UI', monospace; background: transparent;"
        
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet(TIME_STYLE)
        control_layout.addWidget(self.current_time_label)
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 0.1);
                height: 2px;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: {Colors.PRIMARY};
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: {Colors.PRIMARY};
                border-radius: 1px;
            }
        """)
        control_layout.addWidget(self.progress_slider, 1)
        
        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet(TIME_STYLE)
        control_layout.addWidget(self.total_time_label)
        
        layout.addWidget(control_frame)
    
    def _create_script_line_widget(self, line: dict, is_active: bool = False) -> QFrame:
        """创建脚本行组件"""
        frame = QFrame()
        role = line.get('role', 'A')
        bg_color = "rgba(25, 118, 210, 0.3)" if role == "A" else "rgba(245, 124, 0, 0.3)"
        border_color = "#1976d2" if role == "A" else "#f57c00"
        
        if is_active:
            frame.setStyleSheet(f"""
                QFrame {{
                    background: {bg_color};
                    border-left: 3px solid {border_color};
                    border-radius: 8px;
                    padding: 10px;
                }}
            """)
        else:
            frame.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border-left: 3px solid transparent;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        # 角色标签
        role_label = QLabel(role)
        role_label.setFixedSize(28, 28)
        role_label.setAlignment(Qt.AlignCenter)
        role_label.setStyleSheet(f"""
            QLabel {{
                background: {border_color};
                color: white;
                border-radius: 14px;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        layout.addWidget(role_label, 0, Qt.AlignTop)
        
        # 文本 - 可选中以便用户复制或询问AI
        text_label = QLabel(line.get('text', ''))
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        text_label.setCursor(Qt.IBeamCursor)
        text_label.setContextMenuPolicy(Qt.CustomContextMenu)
        text_label.customContextMenuRequested.connect(
            lambda pos, lbl=text_label: self._show_text_context_menu(pos, lbl)
        )
        text_label.setStyleSheet(f"""
            QLabel {{
                color: {"#E5E7EB" if is_active else "#9CA3AF"};
                font-size: 15px;
                line-height: 1.6;
                padding: 4px;
            }}
            QLabel::selection {{
                background: #F59E0B;
                color: white;
            }}
        """)
        layout.addWidget(text_label, 1)
        
        return frame
    
    def _show_text_context_menu(self, pos, label):
        """显示文本右键菜单 - 包含AI解释选项"""
        from PySide6.QtWidgets import QMenu
        
        selected_text = label.selectedText()
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2a2a3e;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: #E5E7EB;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #F59E0B;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.1);
                margin: 4px 8px;
            }
        """)
        
        # 复制
        copy_action = menu.addAction("📋 复制")
        copy_action.setEnabled(bool(selected_text))
        copy_action.triggered.connect(lambda: self._copy_text(selected_text))
        
        menu.addSeparator()
        
        # AI 功能
        explain_action = menu.addAction("🤖 AI 解释")
        explain_action.setEnabled(bool(selected_text))
        explain_action.triggered.connect(lambda: self._ai_explain(selected_text))
        
        translate_action = menu.addAction("🌐 翻译")
        translate_action.setEnabled(bool(selected_text))
        translate_action.triggered.connect(lambda: self._ai_translate(selected_text))
        
        menu.addSeparator()
        
        # 全选
        select_all_action = menu.addAction("全选")
        select_all_action.triggered.connect(lambda: label.setSelection(0, len(label.text())))
        
        menu.exec(label.mapToGlobal(pos))
    
    def _copy_text(self, text):
        """复制文本到剪贴板"""
        from PySide6.QtWidgets import QApplication
        if text:
            QApplication.clipboard().setText(text)
    
    def _ai_explain(self, text):
        """使用AI解释选中文本 - 弹出内联解释窗口"""
        if not text:
            return
        # 在鼠标位置附近显示popup
        popup = AIExplanationPopup(text, action="explain", api_client=self.api_client, parent=self)
        popup.move(QCursor.pos())
        popup.show()
    
    def _ai_translate(self, text):
        """使用AI翻译选中文本 - 弹出内联翻译窗口"""
        if not text:
            return
        popup = AIExplanationPopup(text, action="translate", api_client=self.api_client, parent=self)
        popup.move(QCursor.pos())
        popup.show()
    
    def _get_audio_duration(self):
        """获取音频文件时长"""
        try:
            # 尝试使用 miniaudio 获取时长
            import miniaudio
            file_info = miniaudio.mp3_get_file_info(self.audio_path)
            self._total_duration = file_info.duration
            logging.info(f"音频时长: {self._total_duration:.2f} 秒")
        except Exception as e:
            logging.warning(f"无法获取音频时长: {e}")
            # 备用方案：使用 pydub
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(self.audio_path)
                self._total_duration = len(audio) / 1000.0  # 毫秒转秒
                logging.info(f"音频时长 (pydub): {self._total_duration:.2f} 秒")
            except Exception as e2:
                logging.warning(f"pydub 也无法获取时长: {e2}")
                # 最后备用：估算每行 3 秒
                self._total_duration = len(self.script_lines) * 3
        
        # 计算每行的时长（基于文本长度加权）
        self._calculate_line_durations()
        
        # 更新 UI
        self.total_time_label.setText(self._format_time(self._total_duration))
        self.progress_slider.setMaximum(int(self._total_duration * 1000))  # 毫秒精度
    
    def _calculate_line_durations(self):
        """基于文本长度计算每行的预估时长"""
        if not self.script_lines:
            return
        
        # 计算总字符数
        total_chars = sum(len(line.get('text', '')) for line in self.script_lines)
        if total_chars == 0:
            # 平均分配
            avg_duration = self._total_duration / len(self.script_lines)
            self._line_durations = [avg_duration] * len(self.script_lines)
        else:
            # 按文本长度比例分配时长
            self._line_durations = []
            for line in self.script_lines:
                char_count = len(line.get('text', ''))
                # 每行至少 1 秒
                duration = max(1.0, (char_count / total_chars) * self._total_duration)
                self._line_durations.append(duration)
        
        # 计算每行的累计时间点（用于判断当前应该高亮哪一行）
        self._line_end_times = []
        cumulative = 0
        for duration in self._line_durations:
            cumulative += duration
            self._line_end_times.append(cumulative)
    
    def _setup_timers(self):
        """设置定时器 - 保留但不再启动，使用实时位置信号代替"""
        pass
    
    def _setup_slider_seek(self):
        """设置进度条拖拽功能"""
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self._is_seeking = False
    
    def _on_slider_pressed(self):
        """用户开始拖拽进度条"""
        self._is_seeking = True
    
    def _on_slider_moved(self, value):
        """用户拖拽进度条时更新时间显示"""
        if self._is_seeking:
            seconds = value / 1000.0
            self.current_time_label.setText(self._format_time(seconds))
    
    def _on_slider_released(self):
        """用户释放进度条 - 跳转到新位置"""
        self._is_seeking = False
        new_pos = self.progress_slider.value() / 1000.0
        self._elapsed_time = new_pos
        
        # 更新当前行高亮
        self._update_current_line()
        
        # 注意：实际的音频跳转需要重新播放
        # 由于 miniaudio 不支持seek，我们需要停止并重新开始（简化处理）
        if self._is_playing:
            # 暂时不实现真正的seek，因为miniaudio不支持
            # 只更新UI位置
            pass
    
    def _toggle_play(self):
        """切换播放状态"""
        if self._is_playing:
            self._pause()
        else:
            self._play()
    
    def _play(self):
        """开始播放"""
        self._is_playing = True
        self.play_btn.setText("⏸")
        self.waveform.set_playing(True)
        
        # 连接播放器信号
        if self.tts_handler:
            try:
                self.tts_handler.player.playback_finished.connect(
                    self._on_playback_finished, Qt.UniqueConnection
                )
            except:
                pass
            try:
                # 连接实时位置信号
                self.tts_handler.player.position_changed.connect(
                    self._on_position_changed, Qt.UniqueConnection
                )
            except:
                pass
            # 开始播放音频
            self.tts_handler.player.play_file(self.audio_path)
    
    def _pause(self):
        """暂停播放"""
        self._is_playing = False
        self.play_btn.setText("▶")
        self.waveform.set_playing(False)
        
        # 停止音频
        if self.tts_handler:
            self.tts_handler.player.stop()
    
    def _on_position_changed(self, elapsed: float, total: float):
        """实时位置更新回调 - 用于精确的进度和行高亮"""
        if not self._is_playing:
            return
        
        # 如果用户正在拖拽进度条，不更新滑块位置
        if getattr(self, '_is_seeking', False):
            return
        
        self._elapsed_time = elapsed
        
        # 更新进度条
        self.progress_slider.setValue(int(elapsed * 1000))
        
        # 更新时间显示
        self.current_time_label.setText(self._format_time(elapsed))
        
        # 更新当前高亮行
        self._update_current_line()
    
    def _skip_backward(self):
        """后退到上一句"""
        if self._current_line_index > 0:
            # 切换到上一行
            new_index = self._current_line_index - 1
            self._update_line_style(self._current_line_index, False)
            self._current_line_index = new_index
            self._update_line_style(self._current_line_index, True)
            
            # 计算新的时间位置
            if new_index > 0:
                self._elapsed_time = self._line_end_times[new_index - 1]
            else:
                self._elapsed_time = 0
            
            # 更新UI
            self.progress_slider.setValue(int(self._elapsed_time * 1000))
            self.current_time_label.setText(self._format_time(self._elapsed_time))
            
            # 滚动到可见
            if self._current_line_index < len(self.line_labels):
                widget = self.line_labels[self._current_line_index]
                self.script_scroll.ensureWidgetVisible(widget, 50, 50)
    
    def _skip_forward(self):
        """前进到下一句"""
        if self._current_line_index < len(self.script_lines) - 1:
            # 切换到下一行
            new_index = self._current_line_index + 1
            self._update_line_style(self._current_line_index, False)
            self._current_line_index = new_index
            self._update_line_style(self._current_line_index, True)
            
            # 计算新的时间位置
            self._elapsed_time = self._line_end_times[self._current_line_index - 1] if self._current_line_index > 0 else 0
            
            # 更新UI
            self.progress_slider.setValue(int(self._elapsed_time * 1000))
            self.current_time_label.setText(self._format_time(self._elapsed_time))
            
            # 滚动到可见
            if self._current_line_index < len(self.line_labels):
                widget = self.line_labels[self._current_line_index]
                self.script_scroll.ensureWidgetVisible(widget, 50, 50)
    
    def _on_playback_finished(self):
        """播放完成回调"""
        self._is_playing = False
        self.play_btn.setText("▶")
        self.waveform.set_playing(False)
        
        # 重置到开始
        self._elapsed_time = 0
        self._current_line_index = 0
        self._update_all_line_styles()
        self.progress_slider.setValue(0)
        self.current_time_label.setText("0:00")
    

    
    def _update_current_line(self):
        """根据当前播放时间更新高亮行"""
        if not self._line_end_times:
            return
        
        # 找到当前时间对应的行
        new_line_index = 0
        for i, end_time in enumerate(self._line_end_times):
            if self._elapsed_time < end_time:
                new_line_index = i
                break
        else:
            new_line_index = len(self._line_end_times) - 1
        
        # 如果行变化了，更新样式
        if new_line_index != self._current_line_index:
            self._update_line_style(self._current_line_index, False)
            self._current_line_index = new_line_index
            self._update_line_style(self._current_line_index, True)
            
            # 滚动到可见
            if self._current_line_index < len(self.line_labels):
                widget = self.line_labels[self._current_line_index]
                self.script_scroll.ensureWidgetVisible(widget, 50, 50)
    
    def _update_all_line_styles(self):
        """更新所有行的样式"""
        for i in range(len(self.line_labels)):
            self._update_line_style(i, i == self._current_line_index)
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间为 M:SS 格式"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def _update_line_style(self, index: int, is_active: bool):
        """更新行样式"""
        if 0 <= index < len(self.line_labels):
            frame = self.line_labels[index]
            line = self.script_lines[index]
            role = line.get('role', 'A')
            bg_color = "rgba(25, 118, 210, 0.3)" if role == "A" else "rgba(245, 124, 0, 0.3)"
            border_color = "#1976d2" if role == "A" else "#f57c00"
            
            if is_active:
                frame.setStyleSheet(f"""
                    QFrame {{
                        background: {bg_color};
                        border-left: 3px solid {border_color};
                        border-radius: 8px;
                        padding: 10px;
                    }}
                """)
            else:
                frame.setStyleSheet("""
                    QFrame {
                        background: transparent;
                        border-left: 3px solid transparent;
                        border-radius: 8px;
                        padding: 10px;
                    }
                """)
            
            # 更新文本颜色 - 保持可选中性
            text_label = frame.findChild(QLabel)
            if text_label and text_label.text() != role:
                text_label.setStyleSheet(f"""
                    QLabel {{
                        color: {"#E5E7EB" if is_active else "#9CA3AF"};
                        font-size: 14px;
                        line-height: 1.5;
                        padding: 2px;
                    }}
                    QLabel::selection {{
                        background: #F59E0B;
                        color: white;
                    }}
                """)
    
    def _on_close(self):
        """关闭弹窗"""
        self._pause()
        self.accept()
    
    def _header_mouse_press(self, event):
        """标题栏鼠标按下 - 记录拖拽起始位置"""
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def _header_mouse_move(self, event):
        """标题栏鼠标移动 - 拖拽窗口"""
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_position'):
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self._pause()
        super().closeEvent(event)


class ScriptLineWidget(QFrame):
    """单行对话编辑组件 - 自适应高度版"""
    
    delete_requested = Signal(int)  # 请求删除，参数为索引
    content_changed = Signal()      # 内容变化
    
    def __init__(self, index: int, role: str = "A", text: str = "", api_client=None, parent=None):
        super().__init__(parent)
        self.index = index
        self.api_client = api_client
        self._init_ui(role, text)
    
    def _init_ui(self, role: str, text: str):
        self.setFrameShape(QFrame.StyledPanel)
        # 根据角色设置不同背景色
        bg_color = "#e3f2fd" if role == "A" else "#fff3e0"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 4px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)
        
        # 角色标签（简化为标签而不是下拉框）
        role_text = "A" if role == "A" else "B"
        self.role_label = QLabel(role_text)
        self.role_label.setFixedSize(24, 24)
        self.role_label.setAlignment(Qt.AlignCenter)
        self.role_label.setStyleSheet(f"""
            QLabel {{
                background-color: {"#1976d2" if role == "A" else "#f57c00"};
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.role_label, 0, Qt.AlignTop)
        
        # 保存角色值
        self._role = role
        
        # 文本标签 - 自适应高度，完整显示内容，支持选中和AI解释
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text_label.setCursor(Qt.IBeamCursor)
        self.text_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_label.customContextMenuRequested.connect(self._show_context_menu)
        self.text_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                line-height: 1.4;
                padding: 2px;
            }
            QLabel::selection {
                background: {Colors.PRIMARY};
                color: white;
            }
        """)
        layout.addWidget(self.text_label, 1)
        
        # 编辑按钮
        self.edit_btn = QPushButton("✏")
        self.edit_btn.setFixedSize(22, 22)
        self.edit_btn.setToolTip("编辑")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 11px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.edit_btn.clicked.connect(self._start_edit)
        layout.addWidget(self.edit_btn, 0, Qt.AlignTop)
        
        # 删除按钮
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(22, 22)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                border-radius: 11px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ee5a5a;
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.index))
        layout.addWidget(self.delete_btn, 0, Qt.AlignTop)
        
        # 隐藏的编辑框（编辑时显示）
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.setMinimumHeight(60)
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setPlaceholderText("输入对话内容...")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
                font-size: 13px;
            }
        """)
        self.text_edit.setVisible(False)
        layout.insertWidget(2, self.text_edit, 1)
        
        # 确认编辑按钮（编辑时显示）
        self.confirm_btn = QPushButton("✓")
        self.confirm_btn.setFixedSize(22, 22)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 11px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.confirm_btn.clicked.connect(self._finish_edit)
        self.confirm_btn.setVisible(False)
        layout.insertWidget(4, self.confirm_btn, 0, Qt.AlignTop)
    
    def _start_edit(self):
        """开始编辑"""
        self.text_edit.setPlainText(self.text_label.text())
        self.text_label.setVisible(False)
        self.text_edit.setVisible(True)
        self.edit_btn.setVisible(False)
        self.confirm_btn.setVisible(True)
        self.text_edit.setFocus()
    
    def _finish_edit(self):
        """完成编辑"""
        new_text = self.text_edit.toPlainText().strip()
        self.text_label.setText(new_text)
        self.text_label.setVisible(True)
        self.text_edit.setVisible(False)
        self.edit_btn.setVisible(True)
        self.confirm_btn.setVisible(False)
        self.content_changed.emit()
    
    def _show_context_menu(self, pos):
        """显示右键菜单 - 包含AI解释选项"""
        from PySide6.QtWidgets import QMenu
        
        selected_text = self.text_label.selectedText()
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: #333333;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #F59E0B;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #e0e0e0;
                margin: 4px 8px;
            }
        """)
        
        # 复制
        copy_action = menu.addAction("📋 复制")
        copy_action.setEnabled(bool(selected_text))
        copy_action.triggered.connect(lambda: self._copy_text(selected_text))
        
        menu.addSeparator()
        
        # AI 功能
        explain_action = menu.addAction("🤖 AI 解释")
        explain_action.setEnabled(bool(selected_text))
        explain_action.triggered.connect(lambda: self._ai_explain(selected_text))
        
        translate_action = menu.addAction("🌐 翻译")
        translate_action.setEnabled(bool(selected_text))
        translate_action.triggered.connect(lambda: self._ai_translate(selected_text))
        
        menu.addSeparator()
        
        # 全选
        select_all_action = menu.addAction("全选")
        select_all_action.triggered.connect(lambda: self.text_label.setSelection(0, len(self.text_label.text())))
        
        menu.exec(self.text_label.mapToGlobal(pos))
    
    def _copy_text(self, text):
        """复制文本到剪贴板"""
        from PySide6.QtWidgets import QApplication
        if text:
            QApplication.clipboard().setText(text)
    
    def _ai_explain(self, text):
        """使用AI解释选中文本"""
        if not text or not self.api_client:
            return
        popup = AIExplanationPopup(text, action="explain", api_client=self.api_client, parent=self)
        popup.move(QCursor.pos())
        popup.show()
    
    def _ai_translate(self, text):
        """使用AI翻译选中文本"""
        if not text or not self.api_client:
            return
        popup = AIExplanationPopup(text, action="translate", api_client=self.api_client, parent=self)
        popup.move(QCursor.pos())
        popup.show()
    
    def get_role(self) -> str:
        return self._role
    
    def get_text(self) -> str:
        return self.text_label.text().strip()
    
    def to_dialog_line(self) -> DialogLine:
        return DialogLine(role=self.get_role(), text=self.get_text())


class AudioOverviewPage(QWidget):
    """音频概览生成页面"""
    
    def __init__(self, api_client=None, tts_handler=None, config_manager=None, 
                 translation_manager=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.tts_handler = tts_handler
        self.config_manager = config_manager
        self.translation_manager = translation_manager
        
        # 数据库管理器
        from app.core.database import DatabaseManager
        self.db_manager = DatabaseManager()
        self.current_podcast_id = None  # 当前播客项目ID
        
        # 初始化控制器
        self.controller = AudioOverviewController(
            api_client=api_client,
            tts_handler=tts_handler,
            config_manager=config_manager
        )
        
        # 连接控制器信号
        self.controller.script_generated.connect(self._on_script_generated)
        self.controller.synthesis_progress.connect(self._on_synthesis_progress)
        self.controller.synthesis_complete.connect(self._on_synthesis_complete)
        self.controller.error_occurred.connect(self._on_error)
        
        self.script_widgets = []  # 脚本行组件列表
        self.current_audio_path = None
        self.player_dialog = None  # 存储播放器对话框引用
        
        self._init_ui()
        self._load_voices()
        self._load_latest_podcast()  # 加载最近的播客
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题
        title = QLabel("🎙️ Audio Overview - 播客式音频生成")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #333;")
        main_layout.addWidget(title)
        
        # 使用 Splitter 分割左右区域
        splitter = QSplitter(Qt.Horizontal)
        
        # ===== 左侧：输入和配置（紧凑布局） =====
        left_widget = QWidget()
        left_widget.setMaximumWidth(280)  # 限制最大宽度
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)
        
        # 话题输入
        topic_group = QGroupBox("话题输入")
        topic_layout = QVBoxLayout(topic_group)
        topic_layout.setContentsMargins(8, 8, 8, 8)
        
        self.topic_input = QTextEdit()
        self.topic_input.setPlaceholderText("输入话题...")
        self.topic_input.setMinimumHeight(120)  # 最小高度
        self.topic_input.setMaximumHeight(200)  # 增加最大高度
        topic_layout.addWidget(self.topic_input)
        
        left_layout.addWidget(topic_group)
        
        # 配置区域 - 紧凑布局
        config_group = QGroupBox("配置")
        config_layout = QVBoxLayout(config_group)
        config_layout.setContentsMargins(8, 8, 8, 8)
        config_layout.setSpacing(6)
        
        # AI Provider
        pm_layout = QVBoxLayout()
        pm_layout.setSpacing(4)
        self.provider_combo = QComboBox()
        if self.api_client:
            self.provider_combo.addItems(self.api_client.get_available_providers())
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        pm_layout.addWidget(self.provider_combo)
        
        self.model_combo = QComboBox()
        pm_layout.addWidget(self.model_combo)
        config_layout.addLayout(pm_layout)
        
        # 语言选择
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文", "English"])
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        config_layout.addWidget(self.language_combo)
        
        # TTS 引擎选择
        tts_engine_label = QLabel("🔧 TTS 引擎")
        tts_engine_label.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        config_layout.addWidget(tts_engine_label)
        
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.setStyleSheet("font-size: 11px;")
        self.tts_engine_combo.currentIndexChanged.connect(self._on_tts_engine_changed)
        config_layout.addWidget(self.tts_engine_combo)
        
        # 声音配置
        voice_label = QLabel("🎤 声音")
        voice_label.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        config_layout.addWidget(voice_label)
        
        # 角色A声音
        va_row = QHBoxLayout()
        va_row.setSpacing(4)
        va_label = QLabel("A")
        va_label.setFixedSize(18, 18)
        va_label.setStyleSheet("background: #1976d2; color: white; border-radius: 9px; font-weight: bold; font-size: 10px;")
        va_label.setAlignment(Qt.AlignCenter)
        va_row.addWidget(va_label)
        self.voice_a_combo = QComboBox()
        self.voice_a_combo.setStyleSheet("font-size: 11px;")
        va_row.addWidget(self.voice_a_combo, 1)
        config_layout.addLayout(va_row)
        
        # 角色B声音
        vb_row = QHBoxLayout()
        vb_row.setSpacing(4)
        vb_label = QLabel("B")
        vb_label.setFixedSize(18, 18)
        vb_label.setStyleSheet("background: #f57c00; color: white; border-radius: 9px; font-weight: bold; font-size: 10px;")
        vb_label.setAlignment(Qt.AlignCenter)
        vb_row.addWidget(vb_label)
        self.voice_b_combo = QComboBox()
        self.voice_b_combo.setStyleSheet("font-size: 11px;")
        vb_row.addWidget(self.voice_b_combo, 1)
        config_layout.addLayout(vb_row)
        
        left_layout.addWidget(config_group)
        
        # 初始化 provider/model
        self._init_provider_model()
        
        # 生成脚本按钮 - Claude 主题配色（橙色）
        self.generate_btn = QPushButton("🎬 生成对话脚本")
        self.generate_btn.setFixedHeight(45)
        self.generate_btn.setProperty("class", "PrimaryBtn")
        self.generate_btn.clicked.connect(self._on_generate_script)
        left_layout.addWidget(self.generate_btn)
        
        left_layout.addStretch()
        splitter.addWidget(left_widget)
        
        # ===== 右侧：脚本编辑和播放 =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # 脚本编辑区域
        script_group = QGroupBox("对话脚本 (可编辑)")
        script_layout = QVBoxLayout(script_group)
        
        # 脚本列表滚动区域
        self.script_scroll = QScrollArea()
        self.script_scroll.setWidgetResizable(True)
        self.script_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.script_container = QWidget()
        self.script_layout = QVBoxLayout(self.script_container)
        self.script_layout.setSpacing(8)
        self.script_layout.addStretch()
        
        self.script_scroll.setWidget(self.script_container)
        script_layout.addWidget(self.script_scroll)
        
        # 脚本操作按钮行
        script_btn_layout = QHBoxLayout()
        
        add_line_btn = QPushButton("+ 添加对话")
        add_line_btn.clicked.connect(self._add_empty_line)
        script_btn_layout.addWidget(add_line_btn)
        
        # 下载脚本按钮
        self.download_script_btn = QPushButton("📄 下载脚本")
        self.download_script_btn.setEnabled(False)
        self.download_script_btn.clicked.connect(self._on_download_script)
        script_btn_layout.addWidget(self.download_script_btn)
        
        script_layout.addLayout(script_btn_layout)
        
        right_layout.addWidget(script_group, 1)
        
        # 进度条 - Claude 主题配色
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #e0e0e0;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: {Colors.PRIMARY};
                border-radius: 5px;
            }
        """)
        right_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        right_layout.addWidget(self.status_label)
        
        # 操作按钮区域
        action_layout = QHBoxLayout()
        
        self.synthesize_btn = QPushButton("🔊 合成音频")
        self.synthesize_btn.setEnabled(False)
        self.synthesize_btn.setFixedHeight(40)
        self.synthesize_btn.setProperty("class", "PrimaryBtn")
        self.synthesize_btn.clicked.connect(self._on_synthesize)
        action_layout.addWidget(self.synthesize_btn)
        
        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.setEnabled(False)
        self.play_btn.setFixedHeight(40)
        self.play_btn.clicked.connect(self._on_play)
        action_layout.addWidget(self.play_btn)
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setEnabled(False)
        self.save_btn.setFixedHeight(40)
        self.save_btn.clicked.connect(self._on_save)
        action_layout.addWidget(self.save_btn)
        
        right_layout.addLayout(action_layout)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([240, 760])  # 左侧更窄，右侧更宽
        splitter.setStretchFactor(0, 0)  # 左侧不拉伸
        splitter.setStretchFactor(1, 1)  # 右侧拉伸
        
        main_layout.addWidget(splitter, 1)
    
    def _load_voices(self):
        """加载可用声音列表"""
        # 初始化 TTS 引擎选择器
        self._populate_tts_engines()
        
        if self.tts_handler and hasattr(self.tts_handler, 'voices'):
            self._update_voice_combos()
            # 监听声音加载完成
            if hasattr(self.tts_handler, 'voices_loaded'):
                self.tts_handler.voices_loaded.connect(self._update_voice_combos)
            # 监听引擎切换
            if hasattr(self.tts_handler, 'engine_changed'):
                self.tts_handler.engine_changed.connect(self._on_engine_changed_from_handler)
    
    def _populate_tts_engines(self):
        """填充 TTS 引擎下拉框"""
        if not self.tts_handler:
            return
        
        engines = self.tts_handler.get_available_engines()
        self.tts_engine_combo.blockSignals(True)
        self.tts_engine_combo.clear()
        
        for engine in engines:
            display_name = engine["name"]
            if not engine["available"]:
                display_name += " (未配置)"
            self.tts_engine_combo.addItem(display_name, engine["id"])
        
        # 选中当前引擎
        current_idx = self.tts_engine_combo.findData(self.tts_handler.current_engine)
        if current_idx >= 0:
            self.tts_engine_combo.setCurrentIndex(current_idx)
        
        self.tts_engine_combo.blockSignals(False)
    
    def _on_tts_engine_changed(self, index):
        """TTS 引擎切换"""
        engine_id = self.tts_engine_combo.itemData(index)
        if engine_id and self.tts_handler:
            # 检查引擎是否可用
            engines = self.tts_handler.get_available_engines()
            engine_info = next((e for e in engines if e["id"] == engine_id), None)
            
            if engine_info and not engine_info["available"]:
                QMessageBox.warning(
                    self, 
                    "引擎不可用", 
                    f"{engine_info['name']} 当前不可用。\n请在设置中配置相应的 API Key。"
                )
                # 恢复到当前引擎
                current_idx = self.tts_engine_combo.findData(self.tts_handler.current_engine)
                self.tts_engine_combo.blockSignals(True)
                self.tts_engine_combo.setCurrentIndex(current_idx)
                self.tts_engine_combo.blockSignals(False)
                return
            
            self.tts_handler.set_engine(engine_id)
            self.status_label.setText(f"已切换到 {engine_info['name']}")
    
    def _on_engine_changed_from_handler(self, engine_id):
        """当 TTS Handler 的引擎变化时同步下拉框"""
        current_data = self.tts_engine_combo.currentData()
        if current_data != engine_id:
            self.tts_engine_combo.blockSignals(True)
            idx = self.tts_engine_combo.findData(engine_id)
            if idx >= 0:
                self.tts_engine_combo.setCurrentIndex(idx)
            self.tts_engine_combo.blockSignals(False)
    
    def _update_voice_combos(self, voices=None):
        """更新声音下拉框"""
        if voices is None and self.tts_handler:
            voices = self.tts_handler.voices
        
        if not voices:
            return
        
        # 获取当前 TTS 引擎
        current_engine = self.tts_handler.current_engine if self.tts_handler else TTS_ENGINE_EDGE
        
        # 更新下拉框
        self.voice_a_combo.clear()
        self.voice_b_combo.clear()
        
        if current_engine == TTS_ENGINE_GEMINI:
            # Gemini 声音不需要按语言过滤（多语言支持）
            for voice in voices:
                name = voice.get('ShortName', voice.get('Name', ''))
                gender = voice.get('Gender', '')
                display_name = f"{name} ({gender})"
                self.voice_a_combo.addItem(display_name, name)
                self.voice_b_combo.addItem(display_name, name)
            
            # 设置默认选择 (Gemini: 尝试选择不同性别)
            if voices:
                male_idx = next((i for i, v in enumerate(voices) if v.get('Gender') == 'Male'), 0)
                female_idx = next((i for i, v in enumerate(voices) if v.get('Gender') == 'Female'), 0)
                self.voice_a_combo.setCurrentIndex(male_idx)
                self.voice_b_combo.setCurrentIndex(female_idx if female_idx != male_idx else 0)
        else:
            # Edge-TTS: 根据当前语言过滤声音
            language = "zh" if self.language_combo.currentIndex() == 0 else "en"
            locale_prefix = "zh-CN" if language == "zh" else "en-US"
            
            filtered_voices = [v for v in voices if v.get('Locale', '').startswith(locale_prefix)]
            
            for voice in filtered_voices:
                name = voice.get('ShortName', voice.get('Name', ''))
                gender = voice.get('Gender', '')
                display_name = f"{name} ({gender})"
                self.voice_a_combo.addItem(display_name, name)
                self.voice_b_combo.addItem(display_name, name)
            
            # 设置默认选择（尝试选择不同性别）
            if filtered_voices:
                male_idx = next((i for i, v in enumerate(filtered_voices) if v.get('Gender') == 'Male'), 0)
                female_idx = next((i for i, v in enumerate(filtered_voices) if v.get('Gender') == 'Female'), 0)
                self.voice_a_combo.setCurrentIndex(male_idx)
                self.voice_b_combo.setCurrentIndex(female_idx if female_idx != male_idx else 0)
    
    def _init_provider_model(self):
        """初始化 provider 和 model 选择"""
        if self.api_client and self.provider_combo.count() > 0:
            # 尝试设置默认 provider 为 deepseek 或第一个可用的
            preferred_providers = ["deepseek", "dashscope", "openai"]
            for prov in preferred_providers:
                idx = self.provider_combo.findText(prov, Qt.MatchContains)
                if idx >= 0:
                    self.provider_combo.setCurrentIndex(idx)
                    break
            else:
                self.provider_combo.setCurrentIndex(0)
            
            self._on_provider_changed()
    
    def _on_provider_changed(self):
        """Provider 切换时更新模型列表"""
        provider = self.provider_combo.currentText()
        if not provider or not self.api_client:
            return
        
        # 获取该 provider 的模型列表
        models = self.api_client.get_models_for_provider(provider)
        self.model_combo.clear()
        
        if models:
            self.model_combo.addItems(models)
            # 尝试选择一个合适的模型（优先选择 chat/turbo 类型）
            preferred_keywords = ["chat", "turbo", "plus", "pro"]
            for keyword in preferred_keywords:
                for i in range(self.model_combo.count()):
                    if keyword in self.model_combo.itemText(i).lower():
                        self.model_combo.setCurrentIndex(i)
                        return
        else:
            # 如果没有缓存的模型，尝试异步获取
            self.model_combo.addItem("加载中...")
            self.api_client.fetch_models_for_provider_async(provider)
            # 连接模型更新信号（使用 blockSignals 避免警告）
            self.api_client.models_updated.connect(self._on_models_updated, Qt.UniqueConnection)
    
    def _on_models_updated(self, provider):
        """模型列表更新"""
        if provider == self.provider_combo.currentText():
            models = self.api_client.get_models_for_provider(provider)
            self.model_combo.clear()
            if models:
                self.model_combo.addItems(models)
    
    def _on_language_changed(self):
        """语言切换时更新声音列表"""
        self._update_voice_combos()
    
    def _on_generate_script(self):
        """生成脚本按钮点击"""
        topic = self.topic_input.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "提示", "请输入话题内容")
            return
        
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText()
        
        if not provider or not model or model == "加载中...":
            QMessageBox.warning(self, "提示", "请选择 AI 提供商和模型")
            return
        
        language = "zh" if self.language_combo.currentIndex() == 0 else "en"
        
        self.generate_btn.setEnabled(False)
        self.status_label.setText("正在生成对话脚本...")
        
        # 传递 provider 和 model 给控制器
        self.controller.generate_script(topic, language, provider=provider, model=model)
    
    @Slot(list)
    def _on_script_generated(self, script_data: list):
        """脚本生成完成"""
        self.generate_btn.setEnabled(True)
        self.status_label.setText(f"脚本生成完成，共 {len(script_data)} 行对话")
        
        # 创建新的播客项目（如果是新生成的）
        topic = self.topic_input.toPlainText().strip()
        language = "zh" if self.language_combo.currentIndex() == 0 else "en"
        self.current_podcast_id = self.db_manager.create_podcast(topic, language)
        
        # 清空现有脚本
        self._clear_script_widgets()
        
        # 添加新脚本行
        for data in script_data:
            self._add_script_line(data.get('role', 'A'), data.get('text', ''))
        
        self.synthesize_btn.setEnabled(True)
        self.download_script_btn.setEnabled(True)
        
        # 保存脚本到数据库
        self._save_current_podcast()
    
    def _clear_script_widgets(self):
        """清空脚本组件"""
        for widget in self.script_widgets:
            self.script_layout.removeWidget(widget)
            widget.deleteLater()
        self.script_widgets.clear()
    
    def _add_script_line(self, role: str = "A", text: str = ""):
        """添加脚本行"""
        index = len(self.script_widgets)
        widget = ScriptLineWidget(index, role, text, api_client=self.api_client)
        widget.delete_requested.connect(self._on_delete_line)
        widget.content_changed.connect(self._on_script_content_changed)
        
        # 插入到 stretch 之前
        self.script_layout.insertWidget(self.script_layout.count() - 1, widget)
        self.script_widgets.append(widget)
    
    def _add_empty_line(self):
        """添加空白对话行"""
        # 交替角色
        last_role = self.script_widgets[-1].get_role() if self.script_widgets else "B"
        new_role = "B" if last_role == "A" else "A"
        self._add_script_line(new_role, "")
        self._on_script_content_changed()
    
    def _on_delete_line(self, index: int):
        """删除对话行"""
        if index < len(self.script_widgets):
            widget = self.script_widgets.pop(index)
            self.script_layout.removeWidget(widget)
            widget.deleteLater()
            
            # 更新索引
            for i, w in enumerate(self.script_widgets):
                w.index = i
            
            self._on_script_content_changed()
    
    def _on_script_content_changed(self):
        """脚本内容变化"""
        valid_count = sum(1 for w in self.script_widgets if w.get_text())
        self.synthesize_btn.setEnabled(valid_count >= 2)
    
    def _on_synthesize(self):
        """合成音频"""
        dialog_lines = [w.to_dialog_line() for w in self.script_widgets if w.get_text()]
        
        if len(dialog_lines) < 2:
            QMessageBox.warning(self, "提示", "至少需要2行有效对话")
            return
        
        # 更新配置
        language = "zh" if self.language_combo.currentIndex() == 0 else "en"
        
        # 获取声音名称 - 确保使用正确的格式
        voice_a = self.voice_a_combo.currentData()
        voice_b = self.voice_b_combo.currentData()
        
        # 如果没有选择声音，使用默认值
        if not voice_a or not voice_b:
            defaults = self.controller.config.get_default_voices()
            voice_a = voice_a or defaults[0]
            voice_b = voice_b or defaults[1]
        
        # 获取 TTS 引擎
        tts_engine = self.tts_engine_combo.currentData() or "edge"
        
        logging.info(f"合成音频 - 语言: {language}, 引擎: {tts_engine}, 声音A: {voice_a}, 声音B: {voice_b}")
        
        self.controller.config.language = language
        self.controller.config.voice_a = voice_a
        self.controller.config.voice_b = voice_b
        
        # 生成输出路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join("output", f"audio_overview_{timestamp}.mp3")
        os.makedirs("output", exist_ok=True)
        
        self.synthesize_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在合成音频...")
        
        self.controller.synthesize_audio(dialog_lines, output_path, tts_engine=tts_engine)
    
    @Slot(int)
    def _on_synthesis_progress(self, progress: int):
        """合成进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"正在合成音频... {progress}%")
    
    @Slot(str)
    def _on_synthesis_complete(self, file_path: str):
        """合成完成"""
        self.current_audio_path = file_path
        self.synthesize_btn.setEnabled(True)
        self.play_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"✅ 音频合成完成: {file_path}")
        
        # 更新数据库中的音频路径
        if self.current_podcast_id:
            self.db_manager.update_podcast(self.current_podcast_id, audio_path=file_path)
    
    @Slot(str)
    def _on_error(self, error_msg: str):
        """错误处理"""
        self.generate_btn.setEnabled(True)
        self.synthesize_btn.setEnabled(len(self.script_widgets) >= 2)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ {error_msg}")
        QMessageBox.warning(self, "错误", error_msg)
    
    def _on_play(self):
        """播放音频 - 打开炫酷播放器弹窗"""
        if self.current_audio_path and os.path.exists(self.current_audio_path):
            # 收集脚本数据
            script_data = []
            for widget in self.script_widgets:
                text = widget.get_text()
                if text:
                    script_data.append({
                        "role": widget.get_role(),
                        "text": text
                    })
            
            # 如果已经存在旧的播放器，先关闭它
            if self.player_dialog:
                try:
                    self.player_dialog.close()
                except:
                    pass
            
            # 打开播放器弹窗 - 使用 show() 而不是 exec() 以支持非模态显示
            self.player_dialog = AudioPlayerDialog(
                audio_path=self.current_audio_path,
                script_lines=script_data,
                tts_handler=self.tts_handler,
                api_client=self.api_client,
                parent=self
            )
            # 设置为非模态
            self.player_dialog.setModal(False)
            self.player_dialog.show()
            self.player_dialog.raise_()
            self.player_dialog.activateWindow()
    
    def _get_safe_filename(self, text: str, max_length: int = 30) -> str:
        """将文本转换为安全的文件名"""
        import re
        # 移除不安全的文件名字符
        safe_name = re.sub(r'[\\/:*?"<>|]', '', text)
        # 替换空白为下划线
        safe_name = re.sub(r'\s+', '_', safe_name)
        # 限制长度
        if len(safe_name) > max_length:
            safe_name = safe_name[:max_length]
        # 如果为空，使用默认名称
        return safe_name.strip('_') or "audio_overview"
    
    def _on_save(self):
        """保存音频"""
        if not self.current_audio_path or not os.path.exists(self.current_audio_path):
            return
        
        # 使用话题作为默认文件名
        topic = self.topic_input.toPlainText().strip()
        default_name = self._get_safe_filename(topic) if topic else "audio_overview"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存音频", 
            f"{default_name}.mp3",
            "MP3 文件 (*.mp3)"
        )
        
        if file_path:
            import shutil
            shutil.copy(self.current_audio_path, file_path)
            QMessageBox.information(self, "保存成功", f"音频已保存到:\n{file_path}")
    
    def _on_download_script(self):
        """下载脚本为文本文件"""
        if not self.script_widgets:
            QMessageBox.warning(self, "提示", "没有可下载的脚本")
            return
        
        # 生成脚本内容
        script_lines = []
        for widget in self.script_widgets:
            text = widget.get_text()
            if text:
                role = widget.get_role()
                script_lines.append(f"{role}: {text}")
        
        if not script_lines:
            QMessageBox.warning(self, "提示", "脚本内容为空")
            return
        
        script_content = "\n\n".join(script_lines)
        
        # 使用话题作为默认文件名
        topic = self.topic_input.toPlainText().strip()
        default_name = self._get_safe_filename(topic) if topic else "script"
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存脚本", 
            f"{default_name}.txt",
            "文本文件 (*.txt);;Markdown 文件 (*.md)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 添加标题
                    topic = self.topic_input.toPlainText().strip()[:50]
                    f.write(f"# 播客脚本\n\n")
                    f.write(f"话题: {topic}\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"对话行数: {len(script_lines)}\n\n")
                    f.write("-" * 50 + "\n\n")
                    f.write(script_content)
                QMessageBox.information(self, "保存成功", f"脚本已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"保存脚本时出错:\n{str(e)}")

    # ========== 播客持久化方法 ==========
    
    def _load_latest_podcast(self):
        """加载最近的播客项目"""
        try:
            podcast = self.db_manager.get_latest_podcast()
            if podcast:
                self._load_podcast(podcast['id'])
        except Exception as e:
            logging.warning(f"加载最近播客失败: {e}")
    
    def _load_podcast(self, podcast_id: int):
        """加载指定的播客项目"""
        try:
            podcast = self.db_manager.get_podcast(podcast_id)
            if not podcast:
                return
            
            self.current_podcast_id = podcast_id
            
            # 设置话题
            self.topic_input.setPlainText(podcast.get('topic', ''))
            
            # 设置语言
            language = podcast.get('language', 'zh')
            self.language_combo.setCurrentIndex(0 if language == 'zh' else 1)
            
            # 设置音频路径
            audio_path = podcast.get('audio_path')
            if audio_path and os.path.exists(audio_path):
                self.current_audio_path = audio_path
                self.play_btn.setEnabled(True)
                self.save_btn.setEnabled(True)
            
            # 加载脚本
            script_lines = self.db_manager.get_podcast_script(podcast_id)
            if script_lines:
                self._clear_script_widgets()
                for line in script_lines:
                    self._add_script_line(line.get('role', 'A'), line.get('text', ''))
                self.synthesize_btn.setEnabled(True)
                self.download_script_btn.setEnabled(True)
            
            logging.info(f"已加载播客项目: {podcast_id}")
        except Exception as e:
            logging.error(f"加载播客失败: {e}")
    
    def _save_current_podcast(self):
        """保存当前播客到数据库"""
        try:
            topic = self.topic_input.toPlainText().strip()
            language = "zh" if self.language_combo.currentIndex() == 0 else "en"
            
            # 收集脚本数据
            script_lines = []
            for widget in self.script_widgets:
                text = widget.get_text()
                if text:
                    script_lines.append({
                        'role': widget.get_role(),
                        'text': text
                    })
            
            if not script_lines:
                return  # 没有脚本内容，不保存
            
            # 创建或更新播客
            if self.current_podcast_id:
                self.db_manager.update_podcast(
                    self.current_podcast_id,
                    topic=topic,
                    audio_path=self.current_audio_path
                )
            else:
                self.current_podcast_id = self.db_manager.create_podcast(topic, language)
            
            # 保存脚本
            self.db_manager.save_podcast_script(self.current_podcast_id, script_lines)
            logging.info(f"播客已保存: {self.current_podcast_id}")
        except Exception as e:
            logging.error(f"保存播客失败: {e}")
    
    def _create_new_podcast(self):
        """创建新的播客项目"""
        # 保存当前播客
        if self.script_widgets:
            self._save_current_podcast()
        
        # 重置状态
        self.current_podcast_id = None
        self.current_audio_path = None
        self.topic_input.clear()
        self._clear_script_widgets()
        self.synthesize_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.download_script_btn.setEnabled(False)
        self.status_label.setText("")
