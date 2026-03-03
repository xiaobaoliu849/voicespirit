from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QFrame, QSplitter,
    QComboBox, QLineEdit, QProgressBar, QScrollArea, QGridLayout,
    QListWidget, QListWidgetItem, QGroupBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Slot, Signal, QPropertyAnimation, QEasingCurve, Property, QParallelAnimationGroup
from PySide6.QtGui import QFont, QIcon, QColor
from app.ui.components.voice_selector import VoiceSelector
from app.ui.pages.voice_design_page import VoiceDesignWidget
from app.ui.pages.voice_clone_page import VoiceCloneWidget
from app.ui.styles.design_system import Colors, Typography, Spacing, Radius, Shadows, ComponentSizes
from utils.tts_handler import TtsHandler, TTS_ENGINE_EDGE, TTS_ENGINE_GEMINI, TTS_ENGINE_QWEN_VD, TTS_ENGINE_QWEN_VC, TTS_ENGINE_MINIMAX, TTS_ENGINE_QWEN_FLASH
from app.core.audio_recorder import AudioRecorder
import logging
import os
import base64
import tempfile
import time
from utils.audio_player import AudioPlayer


class ModernButton(QPushButton):
    """
    Modern button with hover animations:
    - Shadow elevation on hover
    - Subtle scale effect on press (for primary buttons)
    """
    def __init__(self, text, is_primary=False, parent=None):
        super().__init__(text, parent)
        self._is_primary = is_primary
        self._shadow_blur = 2 if is_primary else 0

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(ComponentSizes.BTN_MD)
        font = QFont(Typography.FONT_FAMILY.split(',')[0], Typography.SIZE_MD)
        font.setBold(is_primary)
        self.setFont(font)

        # Setup shadow effect
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(self._shadow_blur)
        self._shadow.setColor(QColor(0, 0, 0, 20))
        self._shadow.setOffset(0, 1)
        self.setGraphicsEffect(self._shadow)

        # Shadow animation
        self._shadow_anim = QPropertyAnimation(self, b"shadowBlur", self)
        self._shadow_anim.setDuration(150)
        self._shadow_anim.setEasingCurve(QEasingCurve.OutCubic)

        if is_primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: {Colors.TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {Radius.XXL}px;
                    padding: 0 {Spacing.XL}px;
                    font-weight: {Typography.WEIGHT_SEMIBOLD};
                }}
                QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
                QPushButton:pressed {{ background-color: {Colors.PRIMARY_ACTIVE}; }}
                QPushButton:disabled {{ background-color: {Colors.GRAY_300}; color: {Colors.TEXT_DISABLED}; }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_TERTIARY};
                    border: 1px solid {Colors.BORDER_DEFAULT};
                    border-radius: {Radius.XXL}px;
                    padding: 0 {Spacing.XL}px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.GRAY_100};
                    border-color: {Colors.PRIMARY};
                    color: {Colors.PRIMARY};
                }}
            """)

    # Shadow blur property for animation
    def get_shadow_blur(self):
        return self._shadow_blur

    def set_shadow_blur(self, value):
        self._shadow_blur = value
        self._shadow.setBlurRadius(value)
        # Adjust shadow opacity based on blur
        alpha = min(50, int(15 + value * 2))
        self._shadow.setColor(QColor(0, 0, 0, alpha))
        self._shadow.setOffset(0, value / 5)

    shadowBlur = Property(float, get_shadow_blur, set_shadow_blur)

    def enterEvent(self, event):
        """Mouse enters - animate shadow up"""
        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow_blur)
        self._shadow_anim.setEndValue(12 if self._is_primary else 6)
        self._shadow_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse leaves - animate shadow down"""
        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow_blur)
        self._shadow_anim.setEndValue(2 if self._is_primary else 0)
        self._shadow_anim.start()
        super().leaveEvent(event)





