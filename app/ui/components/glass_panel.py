from PySide6.QtWidgets import QFrame, QVBoxLayout, QGraphicsDropShadowEffect, QWidget
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QEvent, QPoint
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QLinearGradient

from app.ui.styles.design_system import DarkColors, Radius, Spacing, Shadows, Colors

class GlassPanel(QFrame):
    """
    A container with a glassmorphism look (semi-transparent dark background, subtle border).
    """
    def __init__(self, parent=None, radius=Radius.XL, blur_radius=0):
        super().__init__(parent)
        self.radius = radius
        self.setObjectName("GlassPanel")

        # Default Glass Style
        self.bg_color = DarkColors.GLASS_BG
        self.border_color = DarkColors.GLASS_BORDER
        self.border_width = 1

        # Setup Layout (Optional, can be used as container)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        self.main_layout.setSpacing(Spacing.MD)

        # Apply Style
        self.update_style()

        # Optional: Add shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)

    def update_style(self):
        """Updates the stylesheet based on current properties."""
        self.setStyleSheet(f"""
            QFrame#GlassPanel {{
                background-color: {self.bg_color};
                border: {self.border_width}px solid {self.border_color};
                border-radius: {self.radius}px;
            }}
        """)

    def set_content_layout(self, layout):
        """Replaces the default layout with a custom one."""
        # Remove old layout
        if self.layout():
            QWidget().setLayout(self.layout()) # Parenting trick to delete old layout
        self.setLayout(layout)
        self.main_layout = layout


class GlassCard(GlassPanel):
    """
    A GlassPanel that is interactive (hover effects, clickable).
    """
    def __init__(self, parent=None, radius=Radius.XL, hover_lift=True):
        super().__init__(parent, radius)
        self.hover_lift = hover_lift
        self.setObjectName("GlassCard")
        self.setCursor(Qt.PointingHandCursor)

        # Colors
        self.default_bg = DarkColors.GLASS_BG
        self.hover_bg = DarkColors.GLASS_BG_HOVER
        self.default_border = DarkColors.GLASS_BORDER
        self.hover_border = DarkColors.GLASS_BORDER_HOVER
        self.active_border = DarkColors.PRIMARY

        # Animation
        self._animation = QPropertyAnimation(self, b"pos") # Placeholder, usually easier to animate stylesheet or internal properties

        # Apply initial style
        self.update_card_style(hover=False)

    def enterEvent(self, event):
        self.update_card_style(hover=True)
        if self.hover_lift:
             # Lift effect could be done by margin manipulation or translation if parent layout allows
             pass
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_card_style(hover=False)
        super().leaveEvent(event)

    def update_card_style(self, hover=False):
        bg = self.hover_bg if hover else self.default_bg
        border = self.hover_border if hover else self.default_border

        # Add glow effect on hover if desired (via shadow color change)
        if hover:
            self.shadow.setColor(QColor(DarkColors.PRIMARY_GLOW_SOFT)) # Subtle primary glow
            self.shadow.setBlurRadius(25)
        else:
            self.shadow.setColor(QColor(0, 0, 0, 80))
            self.shadow.setBlurRadius(20)

        self.setStyleSheet(f"""
            QFrame#GlassCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {self.radius}px;
            }}
        """)

    def mousePressEvent(self, event):
        """Visual feedback on press"""
        self.setStyleSheet(f"""
            QFrame#GlassCard {{
                background-color: {self.hover_bg};
                border: 1px solid {self.active_border};
                border-radius: {self.radius}px;
            }}
        """)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.update_card_style(hover=True) # Return to hover state
        super().mouseReleaseEvent(event)
