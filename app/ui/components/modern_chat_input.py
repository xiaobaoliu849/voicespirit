from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QToolButton, QFrame, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from PySide6.QtGui import QIcon, QAction
from app.core.translation import TranslationManager
from app.core.config import get_resource_path
from app.ui.styles.design_system import Colors


class ModernChatInput(QFrame):
    """A modern chat input component inspired by Copilot.
    
    Layout (vertical):
    ┌──────────────────────────────────────────┐
    │ Text input area                          │
    │                                          │
    │ [+]                          [📞] [🎤] │ <- Buttons at bottom (Live + Record)
    └──────────────────────────────────────────┘
    """
    
    # Define signals
    text_submitted = Signal(str)
    voice_live_requested = Signal()  # Real-time voice conversation (like Gemini/Grok)
    voice_record_requested = Signal()  # Record voice and send as text
    
    # Define signals for menu actions
    request_add_image = Signal()
    request_add_file = Signal()
    request_generate_image = Signal()

    def __init__(self, translation_manager=None, parent=None):
        super().__init__(parent)
        self.translation_manager = translation_manager or TranslationManager()
        self.setProperty("class", "ModernInputFrame")
        self._init_ui()
        self._apply_styles()
        
    def _init_ui(self):
        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)  # Reduced padding for compact look
        main_layout.setSpacing(6)  # Reduced spacing

        # 1. Text Input Area (top)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(self.translation_manager.t("chat_ask_anything"))
        self.text_input.setAcceptRichText(False)  # 禁用富文本，确保emoji等Unicode字符正确粘贴
        self.text_input.setFrameShape(QFrame.NoFrame)
        self.text_input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.text_input.setMinimumHeight(28)  # Compact minimum
        self.text_input.setMaximumHeight(150)
        self.text_input.setFixedHeight(28)  # Start compact
        self.text_input.textChanged.connect(self._adjust_height)
        self.text_input.installEventFilter(self)
        
        main_layout.addWidget(self.text_input)
        
        # 2. Button row (bottom)
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(10)
        
        # Plus Button (left side) - use QToolButton for proper icon centering
        self.plus_btn = QToolButton()
        icon_path = get_resource_path("icons/plus.svg")
        self.plus_btn.setIcon(QIcon(icon_path))
        self.plus_btn.setIconSize(QSize(18, 18))
        self.plus_btn.setFixedSize(36, 36)
        self.plus_btn.setCursor(Qt.PointingHandCursor)
        self.plus_btn.setToolTip(self.translation_manager.t("input_more_actions"))
        self.plus_btn.setPopupMode(QToolButton.InstantPopup)  # Show menu on click
        self.plus_btn.setStyleSheet("""
            QToolButton {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 18px;
            }
            QToolButton:hover {
                background-color: #e8e8e8;
                border: 1px solid #c0c0c0;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        # Menu for Plus Button
        self.menu = QMenu(self)
        
        self.add_image_action = QAction(self.translation_manager.t("input_add_image"), self)
        self.add_image_action.triggered.connect(self.request_add_image.emit)
        self.menu.addAction(self.add_image_action)

        self.add_file_action = QAction(self.translation_manager.t("input_add_file"), self)
        self.add_file_action.triggered.connect(self.request_add_file.emit)
        self.menu.addAction(self.add_file_action)

        self.menu.addSeparator()

        self.gen_image_action = QAction(self.translation_manager.t("input_create_image"), self)
        self.gen_image_action.triggered.connect(self.request_generate_image.emit)
        self.menu.addAction(self.gen_image_action)
        
        self.plus_btn.setMenu(self.menu)
        
        button_row.addWidget(self.plus_btn)
        
        # Stretch to push mic button to right
        button_row.addStretch()
        
        # Mic Button (right side) - Record voice and send as text
        self.mic_btn = QPushButton()
        self.mic_btn.setIcon(QIcon.fromTheme("audio-input-microphone"))
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setIconSize(QSize(20, 20))
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setProperty("class", "InputCircleBtn")
        self.mic_btn.setProperty("type", "voice")  # Add type property for styling
        self.mic_btn.setToolTip(self.translation_manager.t("input_voice_record_tooltip"))
        self.mic_btn.clicked.connect(self.voice_record_requested.emit)
        
        button_row.addWidget(self.mic_btn)
        
        # Live Voice Button (right side) - Real-time voice conversation like Gemini/Grok
        self.live_voice_btn = QPushButton()
        icon_path = get_resource_path("icons/phone.svg")
        self.live_voice_btn.setIcon(QIcon(icon_path))
        self.live_voice_btn.setFixedSize(36, 36)
        self.live_voice_btn.setIconSize(QSize(20, 20))
        self.live_voice_btn.setCursor(Qt.PointingHandCursor)
        self.live_voice_btn.setProperty("class", "InputCircleBtn")
        self.live_voice_btn.setProperty("type", "live_voice")  # Live voice style (orange)
        self.live_voice_btn.setToolTip(self.translation_manager.t("input_voice_live_tooltip"))
        self.live_voice_btn.clicked.connect(self.voice_live_requested.emit)
        
        button_row.addWidget(self.live_voice_btn)
        
        main_layout.addLayout(button_row)

    def update_ui_text(self, language):
        """Update UI text when language changes"""
        self.plus_btn.setToolTip(self.translation_manager.t("input_more_actions"))
        self.add_image_action.setText(self.translation_manager.t("input_add_image"))
        self.add_file_action.setText(self.translation_manager.t("input_add_file"))
        self.gen_image_action.setText(self.translation_manager.t("input_create_image"))
        self.text_input.setPlaceholderText(self.translation_manager.t("chat_ask_anything"))
        self.mic_btn.setToolTip(self.translation_manager.t("input_voice_record_tooltip"))
        self.live_voice_btn.setToolTip(self.translation_manager.t("input_voice_live_tooltip"))
        
    def _apply_styles(self):
        style = """
            QFrame.ModernInputFrame {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 20px;
            }
            QFrame.ModernInputFrame:hover {
                border: 1px solid #c0c0c0;
            }
            QPushButton.InputCircleBtn {
                background-color: #f5f5f5;
                color: #555;
                border: 1px solid #e0e0e0;
                border-radius: 18px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton.InputCircleBtn[type="voice"] {
                background-color: #6B7280; /* Gray for record button */
                color: white;
                border: 1px solid #6B7280;
            }
            QPushButton.InputCircleBtn[type="voice"]:hover {
                background-color: #4B5563;
                border: 1px solid #4B5563;
            }
            QPushButton.InputCircleBtn[type="live_voice"] {
                background-color: #DA7756; /* Burnt orange like primary button in theme */
                color: white;
                border: 1px solid #DA7756;
            }
            QPushButton.InputCircleBtn[type="live_voice"]:hover {
                background-color: #C86545;
                border: 1px solid #C86545;
            }
            QPushButton.InputCircleBtn:hover {
                background-color: #e8e8e8;
                color: #333;
                border: 1px solid #c0c0c0;
            }
            QPushButton.InputCircleBtn::menu-indicator {
                image: none;
            }
            QTextEdit {
                background: transparent;
                color: #333;
                font-size: 16px;
                font-family: 'Microsoft YaHei', 'Segoe UI', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif;
                border: none;
                padding: 0px;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 8px;
            }
            QMenu::item {
                padding: 10px 20px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
        """
        style = style.replace("#DA7756", Colors.PRIMARY)
        style = style.replace("#C86545", Colors.PRIMARY_HOVER)
        self.setStyleSheet(style)

    def _adjust_height(self):
        doc_height = self.text_input.document().size().height()
        new_height = max(28, min(doc_height + 6, 150))  # Start at 28, grow with content
        self.text_input.setFixedHeight(int(new_height))
        
    def eventFilter(self, obj, event):
        if obj == self.text_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return:
                if event.modifiers() & Qt.ShiftModifier:
                    return False
                else:
                    self._submit()
                    return True
        return super().eventFilter(obj, event)

    def _submit(self):
        text = self.text_input.toPlainText().strip()
        if text:
            self.text_submitted.emit(text)
            self.text_input.clear()
            self.text_input.setFixedHeight(28)  # Reset to compact

    def set_input_text(self, text):
        self.text_input.setPlainText(text)
    
    def set_recording_state(self, recording):
        """Update UI to show recording state."""
        if recording:
            self.mic_btn.setProperty("recording", True)
            self.mic_btn.setStyleSheet("""
                QPushButton.InputCircleBtn {
                    background-color: #EF4444;
                    color: white;
                    border: 1px solid #EF4444;
                    border-radius: 18px;
                }
                QPushButton.InputCircleBtn:hover {
                    background-color: #DC2626;
                    border: 1px solid #DC2626;
                }
            """)
        else:
            self.mic_btn.setProperty("recording", False)
            self._apply_styles()  # Reapply the original styles
