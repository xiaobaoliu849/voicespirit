from PySide6.QtWidgets import QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor

from app.ui.components.glass_panel import GlassCard
from app.ui.styles.design_system import DarkColors, Typography, Spacing, Radius

class StylePresetCard(GlassCard):
    """
    Compact card for selecting a voice style.
    """

    selected = Signal(str) # Emits style ID

    def __init__(self, style_id: str, label: str, icon: str = "🎙️", parent=None):
        super().__init__(parent=parent, radius=Radius.LG, hover_lift=True)
        self.style_id = style_id
        self.label_text = label
        self.icon_text = icon
        self._is_selected = False

        self.setFixedSize(100, 100) # Square card
        self.setCursor(Qt.PointingHandCursor)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(Spacing.SM)

        self.icon_label = QLabel(self.icon_text)
        self.icon_label.setStyleSheet("font-size: 32px; background: transparent;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        self.text_label = QLabel(self.label_text)
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet(f"""
            color: {DarkColors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_SM}px;
            font-weight: {Typography.WEIGHT_MEDIUM};
            background: transparent;
        """)
        layout.addWidget(self.text_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.style_id)
            self.set_selected(True)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self._is_selected = selected
        if selected:
            self.setStyleSheet(f"""
                QFrame#GlassCard {{
                    background-color: {DarkColors.GLASS_BG_HOVER};
                    border: 1px solid {DarkColors.PRIMARY};
                    border-radius: {self.radius}px;
                }}
            """)
            self.text_label.setStyleSheet(f"""
                color: {DarkColors.PRIMARY};
                font-size: {Typography.SIZE_SM}px;
                font-weight: {Typography.WEIGHT_BOLD};
                background: transparent;
            """)
            self.shadow.setColor(QColor(DarkColors.PRIMARY_GLOW))
            self.shadow.setBlurRadius(20)
        else:
            self.update_card_style(hover=False)
            self.text_label.setStyleSheet(f"""
                color: {DarkColors.TEXT_SECONDARY};
                font-size: {Typography.SIZE_SM}px;
                font-weight: {Typography.WEIGHT_MEDIUM};
                background: transparent;
            """)