class SingleTtsWidget(QWidget):
    def __init__(self, tts_handler: TtsHandler, translation_manager=None, parent=None):
        super().__init__(parent)
        self.tts_handler = tts_handler
        self.tm = translation_manager
        self._init_ui()
        self._connect_signals()
        self._populate_engines()
        
        # Store labels for translation updates
        self._labels = {}

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 20, 30, 30)

        # 0. Engine Selection Panel
        engine_panel = QFrame()
        engine_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.LG}px;
            }}
        """)
        e_layout = QHBoxLayout(engine_panel)
        e_layout.setContentsMargins(15, 12, 15, 12)

        self.lbl_engine = QLabel(self.tm.t("tts_engine_label") if self.tm else "🔧 TTS Engine")
        self.lbl_engine.setFont(QFont(Typography.FONT_FAMILY.split(',')[0], 11, QFont.Bold))
        self.lbl_engine.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; border: none;")
        e_layout.addWidget(self.lbl_engine)

        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumWidth(180)
        self.engine_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QComboBox:hover {{ border-color: {Colors.PRIMARY}; }}
            QComboBox::drop-down {{ border: none; }}
        """)
        e_layout.addWidget(self.engine_combo)
        e_layout.addStretch()
        layout.addWidget(engine_panel)

        # 1. Voice Selection Panel
        voice_panel = QFrame()
        voice_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.LG}px;
            }}
        """)
        v_layout = QVBoxLayout(voice_panel)
        v_layout.setContentsMargins(15, 15, 15, 15)

        self.lbl_voice = QLabel(self.tm.t("tts_voice_selection") if self.tm else "🎤 Voice Selection")
        self.lbl_voice.setFont(QFont(Typography.FONT_FAMILY.split(',')[0], 11, QFont.Bold))
        self.lbl_voice.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; border: none;")
        v_layout.addWidget(self.lbl_voice)

        self.voice_selector = VoiceSelector()
        v_layout.addWidget(self.voice_selector)
        layout.addWidget(voice_panel)


        # 2. Text Input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(self.tm.t("tts_text_placeholder") if self.tm else "Enter text to convert to speech...")
        self.text_input.setFont(QFont(Typography.FONT_FAMILY.split(',')[0], 12))
        self.text_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.LG}px;
                padding: 15px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QTextEdit:focus {{ border: 1px solid {Colors.PRIMARY}; }}
        """)
        layout.addWidget(self.text_input)

        # 3. Controls
        btn_layout = QHBoxLayout()

        self.btn_preview = ModernButton(self.tm.t("tts_preview") if self.tm else "Preview", is_primary=False)
        self.btn_generate = ModernButton(self.tm.t("tts_generate_save") if self.tm else "Generate & Save", is_primary=True)

        btn_layout.addWidget(self.btn_preview)
        btn_layout.addWidget(self.btn_generate)
        layout.addLayout(btn_layout)

        # 4. Status
        self.lbl_status = QLabel(self.tm.t("tts_ready") if self.tm else "Ready")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFont(QFont(Typography.FONT_FAMILY.split(',')[0], 10))
        self.lbl_status.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self.lbl_status)

    def _connect_signals(self):
        self.btn_preview.clicked.connect(self._on_preview_clicked)
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)

    def _populate_engines(self):
        """Populate the engine selector with available TTS engines."""
        if not self.tts_handler:
            return
        
        engines = self.tts_handler.get_available_engines()
        self.engine_combo.blockSignals(True)
        self.engine_combo.clear()
        
        for engine in engines:
            # Show availability status
            display_name = engine["name"]
            if not engine["available"]:
                display_name += " (未配置)"
            self.engine_combo.addItem(display_name, engine["id"])
        
        # Select current engine
        current_idx = self.engine_combo.findData(self.tts_handler.current_engine)
        if current_idx >= 0:
            self.engine_combo.setCurrentIndex(current_idx)
        
        self.engine_combo.blockSignals(False)

    def _on_engine_changed(self, index):
        """Handle engine selection change."""
        engine_id = self.engine_combo.itemData(index)
        if engine_id and self.tts_handler:
            # Check if engine is available
            engines = self.tts_handler.get_available_engines()
            engine_info = next((e for e in engines if e["id"] == engine_id), None)
            
            if engine_info and not engine_info["available"]:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("引擎不可用")
                msg_box.setText(f"{engine_info['name']} 当前不可用。\n请在设置中配置相应的 API Key。")
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
                # Reset to current engine
                current_idx = self.engine_combo.findData(self.tts_handler.current_engine)
                self.engine_combo.blockSignals(True)
                self.engine_combo.setCurrentIndex(current_idx)
                self.engine_combo.blockSignals(False)
                return
            
            self.tts_handler.set_engine(engine_id)
            self.lbl_status.setText(f"已切换到 {engine_info['name']}")

    @Slot(str)
    def sync_engine_selector(self, engine_id):
        """Sync engine selector when engine is changed from another widget."""
        current_data = self.engine_combo.currentData()
        if current_data != engine_id:
            self.engine_combo.blockSignals(True)
            idx = self.engine_combo.findData(engine_id)
            if idx >= 0:
                self.engine_combo.setCurrentIndex(idx)
            self.engine_combo.blockSignals(False)

    def populate_voices(self, voices):
        self.voice_selector.populate_voices(voices)



    def _on_preview_clicked(self):
        voice_short_name = self.voice_selector.get_selected_voice()
        if not voice_short_name:
            self.lbl_status.setText(self.tm.t("tts_select_voice_first") if self.tm else "Please select a voice first.")
            return

        user_text = self.text_input.toPlainText().strip()
        
        if user_text:
            sample_text = user_text[:100] if len(user_text) > 100 else user_text
        else:
            sample_text = self.tm.t("tts_default_preview") if self.tm else "Hello, this is a voice preview."
            if "zh-" in voice_short_name.lower():
                sample_text = "你好，我是语音助手，很高兴为你服务。"
            
        self.lbl_status.setText(self.tm.t("tts_generating_preview") if self.tm else "Generating preview...")
        self.set_buttons_enabled(False)
        self.tts_handler.generate_preview(sample_text, voice_short_name)

    def _on_generate_clicked(self):
        text = self.text_input.toPlainText().strip()
        voice = self.voice_selector.get_selected_voice()
        
        if not text:
            self.lbl_status.setText(self.tm.t("tts_enter_text") if self.tm else "Please enter some text.")
            return
        
        save_title = self.tm.t("tts_save_audio") if self.tm else "Save Audio"
        file_filter = self.tm.t("tts_audio_files") if self.tm else "Audio Files"
        file_path, _ = QFileDialog.getSaveFileName(self, save_title, "output.mp3", f"{file_filter} (*.mp3)")
        if not file_path:
            return

        self.lbl_status.setText(self.tm.t("tts_generating_file") if self.tm else "Generating file...")
        self.set_buttons_enabled(False)
        self.tts_handler.generate_audio(text, voice, file_path)

    @Slot(str)
    def play_preview(self, file_path):
        self.lbl_status.setText(self.tm.t("tts_playing_preview") if self.tm else "Playing preview...")
        if hasattr(self.tts_handler, 'player'):
            self.tts_handler.player.play_file(file_path)
        self.lbl_status.setText(self.tm.t("tts_preview_playing") if self.tm else "Preview playing")
        self.set_buttons_enabled(True)

    @Slot(str)
    def generation_finished(self, file_path):
        self.lbl_status.setText(f"Done: {os.path.basename(file_path)}")
        self.set_buttons_enabled(True)
        success_title = self.tm.t("tts_success") if self.tm else "Success"
        saved_msg = self.tm.t("tts_audio_saved") if self.tm else "Audio saved to:"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(success_title)
        msg_box.setText(f"{saved_msg}\n{file_path}")
        msg_box.setIcon(QMessageBox.Information)
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

    @Slot(str)
    def show_error(self, error_msg):
        self.lbl_status.setText(f"Error: {error_msg}")
        self.set_buttons_enabled(True)
        title = self.tm.t("tts_error") if self.tm else "Error"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(error_msg)
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

    def set_buttons_enabled(self, enabled):
        self.btn_preview.setEnabled(enabled)
        self.btn_generate.setEnabled(enabled)

    def update_translations(self):
        """Update UI text when language changes."""
        if not self.tm:
            return
        self.lbl_engine.setText(self.tm.t("tts_engine_label"))
        self.lbl_voice.setText(self.tm.t("tts_voice_selection"))
        self.text_input.setPlaceholderText(self.tm.t("tts_text_placeholder"))
        self.btn_preview.setText(self.tm.t("tts_preview"))
        self.btn_generate.setText(self.tm.t("tts_generate_save"))
        self.lbl_status.setText(self.tm.t("tts_ready"))


