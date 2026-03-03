import math
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QPainter, QPainterPath, QColor, QLinearGradient, QBrush, QFont
from app.ui.styles.design_system import Typography, Colors

class WaveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_wave)
        self.timer.start(16) # ~60 FPS
        self.wave_color = QColor(232, 135, 81, 100)  # Semi-transparent orange (Claude style)
        self.wave_color2 = QColor(207, 107, 52, 100)  # Deeper orange

    def update_wave(self):
        self.offset += 0.05
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Transparent BG
        painter.fillRect(self.rect(), Qt.transparent)
        
        # Draw two overlapping waves for "sea" effect
        self.draw_wave(painter, width, height, 20, 0.02, self.offset, self.wave_color)
        self.draw_wave(painter, width, height, 25, 0.015, self.offset + 2, self.wave_color2)

    def draw_wave(self, painter, width, height, amplitude, frequency, phase, color):
        path = QPainterPath()
        path.moveTo(0, height)
        path.lineTo(0, height / 2)
        
        for x in range(0, width + 1, 5):
            y = height / 2 + amplitude * math.sin(frequency * x + phase)
            path.lineTo(x, y)
            
        path.lineTo(width, height)
        path.lineTo(0, height)
        path.closeSubpath()
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 400)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main Container with rounded corners - Using design system colors
        self.container = QWidget()
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
                border-radius: 20px;
                border: 1px solid {Colors.BORDER_DEFAULT};
            }}
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 50, 0, 0)
        
        # 1. Logo / Text - Using design system typography
        self.logo_label = QLabel("Voice Spirit")
        # Use first font from family, with 4XL size for hero text
        primary_font = Typography.FONT_FAMILY.split(',')[0].strip()
        font = QFont(primary_font, Typography.SIZE_4XL, QFont.Bold)
        self.logo_label.setFont(font)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none;")

        self.sub_label = QLabel("AI Professional Assistant")
        sub_font = QFont(primary_font, Typography.SIZE_MD, Typography.WEIGHT_MEDIUM)
        self.sub_label.setFont(sub_font)
        self.sub_label.setAlignment(Qt.AlignCenter)
        self.sub_label.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; background: transparent; border: none; margin-top: 5px;")
        
        container_layout.addWidget(self.logo_label)
        container_layout.addWidget(self.sub_label)
        container_layout.addStretch()
        
        # 2. Wave Animation at bottom
        self.wave = WaveWidget()
        self.wave.setFixedHeight(150)
        # Fix styling override issues for custom widget inside stylesheet-styled parent
        self.wave.setAttribute(Qt.WA_StyledBackground, False) 
        self.wave.setStyleSheet("background: transparent; border: none; border-bottom-left-radius: 20px; border-bottom-right-radius: 20px;")
        
        container_layout.addWidget(self.wave)
        
        layout.addWidget(self.container)
        
        # Fade In Animation
        self.setWindowOpacity(0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(1000)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

    def finish(self, main_window):
        self.main_window = main_window
        # Fade out
        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(800)
        self.anim_out.setStartValue(1)
        self.anim_out.setEndValue(0)
        self.anim_out.finished.connect(self.close_and_show)
        self.anim_out.start()
        
    def close_and_show(self):
        self.close()
        self.main_window.show()
        # Fade main window in?
        # main_window.setWindowOpacity(0)
        # ... logic for main window fade in if desired
