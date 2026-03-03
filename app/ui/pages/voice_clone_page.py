from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QGridLayout, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Slot, QTimer, QSize, QThreadPool
from PySide6.QtGui import QFont, QColor

from app.ui.components.glass_panel import GlassPanel
from app.ui.components.voice_card import VoiceCardV2
from app.ui.components.audio_drop_zone import AudioDropZoneV2
from app.ui.styles.design_system import DarkColors, Typography, Spacing, Radius
from utils.tts_handler import TtsHandler, QwenTtsGenerateWorker

import logging
import os
import re
import tempfile

class VoiceCloneWidget(QWidget):
    """
    Voice Clone Page - Clone voices from audio samples.
    Aesthetic: Cyberpunk Laboratory.
    """

    def __init__(self, tts_handler: TtsHandler, api_client, translation_manager=None, parent=None):
        super().__init__(parent)
        self.tts_handler = tts_handler
        self.api_client = api_client
        self.tm = translation_manager

        self.audio_path = None
        self.voices_data = []

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # This page uses a dedicated dark studio theme and must not inherit
        # the global light QWidget background.
        self.setObjectName("VoiceCloneWidget")
        self.setStyleSheet(f"""
            QWidget#VoiceCloneWidget {{
                background-color: {DarkColors.BG_PRIMARY};
            }}
            QWidget#VoiceCloneWidget QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget#VoiceCloneWidget QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.XL)
        main_layout.setSpacing(Spacing.XL)

        # 1. Clone Laboratory (Glass Panel)
        lab_panel = GlassPanel(radius=Radius.XL)
        lab_layout = QVBoxLayout(lab_panel)
        lab_layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        lab_layout.setSpacing(Spacing.LG)

        # Header
        lab_header = QLabel("🧬 Clone Laboratory")
        lab_header.setStyleSheet(f"color: {DarkColors.ACCENT_PINK}; font-size: {Typography.SIZE_LG}px; font-weight: {Typography.WEIGHT_BOLD};")
        lab_layout.addWidget(lab_header)

        # Drop Zone
        self.drop_zone = AudioDropZoneV2()
        self.drop_zone.file_dropped.connect(self._on_file_selected)
        lab_layout.addWidget(self.drop_zone)

        # File Info Row
        file_row = QHBoxLayout()
        file_row.setSpacing(Spacing.MD)

        self.input_file_path = QLineEdit()
        self.input_file_path.setReadOnly(True)
        self.input_file_path.setPlaceholderText("No audio file selected...")
        self.input_file_path.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DarkColors.BG_TERTIARY};
                color: {DarkColors.TEXT_TERTIARY};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: {Spacing.MD}px;
                font-size: {Typography.SIZE_MD}px;
            }}
        """)
        file_row.addWidget(self.input_file_path, 1)

        self.btn_play_sample = QPushButton("▶ Preview")
        self.btn_play_sample.setCursor(Qt.PointingHandCursor)
        self.btn_play_sample.setEnabled(False)
        self.btn_play_sample.setFixedSize(100, 40)
        self.btn_play_sample.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkColors.BG_ELEVATED};
                color: {DarkColors.TEXT_PRIMARY};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
            }}
            QPushButton:hover {{
                background-color: {DarkColors.PRIMARY};
                border-color: {DarkColors.PRIMARY};
            }}
            QPushButton:disabled {{
                color: {DarkColors.TEXT_MUTED};
            }}
        """)
        self.btn_play_sample.clicked.connect(self._play_sample)
        file_row.addWidget(self.btn_play_sample)

        lab_layout.addLayout(file_row)

        # Name Input & Clone Action
        action_row = QHBoxLayout()
        action_row.setSpacing(Spacing.XL)

        name_col = QVBoxLayout()
        name_label = QLabel("Voice Name")
        name_label.setStyleSheet(f"color: {DarkColors.TEXT_SECONDARY}; font-size: {Typography.SIZE_MD}px;")
        name_col.addWidget(name_label)

        self.text_name = QLineEdit()
        self.text_name.setPlaceholderText("my_clone_01")
        self.text_name.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DarkColors.BG_TERTIARY};
                color: {DarkColors.TEXT_PRIMARY};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: {Spacing.MD}px;
                font-size: {Typography.SIZE_MD}px;
            }}
            QLineEdit:focus {{ border: 1px solid {DarkColors.ACCENT_PINK}; }}
        """)
        name_col.addWidget(self.text_name)
        action_row.addLayout(name_col, 1)

        # Clone Button
        self.btn_clone = QPushButton("Initialize Clone")
        self.btn_clone.setCursor(Qt.PointingHandCursor)
        self.btn_clone.setFixedSize(180, 45)
        # Pink/Purple Gradient
        self.btn_clone.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {DarkColors.ACCENT_PINK}, stop:1 {DarkColors.ACCENT_PURPLE});
                color: {DarkColors.TEXT_ON_PRIMARY};
                border: none;
                border-radius: {Radius.XXL}px;
                font-size: {Typography.SIZE_MD}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {DarkColors.ACCENT_PINK}, stop:1 #D946EF);
            }}
            QPushButton:disabled {{
                background: {DarkColors.BG_ELEVATED};
                color: {DarkColors.TEXT_MUTED};
            }}
        """)
        self.btn_clone.clicked.connect(self._create_clone)

        # Container for button to align bottom
        btn_container = QVBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.btn_clone)
        action_row.addLayout(btn_container)

        lab_layout.addLayout(action_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(f"color: {DarkColors.TEXT_TERTIARY}; font-size: 13px;")
        lab_layout.addWidget(self.lbl_status)

        main_layout.addWidget(lab_panel)

        # 2. Cloned Voices Grid
        voices_header_layout = QHBoxLayout()
        voices_label = QLabel("🧬 Cloned Specimens")
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

        # Grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        self.voices_container = QWidget()
        self.voices_container.setStyleSheet("background: transparent;")
        self.voices_grid = QGridLayout(self.voices_container)
        self.voices_grid.setSpacing(Spacing.LG)
        self.voices_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll_area.setWidget(self.voices_container)
        main_layout.addWidget(scroll_area, 1)

    def _connect_signals(self):
        if self.api_client:
            self.api_client.qwen_voice_created.connect(self._on_voice_created)
            self.api_client.qwen_voice_list_fetched.connect(self._on_list_fetched)
            self.api_client.qwen_voice_deleted.connect(self._on_voice_deleted)
            self.api_client.qwen_tts_error.connect(self._on_error)

    def _on_file_selected(self, path):
        self.audio_path = path
        self.input_file_path.setText(os.path.basename(path))
        self.btn_play_sample.setEnabled(True)

    def _play_sample(self):
        if self.audio_path and self.tts_handler:
            self.tts_handler.player.play_file(self.audio_path)

    def _create_clone(self):
        name = self.text_name.text().strip()
        if not self.audio_path or not name:
            self._show_msg("Input Error", "Please select an audio file and provide a name.", QMessageBox.Warning)
            return

        if not re.match(r'^[a-zA-Z0-9_]{1,16}$', name):
            self._show_msg("Invalid Name", "Name must be alphanumeric/underscore (max 16 chars).", QMessageBox.Warning)
            return

        self.lbl_status.setText("Cloning sequence initiated... Please wait.")
        self.btn_clone.setEnabled(False)
        self.api_client.create_voice_clone_async(self.audio_path, name)

    def _refresh_list(self):
        if self.api_client:
            self.lbl_status.setText("Scanning database...")
            self.api_client.list_qwen_voices_async("voice_clone")

    @Slot(dict)
    def _on_voice_created(self, data):
        if data.get("type") != "voice_clone": return
        self.lbl_status.setText("✅ Clone Successful!")
        self.btn_clone.setEnabled(True)
        self._refresh_list()

    @Slot(str, list)
    def _on_list_fetched(self, voice_type, voices):
        if voice_type != "voice_clone": return
        self.lbl_status.setText("")
        self.voices_data = voices
        self._update_grid()

        if self.tts_handler:
            self.tts_handler.set_qwen_voices(voices, "voice_clone")

    @Slot(str)
    def _on_voice_deleted(self, voice_id):
        self.lbl_status.setText(f"Specimen {voice_id} deleted.")
        self._refresh_list()

    @Slot(str)
    def _on_error(self, error_msg):
        if self.isVisible():
            self.lbl_status.setText(f"Error: {error_msg}")
            self.btn_clone.setEnabled(True)
            self._show_msg("Clone Failed", error_msg, QMessageBox.Critical)

    def _update_grid(self):
        while self.voices_grid.count():
            item = self.voices_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.voices_data:
            empty_lbl = QLabel("No cloned voices yet.")
            empty_lbl.setStyleSheet(f"color: {DarkColors.TEXT_MUTED}; font-size: 14px;")
            self.voices_grid.addWidget(empty_lbl, 0, 0)
            return

        columns = 3
        for idx, voice in enumerate(self.voices_data):
            row = idx // columns
            col = idx % columns
            card = VoiceCardV2(voice)
            card.play_preview.connect(self._play_voice_preview)
            card.delete_requested.connect(self._delete_voice)
            self.voices_grid.addWidget(card, row, col)

    def _play_voice_preview(self, voice_id):
        # Similar reuse of preview logic
        self.lbl_status.setText(f"Synthesizing preview for {voice_id}...")

        # Simplified for brevity - assumes same worker logic as VoiceDesign
        # ... worker launch code ...
        # For now, just a placeholder
        pass # To be fully implemented or shared

    def _delete_voice(self, voice_id):
        confirm = QMessageBox.question(self, "Confirm Deletion", f"Delete clone '{voice_id}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.api_client.delete_qwen_voice_async(voice_id, "voice_clone")

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
        pass
