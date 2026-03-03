"""
Animated Button Component
Provides hover effects with smooth scaling and shadow transitions
"""

from PySide6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve, Property, QParallelAnimationGroup,
    QSize, Qt
)
from PySide6.QtGui import QColor, QTransform
from app.ui.styles.design_system import Colors, Typography, Radius, Spacing


class AnimatedButton(QPushButton):
    """
    A QPushButton with smooth hover animations:
    - Scale effect (subtle zoom)
    - Shadow elevation change
    - Background color transition
    """

    def __init__(self, text="", parent=None, button_type="primary"):
        super().__init__(text, parent)
        self._scale = 1.0
        self._shadow_blur = 4
        self._button_type = button_type

        # Setup shadow effect
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(self._shadow_blur)
        self._shadow.setColor(QColor(0, 0, 0, 25))
        self._shadow.setOffset(0, 2)
        self.setGraphicsEffect(self._shadow)

        # Animation group for parallel animations
        self._animation_group = QParallelAnimationGroup(self)

        # Scale animation
        self._scale_anim = QPropertyAnimation(self, b"buttonScale", self)
        self._scale_anim.setDuration(150)
        self._scale_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Shadow animation
        self._shadow_anim = QPropertyAnimation(self, b"shadowBlur", self)
        self._shadow_anim.setDuration(150)
        self._shadow_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._animation_group.addAnimation(self._scale_anim)
        self._animation_group.addAnimation(self._shadow_anim)

        # Apply base style
        self._apply_style()

        # Store original size for scaling
        self._original_size = None

    def _apply_style(self):
        """Apply button style based on type"""
        if self._button_type == "primary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: {Colors.TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {Radius.MD}px;
                    padding: {Spacing.SM}px {Spacing.LG}px;
                    font-weight: {Typography.WEIGHT_SEMIBOLD};
                    font-size: {Typography.SIZE_MD}px;
                    min-height: 36px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {Colors.PRIMARY_ACTIVE};
                }}
                QPushButton:disabled {{
                    background-color: {Colors.GRAY_300};
                    color: {Colors.TEXT_DISABLED};
                }}
            """)
        elif self._button_type == "secondary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_SECONDARY};
                    border: 1px solid {Colors.BORDER_DEFAULT};
                    border-radius: {Radius.MD}px;
                    padding: {Spacing.SM}px {Spacing.LG}px;
                    font-size: {Typography.SIZE_MD}px;
                    min-height: 36px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.GRAY_100};
                    border-color: {Colors.GRAY_400};
                }}
                QPushButton:pressed {{
                    background-color: {Colors.GRAY_200};
                }}
            """)
        elif self._button_type == "ghost":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_TERTIARY};
                    border: none;
                    border-radius: {Radius.MD}px;
                    padding: {Spacing.SM}px {Spacing.MD}px;
                    font-size: {Typography.SIZE_MD}px;
                    min-height: 36px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.GRAY_100};
                    color: {Colors.TEXT_SECONDARY};
                }}
            """)

    # Scale property for animation
    def get_button_scale(self):
        return self._scale

    def set_button_scale(self, value):
        self._scale = value
        # Apply scale transform
        if self._original_size:
            new_width = int(self._original_size.width() * value)
            new_height = int(self._original_size.height() * value)
            # Center the scaled button
            self.setFixedSize(new_width, new_height)

    buttonScale = Property(float, get_button_scale, set_button_scale)

    # Shadow blur property for animation
    def get_shadow_blur(self):
        return self._shadow_blur

    def set_shadow_blur(self, value):
        self._shadow_blur = value
        self._shadow.setBlurRadius(value)
        # Adjust shadow opacity based on blur
        alpha = min(40, int(15 + value * 1.5))
        self._shadow.setColor(QColor(0, 0, 0, alpha))
        # Adjust offset based on blur
        self._shadow.setOffset(0, value / 4)

    shadowBlur = Property(float, get_shadow_blur, set_shadow_blur)

    def enterEvent(self, event):
        """Mouse enters - animate to hover state"""
        if self._original_size is None:
            self._original_size = self.size()

        self._animation_group.stop()

        # Scale up slightly (1.02x)
        self._scale_anim.setStartValue(self._scale)
        self._scale_anim.setEndValue(1.02)

        # Increase shadow
        self._shadow_anim.setStartValue(self._shadow_blur)
        self._shadow_anim.setEndValue(12)

        self._animation_group.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse leaves - animate back to normal"""
        self._animation_group.stop()

        # Scale back to normal
        self._scale_anim.setStartValue(self._scale)
        self._scale_anim.setEndValue(1.0)

        # Reduce shadow
        self._shadow_anim.setStartValue(self._shadow_blur)
        self._shadow_anim.setEndValue(4)

        self._animation_group.start()

        # Reset to original size when animation completes
        if self._original_size:
            self.setFixedSize(self._original_size)

        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Add press feedback"""
        if event.button() == Qt.LeftButton:
            # Quick scale down on press
            self._scale_anim.stop()
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(0.98)
            self._scale_anim.setDuration(50)
            self._scale_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Restore after press"""
        if event.button() == Qt.LeftButton:
            self._scale_anim.stop()
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(1.02 if self.underMouse() else 1.0)
            self._scale_anim.setDuration(100)
            self._scale_anim.start()
        super().mouseReleaseEvent(event)


class AnimatedIconButton(QPushButton):
    """
    Icon-only button with hover animation
    Simpler animation: just shadow and color change
    """

    def __init__(self, icon_text="", parent=None):
        super().__init__(icon_text, parent)
        self._shadow_blur = 0

        # Setup shadow effect
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        self._shadow.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow)

        # Shadow animation
        self._shadow_anim = QPropertyAnimation(self, b"shadowBlur", self)
        self._shadow_anim.setDuration(150)
        self._shadow_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_TERTIARY};
                border: none;
                border-radius: {Radius.MD}px;
                padding: {Spacing.SM}px;
                font-size: 18px;
                min-width: 36px;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {Colors.GRAY_100};
                color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:pressed {{
                background-color: {Colors.GRAY_200};
            }}
        """)

    def get_shadow_blur(self):
        return self._shadow_blur

    def set_shadow_blur(self, value):
        self._shadow_blur = value
        self._shadow.setBlurRadius(value)
        alpha = min(30, int(value * 2))
        self._shadow.setColor(QColor(0, 0, 0, alpha))
        self._shadow.setOffset(0, value / 6)

    shadowBlur = Property(float, get_shadow_blur, set_shadow_blur)

    def enterEvent(self, event):
        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow_blur)
        self._shadow_anim.setEndValue(8)
        self._shadow_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow_blur)
        self._shadow_anim.setEndValue(0)
        self._shadow_anim.start()
        super().leaveEvent(event)
