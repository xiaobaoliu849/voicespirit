"""
Professional Sidebar Component - Claude-style Design
Clean, minimal sidebar with professional icons and layout
"""
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QButtonGroup,
    QLabel, QListWidget, QListWidgetItem, QWidget,
    QMenu, QInputDialog, QMessageBox, QHBoxLayout,
    QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Signal, Qt, QSize, QPropertyAnimation, QEasingCurve, Property, QRectF
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QFont
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray
from app.core.database import DatabaseManager
from app.core.translation import TranslationManager
from app.ui.components.session_item import SessionItemWidget
from app.ui.styles.design_system import Colors, Spacing, Typography, Radius


class SvgIcon:
    """Professional SVG icons for sidebar navigation"""

    # Chat/Message icon
    CHAT = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""

    # Translate/Globe icon
    TRANSLATE = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 21a9 9 0 100-18 9 9 0 000 18z" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M3.6 9h16.8M3.6 15h16.8" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M12 3a15.3 15.3 0 014 9 15.3 15.3 0 01-4 9 15.3 15.3 0 01-4-9 15.3 15.3 0 014-9z" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""

    # Voice/Speaker icon
    VOICE = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M11 5L6 9H2v6h4l5 4V5z" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M15.54 8.46a5 5 0 010 7.07M19.07 4.93a10 10 0 010 14.14" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""

    # Podcast/Mic icon
    PODCAST = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""

    # Settings/Gear icon
    SETTINGS = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
    </svg>"""

    # Plus icon for new chat
    PLUS = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>"""

    # Menu/Hamburger icon
    MENU = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <line x1="3" y1="6" x2="21" y2="6" stroke-linecap="round"/>
        <line x1="3" y1="12" x2="21" y2="12" stroke-linecap="round"/>
        <line x1="3" y1="18" x2="21" y2="18" stroke-linecap="round"/>
    </svg>"""

    # Chevron left
    CHEVRON_LEFT = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="15 18 9 12 15 6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""

    # Chevron right
    CHEVRON_RIGHT = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="9 18 15 12 9 6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""

    # Trash icon
    TRASH = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <polyline points="3 6 5 6 21 6" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""


class IconButton(QPushButton):
    """Custom button that renders SVG icons with proper styling"""

    def __init__(self, svg_data: str, text: str = "", parent=None):
        super().__init__(text, parent)
        self.svg_data = svg_data
        self.icon_color = Colors.GRAY_500
        self.icon_size = 18  # Logical size
        # No need to call _update_icon here as we paint in paintEvent

    def set_icon_color(self, color: str):
        self.icon_color = color
        self.update() # Trigger repaint

    def set_icon_size(self, size: int):
        self.icon_size = size
        self.update() # Trigger repaint

    def paintEvent(self, event):
        # 1. Draw background/border (handled by stylesheet via base class)
        super().paintEvent(event)
        
        # 2. Draw SVG Icon directly
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Prepare colorized SVG
        svg_with_color = self.svg_data.replace('stroke="currentColor"', f'stroke="{self.icon_color}"')
        svg_with_color = svg_with_color.replace('fill="currentColor"', f'fill="{self.icon_color}"')
        
        # Render
        renderer = QSvgRenderer(QByteArray(svg_with_color.encode()))
        if renderer.isValid():
            # Center the icon
            icon_rect = QRectF(0, 0, self.icon_size, self.icon_size)
            icon_rect.moveCenter(self.rect().center().toPointF())
            renderer.render(qp, icon_rect)
        qp.end()


class NavButton(QPushButton):
    """Navigation button with icon and text - Claude style"""

    def __init__(self, svg_data: str, text: str, parent=None):
        super().__init__(parent)
        self.svg_data = svg_data
        self._text = text
        self._icon_size = 18  # Compact icon size
        self._is_collapsed = False

        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(34)  # Compact height
        
        # Set font programmatically for sharper rendering
        font = QFont("Microsoft YaHei")
        font.setPixelSize(13)  # Smaller font for compact sidebar
        font.setWeight(QFont.Medium)
        font.setHintingPreference(QFont.PreferFullHinting)
        self.setFont(font)

        self._setup_style()
        # Text is set via setText, so standard painting handles text
        self.setText(f"  {self._text}")

    def _setup_style(self):
        # Calculate padding to accommodate icon
        # Icon width (18) + Spacing (8) + Extra padding
        padding_left = int(self._icon_size + Spacing.SM * 2)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: {Radius.MD}px;
                padding-left: {padding_left}px;
                padding-right: {Spacing.SM}px;
                text-align: left;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: {Typography.SIZE_LG}px;
                font-weight: 500;
                color: {Colors.GRAY_600};
            }}
            QPushButton:hover {{
                background: {Colors.BG_SIDEBAR_HOVER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background: {Colors.PRIMARY_LIGHT};
                color: {Colors.PRIMARY};
            }}
            QPushButton:checked:hover {{
                background: {Colors.PRIMARY_LIGHT};
            }}
        """)

    def set_collapsed(self, collapsed: bool):
        self._is_collapsed = collapsed
        if collapsed:
            self.setFixedWidth(44)
            self.setText("")
            self.setToolTip(self._text)
            # Remove padding in collapsed mode so icon centers correctly
            # Actually, standard centering in paintEvent handles icon. 
            # But we need to reset stylesheet padding or text might look weird if empty?
            # Empty text doesn't show, so padding affects nothing relevant for text.
        else:
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setText(f"  {self._text}")
            self.setToolTip("")
        self.update()

    def set_text(self, text: str):
        self._text = text
        if not self._is_collapsed:
             self.setText(f"  {self._text}")

    def paintEvent(self, event):
        # 1. Draw background/border/text (handled by stylesheet via base class)
        super().paintEvent(event)
        
        # 2. Draw SVG Icon directly
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Determine color
        icon_color = Colors.PRIMARY if self.isChecked() else Colors.GRAY_500
        
        # Prepare colorized SVG
        svg_with_color = self.svg_data.replace('stroke="currentColor"', f'stroke="{icon_color}"')
        svg_with_color = svg_with_color.replace('fill="currentColor"', f'fill="{icon_color}"') # Handle fill too if needed

        renderer = QSvgRenderer(QByteArray(svg_with_color.encode()))
        
        if renderer.isValid():
            icon_rect = QRectF(0, 0, self._icon_size, self._icon_size)
            
            if self._is_collapsed:
                # Center in button - use integer positions for sharp rendering
                x = int((self.width() - self._icon_size) / 2)
                y = int((self.height() - self._icon_size) / 2)
                icon_rect.moveTo(x, y)
            else:
                # Left aligned with spacing - integer positions
                left_pos = int(Spacing.SM)
                y_pos = int((self.height() - self._icon_size) / 2)
                icon_rect.moveTo(left_pos, y_pos)
                
            renderer.render(qp, icon_rect)
        qp.end()

    def nextCheckState(self):
        # Update icon color when check state changes
        super().nextCheckState()
        self.update() # Trigger repaint