class DialogTtsWidget(QWidget):
    def __init__(self, tts_handler: TtsHandler, translation_manager=None, parent=None):
        super().__init__(parent)
        self.tts_handler = tts_handler
        self.tm = translation_manager
        self._init_ui()
        self._connect_signals()
        self._populate_engines()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 20, 30, 30)

        # 0. Engine Selection Panel
        engine_panel = QFrame()
        engine_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.LG}px;
            }}
        """)
        e_layout = QHBoxLayout(engine_panel)
        e_layout.setContentsMargins(15, 12, 15, 12)

        self.lbl_engine = QLabel(self.tm.t("tts_engine_label") if self.tm else "🔧 TTS Engine")
        self.lbl_engine.setFont(QFont(Typography.FONT_FAMILY.split(',')[0], 11, QFont.Bold))
        self.lbl_engine.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; border: none;")
        e_layout.addWidget(self.lbl_engine)

        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumWidth(180)
        self.engine_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QComboBox:hover {{ border-color: {Colors.PRIMARY}; }}
            QComboBox::drop-down {{ border: none; }}
        """)
        e_layout.addWidget(self.engine_combo)
        e_layout.addStretch()
        layout.addWidget(engine_panel)

        # 1. Voice Roles
        roles_layout = QHBoxLayout()
        roles_layout.setSpacing(15)

        # Role A
        grp_a = self._create_role_group("Role A", "#E3F2FD", "#90CAF9")
        l_a = QVBoxLayout(grp_a)
        l_a.setContentsMargins(15, 15, 15, 15)
        self.lbl_role_a = QLabel(self.tm.t("tts_role_a_voice") if self.tm else "Role A Voice")
        l_a.addWidget(self.lbl_role_a)
        self.voice_selector_a = VoiceSelector()
        l_a.addWidget(self.voice_selector_a)
        roles_layout.addWidget(grp_a)

        # Role B
        grp_b = self._create_role_group("Role B", "#FCE4EC", "#F48FB1")
        l_b = QVBoxLayout(grp_b)
        l_b.setContentsMargins(15, 15, 15, 15)
        self.lbl_role_b = QLabel(self.tm.t("tts_role_b_voice") if self.tm else "Role B Voice")
        l_b.addWidget(self.lbl_role_b)
        self.voice_selector_b = VoiceSelector()
        l_b.addWidget(self.voice_selector_b)
        roles_layout.addWidget(grp_b)

        layout.addLayout(roles_layout)


        # 2. Helper Buttons
        helper_layout = QHBoxLayout()
        self.btn_insert_a = ModernButton(self.tm.t("tts_insert_role_a") if self.tm else "Insert Role A", is_primary=False)
        self.btn_insert_b = ModernButton(self.tm.t("tts_insert_role_b") if self.tm else "Insert Role B", is_primary=False)
        helper_layout.addWidget(self.btn_insert_a)
        helper_layout.addWidget(self.btn_insert_b)
        helper_layout.addStretch()
        layout.addLayout(helper_layout)

        # 3. Script Input
        self.script_input = QTextEdit()
        self.script_input.setPlaceholderText("A: 你好\nB: 早上好\nA: 今天天气真好...")
        self.script_input.setFont(QFont(Typography.FONT_FAMILY_MONO, 11))
        self.script_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.LG}px;
                padding: 15px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QTextEdit:focus {{ border: 1px solid {Colors.PRIMARY}; }}
        """)
        layout.addWidget(self.script_input)

        # 4. Generate
        self.btn_generate = ModernButton(self.tm.t("tts_generate_dialog") if self.tm else "Generate Dialog Audio", is_primary=True)
        layout.addWidget(self.btn_generate)

        # 5. Status
        self.lbl_status = QLabel(self.tm.t("tts_dialog_ready") if self.tm else "Ready (Format: 'A: text' or 'B: text')")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFont(QFont(Typography.FONT_FAMILY.split(',')[0], 10))
        self.lbl_status.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self.lbl_status)

    def _create_role_group(self, title, bg_color, border_color):
        grp = QFrame()
        grp.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.LG}px;
            }}
        """)
        return grp

    def _connect_signals(self):
        self.btn_insert_a.clicked.connect(lambda: self._insert_role("A"))
        self.btn_insert_b.clicked.connect(lambda: self._insert_role("B"))
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)

    def _populate_engines(self):
        """Populate the engine selector with available TTS engines."""
        if not self.tts_handler:
            return
        
        engines = self.tts_handler.get_available_engines()
        self.engine_combo.blockSignals(True)
        self.engine_combo.clear()
        
        for engine in engines:
            display_name = engine["name"]
            if not engine["available"]:
                display_name += " (未配置)"
            self.engine_combo.addItem(display_name, engine["id"])
        
        current_idx = self.engine_combo.findData(self.tts_handler.current_engine)
        if current_idx >= 0:
            self.engine_combo.setCurrentIndex(current_idx)
        
        self.engine_combo.blockSignals(False)

    def _on_engine_changed(self, index):
        """Handle engine selection change."""
        engine_id = self.engine_combo.itemData(index)
        if engine_id and self.tts_handler:
            engines = self.tts_handler.get_available_engines()
            engine_info = next((e for e in engines if e["id"] == engine_id), None)
            
            if engine_info and not engine_info["available"]:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("引擎不可用")
                msg_box.setText(f"{engine_info['name']} 当前不可用。\n请在设置中配置相应的 API Key。")
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
                current_idx = self.engine_combo.findData(self.tts_handler.current_engine)
                self.engine_combo.blockSignals(True)
                self.engine_combo.setCurrentIndex(current_idx)
                self.engine_combo.blockSignals(False)
                return
            
            self.tts_handler.set_engine(engine_id)
            self.lbl_status.setText(f"已切换到 {engine_info['name']}")

    @Slot(str)
    def sync_engine_selector(self, engine_id):
        """Sync engine selector when engine is changed from another widget."""
        current_data = self.engine_combo.currentData()
        if current_data != engine_id:
            self.engine_combo.blockSignals(True)
            idx = self.engine_combo.findData(engine_id)
            if idx >= 0:
                self.engine_combo.setCurrentIndex(idx)
            self.engine_combo.blockSignals(False)

    def populate_voices(self, voices):
        self.voice_selector_a.populate_voices(voices)
        self.voice_selector_b.populate_voices(voices)



    def _insert_role(self, role):
        cursor = self.script_input.textCursor()
        text = f"{role}: "
        cursor.insertText(text)
        self.script_input.setFocus()

    def _on_generate_clicked(self):
        script_text = self.script_input.toPlainText().strip()
        voice_a = self.voice_selector_a.get_selected_voice()
        voice_b = self.voice_selector_b.get_selected_voice()

        if not script_text:
            self.lbl_status.setText("请输入对话脚本")
            return
        
        lines = []
        for line in script_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("A:") or line.startswith("A："):
                content = line[2:].strip()
                if content:
                    lines.append({'role': 'A', 'text': content})
            elif line.startswith("B:") or line.startswith("B："):
                content = line[2:].strip()
                if content:
                    lines.append({'role': 'B', 'text': content})
        
        if not lines:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("格式错误")
            msg_box.setText("未找到有效行，请使用 'A: 文本' 格式。")
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

        file_path, _ = QFileDialog.getSaveFileName(self, "保存对话", "dialog.mp3", "音频文件 (*.mp3)")
        if not file_path:
            return

        self.lbl_status.setText("正在生成对话...")
        self.btn_generate.setEnabled(False)
        self.tts_handler.generate_dialog(lines, voice_a, voice_b, file_path)

    @Slot(str)
    def generation_finished(self, file_path):
        self.lbl_status.setText("对话生成完成")
        self.btn_generate.setEnabled(True)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("成功")
        msg_box.setText(f"对话已保存到:\n{file_path}")
        msg_box.setIcon(QMessageBox.Information)
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

    @Slot(str)
    def show_error(self, error_msg):
        self.lbl_status.setText(f"Error: {error_msg}")
        self.btn_generate.setEnabled(True)
        title = self.tm.t("tts_error") if self.tm else "Error"
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(error_msg)
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

    def update_translations(self):
        """Update UI text when language changes."""
        if not self.tm:
            return
        self.lbl_engine.setText(self.tm.t("tts_engine_label"))
        self.lbl_role_a.setText(self.tm.t("tts_role_a_voice"))
        self.lbl_role_b.setText(self.tm.t("tts_role_b_voice"))
        self.btn_insert_a.setText(self.tm.t("tts_insert_role_a"))
        self.btn_insert_b.setText(self.tm.t("tts_insert_role_b"))
        self.script_input.setPlaceholderText(self.tm.t("tts_dialog_placeholder"))
        self.btn_generate.setText(self.tm.t("tts_generate_dialog"))
        self.lbl_status.setText(self.tm.t("tts_dialog_ready"))


