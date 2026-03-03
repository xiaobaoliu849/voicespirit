from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QMenu
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QCursor, QColor

from app.ui.components.glass_panel import GlassCard
from app.ui.styles.design_system import DarkColors, Typography, Spacing, Radius

class VoiceCardV2(GlassCard):
    """
    Modern glassmorphism voice card with playback and selection.
    """

    selected = Signal(str)      # Emits voice ID
    play_preview = Signal(str)  # Emits voice ID or preview URL
    delete_requested = Signal(str) # Emits voice ID

    def __init__(self, voice_data: dict, parent=None):
        super().__init__(parent=parent, radius=Radius.LG, hover_lift=True)
        self.voice_data = voice_data
        self.voice_id = voice_data.get('id') or voice_data.get('Name')
        self._is_selected = False

        self.setFixedHeight(80)
        self.setCursor(Qt.PointingHandCursor)

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.LG)

        # 1. Avatar / Icon
        # Differentiate by gender color
        gender = self.voice_data.get('Gender', 'Unknown')
        if gender == 'Male':
            avatar_color = DarkColors.ACCENT_CYAN
            avatar_char = "M"
        else:
            avatar_color = DarkColors.ACCENT_PINK
            avatar_char = "F"

        self.avatar = QLabel(avatar_char)
        self.avatar.setFixedSize(40, 40)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {QColor(avatar_color).name()};
                color: #000000;
                border-radius: 20px;
                font-weight: {Typography.WEIGHT_BOLD};
                font-size: 16px;
            }}
        """)
        # Add glow to avatar
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self.avatar)
        shadow.setColor(QColor(avatar_color))
        shadow.setBlurRadius(15)
        self.avatar.setGraphicsEffect(shadow)

        layout.addWidget(self.avatar)

        # 2. Info (Name + Description)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignVCenter)

        name = self.voice_data.get('ShortName') or self.voice_data.get('Name', 'Unknown')
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet(f"""
            color: {DarkColors.TEXT_PRIMARY};
            font-size: {Typography.SIZE_MD}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
            background: transparent;
            border: none;
        """)
        info_layout.addWidget(self.name_label)

        desc = f"{gender} • {self.voice_data.get('Locale', 'Unknown')}"
        style_list = self.voice_data.get('StyleList')
        if style_list:
            desc += f" • {len(style_list)} Styles"

        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet(f"""
            color: {DarkColors.TEXT_TERTIARY};
            font-size: {Typography.SIZE_XS}px;
            background: transparent;
            border: none;
        """)
        info_layout.addWidget(self.desc_label)

        layout.addLayout(info_layout, 1) # Stretch to fill

        # 3. Actions (Play, Delete) - Visible on hover or always?
        # Let's make Play always visible, Delete on hover (handled by logic or just always visible but subtle)

        # Play Button
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: {DarkColors.TEXT_PRIMARY};
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding-left: 2px;
            }}
            QPushButton:hover {{
                background-color: {DarkColors.PRIMARY};
                border-color: {DarkColors.PRIMARY};
            }}
        """)
        self.play_btn.clicked.connect(self._on_play_clicked)
        layout.addWidget(self.play_btn)

    def _on_play_clicked(self):
        self.play_preview.emit(self.voice_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Check if clicked on button (handled by button), otherwise select
            if not self.play_btn.underMouse():
                self.selected.emit(self.voice_id)
                self.set_selected(True)
        elif event.button() == Qt.RightButton:
            # Context menu for delete
            self._show_context_menu(event.globalPosition().toPoint())

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
            # Update glow
            self.shadow.setColor(QColor(DarkColors.PRIMARY_GLOW))
            self.shadow.setBlurRadius(30)
        else:
            # Revert to default glass style
            self.update_card_style(hover=False)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DarkColors.BG_ELEVATED};
                border: 1px solid {DarkColors.BORDER_DEFAULT};
                padding: 4px;
            }}
            QMenu::item {{
                color: {DarkColors.TEXT_PRIMARY};
                padding: 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {DarkColors.PRIMARY};
            }}
        """)

        delete_action = menu.addAction("Delete Voice")
        action = menu.exec(pos)

        if action == delete_action:
            self.delete_requested.emit(self.voice_id)

