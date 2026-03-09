import markdown
import os
import hashlib
import requests
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser, QFrame, QHBoxLayout, QPushButton, QApplication, QLabel
from PySide6.QtCore import Qt, Signal, QSize, QThread, QObject, QTimer
from PySide6.QtGui import QDesktopServices, QIcon, QClipboard, QFont, QTextOption, QPixmap
from app.core.config import get_resource_path


def get_image_cache_dir():
    """获取图片缓存目录"""
    # 使用脚本所在目录而不是 cwd，避免中文路径问题
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_dir = os.path.join(base_dir, "cache", "images")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def get_cache_path_for_url(url):
    """根据 URL 生成缓存文件路径"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(get_image_cache_dir(), f"{url_hash}.png")


class ImageLoader(QObject):
    """异步加载图片的工作线程，支持本地缓存"""
    finished = Signal(QPixmap, str)  # pixmap, cache_path
    error = Signal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.cache_path = get_cache_path_for_url(url)
    
    def run(self):
        try:
            # 优先从本地缓存加载
            if os.path.exists(self.cache_path):
                pixmap = QPixmap(self.cache_path)
                if not pixmap.isNull():
                    self.finished.emit(pixmap, self.cache_path)
                    return
            
            # 缓存不存在，从网络下载
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            
            # 保存到缓存
            with open(self.cache_path, 'wb') as f:
                f.write(response.content)
            
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            self.finished.emit(pixmap, self.cache_path)
        except Exception as e:
            self.error.emit(str(e))


# Custom QTextBrowser that properly styles its context menu
class StyledTextBrowser(QTextBrowser):
    """QTextBrowser with styled context menu and select-and-ask feature.
    
    Qt's QTextBrowser creates context menus dynamically, and they don't
    inherit stylesheets from the parent widget. This class overrides
    contextMenuEvent to manually apply styling and add custom actions.
    """
    
    # Signals for custom actions
    ask_about_selection = Signal(str, str)  # (selected_text, action_type)
    
    MENU_STYLE = """
        QMenu {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 6px;
        }
        QMenu::item {
            color: #333333;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: #f0f0f0;
            color: #000000;
        }
        QMenu::item:disabled {
            color: #AAAAAA;
        }
        QMenu::separator {
            height: 1px;
            background-color: #E0E0E0;
            margin: 4px 8px;
        }
    """
    
    def contextMenuEvent(self, event):
        """Override to add custom actions and apply styling."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        selected_text = self.textCursor().selectedText().strip()
        
        # Create custom menu
        menu = QMenu(self)
        menu.setStyleSheet(self.MENU_STYLE)
        
        # Custom AI actions (only if text is selected)
        if selected_text:
            # Explain action
            explain_action = QAction("🔍 解释这段", menu)
            explain_action.triggered.connect(lambda: self.ask_about_selection.emit(selected_text, "explain"))
            menu.addAction(explain_action)
            
            # Translate action
            translate_action = QAction("🌐 翻译", menu)
            translate_action.triggered.connect(lambda: self.ask_about_selection.emit(selected_text, "translate"))
            menu.addAction(translate_action)
            
            # Ask follow-up action
            ask_action = QAction("💬 继续追问", menu)
            ask_action.triggered.connect(lambda: self.ask_about_selection.emit(selected_text, "ask"))
            menu.addAction(ask_action)
            
            menu.addSeparator()
        
        # Standard actions
        copy_action = QAction("📋 复制", menu)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(bool(selected_text))
        menu.addAction(copy_action)
        
        select_all_action = QAction("📄 全选", menu)
        select_all_action.triggered.connect(self.selectAll)
        menu.addAction(select_all_action)
        
        menu.exec(event.globalPos())
        menu.deleteLater()


