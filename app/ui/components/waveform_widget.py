from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPainter, QBrush, QColor, QLinearGradient, QPen
import random
import math

from app.ui.styles.design_system import DarkColors, Colors

class WaveformWidget(QWidget):
    """
    High-fidelity audio waveform visualization with neon glow and smooth physics-based animation.
    """

    def __init__(self, parent=None, bars=50):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setMinimumWidth(200)

        # Configuration
        self._bar_count = bars
        self._spacing = 3
        self._bar_width = 4 # Will be calculated dynamically if needed, but fixed preferred
        self._is_playing = False

        # Physics state
        # current_heights: The actual displayed height (0.0 to 1.0)
        # target_heights: The target height we want to reach
        self._current_heights = [0.1] * self._bar_count
        self._target_heights = [0.1] * self._bar_count

        # Animation loop
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_physics)
        self._timer.setInterval(16) # ~60 FPS

        # Start idle animation immediately
        self._timer.start()

        # Glow Effect
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(20)
        self._glow.setColor(QColor(DarkColors.WAVEFORM_PRIMARY))
        self._glow.setOffset(0, 0)
        self.setGraphicsEffect(self._glow)

        # Time accumulator for idle sine waves
        self._time = 0.0

    def set_playing(self, playing: bool):
        """Sets the playing state. If true, reacts energetically. If false, breathes."""
        self._is_playing = playing
        if playing:
            self._glow.setColor(QColor(DarkColors.WAVEFORM_PRIMARY))
            self._glow.setBlurRadius(25)
        else:
            self._glow.setColor(QColor(DarkColors.WAVEFORM_SECONDARY))
            self._glow.setBlurRadius(15)

    def _update_physics(self):
        """Update bar heights with smoothing"""
        self._time += 0.05

        # 1. Update Targets
        if self._is_playing:
            # Simulate audio data
            for i in range(self._bar_count):
                # Random energetic movement
                if random.random() > 0.5:
                    # Center bias for visual appeal (higher in middle)
                    center_bias = 1.0 - abs(i - self._bar_count / 2) / (self._bar_count / 2) * 0.3
                    self._target_heights[i] = random.uniform(0.3, 0.95) * center_bias
        else:
            # Idle breathing sine wave
            for i in range(self._bar_count):
                # Multiple sine waves for organic feel
                val = math.sin(self._time + i * 0.2) * 0.5 + 0.5 # 0..1
                val2 = math.sin(self._time * 0.5 - i * 0.1) * 0.5 + 0.5

                combined = (val * 0.7 + val2 * 0.3) * 0.3 + 0.1 # Keep it low (0.1 to 0.4)
                self._target_heights[i] = combined

        # 2. Apply Physics (Smoothing)
        for i in range(self._bar_count):
            curr = self._current_heights[i]
            target = self._target_heights[i]

            if target > curr:
                # Attack (rise fast)
                self._current_heights[i] = curr + (target - curr) * 0.3
            else:
                # Decay (fall slow)
                self._current_heights[i] = curr + (target - curr) * 0.1

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Calculate bar geometry
        # Try to fit bars in width
        total_spacing = (self._bar_count - 1) * self._spacing
        bar_w = (w - total_spacing) / self._bar_count

        # Clamp bar width
        bar_w = max(2, min(bar_w, 8))

        # Recalculate total width to center it
        actual_total_width = self._bar_count * bar_w + total_spacing
        start_x = (w - actual_total_width) / 2

        # Create Gradient
        gradient = QLinearGradient(0, h, 0, 0) # Bottom to Top
        if self._is_playing:
            gradient.setColorAt(0.0, QColor(DarkColors.WAVEFORM_SECONDARY).darker(150))
            gradient.setColorAt(0.5, QColor(DarkColors.WAVEFORM_GRADIENT_END))
            gradient.setColorAt(1.0, QColor(DarkColors.WAVEFORM_GRADIENT_START))
        else:
            # Subtle idle gradient
            gradient.setColorAt(0.0, QColor(DarkColors.BG_TERTIARY))
            gradient.setColorAt(1.0, QColor(DarkColors.TEXT_MUTED).darker(120))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)

        for i in range(self._bar_count):
            x = start_x + i * (bar_w + self._spacing)

            # Bar height
            bar_h = h * self._current_heights[i]

            # Center vertically
            y = (h - bar_h) / 2

            # Rounded rect
            radius = bar_w / 2
            painter.drawRoundedRect(x, y, bar_w, bar_h, radius, radius)

