from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QComboBox, QLabel, QFrame, QSplitter, QGraphicsDropShadowEffect,
    QProgressBar, QMessageBox, QSizePolicy, QToolButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QClipboard, QAction, QGuiApplication
from app.ui.styles.design_system import Colors

from app.core.config import ConfigManager, get_resource_path
from app.core.api_client import ApiClient

class ModernTextEdit(QTextEdit):
    def __init__(self, placeholder="", read_only=False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setReadOnly(read_only)
        self.setAcceptRichText(False)
        self.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: transparent;
                color: #2D2D2D;
                padding: 12px;
                font-family: 'Microsoft YaHei', 'Segoe UI', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif;
                font-size: 12pt;
                selection-background-color: #F0E0D8;
                selection-color: #2D2D2D;
            }
        """)

class ComboStyle(QComboBox):
    MAX_POPUP_HEIGHT = 300
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxVisibleItems(10)
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 3px 8px;
                background-color: #FFFFFF;
                color: #4A4A4A;
                font-family: "Segoe UI";
                font-size: 12px;
                min-width: 80px;
                height: 24px;
            }
            QComboBox:hover {
                border: 1px solid {Colors.PRIMARY};
                background-color: #FAF9F6;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #666666;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                selection-background-color: #F5F2EB;
                selection-color: {Colors.PRIMARY};
                outline: none;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                height: 28px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #F5F2EB;
            }
            /* Elegant Scrollbar */
            QComboBox QAbstractItemView QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 8px;
                margin: 0px; 
                border-radius: 4px;
            }
            QComboBox QAbstractItemView QScrollBar::handle:vertical {
                background: #C0C0C0;
                min-height: 30px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
                background: {Colors.PRIMARY};
            }
            QComboBox QAbstractItemView QScrollBar::add-line:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
        """)
    
    def showPopup(self):
        super().showPopup()
        # 获取弹出窗口
        popup = self.view().window()
        if popup and popup != self.window():
            current_height = popup.height()
            if current_height > self.MAX_POPUP_HEIGHT:
                # 计算ComboBox在屏幕上的位置
                global_pos = self.mapToGlobal(self.rect().bottomLeft())
                # 设置弹出窗口位置和大小
                popup.setGeometry(
                    global_pos.x(), 
                    global_pos.y(),
                    popup.width(), 
                    self.MAX_POPUP_HEIGHT
                )

