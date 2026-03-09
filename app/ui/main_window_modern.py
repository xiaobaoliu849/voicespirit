import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QLabel
from PySide6.QtCore import Qt
from app.ui.components.sidebar import Sidebar
from app.ui.pages.chat_page import ChatPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.translate_page import TranslatePage
from app.ui.pages.tts_page import TtsPage
from app.ui.pages.audio_overview_page import AudioOverviewPage
from utils.tts_handler import TtsHandler
from app.core.config import ConfigManager
from app.core.translation import TranslationManager
from app.core.hotkey_manager import GlobalHotkeyManager

class ModernMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Spirit 2.0")
        # Increased default size because we are now DPI Aware (no OS scaling)
        self.resize(1050, 700)
        
        # Set window icon
        from PySide6.QtGui import QIcon
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logo.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Initialize Core Services
        self.config_manager = ConfigManager()
        self.translation_manager = TranslationManager(self.config_manager)
        self.tts_handler = TtsHandler()
        
        # Power User Features (Rigor inspired)
        self.hotkey_manager = GlobalHotkeyManager(self)
        self.hotkey_manager.hotkey_triggered.connect(self._on_hotkey_triggered)
        self._register_global_hotkeys()
        
        # Connect to language change to update window title
        self.translation_manager.language_changed.connect(self.update_ui_text)
        
        # Central Container
        container = QWidget()
        self.setCentralWidget(container)
        
        # Main Horizontal Layout
        self.main_layout = QHBoxLayout(container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. Sidebar
        self.sidebar = Sidebar(translation_manager=self.translation_manager)
        self.sidebar.page_changed.connect(self.switch_page)
        # Connect new sidebar signals
        self.sidebar.new_chat_clicked.connect(self._on_new_chat_clicked)
        self.sidebar.session_selected.connect(self._on_session_selected)
        self.sidebar.session_deleted.connect(self._on_session_deleted)
        self.main_layout.addWidget(self.sidebar)
        
        # 2. Page Container (Stacked)
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # -- Initialize Pages --
        self._init_pages()

        # Connect ChatPage back to Sidebar to refresh history on new chat
        self.chat_page.session_updated.connect(self.sidebar.refresh_history)
        
    def _on_new_chat_clicked(self):
        self.stacked_widget.setCurrentIndex(0) # Switch to Chat
        self.chat_page.create_new_session()
        self.sidebar.refresh_history()

    def _on_session_selected(self, session_id):
        self.stacked_widget.setCurrentIndex(0) # Switch to Chat
        self.chat_page.load_session(session_id)

    def _on_session_deleted(self, session_id):
        if self.chat_page.current_session_id == session_id:
            # 删除当前会话后，准备空白状态而不是创建新会话
            self.chat_page._prepare_blank_session()
        
    def _init_pages(self):
        # Index 0: Chat Page
        self.chat_page = ChatPage(tts_handler=self.tts_handler, translation_manager=self.translation_manager)
        self.stacked_widget.addWidget(self.chat_page)
        
        # Index 1: Translate Page
        self.translate_page = TranslatePage(tts_handler=self.tts_handler, translation_manager=self.translation_manager)
        self.stacked_widget.addWidget(self.translate_page)
        
        # Index 2: TTS Page
        # Create separate ApiClient for TTS Page (Voice Design/Clone)
        from app.core.api_client import ApiClient
        from PySide6.QtCore import QThreadPool
        self.tts_api_client = ApiClient(self.config_manager, QThreadPool.globalInstance())
        
        self.tts_page = TtsPage(
            tts_handler=self.tts_handler,
            translation_manager=self.translation_manager,
            api_client=self.tts_api_client
        )
        self.stacked_widget.addWidget(self.tts_page)

        # Index 3: Audio Overview Page - 使用独立的 ApiClient 避免信号冲突
        from app.core.api_client import ApiClient
        from PySide6.QtCore import QThreadPool
        self.audio_overview_api_client = ApiClient(self.config_manager, QThreadPool.globalInstance())
        
        self.audio_overview_page = AudioOverviewPage(
            api_client=self.audio_overview_api_client,  # 独立的 api_client
            tts_handler=self.tts_handler,
            config_manager=self.config_manager,
            translation_manager=self.translation_manager
        )
        self.stacked_widget.addWidget(self.audio_overview_page)

        # Index 4: Settings
        self.settings_page = SettingsPage(translation_manager=self.translation_manager)
        self.stacked_widget.addWidget(self.settings_page)
        
        # Connect settings_saved to reinitialize API clients
        self.settings_page.settings_saved.connect(self._on_settings_saved)

    def switch_page(self, index):
        """Switches the active page in the stacked widget."""
        if index < self.stacked_widget.count():
            self.stacked_widget.setCurrentIndex(index)

    def update_ui_text(self, language):
        """Update main window UI text"""
        self.setWindowTitle(self.translation_manager.t("app_title"))
    
    def _on_settings_saved(self):
        """Reinitialize API clients after settings are saved."""
        try:
            # Reload config for all config_manager instances
            self.config_manager._load_config()
            
            # Reinitialize API clients in chat page
            if hasattr(self.chat_page, 'api_client'):
                # Also reload the api_client's config_manager
                self.chat_page.api_client.config_manager._load_config()
                self.chat_page.api_client._initialize_clients()
                # Refresh provider combo
                self.chat_page.provider_combo.clear()
                providers = self.chat_page.api_client.get_available_providers()
                self.chat_page.provider_combo.addItems(providers)
                # Select first provider if available
                if providers:
                    self.chat_page.provider_combo.setCurrentIndex(0)
                    self.chat_page._on_provider_changed()
            
            # Reinitialize API clients in audio overview page
            if hasattr(self, 'audio_overview_api_client'):
                self.audio_overview_api_client.config_manager._load_config()
                self.audio_overview_api_client._initialize_clients()

            # Reinitialize API clients in TTS page (Voice Design/Clone)
            if hasattr(self, 'tts_api_client'):
                self.tts_api_client.config_manager._load_config()
                self.tts_api_client._initialize_clients()
                
        except Exception as e:
            logging.error(f"Error reinitializing API clients: {e}")
            
        # Always re-register hotkeys when settings are saved
        self._register_global_hotkeys()

    def _register_global_hotkeys(self):
        """Register global hotkeys from config"""
        # Get window handle
        hwnd = int(self.winId())
        
        self.hotkey_manager.unregister_all(hwnd)
        
        wake_shortcut = self.config_manager.get("shortcuts.wake_app", "Alt+Shift+S")
        if wake_shortcut:
            self.hotkey_manager.register_hotkey("toggle_window", wake_shortcut, hwnd)

        # Add Start/Stop Recording hotkey (toggle_recording)
        # Default: Alt+Shift+R
        recording_shortcut = self.config_manager.get("shortcuts.toggle_recording", "Alt+Shift+R")
        if recording_shortcut:
            self.hotkey_manager.register_hotkey("toggle_recording", recording_shortcut, hwnd)

    def _on_hotkey_triggered(self, action):
        """Handle global hotkey actions"""
        if action == "toggle_window":
            if self.isVisible() and self.isActiveWindow():
                self.hide()
            else:
                self.show()
                self.activateWindow()
                self.raise_()
        elif action == "toggle_recording":
            # Ensure window is visible
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # Switch to chat page if needed
            self.stacked_widget.setCurrentIndex(0)
            
            # Toggle voice mode
            if hasattr(self.chat_page, 'toggle_voice_mode'):
                self.chat_page.toggle_voice_mode()

    def nativeEvent(self, eventType, message):
        """
        Override nativeEvent to intercept Windows messages for Global Hotkeys.
        This provides the rigorous reliability requested.
        """
        try:
            if self.hotkey_manager.process_native_event(eventType, message):
                return True, 0
        except Exception as e:
            logging.error(f"Error processing native event: {e}")
            
        return super().nativeEvent(eventType, message)
