from PySide6.QtWidgets import QLabel, QVBoxLayout, QPushButton, QFrame, QFileDialog
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor

from app.ui.styles.design_system import DarkColors, Typography, Spacing, Radius

class AudioDropZoneV2(QFrame):
    """
    Drag and drop zone for audio files with neon aesthetics.
    """

    file_dropped = Signal(str) # Emits file path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("AudioDropZone")
        self.setFixedHeight(180) # Generous height

        self._init_ui()
        self.set_default_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(Spacing.MD)

        # Icon
        self.icon_label = QLabel("🎵")
        self.icon_label.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(self.icon_label)

        # Main Text
        self.text_label = QLabel("Drag & Drop Audio File Here")
        self.text_label.setStyleSheet(f"""
            color: {DarkColors.TEXT_PRIMARY};
            font-size: {Typography.SIZE_LG}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
            background: transparent;
        """)
        layout.addWidget(self.text_label)

        # Subtext / Or
        self.sub_label = QLabel("Supports MP3, WAV, FLAC, M4A")
        self.sub_label.setStyleSheet(f"""
            color: {DarkColors.TEXT_MUTED};
            font-size: {Typography.SIZE_SM}px;
            background: transparent;
        """)
        layout.addWidget(self.sub_label)

        # Button
        self.select_btn = QPushButton("Select File")
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {DarkColors.TEXT_SECONDARY};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.XXL}px;
                padding: 8px 24px;
                font-size: {Typography.SIZE_MD}px;
            }}
            QPushButton:hover {{
                background-color: {DarkColors.PRIMARY};
                color: {DarkColors.TEXT_ON_PRIMARY};
                border-color: {DarkColors.PRIMARY};
            }}
        """)
        self.select_btn.clicked.connect(self._open_file_dialog)
        layout.addWidget(self.select_btn)

    def set_default_style(self):
        self.setStyleSheet(f"""
            QFrame#AudioDropZone {{
                background-color: {DarkColors.GLASS_BG};
                border: 2px dashed {DarkColors.BORDER_DEFAULT};
                border-radius: {Radius.XL}px;
            }}
        """)

    def set_active_style(self):
        self.setStyleSheet(f"""
            QFrame#AudioDropZone {{
                background-color: {DarkColors.GLASS_BG_HOVER};
                border: 2px dashed {DarkColors.PRIMARY};
                border-radius: {Radius.XL}px;
            }}
        """)

    def set_file_selected_style(self, filename: str):
        self.text_label.setText(filename)
        self.sub_label.setText("Ready to Clone")
        self.icon_label.setText("💿")
        self.setStyleSheet(f"""
            QFrame#AudioDropZone {{
                background-color: rgba(0, 245, 212, 0.05); /* Subtle Cyan tint */
                border: 2px solid {DarkColors.ACCENT_CYAN};
                border-radius: {Radius.XL}px;
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
                event.acceptProposedAction()
                self.set_active_style()
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.set_default_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self._handle_file(file_path)
            event.acceptProposedAction()

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio", "", "Audio Files (*.mp3 *.wav *.flac *.m4a)"
        )
        if file_path:
            self._handle_file(file_path)

    def _handle_file(self, file_path):
        import os
        filename = os.path.basename(file_path)
        self.set_file_selected_style(filename)
        self.file_dropped.emit(file_path)

