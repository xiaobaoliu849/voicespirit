from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFontMetrics
from app.core.config import get_resource_path

class SessionItemWidget(QWidget):
    delete_clicked = Signal()

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._full_title = title
        self.setFixedHeight(30)  # Compact height

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 2, 6, 2)
        self.layout.setSpacing(4)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: #374151;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 12px;
                font-weight: 400;
            }
        """)
        self.title_label.setMinimumHeight(22)
        self.layout.addWidget(self.title_label, 1)

        # Delete Button (Hidden by default)
        self.delete_btn = QPushButton()
        try:
            icon_path = get_resource_path("icons/trash-2.svg")
            self.delete_btn.setIcon(QIcon(icon_path))
        except:
            self.delete_btn.setText("×")

        self.delete_btn.setFixedSize(18, 18)
        self.delete_btn.setFlat(True)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #9CA3AF;
                font-size: 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.1);
                color: #EF4444;
            }
        """)
        self.delete_btn.setVisible(False)
        self.delete_btn.clicked.connect(self.delete_clicked)

        self.layout.addWidget(self.delete_btn)

        # Hover tracking
        self.setAttribute(Qt.WA_Hover)

    def resizeEvent(self, event):
        """Elide text when widget is resized"""
        super().resizeEvent(event)
        self._update_elided_text()
    
    def showEvent(self, event):
        """Elide text when widget is shown"""
        super().showEvent(event)
        self._update_elided_text()
    
    def _update_elided_text(self):
        """Update label with elided text based on available width"""
        fm = QFontMetrics(self.title_label.font())
        # Available width = label width minus some padding
        available_width = self.title_label.width() - 4
        if available_width > 20:
            elided = fm.elidedText(self._full_title, Qt.ElideRight, available_width)
            self.title_label.setText(elided)
        else:
            self.title_label.setText(self._full_title)

    def enterEvent(self, event):
        self.delete_btn.setVisible(True)
        self.title_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: #111827;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.delete_btn.setVisible(False)
        self.title_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: #374151;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 12px;
                font-weight: 400;
            }
        """)
        super().leaveEvent(event)
