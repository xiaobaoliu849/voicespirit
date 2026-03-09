from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit,
    QPushButton, QFrame, QScrollArea, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Slot, QTimer, QSize
from PySide6.QtGui import QFont, QColor

from app.ui.components.glass_panel import GlassPanel
from app.ui.components.voice_card import VoiceCardV2
from app.ui.components.style_preset_card import StylePresetCard
from app.ui.styles.design_system import DarkColors, Typography, Spacing, Radius
from utils.tts_handler import TtsHandler, QwenTtsGenerateWorker
from PySide6.QtCore import QThreadPool

import logging
import base64
import tempfile
import os
import re

class VoiceDesignWidget(QWidget):
    """
    Voice Design Page - Create custom voices using prompts.
    Aesthetic: Deep Space / Neon Glassmorphism.
    """

    def __init__(self, tts_handler: TtsHandler, api_client, translation_manager=None, parent=None):
        super().__init__(parent)
        self.tts_handler = tts_handler
        self.api_client = api_client
        self.tm = translation_manager

        # Internal state
        self.voices_data = []

        # Audio Player (reusing tts_handler player if possible, or create one)
        # Note: tts_handler has 'player'

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # This page uses a dedicated dark studio theme and must not inherit
        # the global light QWidget background.
        self.setObjectName("VoiceDesignWidget")
        self.setStyleSheet(f"""
            QWidget#VoiceDesignWidget {{
                background-color: {DarkColors.BG_PRIMARY};
            }}
            QWidget#VoiceDesignWidget QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget#VoiceDesignWidget QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
        """)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.XL)
        main_layout.setSpacing(Spacing.XL)

        # 1. Quick Presets Section
        presets_label = QLabel("✨ Quick Presets")
        presets_label.setStyleSheet(f"color: {DarkColors.TEXT_PRIMARY}; font-size: {Typography.SIZE_XL}px; font-weight: {Typography.WEIGHT_BOLD};")
        main_layout.addWidget(presets_label)

        presets_scroll = QScrollArea()
        presets_scroll.setWidgetResizable(True)
        presets_scroll.setFixedHeight(130)
        presets_scroll.setStyleSheet("background: transparent; border: none;")
        presets_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        presets_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        presets_container = QWidget()
        presets_container.setStyleSheet("background: transparent;")
        presets_layout = QHBoxLayout(presets_container)
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(Spacing.MD)

        # Define Presets
        presets_data = [
            ("young_female", "Young Female", "👩", "A young female voice, energetic and bright"),
            ("deep_male", "Deep Male", "👨", "A mature male voice, deep and authoritative"),
            ("narrator", "Narrator", "🎙️", "A clear, neutral voice suitable for narration"),
            ("friendly", "Friendly", "😊", "A warm, friendly voice with a smile"),
            ("professional", "Professional", "🏢", "A professional, clear business voice"),
            ("elderly", "Elderly", "👴", "An elderly voice, slow and wise"),
            ("child", "Child", "👶", "A cute child voice, high pitched")
        ]

        for pid, label, icon, prompt in presets_data:
            card = StylePresetCard(pid, label, icon)
            card.selected.connect(lambda _, p=prompt: self._apply_preset(p))
            presets_layout.addWidget(card)

        presets_layout.addStretch()
        presets_scroll.setWidget(presets_container)
        main_layout.addWidget(presets_scroll)

        # 2. Creation Studio (Glass Panel)
        studio_panel = GlassPanel(radius=Radius.XL)
        studio_layout = QVBoxLayout(studio_panel)
        studio_layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        studio_layout.setSpacing(Spacing.LG)

        # Header
        studio_header = QLabel("🎨 Creation Studio")
        studio_header.setStyleSheet(f"color: {DarkColors.TEXT_PRIMARY}; font-size: {Typography.SIZE_LG}px; font-weight: {Typography.WEIGHT_BOLD};")
        studio_layout.addWidget(studio_header)

        # Prompt Input
        prompt_label = QLabel("Voice Description (Prompt)")
        prompt_label.setStyleSheet(f"color: {DarkColors.TEXT_SECONDARY}; font-size: {Typography.SIZE_MD}px;")
        studio_layout.addWidget(prompt_label)

        self.text_prompt = QTextEdit()
        self.text_prompt.setPlaceholderText("Describe the voice you want... (e.g., 'A confident young woman with a British accent')")
        self.text_prompt.setMaximumHeight(80)
        self.text_prompt.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DarkColors.BG_TERTIARY};
                color: {DarkColors.TEXT_PRIMARY};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: {Spacing.MD}px;
                font-size: {Typography.SIZE_MD}px;
            }}
            QTextEdit:focus {{
                border: 1px solid {DarkColors.PRIMARY};
                background-color: {DarkColors.BG_ELEVATED};
            }}
        """)
        studio_layout.addWidget(self.text_prompt)

        # Row: Preview Text + Name
        row_layout = QHBoxLayout()
        row_layout.setSpacing(Spacing.XL)

        # Preview Text
        preview_col = QVBoxLayout()
        preview_label = QLabel("Preview Text")
        preview_label.setStyleSheet(f"color: {DarkColors.TEXT_SECONDARY}; font-size: {Typography.SIZE_MD}px;")
        preview_col.addWidget(preview_label)

        self.text_preview = QLineEdit("Hello, this is a test of my new voice.")
        self.text_preview.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DarkColors.BG_TERTIARY};
                color: {DarkColors.TEXT_PRIMARY};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: {Spacing.MD}px;
                font-size: {Typography.SIZE_MD}px;
            }}
            QLineEdit:focus {{ border: 1px solid {DarkColors.PRIMARY}; }}
        """)
        preview_col.addWidget(self.text_preview)
        row_layout.addLayout(preview_col, 2)

        # Name Input
        name_col = QVBoxLayout()
        name_label = QLabel("Voice Name")
        name_label.setStyleSheet(f"color: {DarkColors.TEXT_SECONDARY}; font-size: {Typography.SIZE_MD}px;")
        name_col.addWidget(name_label)

        self.text_name = QLineEdit()
        self.text_name.setPlaceholderText("my_voice_01")
        self.text_name.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DarkColors.BG_TERTIARY};
                color: {DarkColors.TEXT_PRIMARY};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: {Spacing.MD}px;
                font-size: {Typography.SIZE_MD}px;
            }}
            QLineEdit:focus {{ border: 1px solid {DarkColors.PRIMARY}; }}
        """)
        name_col.addWidget(self.text_name)
        row_layout.addLayout(name_col, 1)

        studio_layout.addLayout(row_layout)

        # Create Button
        btn_row = QHBoxLayout()
        self.btn_create = QPushButton("Generate Voice")
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setFixedSize(180, 45)
        # Use gradient style from Design System helper or inline
        self.btn_create.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {DarkColors.PRIMARY}, stop:1 #FF8E53);
                color: {DarkColors.TEXT_ON_PRIMARY};
                border: none;
                border-radius: {Radius.XXL}px;
                font-size: {Typography.SIZE_MD}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {DarkColors.PRIMARY_HOVER}, stop:1 #FFA068);
            }}
            QPushButton:disabled {{
                background: {DarkColors.BG_ELEVATED};
                color: {DarkColors.TEXT_MUTED};
            }}
        """)
        self.btn_create.clicked.connect(self._create_voice)
        btn_row.addWidget(self.btn_create)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"color: {DarkColors.TEXT_TERTIARY}; margin-left: 10px;")
        btn_row.addWidget(self.lbl_status)
        btn_row.addStretch()

        studio_layout.addLayout(btn_row)
        main_layout.addWidget(studio_panel)

        # 3. My Voices Section
        voices_header_layout = QHBoxLayout()
        voices_label = QLabel("📚 My Voices")
        voices_label.setStyleSheet(f"color: {DarkColors.TEXT_PRIMARY}; font-size: {Typography.SIZE_XL}px; font-weight: {Typography.WEIGHT_BOLD};")
        voices_header_layout.addWidget(voices_label)

        voices_header_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {DarkColors.TEXT_SECONDARY};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background: {DarkColors.BG_ELEVATED};
                color: {DarkColors.TEXT_PRIMARY};
            }}
        """)
        self.btn_refresh.clicked.connect(self._refresh_list)
        voices_header_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(voices_header_layout)

        # Grid for Voices
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        self.voices_container = QWidget()
        self.voices_container.setStyleSheet("background: transparent;")
        self.voices_grid = QGridLayout(self.voices_container)
        self.voices_grid.setSpacing(Spacing.LG)
        self.voices_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll_area.setWidget(self.voices_container)
        main_layout.addWidget(scroll_area, 1) # Expand

    def _connect_signals(self):
        if self.api_client:
            self.api_client.qwen_voice_created.connect(self._on_voice_created)
            self.api_client.qwen_voice_list_fetched.connect(self._on_list_fetched)
            self.api_client.qwen_voice_deleted.connect(self._on_voice_deleted)
            self.api_client.qwen_tts_error.connect(self._on_error)

    def _apply_preset(self, prompt: str):
        self.text_prompt.setPlainText(prompt)
        self.text_prompt.setFocus()
        # Optional: Flash effect?

    def _create_voice(self):
        prompt = self.text_prompt.toPlainText().strip()
        preview = self.text_preview.text().strip()
        name = self.text_name.text().strip()

        if not prompt or not name:
            self._show_msg("Input Error", "Please provide a voice description and a name.", QMessageBox.Warning)
            return

        if not re.match(r'^[a-zA-Z0-9_]{1,16}$', name):
            self._show_msg("Invalid Name", "Name must be alphanumeric/underscore (max 16 chars). No spaces or special chars.", QMessageBox.Warning)
            return

        self.lbl_status.setText("Creating voice... This may take a moment.")
        self.btn_create.setEnabled(False)
        self.api_client.create_voice_design_async(prompt, preview, name)

    def _refresh_list(self):
        if self.api_client:
            self.lbl_status.setText("Refreshing list...")
            self.api_client.list_qwen_voices_async("voice_design")

    @Slot(dict)
    def _on_voice_created(self, data):
        if data.get("type") != "voice_design": return

        self.lbl_status.setText("✅ Voice Created Successfully!")
        self.btn_create.setEnabled(True)
        self._refresh_list()

        # Play preview if available
        audio_b64 = data.get("preview_audio_data")
        if audio_b64:
            self._play_b64_audio(audio_b64)

    @Slot(str, list)
    def _on_list_fetched(self, voice_type, voices):
        if voice_type != "voice_design": return

        self.lbl_status.setText("")
        self.voices_data = voices
        self._update_grid()

        # Sync with handler
        if self.tts_handler:
            self.tts_handler.set_qwen_voices(voices, "voice_design")

    @Slot(str)
    def _on_voice_deleted(self, voice_id):
        self.lbl_status.setText(f"Voice {voice_id} deleted.")
        self._refresh_list()

    @Slot(str)
    def _on_error(self, error_msg):
        # Only show if visible or related
        if self.isVisible():
            self.lbl_status.setText(f"Error: {error_msg}")
            self.btn_create.setEnabled(True)
            self._show_msg("Error", error_msg, QMessageBox.Critical)

    def _update_grid(self):
        # Clear
        while self.voices_grid.count():
            item = self.voices_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.voices_data:
            empty_lbl = QLabel("No designed voices yet. Create one above!")
            empty_lbl.setStyleSheet(f"color: {DarkColors.TEXT_MUTED}; font-size: 14px;")
            self.voices_grid.addWidget(empty_lbl, 0, 0)
            return

        # Populate
        columns = 3
        for idx, voice in enumerate(self.voices_data):
            row = idx // columns
            col = idx % columns

            card = VoiceCardV2(voice)
            card.play_preview.connect(self._play_voice_preview)
            card.delete_requested.connect(self._delete_voice)

            self.voices_grid.addWidget(card, row, col)

    def _play_voice_preview(self, voice_id):
        # Implementation similar to previous, using tts_handler to generate/play
        self.lbl_status.setText(f"Generating preview for {voice_id}...")

        # ... logic to generate/play preview (omitted for brevity, assume reusing same logic)
        # Using a simplified version here for porting efficiency
        if not self.tts_handler: return

        # Find voice data
        voice_data = next((v for v in self.voices_data if v.get('voice') == voice_id), None)
        target_model = voice_data.get('target_model', 'qwen3-tts-vd-realtime-2025-12-16') if voice_data else 'qwen3-tts-vd-realtime-2025-12-16'

        # Launch worker (reuse code from old widget)
        try:
             # ... setup worker ...
             # For now, just logging placeholder
             logging.info(f"Should play preview for {voice_id} model {target_model}")

             # ACTUAL IMPLEMENTATION
             preview_text = "Hello, this is a voice preview."
             temp_dir = tempfile.gettempdir()
             output_path = os.path.join(temp_dir, f"voice_preview_{voice_id}.mp3")

             config_manager = self.api_client.config_manager if self.api_client else None
             if not config_manager: return

             self._preview_worker = QwenTtsGenerateWorker(
                text=preview_text,
                voice_name=voice_id,
                target_model=target_model,
                output_path=output_path,
                config_manager=config_manager
             )
             self._preview_worker.signals.finished.connect(self._on_preview_ready, Qt.QueuedConnection)
             QThreadPool.globalInstance().start(self._preview_worker)
        except Exception as e:
            logging.error(f"Preview error: {e}")

    def _on_preview_ready(self, path, success):
        if success and self.tts_handler:
            self.tts_handler.player.play_file(path)
            self.lbl_status.setText("Playing preview...")
        else:
            self.lbl_status.setText("Preview failed.")

    def _delete_voice(self, voice_id):
        confirm = QMessageBox.question(self, "Confirm Delete", f"Delete voice '{voice_id}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.api_client.delete_qwen_voice_async(voice_id, "voice_design")

    def _play_b64_audio(self, b64_data):
        try:
            audio_data = base64.b64decode(b64_data)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            if self.tts_handler:
                self.tts_handler.player.play_file(temp_path)
        except Exception as e:
            logging.error(f"Failed to play b64 audio: {e}")

    def _show_msg(self, title, text, icon):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: {DarkColors.BG_PRIMARY}; color: {DarkColors.TEXT_PRIMARY}; }}
            QLabel {{ color: {DarkColors.TEXT_PRIMARY}; }}
            QPushButton {{
                background-color: {DarkColors.PRIMARY};
                color: {DarkColors.TEXT_ON_PRIMARY};
                border-radius: 4px; padding: 6px 12px;
            }}
        """)
        msg.exec()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.voices_data and self.api_client:
            self._refresh_list()

    def update_translations(self):
        # TODO: Implement translation update if needed
        pass