class TtsPage(QWidget):
    def __init__(self, tts_handler: TtsHandler, parent=None, translation_manager=None, api_client=None):
        super().__init__(parent)
        self.tts_handler = tts_handler
        self.api_client = api_client
        self.tm = translation_manager
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # Global Background
        self.setStyleSheet(f"background-color: {Colors.BG_TERTIARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 0; }}
            QTabWidget {{ background-color: {Colors.BG_TERTIARY}; }}
            QTabBar::tab {{
                background-color: transparent;
                padding: 12px 24px;
                font-family: {Typography.FONT_FAMILY.split(',')[0]};
                font-size: 14px;
                color: {Colors.TEXT_TERTIARY};
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {Colors.PRIMARY};
                font-weight: 600;
                border-bottom: 2px solid {Colors.PRIMARY};
            }}
            QTabBar::tab:hover {{ color: {Colors.PRIMARY}; }}
        """)
        
        self.single_tts_widget = SingleTtsWidget(self.tts_handler, self.tm)
        self.dialog_tts_widget = DialogTtsWidget(self.tts_handler, self.tm)
        self.voice_design_widget = VoiceDesignWidget(self.tts_handler, self.api_client, self.tm)
        self.voice_clone_widget = VoiceCloneWidget(self.tts_handler, self.api_client, self.tm)
        
        # Use translated tab names
        tab1 = self.tm.t("tts_single_voice") if self.tm else "Single Voice"
        tab2 = self.tm.t("tts_dialog_mode") if self.tm else "Dialog Mode"
        tab3 = self.tm.t("tts_voice_design") if self.tm else "🎨 Voice Design"
        tab4 = self.tm.t("tts_voice_clone") if self.tm else "🎭 Voice Clone"
        
        self.tabs.addTab(self.single_tts_widget, tab1)
        self.tabs.addTab(self.dialog_tts_widget, tab2)
        self.tabs.addTab(self.voice_design_widget, tab3)
        self.tabs.addTab(self.voice_clone_widget, tab4)
        
        layout.addWidget(self.tabs)
        
        # Connect to language change signal
        if self.tm:
            self.tm.language_changed.connect(self.update_translations)

    def update_translations(self):
        """Update all UI text when language changes."""
        if not self.tm:
            return
        
        # Update tab titles
        self.tabs.setTabText(0, self.tm.t("tts_single_voice"))
        self.tabs.setTabText(1, self.tm.t("tts_dialog_mode"))
        self.tabs.setTabText(2, self.tm.t("tts_voice_design"))
        self.tabs.setTabText(3, self.tm.t("tts_voice_clone"))
        
        # Update child widgets
        if hasattr(self.single_tts_widget, 'update_translations'):
            self.single_tts_widget.update_translations()
        if hasattr(self.dialog_tts_widget, 'update_translations'):
            self.dialog_tts_widget.update_translations()
        if hasattr(self.voice_design_widget, 'update_translations'):
            self.voice_design_widget.update_translations()
        if hasattr(self.voice_clone_widget, 'update_translations'):
            self.voice_clone_widget.update_translations()

    def _connect_signals(self):
        if not self.tts_handler:
            return
            
        self.tts_handler.voices_loaded.connect(self.single_tts_widget.populate_voices)
        self.tts_handler.voices_loaded.connect(self.dialog_tts_widget.populate_voices)
        self.tts_handler.preview_ready.connect(self.single_tts_widget.play_preview)
        
        # Route to active tab only to avoid double dialogs
        self.tts_handler.generation_complete.connect(self._on_generation_complete)
        self.tts_handler.generation_error.connect(self._on_generation_error)
        
        # Sync engine selectors between tabs
        self.tts_handler.engine_changed.connect(self.single_tts_widget.sync_engine_selector)
        self.tts_handler.engine_changed.connect(self.dialog_tts_widget.sync_engine_selector)
        
        # Auto-fetch Qwen voices if empty
        self.tts_handler.engine_changed.connect(self._on_engine_changed_handler)
        
        self.tts_handler.tts_error.connect(self.single_tts_widget.show_error)
        
        if self.tts_handler.voices:
            self.single_tts_widget.populate_voices(self.tts_handler.voices)
            self.dialog_tts_widget.populate_voices(self.tts_handler.voices)


    @Slot(str)
    def _on_generation_complete(self, file_path):
        """Route generation complete to active tab only."""
        if self.tabs.currentIndex() == 0:
            self.single_tts_widget.generation_finished(file_path)
        else:
            self.dialog_tts_widget.generation_finished(file_path)

    @Slot(str)
    def _on_generation_error(self, error_msg):
        """Route generation error to active tab only."""
        if self.tabs.currentIndex() == 0:
            self.single_tts_widget.show_error(error_msg)
        else:
            self.dialog_tts_widget.show_error(error_msg)
            
    @Slot(str)
    def _on_engine_changed_handler(self, engine_id):
        """Auto-fetch voices when switching engine."""
        if not self.api_client:
            return

        if engine_id == TTS_ENGINE_QWEN_VD:
             # Check if voices are loaded. If not (or empty list), fetch.
             if not self.tts_handler.voices:
                 try:
                     self.single_tts_widget.lbl_status.setText("Fetching Qwen Voice Design list...")
                     self.api_client.list_qwen_voices_async("voice_design")
                 except Exception as e:
                     logging.error(f"Auto-fetch VD voices failed: {e}")

        elif engine_id == TTS_ENGINE_QWEN_VC:
             if not self.tts_handler.voices:
                 try:
                     self.single_tts_widget.lbl_status.setText("Fetching Qwen Voice Clone list...")
                     self.api_client.list_qwen_voices_async("voice_clone")
                 except Exception as e:
                     logging.error(f"Auto-fetch VC voices failed: {e}")

        elif engine_id == TTS_ENGINE_MINIMAX:
            # Load MiniMax voices
            try:
                self.single_tts_widget.lbl_status.setText("Loading MiniMax voices...")
                self.tts_handler.set_minimax_voices()
            except Exception as e:
                logging.error(f"Failed to load MiniMax voices: {e}")

        elif engine_id == TTS_ENGINE_QWEN_FLASH:
            # Qwen Flash uses QWEN_TTS_FLASH_VOICES from tts_handler
            try:
                self.single_tts_widget.lbl_status.setText("Loading Qwen Flash voices...")
                from utils.tts_handler import QWEN_TTS_FLASH_VOICES
                self.tts_handler.voices = QWEN_TTS_FLASH_VOICES.copy()
                self.tts_handler.voices_loaded.emit(self.tts_handler.voices)
            except Exception as e:
                logging.error(f"Failed to load Qwen Flash voices: {e}")