class Sidebar(QFrame):
    page_changed = Signal(int)
    new_chat_clicked = Signal()
    session_selected = Signal(int)
    session_deleted = Signal(int)

    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 60

    def __init__(self, translation_manager=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._width = self.EXPANDED_WIDTH
        self.setFixedWidth(self._width)
        self._is_collapsed = False
        self.db_manager = DatabaseManager()
        self.translation_manager = translation_manager or TranslationManager()

        if self.translation_manager:
            self.translation_manager.language_changed.connect(self.update_ui_text)

        self._setup_ui()
        self._setup_styles()
        self.refresh_history()

    def _setup_ui(self):
        """Setup the sidebar UI layout"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(Spacing.SM, Spacing.MD, Spacing.SM, Spacing.MD)
        self.layout.setSpacing(Spacing.XS)

        # === TOP SECTION ===
        self._setup_top_section()

        # === NAVIGATION SECTION ===
        self._setup_navigation()

        # === RECENTS/HISTORY SECTION ===
        self._setup_history_section()

        # === BOTTOM SECTION (Settings) ===
        self._setup_bottom_section()

    def _setup_top_section(self):
        """Top section: Toggle button + New Chat button"""
        self.top_container = QWidget()
        self.top_layout = QHBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(Spacing.SM)

        # Toggle/Menu button
        self.btn_toggle = IconButton(SvgIcon.MENU)
        self.btn_toggle.setObjectName("ToggleBtn")
        self.btn_toggle.setFixedSize(36, 36)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: {Radius.MD}px;
            }}
            QPushButton:hover {{
                background: {Colors.BG_SIDEBAR_HOVER};
            }}
        """)
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        self.top_layout.addWidget(self.btn_toggle)

        # New Chat button
        self.btn_new_chat = QPushButton(self.translation_manager.t('sidebar_new_chat'))
        self.btn_new_chat.setFixedHeight(36)
        self.btn_new_chat.setCursor(Qt.PointingHandCursor)
        self.btn_new_chat.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: {Colors.TEXT_ON_PRIMARY};
                border: none;
                border-radius: {Radius.MD}px;
                padding: 0 {Spacing.MD}px;
                font-family: "Microsoft YaHei", sans-serif;
                font-weight: 600;
                font-size: {Typography.SIZE_MD}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY_ACTIVE};
            }}
        """)
        self.btn_new_chat.clicked.connect(self.new_chat_clicked)
        self.top_layout.addWidget(self.btn_new_chat, 1)

        self.layout.addWidget(self.top_container)
        self.layout.addSpacing(Spacing.LG)

    def _setup_navigation(self):
        """Navigation buttons section"""
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.btn_group.buttonClicked.connect(self._on_nav_clicked)

        self.nav_buttons = {}

        # Icon mapping for navigation - using SVG icons
        self.nav_icons = {
            "chat_tab": SvgIcon.CHAT,
            "translate_tab": SvgIcon.TRANSLATE,
            "tts_tab": SvgIcon.VOICE,
            "audio_overview_tab": SvgIcon.PODCAST,
        }

        # Add navigation buttons (Settings will be at bottom)
        self._add_nav_button(0, "chat_tab", "Chat")
        self._add_nav_button(1, "translate_tab", "Translate")
        self._add_nav_button(2, "tts_tab", "Voice")
        self._add_nav_button(3, "audio_overview_tab", "Podcast")

        self.layout.addSpacing(Spacing.MD)

    def _add_nav_button(self, index: int, key: str, default_text: str):
        """Add a navigation button"""
        text = self.translation_manager.t(key)
        if text == key:
            text = default_text

        svg_icon = self.nav_icons.get(key, SvgIcon.CHAT)
        btn = NavButton(svg_icon, text)
        btn.setProperty("pageIndex", index)

        if index == 0:
            btn.setChecked(True)

        self.layout.addWidget(btn)
        self.btn_group.addButton(btn)
        self.nav_buttons[key] = btn

    def _setup_history_section(self):
        """Recents/History section"""
        # Section header
        recents_header = QHBoxLayout()
        recents_header.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)

        self.recent_label = QLabel(self.translation_manager.t("sidebar_recents"))
        self.recent_label.setStyleSheet(f"""
            font-family: "Microsoft YaHei", sans-serif;
            font-size: {Typography.SIZE_SM}px;
            font-weight: 600;
            color: {Colors.TEXT_MUTED};
            letter-spacing: 0.5px;
            text-transform: uppercase;
        """)
        recents_header.addWidget(self.recent_label)
        recents_header.addStretch()

        self.btn_clear_all = QPushButton(self.translation_manager.t("sidebar_clear_all"))
        self.btn_clear_all.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_MUTED};
                font-family: "Microsoft YaHei", sans-serif;
                font-size: {Typography.SIZE_SM}px;
                border: none;
                padding: 2px {Spacing.SM}px;
                border-radius: {Radius.SM}px;
            }}
            QPushButton:hover {{
                background: rgba(0,0,0,0.05);
                color: {Colors.ERROR};
            }}
        """)
        self.btn_clear_all.setCursor(Qt.PointingHandCursor)
        self.btn_clear_all.clicked.connect(self._on_clear_all_clicked)
        recents_header.addWidget(self.btn_clear_all)

        self.recents_container = QWidget()
        self.recents_container.setLayout(recents_header)
        self.layout.addWidget(self.recents_container)

        # History list
        self.history_list = QListWidget()
        self.history_list.setFrameShape(QFrame.NoFrame)
        self.history_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                outline: none;
                border: none;
            }}
            QListWidget::item {{
                border-radius: {Radius.MD}px;
                padding: 0;
                margin: 1px 0;
                min-height: 36px;
            }}
            QListWidget::item:hover {{
                background: {Colors.BG_SIDEBAR_HOVER};
            }}
            QListWidget::item:selected {{
                background: {Colors.PRIMARY_LIGHT};
            }}
        """)
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.history_list.setSpacing(2)
        self.history_list.setUniformItemSizes(True)  # Optimize for uniform height
        self.history_list.itemClicked.connect(self._on_history_clicked)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_context_menu)
        self.layout.addWidget(self.history_list, 1)  # stretch=1 to fill available space

        # Collapsed mode clear button
        self.btn_collapsed_clear = IconButton(SvgIcon.TRASH)
        self.btn_collapsed_clear.setFixedSize(44, 44)
        self.btn_collapsed_clear.setCursor(Qt.PointingHandCursor)
        self.btn_collapsed_clear.setToolTip(self.translation_manager.t("sidebar_clear_all"))
        self.btn_collapsed_clear.clicked.connect(self._on_clear_all_clicked)
        self.btn_collapsed_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: {Radius.MD}px;
            }}
            QPushButton:hover {{
                background: {Colors.BG_SIDEBAR_HOVER};
            }}
        """)
        self.layout.addWidget(self.btn_collapsed_clear, 0, Qt.AlignCenter)
        self.btn_collapsed_clear.hide()

        # Spacer for collapsed mode
        self.bottom_filler = QWidget()
        self.bottom_filler.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addWidget(self.bottom_filler)
        self.bottom_filler.hide()

    def _setup_bottom_section(self):
        """Bottom section with Settings button"""
        # Separator line
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setStyleSheet(f"background: {Colors.BORDER_LIGHT}; max-height: 1px;")
        self.layout.addWidget(self.separator)
        self.layout.addSpacing(Spacing.SM)

        # Settings button at the bottom
        self.btn_settings = NavButton(SvgIcon.SETTINGS, self.translation_manager.t("settings_tab"))
        self.btn_settings.setProperty("pageIndex", 4)
        self.btn_settings.clicked.connect(lambda: self._on_settings_clicked())
        self.layout.addWidget(self.btn_settings)
        self.btn_group.addButton(self.btn_settings)
        self.nav_buttons["settings_tab"] = self.btn_settings

        self.layout.addSpacing(Spacing.SM)

    def _on_settings_clicked(self):
        """Handle settings button click"""
        self.page_changed.emit(4)

    def _setup_styles(self):
        """Setup sidebar styles"""
        self.setStyleSheet(f"""
            #Sidebar {{
                background-color: {Colors.BG_SIDEBAR};
                border-right: 1px solid {Colors.BORDER_LIGHT};
            }}
        """)

    def _on_clear_all_clicked(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.translation_manager.t("clear_history_title"))
        msg_box.setText(self.translation_manager.t("clear_history_confirm"))
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #FFFFFF;
                color: #333333;
            }
            QLabel {
                color: #333333;
                background-color: transparent;
            }
            QPushButton {
                background-color: #E66840;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #D45630;
            }
        """)
        confirm = msg_box.exec()
        if confirm == QMessageBox.Yes:
            self.db_manager.clear_all_history()
            self.refresh_history()
            self.new_chat_clicked.emit()

    def _show_context_menu(self, position):
        item = self.history_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radius.MD}px;
                padding: {Spacing.XS}px;
            }}
            QMenu::item {{
                padding: {Spacing.SM}px {Spacing.MD}px;
                border-radius: {Radius.SM}px;
            }}
            QMenu::item:selected {{
                background: {Colors.BG_SIDEBAR_HOVER};
            }}
        """)

        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        action = menu.exec(self.history_list.mapToGlobal(position))

        if action == rename_action:
            self._rename_session(item)
        elif action == delete_action:
            session_id = item.data(Qt.UserRole)
            self._delete_session(session_id)

    def _rename_session(self, item):
        session_id = item.data(Qt.UserRole)
        current_title = ""
        widget = self.history_list.itemWidget(item)
        if widget:
            current_title = widget.title_label.text()

        new_title, ok = QInputDialog.getText(self, "Rename Chat", "New Title:", text=current_title)
        if ok and new_title:
            self.db_manager.update_session_title(session_id, new_title)
            self.refresh_history()

    def _delete_session(self, session_id):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Delete Chat")
        msg_box.setText("Are you sure you want to delete this chat?")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #FFFFFF;
                color: #333333;
            }
            QLabel {
                color: #333333;
                background-color: transparent;
            }
            QPushButton {
                background-color: #E66840;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #D45630;
            }
        """)
        confirm = msg_box.exec()
        if confirm == QMessageBox.Yes:
            self.db_manager.delete_session(session_id)
            self.refresh_history()
            self.session_deleted.emit(session_id)

    def _on_nav_clicked(self, btn):
        index = btn.property("pageIndex")
        if index is not None:
            self.page_changed.emit(int(index))
            # Update all button icons
            for key, nav_btn in self.nav_buttons.items():
                if isinstance(nav_btn, NavButton):
                    nav_btn.update()

    def _on_history_clicked(self, item):
        session_id = item.data(Qt.UserRole)
        if session_id:
            self.session_selected.emit(session_id)

    def refresh_history(self):
        """Reload history list from database"""
        self.history_list.clear()
        sessions = self.db_manager.get_sessions(limit=20)
        for sess_id, title, _ in sessions:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, sess_id)

            widget = SessionItemWidget(title)
            widget.delete_clicked.connect(lambda s=sess_id: self._delete_session(s))

            # Set proper size hint - width should adapt to list width
            item.setSizeHint(QSize(self.history_list.viewport().width() or 180, 36))

            self.history_list.addItem(item)
            self.history_list.setItemWidget(item, widget)

    def update_ui_text(self, language):
        """Update UI text when language changes"""
        self.btn_new_chat.setText(self.translation_manager.t("sidebar_new_chat"))
        self.recent_label.setText(self.translation_manager.t("sidebar_recents"))
        self.btn_clear_all.setText(self.translation_manager.t("sidebar_clear_all"))

        # Update nav buttons text
        for key, btn in self.nav_buttons.items():
            text = self.translation_manager.t(key)
            if isinstance(btn, NavButton):
                btn.set_text(text)

    # ========== Collapse/Expand functionality ==========
    def get_sidebar_width(self):
        return self._width

    def set_sidebar_width(self, width):
        self._width = width
        self.setFixedWidth(int(width))

    sidebar_width = Property(int, get_sidebar_width, set_sidebar_width)

    def toggle_collapse(self):
        """Toggle sidebar collapse state"""
        self._is_collapsed = not self._is_collapsed

        target_width = self.COLLAPSED_WIDTH if self._is_collapsed else self.EXPANDED_WIDTH

        self.animation = QPropertyAnimation(self, b"sidebar_width")
        self.animation.setDuration(200)
        self.animation.setStartValue(self._width)
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self._on_animation_finished)
        self.animation.start()

    def _on_animation_finished(self):
        """Update UI after animation completes"""
        if self._is_collapsed:
            # Collapsed state
            self.layout.setContentsMargins(Spacing.XS, Spacing.MD, Spacing.XS, Spacing.MD)

            # Change top layout to vertical
            # Remove widgets from horizontal layout
            self.top_layout.removeWidget(self.btn_toggle)
            self.top_layout.removeWidget(self.btn_new_chat)

            # Create vertical layout for collapsed state
            self.top_layout.setDirection(QHBoxLayout.TopToBottom)

            # Re-add widgets vertically aligned
            self.btn_toggle.setFixedSize(40, 40)
            self.top_layout.addWidget(self.btn_toggle)

            # Hide new chat text, show + icon only
            self.btn_new_chat.setText("+")
            self.btn_new_chat.setFixedSize(40, 40)
            self.btn_new_chat.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: {Colors.TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
            """)
            self.top_layout.addWidget(self.btn_new_chat)

            # Hide history and separator
            self.recents_container.hide()
            self.history_list.hide()
            self.separator.hide()
            self.bottom_filler.show()
            self.btn_collapsed_clear.show()

            # Collapse nav buttons
            for key, btn in self.nav_buttons.items():
                if isinstance(btn, NavButton):
                    btn.set_collapsed(True)

        else:
            # Expanded state
            self.layout.setContentsMargins(Spacing.SM, Spacing.MD, Spacing.SM, Spacing.MD)

            # Remove widgets and restore horizontal layout
            self.top_layout.removeWidget(self.btn_toggle)
            self.top_layout.removeWidget(self.btn_new_chat)

            self.top_layout.setDirection(QHBoxLayout.LeftToRight)

            # Re-add widgets horizontally
            self.btn_toggle.setFixedSize(36, 36)
            self.top_layout.addWidget(self.btn_toggle)

            # Restore new chat button
            self.btn_new_chat.setText(self.translation_manager.t("sidebar_new_chat"))
            self.btn_new_chat.setFixedHeight(36)
            self.btn_new_chat.setMinimumWidth(0)
            self.btn_new_chat.setMaximumWidth(16777215)
            self.btn_new_chat.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: {Colors.TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {Radius.MD}px;
                    padding: 0 {Spacing.MD}px;
                    font-weight: 600;
                    font-size: {Typography.SIZE_MD}px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {Colors.PRIMARY_ACTIVE};
                }}
            """)
            self.top_layout.addWidget(self.btn_new_chat, 1)

            # Show history and separator
            self.recents_container.show()
            self.history_list.show()
            self.separator.show()
            self.bottom_filler.hide()
            self.btn_collapsed_clear.hide()

            # Expand nav buttons
            for key, btn in self.nav_buttons.items():
                if isinstance(btn, NavButton):
                    btn.set_collapsed(False)

    @property
    def is_collapsed(self):
        return self._is_collapsed