class MessageBubble(QWidget):
    delete_requested = Signal(int, QWidget) # message_id, self
    play_requested = Signal(str) # text content
    ask_about_selection = Signal(str, str)  # (selected_text, action_type: "explain"/"translate"/"ask")

    def __init__(self, text, is_user=False, message_id=None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.text_content = text # Store original text
        self.message_id = message_id
        # Remove WA_TranslucentBackground to prevent ghosting artifacts
        # self.setAttribute(Qt.WA_TranslucentBackground) 
        self.setStyleSheet("background: transparent;")
        self._init_ui()

    def _init_ui(self):
        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(10, 5, 10, 5)
        
        # Bubble Frame
        bubble = QFrame()
        bubble.setProperty("class", "UserBubble" if self.is_user else "BotBubble")
        bubble.setStyleSheet(self._get_bubble_style())
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 10, 12, 6)  # Compact margins
        bubble_layout.setSpacing(2)  # Minimal spacing between text and toolbar
        self._bubble_layout = bubble_layout  # 保存引用供 set_image 使用
        
        # Text Browser for Markdown - use custom class for proper context menu styling
        self.text_view = StyledTextBrowser()
        self.text_view.setObjectName("BubbleText") # ID for styling
        self.text_view.setFrameShape(QFrame.NoFrame)
        self.text_view.setFrameShadow(QFrame.Plain)
        # Force removal of all borders, backgrounds, and margins
        self.text_view.setStyleSheet("""
            QTextBrowser#BubbleText {
                border: none;
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
        """)
        # Specific fix for "box-in-box": The viewport needs to be transparent too
        self.text_view.viewport().setAutoFillBackground(False)
        self.text_view.viewport().setStyleSheet("background: transparent;")
        
        self.text_view.setOpenExternalLinks(True)
        # Connect text selection signal
        self.text_view.ask_about_selection.connect(self.ask_about_selection)
        self.text_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Force word wrapping for all text including CJK
        self.text_view.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        # Remove internal document margins
        self.text_view.document().setDocumentMargin(0)
        
        self.text_view.document().contentsChanged.connect(self._adjust_height)
        
        # Add text_view with alignment based on message type
        if self.is_user:
            bubble_layout.addWidget(self.text_view, 0, Qt.AlignRight)
        else:
            bubble_layout.addWidget(self.text_view, 0, Qt.AlignLeft)
        
        # Tool Bar (Copy, Delete, Play)
        tool_layout = QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)  # No extra margins
        tool_layout.setSpacing(2)  # Tight button spacing
        tool_layout.addStretch()
        
        icon_color = "white" if self.is_user else "black"
        # Helper to find icon path
        icon_base = get_resource_path("icons")
        
        # Common Button Style
        btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0); /* Explicitly transparent white */
                border: none;
                border-radius: 6px;
                padding: 4px; 
            }
            QPushButton:hover {
                background-color: rgba(240, 240, 240, 255); /* Explicit light gray */
            }
            QPushButton:pressed {
                background-color: rgba(224, 224, 224, 255);
            }
        """

        # Play Button (using volume-2 icon for both user and bot messages)
        self.btn_play = QPushButton()
        self.btn_play.setIcon(QIcon(os.path.join(icon_base, "volume-2.svg")))
        self.btn_play.setFixedSize(28, 28)  # Refined size
        self.btn_play.setIconSize(QSize(16, 16))
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.setStyleSheet(btn_style)
        self.btn_play.clicked.connect(self.request_play)
        tool_layout.addWidget(self.btn_play)

        # Copy Button
        self.btn_copy = QPushButton()
        self.btn_copy.setIcon(QIcon(os.path.join(icon_base, "copy.svg")))
        self.btn_copy.setFixedSize(28, 28)  # Refined size
        self.btn_copy.setIconSize(QSize(16, 16))
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setStyleSheet(btn_style)
        self.btn_copy.clicked.connect(self.copy_text)
        tool_layout.addWidget(self.btn_copy)
        
        # Download Button (for images, hidden by default)
        self.btn_download = QPushButton()
        self.btn_download.setIcon(QIcon(os.path.join(icon_base, "save.svg")))
        self.btn_download.setFixedSize(28, 28)  # Refined size
        self.btn_download.setIconSize(QSize(16, 16))
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.setStyleSheet(btn_style)
        self.btn_download.clicked.connect(self._download_image)
        self.btn_download.hide()
        tool_layout.addWidget(self.btn_download)
        
        # Delete Button
        self.btn_delete = QPushButton()
        self.btn_delete.setIcon(QIcon(os.path.join(icon_base, "trash-2.svg")))
        self.btn_delete.setFixedSize(28, 28)  # Refined size
        self.btn_delete.setIconSize(QSize(16, 16))
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet(btn_style)
        self.btn_delete.clicked.connect(self.request_delete)
        tool_layout.addWidget(self.btn_delete)
        
        bubble_layout.addLayout(tool_layout)
        
        if self.is_user:
            row_layout.addStretch()
            row_layout.addWidget(bubble)
            bubble.setMaximumWidth(850)
        else:
            row_layout.addWidget(bubble)
            row_layout.addStretch()
            bubble.setMaximumWidth(1050)
        
        # Initial Render - 必须在所有按钮创建之后调用
        self.update_text(self.text_content)

    def copy_text(self):
        cb = QApplication.clipboard()
        cb.setText(self.text_content)
        # Optional: Show toast

    def request_play(self):
        self.play_requested.emit(self.text_content)

    def request_delete(self):
        self.delete_requested.emit(self.message_id, self)

    def set_playing_state(self, state):
        """Updates the play button icon based on state: 'generating', 'playing', 'paused', 'stopped'"""
        # Safety check: ensure the button widget still exists (C++ object not deleted)
        try:
            from shiboken6 import isValid
            if not isValid(self.btn_play):
                return
        except ImportError:
            # Fallback: check if attribute exists
            if not hasattr(self, 'btn_play') or self.btn_play is None:
                return
        
        icon_base = get_resource_path("icons")
        if state == "generating":
            self.btn_play.setIcon(QIcon(os.path.join(icon_base, "refresh-cw.svg")))
            self.btn_play.setEnabled(False)  # Disable during generation
        elif state == "playing":
            self.btn_play.setIcon(QIcon(os.path.join(icon_base, "pause.svg")))
            self.btn_play.setEnabled(True)
        elif state == "paused":
            self.btn_play.setIcon(QIcon(os.path.join(icon_base, "play.svg")))
            self.btn_play.setEnabled(True)
        else: # stopped
            self.btn_play.setIcon(QIcon(os.path.join(icon_base, "volume-2.svg")))
            self.btn_play.setEnabled(True)

    def set_image(self, url):
        """设置并显示图片"""
        self.image_url = url
        self.text_content = f"[IMAGE]{url}"
        
        # 隐藏文本视图
        self.text_view.hide()
        
        # 获取 bubble_layout - 通过保存的引用而不是 parent()
        bubble_layout = self._bubble_layout
        
        # 创建图片标签
        if not hasattr(self, 'image_label'):
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #f5f5f5;
                    border-radius: 8px;
                    padding: 5px;
                }
            """)
            # 插入到bubble_layout
            bubble_layout.insertWidget(0, self.image_label)
        
        # 先检查本地缓存，有缓存直接同步加载
        cache_path = get_cache_path_for_url(url)
        if os.path.exists(cache_path):
            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                self._on_image_loaded(pixmap, cache_path)
                return
        
        # 没有缓存，显示加载中并异步下载
        self.image_label.setText("🎨 加载图片中...")
        self.image_label.setFixedSize(500, 400)
        self.image_label.show()
        
        # 异步加载图片
        self._load_image_async(url)
    
    def _download_image(self):
        """下载图片到本地"""
        if not hasattr(self, 'image_url') or not self.image_url:
            return
        
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import datetime
        
        # 生成默认文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"generated_image_{timestamp}.png"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", default_name, "PNG图片 (*.png);;JPEG图片 (*.jpg);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                # 如果已经加载了图片，直接保存原始尺寸
                if hasattr(self, '_loaded_pixmap') and self._loaded_pixmap:
                    self._loaded_pixmap.save(file_path)
                else:
                    # 否则重新下载
                    response = requests.get(self.image_url, timeout=30)
                    response.raise_for_status()
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                
                # 手动创建 QMessageBox 实例以应用样式表
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("保存成功")
                msg_box.setText(f"图片已保存到:\n{file_path}")
                msg_box.setIcon(QMessageBox.Information)
                # 显式设置样式表，覆盖任何全局设置
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #FFFFFF;
                        color: #333333;
                    }
                    QLabel {
                        color: #333333;
                        background-color: transparent;
                    }
                    QPushButton {
                        background-color: #E66840;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 16px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #D45630;
                    }
                """)
                msg_box.exec()
            except Exception as e:
                # 手动创建 QMessageBox 实例以应用样式表
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("保存失败")
                msg_box.setText(f"无法保存图片:\n{str(e)}")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #FFFFFF;
                        color: #333333;
                    }
                    QLabel {
                        color: #333333;
                        background-color: transparent;
                    }
                    QPushButton {
                        background-color: #E66840;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 16px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #D45630;
                    }
                """)
                msg_box.exec()
    
    def _load_image_async(self, url):
        """异步加载图片"""
        # 先清理之前的线程
        self._cleanup_image_thread()
        
        self._image_thread = QThread()
        self._image_loader = ImageLoader(url)
        self._image_loader.moveToThread(self._image_thread)
        
        self._image_thread.started.connect(self._image_loader.run)
        self._image_loader.finished.connect(self._on_image_loaded)
        self._image_loader.error.connect(self._on_image_load_error)
        self._image_loader.finished.connect(self._cleanup_image_thread)
        self._image_loader.error.connect(self._cleanup_image_thread)
        
        self._image_thread.start()
    
    def _cleanup_image_thread(self):
        """清理图片加载线程"""
        if hasattr(self, '_image_thread') and self._image_thread is not None:
            if self._image_thread.isRunning():
                self._image_thread.quit()
                self._image_thread.wait(3000)  # 等待最多3秒
            self._image_thread.deleteLater()
            self._image_thread = None
        if hasattr(self, '_image_loader') and self._image_loader is not None:
            self._image_loader.deleteLater()
            self._image_loader = None
    
    def closeEvent(self, event):
        """窗口关闭时清理线程"""
        self._cleanup_image_thread()
        super().closeEvent(event)
    
    def __del__(self):
        """析构时确保线程被清理"""
        self._cleanup_image_thread()
    
    def _on_image_loaded(self, pixmap, cache_path):
        """图片加载完成"""
        if not pixmap.isNull():
            # 保存原始图片用于下载
            self._loaded_pixmap = pixmap
            self._cache_path = cache_path

            # 获取设备像素比（高DPI屏幕上可能是1.25, 1.5, 2.0等）
            device_pixel_ratio = self.image_label.devicePixelRatio()

            # 目标逻辑尺寸（屏幕上显示的大小）
            max_logical_width = 600
            max_logical_height = 600

            # 实际缩放尺寸需要乘以设备像素比，保证高DPI下清晰
            scale_width = int(max_logical_width * device_pixel_ratio)
            scale_height = int(max_logical_height * device_pixel_ratio)

            scaled = pixmap.scaled(scale_width, scale_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # 设置设备像素比，告诉Qt这是高DPI图片
            scaled.setDevicePixelRatio(device_pixel_ratio)

            self.image_label.setPixmap(scaled)
            # 逻辑尺寸 = 实际像素尺寸 / 设备像素比
            logical_width = int(scaled.width() / device_pixel_ratio)
            logical_height = int(scaled.height() / device_pixel_ratio)
            self.image_label.setFixedSize(logical_width, logical_height)

            # 显示工具栏的下载按钮
            self.btn_download.show()
        else:
            self.image_label.setText("❌ 图片加载失败")
    
    def _on_image_load_error(self, error):
        """图片加载失败"""
        self.image_label.setText(f"❌ 加载失败: {error[:50]}")

    def update_text(self, text):
        self.text_content = text.strip()
        
        # 检测是否是图片消息 [IMAGE]url 格式
        if self.text_content.startswith("[IMAGE]"):
            image_url = self.text_content[7:]  # 去掉 [IMAGE] 前缀
            self.set_image(image_url)
            return
        
        html = markdown.markdown(self.text_content, extensions=['fenced_code', 'tables', 'nl2br'])
        
        # Sync Font for accurate metrics - Use Microsoft YaHei (not UI) for better CJK rendering
        font = QFont("Microsoft YaHei")
        font.setPointSize(16)  # 16pt = ~21px, matches ChatGPT/Claude body text
        font.setHintingPreference(QFont.PreferFullHinting)  # Better text clarity
        self.text_view.setFont(font)
        
        # Determine styling based on bubble type
        text_color = "#1F2937"  # Darker for better contrast
        align_mode = 'right' if self.is_user else 'left'
        
        # CSS to reset margins and ensure tight fit with improved text rendering
        style = f"""
        <style>
            body {{ 
                margin: 0; 
                padding: 0; 
                font-family: 'Microsoft YaHei', 'PingFang SC', 'Segoe UI', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif; 
                font-size: 16pt; 
                color: {text_color}; 
                text-align: {align_mode}; 
                line-height: 1.6;
                -webkit-font-smoothing: antialiased;
            }}
            p {{ margin: 4px 0; padding: 0; }}
            code {{ background-color: rgba(255,255,255,0.2); padding: 2px 4px; border-radius: 4px; font-family: Consolas, monospace; }}
            pre {{ background-color: #f6f8fa; padding: 10px; border-radius: 5px; color: #24292e; white-space: pre-wrap; text-align: left; }}
            a {{ color: {text_color}; text-decoration: underline; }}
        </style>
        """
        # Bot bubble might need different code block styling (dark text on light bg)
        if not self.is_user:
             style += """
             <style>
                code { background-color: #f0f0f0; color: #d63384; }
             </style>
             """

        self.text_view.setHtml(style + html)
        
        # --- Apply Native Qt Text Alignment ---
        doc = self.text_view.document()
        text_option = QTextOption()
        if self.is_user:
            text_option.setAlignment(Qt.AlignRight)
        else:
            text_option.setAlignment(Qt.AlignLeft)
        doc.setDefaultTextOption(text_option)
        
        # Trigger layout update
        self._update_layout()

    def resizeEvent(self, event):
        self._update_layout()
        super().resizeEvent(event)

    def _adjust_height(self):
        """Adjust text view height when document content changes."""
        if not hasattr(self, 'text_view') or not self.text_view:
            return
        doc = self.text_view.document()
        doc_height = doc.size().height()
        new_height = int(doc_height + 5)
        if abs(self.text_view.height() - new_height) > 2:
            self.text_view.setFixedHeight(new_height)

    def _update_layout(self):
        """Recalculate bubble size based on available width."""
        if not hasattr(self, 'text_view') or not self.text_view:
            return

        # Constraints
        # Max bubble width (hard limit for aesthetic reasons on large screens)
        max_limit = 850 if self.is_user else 1050

        # Get available width from scroll area parent if possible
        available_width = self.width()

        # Try to get actual available width from parent scroll area
        parent = self.parent()
        while parent:
            if hasattr(parent, 'viewport'):
                # This is a scroll area
                available_width = parent.viewport().width()
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

        if available_width <= 0:
            # Fallback if not yet shown
            available_width = max_limit + 50

        # Margins & Padding
        # QHBoxLayout margins (10 left + 10 right) = 20
        # Bubble Frame layout margins (12 left + 12 right) = 24
        # Total horizontal padding = 44
        padding = 60  # Increased padding for safety

        # Calculate effective max width
        # Ensure we don't exceed the aesthetic max limit, BUT ALSO don't exceed available space
        target_max_width = min(max_limit, available_width - padding)
        target_max_width = max(100, target_max_width) # Minimum width safety

        doc = self.text_view.document()

        # 1. Set text width to target max to allow wrapping
        doc.setTextWidth(target_max_width)

        # 2. Get ideal width (shrink-wrap)
        ideal_width = doc.idealWidth()

        # 3. Determine final width
        # Use ideal width, but cap at target_max_width
        final_width = min(ideal_width + 10, target_max_width) # +10 buffer
        final_width = max(final_width, 110) # Min width for buttons

        # 4. Apply dimensions
        # We set FixedWidth on the text_view to force the bubble frame to shrink/grow
        self.text_view.setFixedWidth(int(final_width))
        doc.setTextWidth(final_width) # Ensure wrapping matches visual width

        # 5. Adjust Height
        doc_height = doc.size().height()
        new_height = int(doc_height + 5)
        if abs(self.text_view.height() - new_height) > 2:
            self.text_view.setFixedHeight(new_height)

    def _get_bubble_style(self):
        if self.is_user:
            return """
                QFrame {
                    background-color: transparent; /* User requested removal of background */
                    color: #333333;
                    border: none;
                    padding: 0px;
                }
            """
        else:
            return """
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #E0E0E0;
                    border-radius: 18px;
                    border-bottom-left-radius: 4px;
                }
            """
