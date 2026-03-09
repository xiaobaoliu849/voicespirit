import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QFileDialog, QMessageBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QClipboard, QGuiApplication

from app.ui.components.audio_drop_zone import AudioDropZoneV2
from app.ui.styles.design_system import Colors, DarkColors, Typography, Spacing, Radius

class TranscriptionPage(QWidget):
    """
    Transcription Center Workbench UI
    Supports local file drop, real API transcription hook, and text tools.
    """
    def __init__(self, api_client, translation_manager, config_manager, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.translation_manager = translation_manager
        self.config_manager = config_manager
        
        self.current_audio_path = None
        self.is_transcribing = False

        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        self.layout.setSpacing(Spacing.LG)
        self.setStyleSheet(f"background-color: {Colors.BG_PRIMARY};")

        # Header Title
        self.title_label = QLabel("转写中心 (Transcription Center)")
        self.title_label.setStyleSheet(f"""
            font-size: {Typography.SIZE_XL}px;
            font-weight: {Typography.WEIGHT_BOLD};
            color: {Colors.TEXT_PRIMARY};
        """)
        self.layout.addWidget(self.title_label)

        # Drop Zone Row
        self.drop_zone = AudioDropZoneV2(
            main_text="拖拽或选择要转写的音频",
            sub_text="支持 MP3, WAV, M4A",
            ready_sub_text="准备就绪",
            parent=self
        )
        self.layout.addWidget(self.drop_zone)

        # Status and Primary Action Row
        self.action_layout = QHBoxLayout()
        self.action_layout.setSpacing(Spacing.MD)

        self.status_label = QLabel("等待上传...")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self.action_layout.addWidget(self.status_label)

        self.action_layout.addStretch()

        self.transcribe_btn = QPushButton("开始转写")
        self.transcribe_btn.setCursor(Qt.PointingHandCursor)
        self.transcribe_btn.setFixedWidth(160)
        self.transcribe_btn.setFixedHeight(40)
        self.transcribe_btn.setEnabled(False) # Disabled until file picked
        self.transcribe_btn.setStyleSheet(self._primary_btn_style())
        self.action_layout.addWidget(self.transcribe_btn)
        
        self.layout.addLayout(self.action_layout)

        # Transcript Output Area
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("转写文本将在这里显示...")
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: {Spacing.MD}px;
                font-size: {Typography.SIZE_MD}px;
                color: {Colors.TEXT_PRIMARY};
                line-height: 1.6;
            }}
        """)
        self.layout.addWidget(self.text_area, 1) # Give it stretch

        # Utility Buttons Row
        self.utils_layout = QHBoxLayout()
        self.utils_layout.setSpacing(Spacing.SM)

        self.copy_btn = QPushButton("复制文本")
        self.copy_btn.setStyleSheet(self._secondary_btn_style())
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        
        self.export_btn = QPushButton("导出为 TXT")
        self.export_btn.setStyleSheet(self._secondary_btn_style())
        self.export_btn.setCursor(Qt.PointingHandCursor)

        self.utils_layout.addWidget(self.copy_btn)
        self.utils_layout.addWidget(self.export_btn)
        self.utils_layout.addStretch()

        self.layout.addLayout(self.utils_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet(f"background-color: {Colors.BORDER_LIGHT};")
        self.layout.addWidget(sep)

        # Reserved Future Actions Row
        reserved_lbl = QLabel("后续动作链：")
        reserved_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: {Typography.WEIGHT_SEMIBOLD};")
        self.layout.addWidget(reserved_lbl)

        self.reserved_layout = QHBoxLayout()
        self.reserved_layout.setSpacing(Spacing.MD)

        self.btn_send_chat = QPushButton("发送到聊天")
        self.btn_summary = QPushButton("生成摘要")
        self.btn_memory = QPushButton("提取到长期记忆")
        self.btn_podcast = QPushButton("生成播客脚本")

        for btn in [self.btn_send_chat, self.btn_summary, self.btn_memory, self.btn_podcast]:
            btn.setStyleSheet(self._outline_btn_style())
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(self._on_reserved_action_clicked)
            self.reserved_layout.addWidget(btn)

        self.reserved_layout.addStretch()
        self.layout.addLayout(self.reserved_layout)


    def _setup_connections(self):
        self.drop_zone.file_dropped.connect(self._on_file_selected)
        self.transcribe_btn.clicked.connect(self._on_transcribe_clicked)
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        self.export_btn.clicked.connect(self._on_export_clicked)

        # Connect API Client Signals
        self.api_client.transcription_finished.connect(self._on_transcription_success)
        # Re-use generic error handling for now unless we add a specific transcription error signal
        self.api_client.translation_error.connect(self._on_transcription_error) # Temporary override if transcription fails

    # --- Styles ---
    def _primary_btn_style(self):
        return f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: {Colors.TEXT_ON_PRIMARY};
                border: none;
                border-radius: {Radius.MD}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
            QPushButton:disabled {{ background-color: {Colors.GRAY_300}; color: {Colors.GRAY_500}; }}
        """

    def _secondary_btn_style(self):
         return f"""
            QPushButton {{
                background-color: {Colors.BG_SIDEBAR};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_SIDEBAR_HOVER}; }}
        """

    def _outline_btn_style(self):
         return f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.PRIMARY};
                border: 1px dashed {Colors.PRIMARY};
                border-radius: {Radius.MD}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
            }}
            QPushButton:hover {{ background-color: {Colors.PRIMARY_LIGHT}; }}
        """

    # --- Slots / Handlers ---
    def _on_file_selected(self, file_path: str):
        self.current_audio_path = file_path
        self.status_label.setText(f"File: {os.path.basename(file_path)}")
        self.transcribe_btn.setEnabled(True)

    def _on_transcribe_clicked(self):
        if not self.current_audio_path: return
        
        self.is_transcribing = True
        self.transcribe_btn.setEnabled(False)
        self.status_label.setText("🚀 转写中...请耐心等待 (Transcribing...)")
        self.status_label.setStyleSheet(f"color: {DarkColors.ACCENT_CYAN}; font-weight: bold;")
        self.text_area.clear()
        
        # Trigger the actual backend service
        self.api_client.start_transcription_request_async(self.current_audio_path)

    def _on_transcription_success(self, transcript: str):
        self.is_transcribing = False
        self.transcribe_btn.setEnabled(True)
        self.status_label.setText("✅ 转写完成 (Transcription Complete)")
        self.status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        self.text_area.setPlainText(transcript)

    def _on_transcription_error(self, error_msg: str):
        # We might catch translation errors here due to signal sharing, so check if we were transcribing
        if not self.is_transcribing: return 

        self.is_transcribing = False
        self.transcribe_btn.setEnabled(True)
        self.status_label.setText(f"❌ 转写失败: {error_msg}")
        self.status_label.setStyleSheet(f"color: {Colors.ERROR};")

    def _on_copy_clicked(self):
        text = self.text_area.toPlainText()
        if text:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(text)
            self.status_label.setText("已复制到剪贴板！")

    def _on_export_clicked(self):
        text = self.text_area.toPlainText()
        if not text: return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存转写结果", "transcript.txt", "Text Files (*.txt)"
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            self.status_label.setText(f"已导出到: {file_path}")

    def _on_reserved_action_clicked(self):
        QMessageBox.information(
            self,
            "Coming Soon",
            "该后续动作链功能即将开放，请期待后续版本！\n(This action will be available in a future update.)"
        )
