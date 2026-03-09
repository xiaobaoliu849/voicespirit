from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QComboBox, QScrollArea, QFrame, QLabel,
    QProgressBar, QMenu, QSizePolicy, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThreadPool, QEvent
from PySide6.QtGui import QAction, QKeyEvent, QIcon, QFont, QDesktopServices, QColor, QTextCursor, QAbstractTextDocumentLayout
from app.core.api_client import ApiClient
from app.core.config import ConfigManager, get_resource_path
from app.core.database import DatabaseManager
from app.core.desktop_memory import DesktopMemoryManager
from app.core.translation import TranslationManager
import logging
from app.ui.styles.design_system import Colors
from app.ui.components.message_bubble import MessageBubble
from app.ui.components.voice_call_overlay import VoiceCallOverlay
from utils.tts_handler import TtsHandler, GEMINI_TTS_VOICES, QWEN_TTS_FLASH_VOICES

from app.ui.components.modern_chat_input import ModernChatInput


class LimitedHeightComboBox(QComboBox):
    """自定义ComboBox，限制下拉菜单高度"""
    MAX_POPUP_HEIGHT = 320
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxVisibleItems(10)
    
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


class ChatPage(QWidget):
    session_updated = Signal() # Emitted when session list needs refresh

    def __init__(self, tts_handler=None, translation_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.translation_manager = translation_manager or TranslationManager(self.config_manager)
        self.translation_manager.language_changed.connect(self.update_ui_text)
        
        self.db_manager = DatabaseManager()
        self.memory_manager = DesktopMemoryManager(self.config_manager, self.db_manager)
        self.thread_pool = QThreadPool()
        self.api_client = ApiClient(self.config_manager, self.thread_pool)
        self.tts_handler = tts_handler
        
        self.current_session_id = None
        self.current_playing_bubble = None
        self.is_paused = False
        
        if self.tts_handler:
            # Note: Removed playback_generating signal - user prefers no visible "generating" state
            self.tts_handler.playback_started.connect(self._on_playback_started)
            self.tts_handler.playback_finished.connect(self._on_playback_finished)
            self.tts_handler.playback_paused.connect(self._on_playback_paused)
            self.tts_handler.playback_resumed.connect(self._on_playback_resumed)
            # Error handling - reset UI on failure
            self.tts_handler.tts_error.connect(self._on_playback_error)
            if hasattr(self.tts_handler, 'player'):
                self.tts_handler.player.playback_error.connect(self._on_playback_error)
        
        self._init_ui()
        self._connect_signals()
        
        # Init state
        self.current_bot_text = ""
        self.current_bot_bubble = None
        
        # Trigger initial model load - 默认选择 DashScope（实时通话模型）
        if self.provider_combo.count() > 0:
            # 尝试找到 DashScope 并设置为默认
            dashscope_index = self.provider_combo.findText("DashScope")
            if dashscope_index >= 0:
                self.provider_combo.setCurrentIndex(dashscope_index)
            else:
                self.provider_combo.setCurrentIndex(0)
            self._on_provider_changed()
        
        # 尝试加载最近的会话，如果没有则创建新会话
        self._load_or_create_session()
        
    def _load_or_create_session(self):
        """启动时准备空白状态（不自动加载上次会话，与 ChatGPT/Claude 行为一致）
        
        用户可以从侧边栏历史记录中访问之前的会话
        """
        # 始终以空白状态启动，用户可从侧边栏访问历史会话
        self._prepare_blank_session()
    
    def _prepare_blank_session(self):
        """准备空白会话状态，但不创建数据库记录"""
        self.current_session_id = None
        self.clear_chat_ui()
    
    def create_new_session(self):
        """Starts a fresh session - 只在用户点击新建聊天时调用"""
        # 检查当前会话是否为空（没有消息），如果是则复用
        if self.current_session_id:
            messages = self.db_manager.get_messages(self.current_session_id)
            if not messages:
                # 当前会话是空的，直接复用，不创建新的
                self.clear_chat_ui()
                return
        
        self.current_session_id = self.db_manager.create_session("New Chat")
        self.clear_chat_ui()
        
    def clear_chat_ui(self):
        """Removes all bubbles."""
        while self.chat_layout.count() > 1: # Keep the stretch item
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load_session(self, session_id):
        """Loads a specific session from history."""
        self.current_session_id = session_id
        self.clear_chat_ui()
        
        messages = self.db_manager.get_messages(session_id)
        for msg_id, role, content in messages:
            self.add_message(content, is_user=(role == "user"), message_id=msg_id)

    def _init_ui(self):
        # Main Layout (Full Width)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Top Bar (Minimalist & Centered)
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: transparent; border-bottom: 1px solid #F3F4F6;")
        top_layout = QVBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 10, 0, 10) 
        top_layout.setSpacing(0)
        
        # Center the controls
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)
        
        # Provider
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumWidth(140)
        self.provider_combo.setFixedHeight(32) 
        self.provider_combo.addItems(self.api_client.get_available_providers())
        self.provider_combo.setPlaceholderText("Select Provider")
        
        # Model 
        self.model_combo = LimitedHeightComboBox()
        self.model_combo.setMinimumWidth(280)
        self.model_combo.setFixedHeight(32)
        self.model_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.model_combo.setPlaceholderText("Select Model")
        self.model_combo.setMaxVisibleItems(10)
        
        # Gemini Voice Selector (visible only for Google provider)
        self.voice_label = QLabel(self.translation_manager.t("chat_voice") if hasattr(self.translation_manager, 't') else "音色:")
        self.voice_label.setStyleSheet("color: #6B7280; font-weight: 500; font-size: 14px; font-family: 'Microsoft YaHei';")
        self.voice_label.hide()  # Hidden by default
        
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(180)
        self.voice_combo.setFixedHeight(32)
        self.voice_combo.setPlaceholderText("Select Voice")
        self.voice_combo.setEditable(True)
        self.voice_combo.setInsertPolicy(QComboBox.NoInsert)
        self._selected_gemini_voice = "Zephyr"  # Default
        self._selected_qwen_voice = "Cherry"  # Default Qwen voice
        
        for voice in GEMINI_TTS_VOICES:
            name = voice.get("Name", voice.get("ShortName", "Unknown"))
            gender = voice.get("Gender", "")
            short_name = voice.get("ShortName", "Zephyr")
            display_name = f"{name} ({gender})" if gender else f"{name}"
            self.voice_combo.addItem(display_name, short_name)
        
        self._populate_qwen_voices_grouped()
        
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        self.voice_combo.hide()  # Hidden by default
        
        # Minimalist Combo Style (Light Theme)
        combo_style = """
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB; /* Gray 200 */
                border-radius: 6px;
                padding: 0px 10px;
                color: #374151; /* Gray 700 */
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            QComboBox:hover {
                background-color: #F9FAFB; /* Gray 50 */
                border-color: #D1D5DB; /* Gray 300 */
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(CHEVRON_ICON_PATH);
                width: 10px;
                height: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                selection-background-color: #F3F4F6; /* Gray 100 */
                selection-color: #111827; /* Gray 900 */
                outline: none;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                height: 28px;
                padding: 4px 8px;
                border-radius: 4px;
                color: #374151;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #F3F4F6;
            }
        """
        chevron_icon = get_resource_path("icons/chevron-down.svg").replace("\\", "/")
        combo_style = combo_style.replace("CHEVRON_ICON_PATH", chevron_icon)
        self.provider_combo.setStyleSheet(combo_style)
        self.model_combo.setStyleSheet(combo_style)
        self.voice_combo.setStyleSheet(combo_style)
        
        # Labels (Subtle)
        self.provider_label = QLabel(self.translation_manager.t("chat_provider"))
        self.provider_label.setStyleSheet("color: #6B7280; font-weight: 500; font-size: 14px; font-family: 'Microsoft YaHei';")
        self.model_label = QLabel(self.translation_manager.t("chat_model"))
        self.model_label.setStyleSheet("color: #6B7280; font-weight: 500; font-size: 14px; font-family: 'Microsoft YaHei';")
        
        # Assembly
        # Left-aligned controls
        controls_layout.addWidget(self.provider_label)
        controls_layout.addWidget(self.provider_combo)
        controls_layout.addWidget(self.model_label)
        controls_layout.addWidget(self.model_combo)
        controls_layout.addWidget(self.voice_label)
        controls_layout.addWidget(self.voice_combo)
        controls_layout.addStretch() # Push everything to the left
        
        top_layout.addWidget(controls_container)
        main_layout.addWidget(top_bar)
        
        # 2. Central Content Area - Wide layout like Claude
        center_wrapper = QWidget()
        center_wrapper.setStyleSheet("background-color: #FFFFFF;") 
        
        # Use QHBoxLayout to center content with proper margins
        hbox = QHBoxLayout(center_wrapper)
        hbox.setContentsMargins(24, 0, 24, 0)  # Horizontal margins for elegance
        hbox.setSpacing(0)
        
        self.content_column = QWidget()
        # Set max width for readability but allow filling most of the space
        self.content_column.setMinimumWidth(400)
        self.content_column.setMaximumWidth(1600)  # Increased max width
        
        col_layout = QVBoxLayout(self.content_column)
        col_layout.setContentsMargins(0, 0, 0, 16)  # Less side margins, bottom for input
        col_layout.setSpacing(16)
        
        # -- Chat Area --
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Disable horizontal scroll
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #E5E7EB; border-radius: 3px; }
        """)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 16, 0, 16)
        self.chat_layout.addStretch() 
        
        self.scroll_area.setWidget(self.chat_container)
        col_layout.addWidget(self.scroll_area, 1) 
        
        # -- Input Card --
        self.input_card = ModernChatInput(translation_manager=self.translation_manager)
        col_layout.addWidget(self.input_card)
        
        # Center the content column
        hbox.addStretch(1)
        hbox.addWidget(self.content_column, 8)  # Content takes most space (weight 8)
        hbox.addStretch(1)
        
        main_layout.addWidget(center_wrapper)

    def update_ui_text(self, language):
        """Update UI text when language changes"""
        self.provider_label.setText(self.translation_manager.t("chat_provider"))
        self.model_label.setText(self.translation_manager.t("chat_model"))
        # Also update input card if it supports it
        if hasattr(self.input_card, 'update_ui_text'):
            self.input_card.update_ui_text(language)

    def _connect_signals(self):
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        
        # Modern Input Signals
        self.input_card.text_submitted.connect(self.send_message_text)
        self.input_card.voice_live_requested.connect(self.toggle_voice_call)
        self.input_card.voice_record_requested.connect(self.start_voice_recording)
        
        # Menu Actions
        self.input_card.request_add_image.connect(self.open_image_file_dialog)
        self.input_card.request_add_file.connect(self.open_general_file_dialog)
        self.input_card.request_generate_image.connect(self.start_image_generation_flow)
        
        # API Client Signals
        self.api_client.chat_stream_chunk.connect(self._on_bot_chunk)
        self.api_client.chat_stream_finished.connect(self._on_bot_finished)
        self.api_client.chat_response_error.connect(self._on_bot_error)
        self.api_client.models_updated.connect(self._on_models_updated)
        
        # Image Generation Signals
        self.api_client.image_generation_finished.connect(self._on_image_generated)
        self.api_client.image_generation_error.connect(self._on_image_error)
    
    def _is_image_model(self, model_name):
        """检查是否是图像生成模型"""
        image_models = ['flux-merged', 'flux-dev', 'flux-schnell', 'wanx', 'qwen-image-plus', 'qwen-image']
        return any(img_model in model_name.lower() for img_model in image_models)

    def show_history_menu(self):
        """Shows a popup menu with recent sessions."""
        menu = QMenu(self)
        sessions = self.db_manager.get_sessions(limit=10)
        
        if not sessions:
            menu.addAction("No recent history")
        else:
            for sess_id, title, _ in sessions:
                # Capture sess_id in closure
                action = menu.addAction(f"{title}")
                action.triggered.connect(lambda checked=False, sid=sess_id: self.load_session(sid))
                
        # menu.exec(self.history_btn.mapToGlobal(self.history_btn.rect().bottomLeft()))
        # NOTE: history_btn was removed? If so, this method might be dead code or need a new trigger.
        # For now, we leave it but comment out the exec if button is missing, or fix caller.
        pass

    def _on_provider_changed(self):
        provider = self.provider_combo.currentText()
        if provider:
            cached_models = self.api_client.get_models_for_provider(provider)
            self.model_combo.clear()
            if cached_models:
                self.model_combo.addItems(cached_models)
                self._set_default_model(provider)
            else:
                self.model_combo.addItem("Loading...")
                self.api_client.fetch_models_for_provider_async(provider)
            
            # Show/hide voice selector based on provider
            is_google = (provider == "Google")
            is_dashscope = (provider == "DashScope")
            self.voice_label.setVisible(is_google or is_dashscope)
            self.voice_combo.setVisible(is_google or is_dashscope)
            
            # Clear and populate voice combo based on provider
            self.voice_combo.clear()
            
            if is_dashscope:
                # Add DashScope voices
                for voice in QWEN_TTS_FLASH_VOICES:
                    name = voice.get("Name", voice.get("ShortName", "Unknown"))
                    short_name = voice.get("ShortName", "Cherry")
                    self.voice_combo.addItem(name, short_name)
                self._select_qwen_voice_in_combo()
            elif is_google:
                # Add Google voices
                for voice in GEMINI_TTS_VOICES:
                    name = voice.get("Name", voice.get("ShortName", "Unknown"))
                    gender = voice.get("Gender", "")
                    short_name = voice.get("ShortName", "Zephyr")
                    display_name = f"{name} ({gender})" if gender else name
                    self.voice_combo.addItem(display_name, short_name)
                self._select_gemini_voice_in_combo()
    
    def _select_gemini_voice_in_combo(self):
        """Select the current Gemini voice in the combo box."""
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i) == self._selected_gemini_voice:
                self.voice_combo.setCurrentIndex(i)
                return
    
    def _populate_qwen_voices_grouped(self):
        """Populate Qwen voices with grouped categories."""
        locale_names = {
            "zh-CN": "中文",
            "en-US": "English",
            "es-ES": "Español",
            "ru-RU": "Русский",
            "it-IT": "Italiano",
            "ko-KR": "한국어",
            "ja-JP": "日本語",
            "de-DE": "Deutsch",
            "fr-FR": "Français",
            "pt-BR": "Português",
        }
        
        voices_by_locale = {}
        for voice in QWEN_TTS_FLASH_VOICES:
            locale = voice.get("Locale", "zh-CN")
            if locale not in voices_by_locale:
                voices_by_locale[locale] = []
            voices_by_locale[locale].append(voice)
        
        for locale in ["zh-CN", "en-US", "es-ES", "ru-RU", "it-IT", "ko-KR", "ja-JP", "de-DE", "fr-FR", "pt-BR"]:
            if locale not in voices_by_locale:
                continue
                
            locale_name = locale_names.get(locale, locale)
            group_name = f"═══ {locale_name} ═══"
            self.voice_combo.addItem(group_name, "")
            self.voice_combo.model().item(self.voice_combo.count() - 1).setEnabled(False)
            
            for voice in voices_by_locale[locale]:
                display_name = voice.get("Name", voice.get("ShortName", "Unknown"))
                short_name = voice.get("ShortName", "")
                gender = voice.get("Gender", "")
                gender_mark = "♀" if gender == "Female" else "♂"
                final_name = f"{display_name} ({gender_mark})"
                self.voice_combo.addItem(final_name, short_name)
    
    def _select_qwen_voice_in_combo(self):
        """Select the current Qwen voice in the combo box."""
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i) == self._selected_qwen_voice:
                self.voice_combo.setCurrentIndex(i)
                return
    
    def _on_voice_changed(self, index):
        """Handle voice selection change for Google or DashScope."""
        voice_id = self.voice_combo.itemData(index)
        provider = self.provider_combo.currentText()
        
        if provider == "DashScope":
            self._selected_qwen_voice = voice_id
            logging.info(f"DashScope voice changed to: {self._selected_qwen_voice}")
        else:
            self._selected_gemini_voice = voice_id
            logging.info(f"Google voice changed to: {self._selected_gemini_voice}")

    def _on_models_updated(self, provider):
        if provider == self.provider_combo.currentText():
            self.model_combo.clear()
            self.model_combo.addItems(self.api_client.get_models_for_provider(provider))
            self._set_default_model(provider)

    def _set_default_model(self, provider):
        """Set the default model for the given provider from config."""
        try:
            # Try to get default from nested structure (new format)
            default_model = self.config_manager.get(f"default_models.{provider}.default")
            if not default_model:
                # Fallback to old format (direct string)
                default_model = self.config_manager.get(f"default_models.{provider}")
            
            if default_model and isinstance(default_model, str):
                # Find the model in the combo box
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemText(i) == default_model:
                        self.model_combo.setCurrentIndex(i)
                        return
                # If not found exactly, try case-insensitive match
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemText(i).lower() == default_model.lower():
                        self.model_combo.setCurrentIndex(i)
                        return
        except Exception as e:
            print(f"Error setting default model for {provider}: {e}")

    def send_message_text(self, text):
        if not text:
            return
            
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText()
        
        if not provider or not model:
            return
        
        # 如果当前没有会话，在发送第一条消息时创建
        if not self.current_session_id:
            self.current_session_id = self.db_manager.create_session(text[:30])
            self.session_updated.emit()
            
        # Save to DB & Add User Bubble
        msg_id = self.db_manager.add_message(self.current_session_id, "user", text)
        self.memory_manager.capture_chat_message(text=text, source="chat_text")
        
        # 检查是否需要更新标题（如果是 "New Chat" 则更新）
        sessions = self.db_manager.get_sessions(limit=20)
        for sess_id, title, _ in sessions:
            if sess_id == self.current_session_id and title == "New Chat":
                self.db_manager.update_session_title(self.current_session_id, text[:30])
                self.session_updated.emit()
                break
        
        self.add_message(text, is_user=True, message_id=msg_id)
        # Note: Input clearing is handled by the component itself now
        
        # Prepare for Bot Response
        self.current_bot_text = ""
        self.current_bot_bubble = None
        
        # 检查是否是图像生成模型
        if self._is_image_model(model):
            # 图像生成模式
            self.current_bot_bubble = self.add_message("🎨 正在生成图像...", is_user=False)
            self._pending_image_prompt = text
            self.api_client.start_image_generation_async(provider, text, model)
        else:
            # 普通聊天模式
            # Build conversation history (last 10 messages, excluding current)
            history = self._get_conversation_history(limit=10)
            # Send Request with history
            self.api_client.start_chat_request_async(provider, model, text, history=history)

    def add_message(self, text, is_user=False, message_id=None):
        bubble = MessageBubble(text, is_user, message_id=message_id)
        bubble.delete_requested.connect(self._on_message_delete)
        bubble.play_requested.connect(self._on_play_requested)
        bubble.ask_about_selection.connect(self._on_ask_about_selection)
        self.chat_layout.insertWidget(self.chat_layout.count()-1, bubble) # Insert before stretch
        # Auto scroll logic needed here usually
        QTimer.singleShot(10, self._scroll_to_bottom)
        return bubble

    def _on_play_requested(self, text):
        sender_bubble = self.sender()
        
        if self.current_playing_bubble == sender_bubble:
            # Toggle Pause/Resume
            if self.is_paused:
                self.tts_handler.resume_playback()
            else:
                self.tts_handler.pause_playback()
        else:
            # Play new - set pending bubble BEFORE calling play_audio
            # because playback_generating signal is emitted synchronously
            self._pending_bubble = sender_bubble
            self.tts_handler.play_audio(text)

    # Removed _on_playback_generating - user prefers no visible "generating" state,
    # clicking play button will silently generate in background and auto-play when ready

    def _on_playback_started(self):
        from shiboken6 import isValid
        # Stop previous if any (visual only, handler handles audio)
        if self.current_playing_bubble and self.current_playing_bubble != getattr(self, '_pending_bubble', None):
            if isValid(self.current_playing_bubble):
                self.current_playing_bubble.set_playing_state("stopped")
        
        self.current_playing_bubble = getattr(self, '_pending_bubble', None)
        self.is_paused = False
        if self.current_playing_bubble and isValid(self.current_playing_bubble):
            self.current_playing_bubble.set_playing_state("playing")

    def _on_playback_finished(self):
        if self.current_playing_bubble:
            # Safety check: ensure widget still exists (C++ object not deleted)
            try:
                from shiboken6 import isValid
                if isValid(self.current_playing_bubble):
                    self.current_playing_bubble.set_playing_state("stopped")
            except ImportError:
                self.current_playing_bubble.set_playing_state("stopped")
            self.current_playing_bubble = None
        self.is_paused = False

    def _on_playback_paused(self):
        from shiboken6 import isValid
        self.is_paused = True
        if self.current_playing_bubble and isValid(self.current_playing_bubble):
            self.current_playing_bubble.set_playing_state("paused")

    def _on_playback_resumed(self):
        from shiboken6 import isValid
        self.is_paused = False
        if self.current_playing_bubble and isValid(self.current_playing_bubble):
            self.current_playing_bubble.set_playing_state("playing")

    def _on_playback_error(self, error_msg):
        """Called when TTS generation or playback fails."""
        import logging
        logging.error(f"TTS/Playback error: {error_msg}")
        
        from shiboken6 import isValid
        # Reset pending bubble if it was in generating state
        pending = getattr(self, '_pending_bubble', None)
        if pending and isValid(pending):
            pending.set_playing_state("stopped")
            self._pending_bubble = None
        
        # Reset current playing bubble
        if self.current_playing_bubble and isValid(self.current_playing_bubble):
            self.current_playing_bubble.set_playing_state("stopped")
            self.current_playing_bubble = None
        
        self.is_paused = False

    def _on_message_delete(self, message_id, bubble_widget):
        if message_id:
             self.db_manager.delete_message(message_id)
        
        self.chat_layout.removeWidget(bubble_widget)
        bubble_widget.deleteLater()

    def start_image_generation_flow(self):
        # Insert a prefix for image generation or open a mode
        self.input_card.set_input_text("/image ")
        self.input_card.text_input.setFocus()
        
    def toggle_voice_mode(self):
        """Toggle voice call overlay visibility."""
        if hasattr(self, 'voice_overlay') and self.voice_overlay.isVisible():
            self.voice_overlay.close()
        else:
            self.open_voice_call()

    def toggle_voice_call(self):
        """Toggle voice call overlay visibility - open or close."""
        if hasattr(self, 'voice_overlay') and self.voice_overlay.is_active:
            # 如果通话正在进行，关闭它
            self.voice_overlay.close_overlay()
        else:
            # 否则打开通话
            self.open_voice_call()
    
    def open_voice_call(self):
        """Opens the Voice Call Overlay with current provider/model/voice."""
        current_provider = self.provider_combo.currentText()
        current_model = self.model_combo.currentText()
        
        if current_provider == "DashScope":
            current_voice = getattr(self, '_selected_qwen_voice', 'Cherry')
        else:
            current_voice = getattr(self, '_selected_gemini_voice', 'Zephyr')
        
        logging.info(f"Opening voice call: {current_provider} / {current_model} / voice: {current_voice}")
            
        if not hasattr(self, 'voice_overlay'):
            self.voice_overlay = VoiceCallOverlay(self.api_client, self)
            # Connect signals to display messages in chat
            self.voice_overlay.ai_response_text.connect(self._on_voice_ai_response)
            self.voice_overlay.ai_response_finished.connect(self._on_voice_ai_response_finished)
            self.voice_overlay.user_transcript.connect(self._on_voice_user_transcript)
            self.voice_overlay.tts_request.connect(self._on_voice_tts_request)
            # Provide history callback for multi-turn context
            self.voice_overlay.history_provider = self._get_conversation_history
        
        self.voice_overlay.start_call(provider=current_provider, model=current_model, voice=current_voice)
    
    def start_voice_recording(self):
        """Start voice recording for transcription and sending as text message."""
        from app.core.audio_recorder import AudioRecorder
        
        logging.info("Starting voice recording for transcription")
        
        # Create recorder if not exists
        if not hasattr(self, '_voice_recorder'):
            self._voice_recorder = AudioRecorder(self)
            self._voice_recorder.recording_stopped.connect(self._on_voice_recording_stopped)
            self._voice_recorder.recording_started.connect(self._on_voice_recording_started)
        
        # Update input card to show recording state
        self.input_card.set_recording_state(True)
        
        # Start recording
        self._voice_recorder.start_recording()
    
    def _on_voice_recording_started(self):
        """Called when voice recording starts."""
        logging.info("Voice recording started")
    
    def _on_voice_recording_stopped(self, file_path):
        """Called when voice recording stops - send audio directly or transcribe first."""
        logging.info(f"Voice recording stopped: {file_path}")
        
        # Reset input card state
        self.input_card.set_recording_state(False)
        
        if not file_path:
            logging.warning("No audio file recorded")
            return
        
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText()
        
        if not provider or not model:
            self.add_message("❌ 请先选择 Provider 和 Model", is_user=False)
            return
        
        # Check if current model supports audio input directly (omni/multimodal models)
        # Qwen3-Omni, Gemini (all versions), GPT-4o-audio, etc.
        model_lower = model.lower()
        
        # Check for various audio-capable model patterns
        is_omni_model = (
            'omni' in model_lower or           # Qwen3-Omni
            'audio' in model_lower or          # Audio models
            'realtime' in model_lower or       # Realtime models
            'live' in model_lower or           # Live models
            'gemini' in model_lower and 'pro' not in model_lower and 'ultra' not in model_lower or  # Gemini Flash/Aim (not Pro/Ultra)
            'flash' in model_lower or          # Flash models
            'sonnet' in model_lower            # Claude Sonnet
        )
        
        # Exclude explicit non-audio models
        if 'text' in model_lower:
            is_omni_model = False
        
        # Google provider: Gemini models (except Pro/Ultra) support audio
        if provider == "Google" and 'gemini' in model_lower:
            is_omni_model = True
        
        # DashScope realtime models
        if provider == "DashScope" and 'realtime' in model_lower:
            is_omni_model = True
        
        logging.info(f"Voice recording: provider={provider}, model={model}, is_omni={is_omni_model}")
        
        if is_omni_model:
            # 直接发送音频给多模态模型
            logging.info(f"Sending audio directly to {model} (omni/multimodal model)")
            self._send_audio_directly(provider, model, file_path)
        else:
            # 文本模型：尝试转录，如果失败则提示用户
            logging.info(f"Model {model} doesn't support audio directly, trying transcription")
            self._transcribe_and_send(provider, model, file_path)
    
    def _send_audio_directly(self, provider, model, file_path):
        """Send audio file directly to an omni/multimodal model."""
        # 显示用户语音消息占位符
        self.add_message("🎤 语音输入中...", is_user=True)
        self._scroll_to_bottom()
        
        def on_response(text):
            self._remove_last_message()
            if text:
                # 创建新会话（如果需要）
                if not self.current_session_id:
                    title_text = text.replace('\n', ' ').strip()[:30]
                    self.current_session_id = self.db_manager.create_session(title_text)
                    self.session_updated.emit()
                
                # 保存用户消息
                msg_id = self.db_manager.add_message(self.current_session_id, "user", "[语音输入]")
                self.add_message("[语音输入]", is_user=True, message_id=msg_id)
                
                # 添加 AI 回复
                self.current_bot_text = ""
                self.current_bot_bubble = self.add_message(text, is_user=False)
                self._scroll_to_bottom()
                
                # 保存到数据库
                msg_id = self.db_manager.add_message(self.current_session_id, "assistant", text)
                if self.current_bot_bubble:
                    self.current_bot_bubble.message_id = msg_id
            else:
                self.add_message("❌ 未收到回复", is_user=False)
        
        def on_error(error_msg):
            self._remove_last_message()
            self.add_message(f"❌ 错误: {error_msg}", is_user=False)
        
        # 直接发送音频到多模态模型（支持 audio_output 获得语音回复）
        # 注意：对于音频输入，需要提供一个默认的文本提示
        history = self._get_conversation_history(limit=10)
        
        # 对于音频输入，Gemini API 需要 contents，不能为空
        # 使用通用提示语，AI 会根据音频内容理解用户意图
        default_prompt = "请处理这段语音输入并回答我的问题"
        
        self.api_client.start_chat_request_async(
            provider, model, user_message=default_prompt,
            file_path=file_path, file_type='audio',
            audio_output=True, history=history
        )
        
        # Connect to signals for this request
        def on_chunk(chunk):
            if not self.current_bot_bubble:
                self._remove_last_message()
                self.current_bot_text = ""
                self.current_bot_bubble = self.add_message(chunk, is_user=False)
            else:
                self.current_bot_text += chunk
                self.current_bot_bubble.update_text(self.current_bot_text)
            self._scroll_to_bottom()
        
        def on_finished():
            # 保存到数据库
            if self.current_session_id and self.current_bot_text:
                msg_id = self.db_manager.add_message(self.current_session_id, "assistant", self.current_bot_text)
                if self.current_bot_bubble:
                    self.current_bot_bubble.message_id = msg_id
            self.current_bot_bubble = None
            self.current_bot_text = ""
        
        def on_api_error(error_msg):
            self._remove_last_message()
            self.add_message(f"❌ 错误: {error_msg}", is_user=False)
        
        # 连接信号（一次性使用）
        self.api_client.chat_stream_chunk.connect(on_chunk)
        self.api_client.chat_stream_finished.connect(on_finished)
        self.api_client.chat_response_error.connect(on_api_error)
    
    def _transcribe_and_send(self, provider, model, file_path):
        """Transcribe audio first, then send text to AI."""
        self.add_message("🎤 正在识别语音...", is_user=True)
        self._scroll_to_bottom()
        
        def on_transcription_finished(text):
            self._remove_last_message()
            if text and text.strip():
                # Create new session if needed
                if not self.current_session_id:
                    title_text = text.replace('\n', ' ').strip()[:30]
                    self.current_session_id = self.db_manager.create_session(title_text)
                    self.session_updated.emit()
                
                # Save and display the transcribed text
                msg_id = self.db_manager.add_message(self.current_session_id, "user", text)
                self.add_message(text, is_user=True, message_id=msg_id)
                self.memory_manager.capture_voice_transcript(
                    session_id=self.current_session_id,
                    text=text,
                    source="recording_transcription",
                    provider=provider,
                    model=model,
                )
                
                # Now send to AI for response
                self._send_transcribed_message(text)
            else:
                self.add_message("❌ 未能识别语音", is_user=False)
        
        def on_error(error_msg):
            self._remove_last_message()
            self.add_message(f"❌ 语音识别失败: {error_msg}", is_user=False)
        
        # Start transcription request
        self.api_client.start_transcription_request_async(file_path)
        
        # Connect signals
        self.api_client.transcription_finished.connect(on_transcription_finished)
        self.api_client.chat_response_error.connect(on_error)
    
    def _remove_last_message(self):
        """Remove the last message bubble (used to clean up placeholders)."""
        if self.chat_layout.count() > 1:
            item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
            if item and item.widget():
                item.widget().deleteLater()
    
    def _send_transcribed_message(self, text):
        """Send the transcribed text as a user message and get AI response."""
        if not text:
            return
        
        # Update UI for bot response
        self.current_bot_text = ""
        self.current_bot_bubble = None
        
        # Get conversation history
        history = self._get_conversation_history(limit=10)
        
        # Send to AI for response
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText()
        self.api_client.start_chat_request_async(provider, model, text, history=history)
    
    def _on_voice_user_transcript(self, text):
        """Handles user's speech transcript from live voice session."""
        if not text:
            return
        
        # Ensure session exists for saving - use first message as title (like ChatGPT/Claude)
        if not self.current_session_id:
            # Clean up the text for title: remove newlines, trim whitespace
            title_text = text.replace('\n', ' ').strip()[:30]
            self.current_session_id = self.db_manager.create_session(title_text)
            self.session_updated.emit()
        
        # Save user message to database
        msg_id = self.db_manager.add_message(self.current_session_id, "user", text)
        self.memory_manager.capture_voice_transcript(
            session_id=self.current_session_id,
            text=text,
            source="live_transcript",
            provider=self.provider_combo.currentText(),
            model=self.model_combo.currentText(),
        )
        
        # Add user message bubble with ID
        self.add_message(text, is_user=True, message_id=msg_id)
        self._scroll_to_bottom()
        
        # Reset bot bubble for next AI response
        self.current_bot_text = ""
        self.current_bot_bubble = None
    
    def _on_voice_ai_response(self, text):
        """Handles AI text responses from live voice session."""
        if not text:
            return
        
        self.current_bot_text += text
        
        if not self.current_bot_bubble:
            # Create bubble on first text chunk
            self.current_bot_bubble = self.add_message(self.current_bot_text, is_user=False)
            self._scroll_to_bottom()
        else:
            # Update existing bubble
            self.current_bot_bubble.update_text(self.current_bot_text)
            bar = self.scroll_area.verticalScrollBar()
            if bar.maximum() - bar.value() < 50:
                self._scroll_to_bottom()
    
    def _on_voice_ai_response_finished(self):
        """Called when AI finishes speaking in voice mode - save to database."""
        if self.current_session_id and self.current_bot_text:
            msg_id = self.db_manager.add_message(self.current_session_id, "assistant", self.current_bot_text)
            if self.current_bot_bubble:
                self.current_bot_bubble.message_id = msg_id

        self.current_bot_bubble = None
        self.current_bot_text = ""

    def _on_voice_tts_request(self, text, voice_name):
        """Handle TTS request from voice overlay - use Qwen3 TTS Flash."""
        if not text or not voice_name:
            return
        logging.info(f"Voice TTS request: voice={voice_name}, text={text[:50]}...")
        # Use TtsHandler to play with Qwen3 TTS Flash
        if hasattr(self, 'tts_handler') and self.tts_handler:
            # Set engine to Qwen Flash temporarily and play
            from utils.tts_handler import TTS_ENGINE_QWEN_FLASH
            old_engine = self.tts_handler.current_engine
            self.tts_handler.set_engine(TTS_ENGINE_QWEN_FLASH)
            self.tts_handler.play_audio(text, voice_name)
            # Note: We don't restore old engine here as user chose this voice

    def _scroll_to_bottom(self):
        """Scroll chat to bottom with a slight delay for UI updates."""
        def do_scroll():
            bar = self.scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())
        # Double scroll: immediate + delayed for layout completion
        do_scroll()
        QTimer.singleShot(50, do_scroll)

    def _on_bot_chunk(self, chunk):
        if not chunk: return
        
        self.current_bot_text += chunk
        
        if not self.current_bot_bubble:
            # Create bubble on first chunk
            self.current_bot_bubble = self.add_message(self.current_bot_text, is_user=False)
            self._scroll_to_bottom() # Always scroll on first chunk
        else:
            # Update text via method
            self.current_bot_bubble.update_text(self.current_bot_text)
            
            # Smart Auto-Scroll: Only scroll if user was at the bottom
            bar = self.scroll_area.verticalScrollBar()
            # Threshold: if within 50px of bottom, auto-scroll. Otherwise, let user read/scroll up.
            if bar.maximum() - bar.value() < 50:
                self._scroll_to_bottom()

    def _on_bot_finished(self):
        # Save Bot Message to DB
        if self.current_session_id and self.current_bot_text:
             msg_id = self.db_manager.add_message(self.current_session_id, "assistant", self.current_bot_text)
             if self.current_bot_bubble:
                 self.current_bot_bubble.message_id = msg_id # Set ID for delete

        self.current_bot_bubble = None
        self.current_bot_text = ""

    def _on_bot_error(self, error_msg):
        self.add_message(f"Error: {error_msg}", is_user=False)
    
    def _on_image_generated(self, urls):
        """处理图像生成完成"""
        if urls and self.current_bot_bubble:
            # 更新气泡显示图片
            self.current_bot_bubble.set_image(urls[0])
            self._scroll_to_bottom()
            
            # 保存到数据库
            if self.current_session_id:
                msg_id = self.db_manager.add_message(
                    self.current_session_id, "assistant", f"[IMAGE]{urls[0]}"
                )
                if self.current_bot_bubble:
                    self.current_bot_bubble.message_id = msg_id
        
        self.current_bot_bubble = None
    
    def _on_image_error(self, error_msg):
        """处理图像生成错误"""
        if self.current_bot_bubble:
            self.current_bot_bubble.update_text(f"❌ 图像生成失败: {error_msg}")
        else:
            self.add_message(f"❌ 图像生成失败: {error_msg}", is_user=False)
        self.current_bot_bubble = None
        
    # --- Menu Action Handlers ---
    def open_image_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            # For now, just append [Image: path] to input, or handle more gracefully
            # Ideally, show a chip or preview in the input box
            current_text = self.input_card.text_input.toPlainText()
            new_text = f"{current_text}\n[Image: {file_path}]" if current_text else f"[Image: {file_path}]"
            self.input_card.set_input_text(new_text)

    def open_general_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "All Files (*.*)"
        )
        if file_path:
            # Append [File: path] to input
            current_text = self.input_card.text_input.toPlainText()
            new_text = f"{current_text}\n[File: {file_path}]" if current_text else f"[File: {file_path}]"
            self.input_card.set_input_text(new_text)

    def start_image_generation_flow(self):
        # Insert a prefix for image generation or open a mode
        self.input_card.set_input_text("/image ")
        self.input_card.text_input.setFocus()

    def _get_conversation_history(self, limit=10):
        """Get last N messages from current session for multi-turn context.
        
        Returns:
            List of dicts with 'role' and 'content' keys, excluding current message
        """
        if not self.current_session_id:
            return []
        
        try:
            # Get messages from database
            messages = self.db_manager.get_messages(self.current_session_id)
            
            # Convert to API format and limit to last N
            # Each message is (id, role, content)
            history = []
            for msg in messages[-limit:]:
                role = msg[1]  # 'user' or 'assistant'
                content = msg[2]
                # Skip placeholder voice inputs
                if content and not content.startswith("[🎤"):
                    history.append({"role": role, "content": content})
            
            return history
        except Exception as e:
            logging.error(f"Error getting conversation history: {e}")
            return []

    def _on_ask_about_selection(self, selected_text, action_type):
        """Handle ask-about-selection actions from message bubbles.
        
        Args:
            selected_text: The text the user selected
            action_type: "explain", "translate", or "ask"
        """
        if not selected_text:
            return
        
        # Truncate very long selections
        if len(selected_text) > 500:
            selected_text = selected_text[:500] + "..."
        
        if action_type == "explain":
            # Auto-send explanation request with text-compatible model
            prompt = f'请详细解释以下内容：\n\n"{selected_text}"'
            self._send_with_text_model(prompt)
            
        elif action_type == "translate":
            # Auto-send translation request with text-compatible model
            prompt = f'请翻译以下内容：\n\n"{selected_text}"'
            self._send_with_text_model(prompt)
            
        elif action_type == "ask":
            # Pre-fill input for user to complete
            context = f'关于 "{selected_text[:50]}{"..." if len(selected_text) > 50 else ""}"：'
            self.input_card.set_input_text(context)
            self.input_card.text_input.setFocus()
            # Move cursor to end
            cursor = self.input_card.text_input.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.input_card.text_input.setTextCursor(cursor)
    
    def _send_with_text_model(self, prompt):
        """发送消息时自动选择文本兼容的模型，避免使用语音专用模型。
        
        当用户使用语音模型（如 gemini-native-audio-preview）时，
        右键解释/翻译需要使用文本模型才能工作。
        """
        current_provider = self.provider_combo.currentText()
        current_model = self.model_combo.currentText()
        
        # 检查当前模型是否是语音/音频专用模型
        audio_keywords = ['audio', 'voice', 'native-audio', 'realtime', 'tts']
        is_audio_model = any(kw in current_model.lower() for kw in audio_keywords)
        
        if is_audio_model:
            # 需要使用文本兼容模型
            text_model = self._find_text_compatible_model(current_provider)
            
            if text_model:
                logging.info(f"解释/翻译: 切换模型 {current_model} -> {text_model}")
                # 使用文本模型发送，但不改变UI选择
                self._send_internal_request(current_provider, text_model, prompt)
            else:
                # 找不到合适的文本模型，尝试 DeepSeek 等其他 provider
                fallback_result = self._find_fallback_text_model()
                if fallback_result:
                    fb_provider, fb_model = fallback_result
                    logging.info(f"解释/翻译: 使用备用模型 {fb_provider}/{fb_model}")
                    self._send_internal_request(fb_provider, fb_model, prompt)
                else:
                    # 实在找不到，用原模型尝试（会报错但至少给用户反馈）
                    self.send_message_text(prompt)
        else:
            # 当前模型支持文本生成，直接使用
            self.send_message_text(prompt)
    
    def _find_text_compatible_model(self, provider):
        """为指定 provider 查找文本兼容的模型。"""
        audio_keywords = ['audio', 'voice', 'native-audio', 'realtime', 'tts']
        
        # 从缓存的模型列表中查找
        models = self.api_client.get_models_for_provider(provider)
        
        # 如果是 Google，优先尝试指定的优质文本模型
        if provider == "Google":
            preferred_text_models = [
                "gemini-3-flash-preview",
                "models/gemini-flash-latest",
                "gemini-2.0-flash"
            ]
            for model in preferred_text_models:
                if models and model in models:
                    return model
        
        # 通用查找：返回第一个非音频模型
        if models:
            for model in models:
                if not any(kw in model.lower() for kw in audio_keywords):
                    return model
        
        return None
    
    def _find_fallback_text_model(self):
        """查找备用的文本模型（跨 provider）。
        
        Returns:
            (provider, model) tuple 或 None
        """
        # 优先使用 DeepSeek，性价比高
        preferred_providers = ["DeepSeek", "DashScope", "OpenAI", "Groq", "SiliconFlow"]
        audio_keywords = ['audio', 'voice', 'native-audio', 'realtime', 'tts']
        
        for provider in preferred_providers:
            # 从配置中获取默认模型
            default_model = self.config_manager.get(f"default_models.{provider}.default", "")
            if default_model and not any(kw in default_model.lower() for kw in audio_keywords):
                return (provider, default_model)
            
            # 从缓存模型中查找
            models = self.api_client.get_models_for_provider(provider)
            if models:
                for model in models:
                    if not any(kw in model.lower() for kw in audio_keywords):
                        return (provider, model)
        
        return None
    
    def _send_internal_request(self, provider, model, prompt):
        """内部发送请求方法，不添加到用户历史但显示在UI中。"""
        # 确保有会话
        if not self.current_session_id:
            self.current_session_id = self.db_manager.create_session(prompt[:30])
            self.session_updated.emit()
        
        # 保存用户消息
        msg_id = self.db_manager.add_message(self.current_session_id, "user", prompt)
        self.add_message(prompt, is_user=True, message_id=msg_id)
        
        # 准备接收响应
        self.current_bot_text = ""
        self.current_bot_bubble = None
        
        # 获取历史并发送请求
        history = self._get_conversation_history(limit=10)
        self.api_client.start_chat_request_async(provider, model, prompt, history=history)