class TranslatePage(QWidget):
    def __init__(self, tts_handler=None, translation_manager=None, parent=None):
        super().__init__(parent)
        self.tts_handler = tts_handler
        self.translation_manager = translation_manager
        
        # Core Services
        self.config_manager = ConfigManager()
        from PySide6.QtCore import QThreadPool
        self.thread_pool = QThreadPool.globalInstance()
        self.api_client = ApiClient(self.config_manager, self.thread_pool)
        
        # Connect Signals
        self.api_client.translation_finished.connect(self._on_translation_finished)
        self.api_client.translation_error.connect(self._on_translation_error)
        self.api_client.models_updated.connect(self._refresh_model_list)
        
        # UI Setup
        self.setStyleSheet("background-color: #F5F2EB;") 
        self._init_ui()
        
        # Initial Data
        QTimer.singleShot(100, self._load_initial_data)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        
        # --- Ultra Compact Toolbar ---
        toolbar_frame = QFrame()
        toolbar_frame.setFixedHeight(48)
        toolbar_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #E6E6E6;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(8, 0, 8, 0)
        toolbar_layout.setSpacing(8)
        
        # Provider & Model
        self.provider_combo = ComboStyle()
        self.provider_combo.setPlaceholderText("Provider")
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        
        self.model_combo = ComboStyle()
        self.model_combo.setPlaceholderText("Model")
        self.model_combo.setMinimumWidth(200) # Increased width for better visibility
        self.model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) # Allow expanding
        self.model_combo.setMaxVisibleItems(10) # Limit dropdown height
        self.model_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        toolbar_layout.addWidget(self.provider_combo)
        toolbar_layout.addWidget(self.model_combo, 1) # Add stretch factor to model combo
        
        # Vertical Separator
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0; max-width: 1px; margin: 8px 0;")
        toolbar_layout.addWidget(line)
        
        # Languages
        self.source_lang = ComboStyle()
        self.source_lang.addItems(["Auto Detect", "English", "Chinese", "Japanese", "Korean", "French", "German", "Spanish", "Russian"])
        self.source_lang.setCurrentText("Auto Detect")
        
        swap_btn = QPushButton("⇄")
        swap_btn.setFixedSize(24, 24)
        swap_btn.setCursor(Qt.PointingHandCursor)
        swap_btn.clicked.connect(self._swap_languages)
        swap_btn.setStyleSheet(f"""
            QPushButton {{ border: none; font-size: 16px; color: #888; border-radius: 4px; }}
            QPushButton:hover {{ background-color: #F0F0F0; color: {Colors.PRIMARY}; }}
        """)
        
        self.target_lang = ComboStyle()
        self.target_lang.addItems(["English", "Chinese", "Japanese", "Korean", "French", "German", "Spanish", "Russian"])
        self.target_lang.setCurrentText("English")
        
        toolbar_layout.addWidget(self.source_lang)
        toolbar_layout.addWidget(swap_btn)
        toolbar_layout.addWidget(self.target_lang)
        
        toolbar_layout.addStretch()
        
        # Translate Button (Compact)
        self.translate_btn = QPushButton("Translate")
        self.translate_btn.setCursor(Qt.PointingHandCursor)
        self.translate_btn.setFixedSize(80, 28)
        self.translate_btn.clicked.connect(self.start_translation)
        self.translate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: 600;
                font-family: "Segoe UI";
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {Colors.PRIMARY_ACTIVE}; }}
            QPushButton:disabled {{ background-color: #E0E0E0; color: #999; }}
        """)
        toolbar_layout.addWidget(self.translate_btn)
        
        main_layout.addWidget(toolbar_frame)
        
        # --- Main Splitter Content (Maximized) ---
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #E0E0E0; }")
        
        # Left Panel (Source)
        left_panel = self._create_text_panel(is_source=True)
        self.splitter.addWidget(left_panel)
        
        # Right Panel (Target)
        right_panel = self._create_text_panel(is_source=False)
        self.splitter.addWidget(right_panel)
        
        self.splitter.setSizes([600, 600])
        main_layout.addWidget(self.splitter)
        
        # Progress Bar (Thin)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ border: none; background: transparent; }}
            QProgressBar::chunk {{ background-color: {Colors.PRIMARY}; }}
        """)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

    def _create_text_panel(self, is_source):
        panel = QFrame()
        panel.setStyleSheet("background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E6E6E6;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Text Area
        placeholder = "Enter text..." if is_source else "Translation..."
        text_edit = ModernTextEdit(placeholder, read_only=not is_source)
        layout.addWidget(text_edit)
        
        if is_source:
            self.source_text = text_edit
        else:
            self.target_text = text_edit
            text_edit.setStyleSheet(text_edit.styleSheet() + "background-color: #FCFCFC;")
            
        # Bottom Actions Bar
        actions_bar = QFrame()
        actions_bar.setFixedHeight(36) 
        actions_bar.setStyleSheet("background-color: transparent; border-top: 1px solid #F0F0F0;")
        actions_layout = QHBoxLayout(actions_bar)
        actions_layout.setContentsMargins(8, 0, 8, 0)
        actions_layout.setSpacing(4)
        
        # Play Button
        play_btn = self._create_icon_button("Play", lambda: self._play_audio(is_source))
        play_btn.setIcon(QIcon(get_resource_path("icons/play.svg"))) 
        actions_layout.addWidget(play_btn)
        
        actions_layout.addStretch()
        
        # Action Buttons
        if is_source:
            paste_btn = self._create_icon_button("Paste", self._paste_text)
            clear_btn = self._create_icon_button("Clear", self.source_text.clear)
            actions_layout.addWidget(paste_btn)
            actions_layout.addWidget(clear_btn)
        else:
            copy_btn = self._create_icon_button("Copy", self._copy_result)
            actions_layout.addWidget(copy_btn)
            
        layout.addWidget(actions_bar)
        
        return panel

    def _create_icon_button(self, text, slot):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(slot)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888;
                border: none;
                font-size: 11px;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #F0F0F0; color: #555; }
        """)
        return btn
        
    def _play_audio(self, is_source):
        text = self.source_text.toPlainText() if is_source else self.target_text.toPlainText()
        if text and self.tts_handler:
            self.tts_handler.play_audio(text)

    # --- Logic Methods ---
    def _load_initial_data(self):
        providers = self.api_client.get_available_providers()
        self.provider_combo.clear()
        if providers:
            self.provider_combo.addItems(providers)
            
            # Select current provider from config if available, else first one
            current_provider = self.config_manager.get("current_provider")
            if current_provider and current_provider in providers:
                self.provider_combo.setCurrentText(current_provider)
                self._on_provider_changed(current_provider)
            else:
                self.provider_combo.setCurrentIndex(0)
                self._on_provider_changed(providers[0])
        else:
            self.provider_combo.addItem("No Providers")
            self.translate_btn.setEnabled(False)

    def _on_provider_changed(self, provider_name):
        # Save current provider selection
        self.config_manager.update_setting("current_provider", provider_name)
        
        self.model_combo.clear()
        models = self.api_client.get_models_for_provider(provider_name)
        if models:
            self.model_combo.addItems(models)
            self.translate_btn.setEnabled(True)
            
            # Try to select default model
            default_model = self._get_default_model_for_provider(provider_name)
            if default_model and default_model in models:
                self.model_combo.setCurrentText(default_model)
            elif len(models) > 0:
                self.model_combo.setCurrentIndex(0)
        else:
            self.model_combo.addItem("Fetching...")
            self.api_client.fetch_models_for_provider_async(provider_name)
            
    def _refresh_model_list(self, provider_name):
        if self.provider_combo.currentText() == provider_name:
            self.model_combo.clear()
            models = self.api_client.get_models_for_provider(provider_name)
            if models:
                self.model_combo.addItems(models)
                
                # Try to select default model again after refresh
                default_model = self._get_default_model_for_provider(provider_name)
                if default_model and default_model in models:
                    self.model_combo.setCurrentText(default_model)
                elif len(models) > 0:
                    self.model_combo.setCurrentIndex(0)
            else:
                self.model_combo.addItem("No models found")

    def _get_default_model_for_provider(self, provider_name):
        """Retrieves the default model string for a given provider from config."""
        defaults = self.config_manager.get("default_models")
        if not defaults or provider_name not in defaults:
            return None
            
        entry = defaults[provider_name]
        if isinstance(entry, dict):
            return entry.get("default")
        elif isinstance(entry, str):
            return entry
        return None

    def _swap_languages(self):
        source = self.source_lang.currentText()
        target = self.target_lang.currentText()
        if source == "Auto Detect": return
        self.source_lang.setCurrentText(target)
        self.target_lang.setCurrentText(source)
        
        src_text = self.source_text.toPlainText()
        tgt_text = self.target_text.toPlainText()
        if tgt_text:
            self.source_text.setPlainText(tgt_text)
            self.target_text.setPlainText(src_text)

    def _paste_text(self):
        self.source_text.insertPlainText(QGuiApplication.clipboard().text())

    def _copy_result(self):
        text = self.target_text.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.translate_btn.setText("Copied!")
            QTimer.singleShot(2000, lambda: self.translate_btn.setText("Translate"))

    def start_translation(self):
        text = self.source_text.toPlainText().strip()
        if not text: return
            
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText()
        source_lang = self.source_lang.currentText()
        target_lang = self.target_lang.currentText()
        
        if not provider or not model:
            # 手动创建 QMessageBox 实例以应用样式表
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Please select a provider and model.")
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
            return

        self.translate_btn.setEnabled(False)
        self.translate_btn.setText("Translating...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.target_text.setPlaceholderText("Thinking...")
        self.target_text.clear()
        
        self.api_client.start_translation_request_async(
            provider=provider,
            model=model,
            text=text,
            source_lang_api=source_lang,
            target_lang_api=target_lang
        )

    def _on_translation_finished(self, translated_text):
        self.target_text.setPlainText(translated_text)
        self._reset_ui_state()

    def _on_translation_error(self, error_message):
        self.target_text.setPlainText(f"Error: {error_message}")
        self._reset_ui_state()
        
    def _reset_ui_state(self):
        self.translate_btn.setEnabled(True)
        self.translate_btn.setText("Translate")
        self.progress_bar.hide()
