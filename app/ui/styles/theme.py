from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from app.ui.styles.design_system import Colors, Typography, Spacing, Radius, Shadows, Transitions

def apply_theme(app: QApplication):
    """Applies the professional global QSS theme to the application."""

    # Set global font with proper size
    font = QFont(Typography.FONT_FAMILY.split(',')[0], Typography.SIZE_MD)
    # REMOVED: font.setStyleStrategy(QFont.PreferAntialias) - Use system subpixel rendering
    app.setFont(font)

    # Load Professional QSS
    qss = f"""
    /* ============================================================
       GLOBAL RESET & BASE STYLES
       ============================================================ */
    * {{
        outline: none;
    }}

    QWidget {{
        background-color: {Colors.BG_PRIMARY};
        color: {Colors.TEXT_SECONDARY};
        font-family: {Typography.FONT_FAMILY};
    }}

    /* FORCE LIGHT PALETTE FOR DIALOGS AND MESSAGE BOXES */
    QDialog, QMessageBox {{
        background-color: #FFFFFF;
        color: {Colors.TEXT_SECONDARY};
    }}

    QMessageBox QLabel {{
        color: {Colors.TEXT_SECONDARY};
        background-color: transparent;
    }}

    /* Force button styles within message boxes */
    QMessageBox QPushButton {{
        background-color: {Colors.PRIMARY};
        color: {Colors.TEXT_ON_PRIMARY};
        border: none;
        border-radius: {Radius.MD}px;
        padding: 6px 16px;
        min-width: 80px;
    }}

    QMessageBox QPushButton:hover {{
        background-color: {Colors.PRIMARY_HOVER};
    }}
    /* ============================================================
       LIGHT SIDEBAR - Professional Look
       ============================================================ */
    QFrame#Sidebar {{
        background-color: {Colors.BG_SIDEBAR};
        border-right: 1px solid {Colors.BORDER_LIGHT}; /* Subtle separator */
    }}

    /* Sidebar Buttons - Clean Light Theme */
    QPushButton[class="SidebarBtn"] {{
        background-color: transparent;
        color: {Colors.TEXT_SECONDARY};
        border: none;
        text-align: left;
        padding: 6px 10px;
        font-size: 12px;
        border-radius: 5px;
        margin: 1px 4px;
    }}
    QPushButton[class="SidebarBtn"]:hover {{
        background-color: {Colors.BG_SIDEBAR_HOVER};
        color: {Colors.TEXT_PRIMARY};
    }}
    QPushButton[class="SidebarBtn"]:checked {{
        background-color: {Colors.BG_SIDEBAR_ACTIVE};
        color: {Colors.PRIMARY};
        font-weight: {Typography.WEIGHT_SEMIBOLD};
    }}

    /* Sidebar Buttons - Collapsed State (Icon Only) */
    QPushButton[class="SidebarBtnCollapsed"] {{
        background-color: transparent;
        color: {Colors.TEXT_SECONDARY};
        border: none;
        text-align: center;
        padding: 0px;
        font-size: 18px;
        border-radius: 8px;
        margin: 4px 0px;
        min-width: 44px;
        max-width: 44px;
        min-height: 44px;
        max-height: 44px;
    }}
    QPushButton[class="SidebarBtnCollapsed"]:hover {{
        background-color: {Colors.BG_SIDEBAR_HOVER};
        color: {Colors.TEXT_PRIMARY};
    }}
    QPushButton[class="SidebarBtnCollapsed"]:checked {{
        background-color: {Colors.BG_SIDEBAR_ACTIVE};
        color: {Colors.PRIMARY}; 
    }}

    /* Sidebar History List Items */
    QListWidget {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        color: {Colors.TEXT_SECONDARY};
        padding: 4px 8px; /* Reduced padding */
        border-radius: {Radius.MD}px;
        margin: 0px {Spacing.SM}px;
        font-size: 12px; /* Smaller font for history */
    }}
    QListWidget::item:hover {{
        background: {Colors.BG_SIDEBAR_HOVER};
        color: {Colors.TEXT_PRIMARY};
    }}
    QListWidget::item:selected {{
        background: {Colors.BG_SIDEBAR_ACTIVE};
        color: {Colors.PRIMARY};
        font-weight: {Typography.WEIGHT_MEDIUM};
    }}

    /* ============================================================
       CONTENT AREA
       ============================================================ */
    QStackedWidget {{
        background-color: {Colors.BG_TERTIARY};
    }}

    /* ============================================================
       SCROLLBARS - Modern Minimal Style
       ============================================================ */
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: #D1D5DB; /* GRAY_300 equivalent */
        min-height: 40px;
        border-radius: 5px;
        border: 2px solid transparent; /* Creates padding effect */
        background-clip: content-box;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #9CA3AF; /* GRAY_400 */
        border: 2px solid transparent;
        background-clip: content-box;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        border: none;
        background: transparent;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: #D1D5DB;
        min-width: 40px;
        border-radius: 5px;
        border: 2px solid transparent;
        background-clip: content-box;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: #9CA3AF;
        border: 2px solid transparent;
        background-clip: content-box;
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: none;
    }}

    /* ============================================================
       FLOATING INPUT CARD (Chat Input)
       ============================================================ */
    QFrame[class="InputCard"] {{
        background-color: {Colors.BG_PRIMARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: {Radius.XXL}px;
    }}

    /* Chat Input Text Area */
    QTextEdit[class="ChatInput"] {{
        background-color: transparent;
        border: none;
        color: {Colors.TEXT_SECONDARY};
        font-size: {Typography.SIZE_MD}px;
        padding: {Spacing.SM}px {Spacing.LG}px;
        selection-background-color: {Colors.PRIMARY};
        selection-color: {Colors.TEXT_ON_PRIMARY};
    }}

    /* ============================================================
       BUTTONS - Professional Button System
       ============================================================ */

    /* Primary Action Button */
    QPushButton[class="PrimaryBtn"] {{
        background-color: {Colors.PRIMARY};
        color: {Colors.TEXT_ON_PRIMARY};
        border: none;
        border-radius: {Radius.MD}px;
        padding: {Spacing.SM}px {Spacing.LG}px;
        font-weight: {Typography.WEIGHT_SEMIBOLD};
        font-size: {Typography.SIZE_MD}px;
    }}
    QPushButton[class="PrimaryBtn"]:hover {{
        background-color: {Colors.PRIMARY_HOVER};
    }}
    QPushButton[class="PrimaryBtn"]:pressed {{
        background-color: {Colors.PRIMARY_ACTIVE};
    }}
    QPushButton[class="PrimaryBtn"]:disabled {{
        background-color: {Colors.GRAY_300};
        color: {Colors.TEXT_DISABLED};
    }}

    /* Secondary Button */
    QPushButton[class="SecondaryBtn"] {{
        background-color: transparent;
        color: {Colors.TEXT_SECONDARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: {Radius.MD}px;
        padding: {Spacing.SM}px {Spacing.LG}px;
        font-size: {Typography.SIZE_MD}px;
    }}
    QPushButton[class="SecondaryBtn"]:hover {{
        background-color: {Colors.GRAY_100};
        border-color: {Colors.GRAY_400};
    }}
    QPushButton[class="SecondaryBtn"]:pressed {{
        background-color: {Colors.GRAY_200};
    }}

    /* Ghost Button */
    QPushButton[class="GhostBtn"] {{
        background-color: transparent;
        color: {Colors.TEXT_TERTIARY};
        border: none;
        border-radius: {Radius.MD}px;
        padding: {Spacing.SM}px {Spacing.MD}px;
        font-size: {Typography.SIZE_MD}px;
    }}
    QPushButton[class="GhostBtn"]:hover {{
        background-color: {Colors.GRAY_100};
        color: {Colors.TEXT_SECONDARY};
    }}

    /* ============================================================
       DROPDOWNS / COMBO BOXES - Claude Style
       ============================================================ */
    QComboBox {{
        background-color: {Colors.BG_SECONDARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: {Radius.MD}px;
        padding: 6px 14px;
        min-width: 100px;
        font-size: {Typography.SIZE_MD}px;
        color: {Colors.TEXT_SECONDARY};
    }}
    QComboBox:hover {{
        background-color: {Colors.GRAY_100};
        border-color: {Colors.BORDER_STRONG};
    }}
    QComboBox:focus {{
        background-color: {Colors.BG_PRIMARY};
        border-color: {Colors.PRIMARY};
    }}
    QComboBox::drop-down {{
        border: none;
        background: transparent;
        width: 32px;
    }}
    QComboBox::down-arrow {{
        image: url("d:/voicespirit/icons/chevron-down.svg");
        width: 14px;
        height: 14px;
    }}
    QComboBox[editable="true"] {{
        padding-right: 0px;
    }}
    QComboBox[editable="true"] QLineEdit {{
        border: none;
        background: transparent;
        padding-left: 14px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {Colors.BG_PRIMARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: {Radius.LG}px;
        padding: {Spacing.XS}px;
        selection-background-color: {Colors.GRAY_100};
        selection-color: {Colors.PRIMARY};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        padding: {Spacing.SM}px {Spacing.MD}px;
        border-radius: {Radius.SM}px;
        min-height: 28px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {Colors.GRAY_100};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: {Colors.PRIMARY_LIGHT};
        color: {Colors.TEXT_SECONDARY};
    }}

    /* ============================================================
       TEXT INPUTS
       ============================================================ */
    QLineEdit, QTextEdit {{
        background-color: {Colors.BG_PRIMARY};
        color: {Colors.TEXT_SECONDARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: {Radius.MD}px;
        padding: 8px 12px; /* Increased padding */
        font-size: {Typography.SIZE_MD}px;
        selection-background-color: {Colors.PRIMARY};
        selection-color: {Colors.TEXT_ON_PRIMARY};
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border: 1px solid {Colors.PRIMARY};
        background-color: #FFFFFF;
    }}
    QLineEdit:disabled, QTextEdit:disabled {{
        background-color: {Colors.GRAY_100};
        color: {Colors.TEXT_DISABLED};
        border-color: {Colors.GRAY_200};
    }}

    /* ============================================================
       MESSAGE BUBBLES
       ============================================================ */
    QFrame[class="UserBubble"], QFrame[class="BotBubble"] {{
        border-radius: {Radius.LG}px;
        padding: {Spacing.SM}px;
    }}

    /* ============================================================
       TOOLTIP
       ============================================================ */
    QToolTip {{
        border: 1px solid {Colors.BORDER_DEFAULT};
        background-color: {Colors.BG_PRIMARY};
        color: {Colors.TEXT_SECONDARY};
        padding: {Spacing.SM}px {Spacing.MD}px;
        border-radius: {Radius.SM}px;
        font-size: {Typography.SIZE_SM}px;
    }}

    /* ============================================================
       MENU / CONTEXT MENU
       ============================================================ */
    QMenu {{
        background-color: {Colors.BG_PRIMARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: {Radius.MD}px;
        padding: {Spacing.XS}px;
    }}
    QMenu::item {{
        padding: {Spacing.SM}px {Spacing.LG}px;
        border-radius: {Radius.SM}px;
        color: {Colors.TEXT_SECONDARY};
    }}
    QMenu::item:selected {{
        background-color: {Colors.PRIMARY_LIGHT};
        color: {Colors.TEXT_SECONDARY};
    }}
    QMenu::separator {{
        height: 1px;
        background: {Colors.BORDER_LIGHT};
        margin: {Spacing.XS}px {Spacing.MD}px;
    }}

    /* ============================================================
       GROUP BOX
       ============================================================ */
    QGroupBox {{
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: {Radius.MD}px;
        margin-top: {Spacing.LG}px;
        padding-top: {Spacing.MD}px;
        font-weight: {Typography.WEIGHT_SEMIBOLD};
        color: {Colors.TEXT_PRIMARY};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: {Spacing.MD}px;
        padding: 0 {Spacing.SM}px;
        background-color: {Colors.BG_PRIMARY};
    }}

    /* ============================================================
       PROGRESS BAR
       ============================================================ */
    QProgressBar {{
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: {Radius.SM}px;
        background-color: {Colors.GRAY_100};
        text-align: center;
        color: {Colors.TEXT_SECONDARY};
        font-size: {Typography.SIZE_SM}px;
        height: 20px;
    }}
    QProgressBar::chunk {{
        background-color: {Colors.PRIMARY};
        border-radius: {Radius.SM}px;
    }}

    /* ============================================================
       TAB WIDGET
       ============================================================ */
    /* ============================================================
       TAB WIDGET - Modern Pill Style
       ============================================================ */
    QTabWidget::pane {{
        border: none;
        background-color: transparent;
        top: 0px;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {Colors.TEXT_TERTIARY};
        border: none;
        padding: 8px 16px;
        margin-right: 4px;
        border-radius: 6px;
        font-size: {Typography.SIZE_MD}px;
        font-weight: {Typography.WEIGHT_MEDIUM};
    }}
    QTabBar::tab:hover {{
        background-color: rgba(0, 0, 0, 0.04); /* Subtler hover */
        color: {Colors.TEXT_SECONDARY};
    }}
    QTabBar::tab:selected {{
        background-color: #FFFFFF; /* White pill */
        color: {Colors.PRIMARY};
        font-weight: {Typography.WEIGHT_SEMIBOLD};
        border: 1px solid {Colors.BORDER_LIGHT};
        /* Add subtle shadow if possible, otherwise rely on contrast */
    }}

    /* ============================================================
       LABELS - Typography Hierarchy
       ============================================================ */
    QLabel[class="Title"] {{
        font-size: {Typography.SIZE_2XL}px;
        font-weight: {Typography.WEIGHT_BOLD};
        color: {Colors.TEXT_PRIMARY};
    }}
    QLabel[class="Heading"] {{
        font-size: {Typography.SIZE_LG}px;
        font-weight: {Typography.WEIGHT_SEMIBOLD};
        color: {Colors.TEXT_PRIMARY};
    }}
    QLabel[class="Body"] {{
        font-size: {Typography.SIZE_MD}px;
        color: {Colors.TEXT_SECONDARY};
    }}
    QLabel[class="Caption"] {{
        font-size: {Typography.SIZE_SM}px;
        color: {Colors.TEXT_MUTED};
    }}

    /* ============================================================
       MESSAGE BOX - Dialog Style
       ============================================================ */
    QMessageBox {{
        background-color: {Colors.BG_PRIMARY};
        color: {Colors.TEXT_SECONDARY};
    }}
    QMessageBox QLabel {{
        color: {Colors.TEXT_SECONDARY};
        font-size: {Typography.SIZE_MD}px;
    }}
    QMessageBox QPushButton {{
        background-color: {Colors.PRIMARY};
        color: {Colors.TEXT_ON_PRIMARY};
        border: none;
        border-radius: {Radius.MD}px;
        padding: {Spacing.SM}px {Spacing.LG}px;
        font-weight: {Typography.WEIGHT_SEMIBOLD};
        font-size: {Typography.SIZE_MD}px;
        min-width: 80px;
    }}
    QMessageBox QPushButton:hover {{
        background-color: {Colors.PRIMARY_HOVER};
    }}
    QMessageBox QPushButton:pressed {{
        background-color: {Colors.PRIMARY_ACTIVE};
    }}
    """
    app.setStyleSheet(qss)
