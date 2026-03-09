"""
Voice Spirit Design System
Professional UI design constants and utilities
"""

# ============================================================
# SPACING SYSTEM (4px Grid)
# ============================================================
class Spacing:
    """4px grid-based spacing system"""
    XS = 4    # Extra small
    SM = 8    # Small
    MD = 12   # Medium
    LG = 16   # Large
    XL = 24   # Extra large
    XXL = 32  # Double extra large
    XXXL = 48 # Triple extra large


# ============================================================
# COLOR PALETTE
# ============================================================
class Colors:
    """Professional color palette with semantic naming"""

    # --- Primary Brand Colors (Refined Warm) ---
    PRIMARY = "#E66840"           # Slightly more vibrant Burnt Orange
    PRIMARY_HOVER = "#D45630"     # Darker on hover
    PRIMARY_ACTIVE = "#B84320"    # Even darker on press
    PRIMARY_LIGHT = "#FFF2EB"     # Lighter, cleaner tint
    PRIMARY_LIGHTER = "#FFFAF8"   # Very light tint

    # --- Neutral Grays (Modern Slate-Warm Scale) ---
    GRAY_50 = "#F9FAFB"           # Lightest
    GRAY_100 = "#F3F4F6"          # Light backgrounds
    GRAY_200 = "#E5E7EB"          # Borders
    GRAY_300 = "#D1D5DB"          # Stronger borders
    GRAY_400 = "#9CA3AF"          # Disabled
    GRAY_500 = "#6B7280"          # Placeholder
    GRAY_600 = "#4B5563"          # Secondary
    GRAY_700 = "#374151"          # Body
    GRAY_800 = "#1F2937"          # String
    GRAY_900 = "#111827"          # Headings

    # --- Background Colors ---
    BG_PRIMARY = "#FFFFFF"        # Main content
    BG_SECONDARY = "#F9FAFB"      # Secondary
    BG_TERTIARY = "#F3F4F6"       # Page bg
    BG_SIDEBAR = "#F7F8FA"        # Light Gray (MemoAI Style)
    BG_SIDEBAR_HOVER = "#E5E7EB"  # Gray-200
    BG_SIDEBAR_ACTIVE = "#E0E7FF" # Subtle Indigo/Blue tint for active state

    # --- Text Colors ---
    TEXT_PRIMARY = "#111827"      # Headings (Darker)
    TEXT_SECONDARY = "#374151"    # Body text
    TEXT_TERTIARY = "#6B7280"     # Secondary text
    TEXT_MUTED = "#9CA3AF"        # Muted text
    TEXT_DISABLED = "#D1D5DB"     # Disabled text
    TEXT_ON_PRIMARY = "#FFFFFF"   # Text on primary color
    TEXT_ON_DARK = "#111827"      # Text on Sidebar (Now Light) -> Dark
    TEXT_ON_DARK_MUTED = "#6B7280" # Muted text on Sidebar -> Gray-500

    # --- Border Colors ---
    BORDER_LIGHT = "#F3F4F6"      # Subtle borders
    BORDER_DEFAULT = "#E5E7EB"    # Standard Border
    BORDER_STRONG = "#D1D5DB"     # Strong borders

    # --- Semantic Colors ---
    SUCCESS = "#4CAF50"           # Success green
    SUCCESS_LIGHT = "#E8F5E9"     # Success background
    WARNING = "#FF9800"           # Warning orange
    WARNING_LIGHT = "#FFF3E0"     # Warning background
    ERROR = "#F44336"             # Error red
    ERROR_LIGHT = "#FFEBEE"       # Error background
    INFO = "#2196F3"              # Info blue
    INFO_LIGHT = "#E3F2FD"        # Info background

    # --- Special Colors ---
    OVERLAY = "rgba(0, 0, 0, 0.5)"  # Modal overlay
    SHADOW = "rgba(0, 0, 0, 0.08)"  # Shadow color


# ============================================================
# DARK THEME COLOR PALETTE (Voice Studio)
# ============================================================
class DarkColors:
    """Dark theme color palette for Voice Design/Clone studio"""

    # --- Background Colors (Deep Space) ---
    BG_PRIMARY = "#0D0D14"          # Deepest background
    BG_SECONDARY = "#12121A"        # Card backgrounds
    BG_TERTIARY = "#1A1A24"         # Elevated surfaces
    BG_ELEVATED = "#22222E"         # Hover states, inputs

    # --- Glass Effect Colors ---
    GLASS_BG = "rgba(255, 255, 255, 0.03)"       # Glass background
    GLASS_BG_HOVER = "rgba(255, 255, 255, 0.06)" # Glass hover
    GLASS_BORDER = "rgba(255, 255, 255, 0.08)"   # Glass border
    GLASS_BORDER_HOVER = "rgba(255, 255, 255, 0.15)"  # Glass border hover

    # --- Primary Brand (Warm Orange with Glow) ---
    PRIMARY = "#E66840"
    PRIMARY_HOVER = "#F07850"
    PRIMARY_ACTIVE = "#D45630"
    PRIMARY_GLOW = "rgba(230, 104, 64, 0.4)"
    PRIMARY_GLOW_SOFT = "rgba(230, 104, 64, 0.15)"

    # --- Accent Colors (Neon) ---
    ACCENT_CYAN = "#00F5D4"         # Waveform, success accents
    ACCENT_PURPLE = "#A855F7"       # Highlights, special states
    ACCENT_BLUE = "#3B82F6"         # Info, links
    ACCENT_PINK = "#EC4899"         # Clone/DNA theme

    # --- Neon Glows ---
    GLOW_CYAN = "rgba(0, 245, 212, 0.3)"
    GLOW_PURPLE = "rgba(168, 85, 247, 0.3)"
    GLOW_PINK = "rgba(236, 72, 153, 0.3)"

    # --- Text Colors (High Contrast) ---
    TEXT_PRIMARY = "#FFFFFF"        # Headings
    TEXT_SECONDARY = "#E5E5E5"      # Body text
    TEXT_TERTIARY = "#A0A0A0"       # Secondary info
    TEXT_MUTED = "#6B6B6B"          # Disabled, hints
    TEXT_ON_PRIMARY = "#FFFFFF"     # On primary button

    # --- Border Colors ---
    BORDER_SUBTLE = "rgba(255, 255, 255, 0.06)"
    BORDER_DEFAULT = "rgba(255, 255, 255, 0.1)"
    BORDER_STRONG = "rgba(255, 255, 255, 0.2)"
    BORDER_FOCUS = "#E66840"

    # --- Semantic Colors (Neon versions) ---
    SUCCESS = "#00FF88"
    SUCCESS_BG = "rgba(0, 255, 136, 0.1)"
    ERROR = "#FF4757"
    ERROR_BG = "rgba(255, 71, 87, 0.1)"
    WARNING = "#FFB347"
    WARNING_BG = "rgba(255, 179, 71, 0.1)"

    # --- Waveform Colors ---
    WAVEFORM_PRIMARY = "#00F5D4"
    WAVEFORM_SECONDARY = "#A855F7"
    WAVEFORM_GRADIENT_START = "#00F5D4"
    WAVEFORM_GRADIENT_END = "#A855F7"

    # --- Shadows (Colored) ---
    SHADOW_SM = "0 2px 8px rgba(0, 0, 0, 0.3)"
    SHADOW_MD = "0 4px 16px rgba(0, 0, 0, 0.4)"
    SHADOW_LG = "0 8px 32px rgba(0, 0, 0, 0.5)"
    SHADOW_GLOW_PRIMARY = "0 0 20px rgba(230, 104, 64, 0.3)"
    SHADOW_GLOW_CYAN = "0 0 20px rgba(0, 245, 212, 0.2)"


# ============================================================
# TYPOGRAPHY
# ============================================================
class Typography:
    """Typography system"""

    # Font families - Microsoft YaHei (not UI) for better CJK rendering, with Emoji font support
    FONT_FAMILY = "Microsoft YaHei, Segoe UI, Segoe UI Emoji, Segoe UI Symbol, Apple Color Emoji, Noto Color Emoji, sans-serif"
    FONT_FAMILY_MONO = "Consolas, Courier New, monospace"

    # Font sizes (in pixels) - ChatGPT/Claude standard: 16px body text baseline
    SIZE_XS = 12      # Extra small (minimum readable)
    SIZE_SM = 13      # Small captions
    SIZE_MD = 14      # Medium (UI labels)
    SIZE_LG = 16      # Large (Body text - primary)
    SIZE_XL = 20      # Extra large (Subheadings)
    SIZE_2XL = 26     # 2x large (Headings)
    SIZE_3XL = 32     # 3x large
    SIZE_4XL = 40     # 4x large (hero)

    # Font weights
    WEIGHT_NORMAL = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


# ============================================================
# BORDER RADIUS
# ============================================================
class Radius:
    """Consistent border radius values"""
    SM = 4       # Small elements
    MD = 8       # Default (buttons, inputs)
    LG = 12      # Cards, dialogs
    XL = 16      # Large cards
    XXL = 24     # Pill shapes
    FULL = 9999  # Circles


# ============================================================
# SHADOWS
# ============================================================
class Shadows:
    """Elevation shadow system"""

    # Subtle shadow for cards at rest
    SM = "0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06)"

    # Medium shadow for hover states
    MD = "0 4px 6px rgba(0, 0, 0, 0.07), 0 2px 4px rgba(0, 0, 0, 0.06)"

    # Large shadow for dropdowns, popovers
    LG = "0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)"

    # Extra large for modals
    XL = "0 20px 25px rgba(0, 0, 0, 0.15), 0 10px 10px rgba(0, 0, 0, 0.04)"

    # Inner shadow for inputs
    INNER = "inset 0 2px 4px rgba(0, 0, 0, 0.06)"

    # Glow effect for focus
    GLOW_PRIMARY = f"0 0 0 3px rgba(218, 119, 86, 0.2)"


# ============================================================
# TRANSITIONS
# ============================================================
class Transitions:
    """Animation timing"""
    FAST = "0.15s ease"
    NORMAL = "0.2s ease"
    SLOW = "0.3s ease"
    SPRING = "0.3s cubic-bezier(0.34, 1.56, 0.64, 1)"


# ============================================================
# Z-INDEX LAYERS
# ============================================================
class ZIndex:
    """Z-index layering system"""
    BASE = 0
    DROPDOWN = 100
    STICKY = 200
    FIXED = 300
    MODAL_BACKDROP = 400
    MODAL = 500
    POPOVER = 600
    TOOLTIP = 700


# ============================================================
# COMPONENT SIZES
# ============================================================
class ComponentSizes:
    """Standard component dimensions"""

    # Button heights
    BTN_SM = 28
    BTN_MD = 36
    BTN_LG = 44

    # Input heights
    INPUT_SM = 32
    INPUT_MD = 40
    INPUT_LG = 48

    # Icon sizes
    ICON_SM = 16
    ICON_MD = 20
    ICON_LG = 24
    ICON_XL = 32

    # Avatar sizes
    AVATAR_SM = 28
    AVATAR_MD = 36
    AVATAR_LG = 48
    AVATAR_XL = 64

    # Sidebar
    SIDEBAR_EXPANDED = 240
    SIDEBAR_COLLAPSED = 64


# ============================================================
# QSS STYLE HELPERS
# ============================================================
def get_button_primary_style():
    """Primary button QSS"""
    return f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: {Colors.TEXT_ON_PRIMARY};
            border: none;
            border-radius: {Radius.MD}px;
            padding: {Spacing.SM}px {Spacing.LG}px;
            font-size: {Typography.SIZE_MD}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QPushButton:hover {{
            background-color: {Colors.PRIMARY_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.PRIMARY_ACTIVE};
        }}
        QPushButton:disabled {{
            background-color: {Colors.GRAY_300};
            color: {Colors.GRAY_500};
        }}
    """

def get_button_secondary_style():
    """Secondary/outline button QSS"""
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: {Radius.MD}px;
            padding: {Spacing.SM}px {Spacing.LG}px;
            font-size: {Typography.SIZE_MD}px;
        }}
        QPushButton:hover {{
            background-color: {Colors.GRAY_100};
            border-color: {Colors.GRAY_400};
        }}
        QPushButton:pressed {{
            background-color: {Colors.GRAY_200};
        }}
    """

def get_button_ghost_style():
    """Ghost/text button QSS"""
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {Colors.TEXT_TERTIARY};
            border: none;
            border-radius: {Radius.MD}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
            font-size: {Typography.SIZE_MD}px;
        }}
        QPushButton:hover {{
            background-color: {Colors.GRAY_100};
            color: {Colors.TEXT_SECONDARY};
        }}
    """

def get_card_style(with_hover=False):
    """Card container QSS"""
    base = f"""
        QFrame {{
            background-color: {Colors.BG_PRIMARY};
            border: 1px solid {Colors.BORDER_LIGHT};
            border-radius: {Radius.LG}px;
        }}
    """
    if with_hover:
        base += f"""
        QFrame:hover {{
            border-color: {Colors.PRIMARY};
            background-color: {Colors.PRIMARY_LIGHTER};
        }}
        """
    return base

def get_input_style():
    """Text input QSS"""
    return f"""
        QLineEdit, QTextEdit {{
            background-color: {Colors.BG_PRIMARY};
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: {Radius.MD}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
            font-size: {Typography.SIZE_MD}px;
            selection-background-color: {Colors.PRIMARY};
            selection-color: {Colors.TEXT_ON_PRIMARY};
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {Colors.PRIMARY};
        }}
        QLineEdit:disabled, QTextEdit:disabled {{
            background-color: {Colors.GRAY_100};
            color: {Colors.TEXT_DISABLED};
        }}
    """

def get_scrollbar_style():
    """Modern scrollbar QSS"""
    return f"""
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {Colors.GRAY_300};
            min-height: 30px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {Colors.GRAY_400};
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
            height: 8px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {Colors.GRAY_300};
            min-width: 30px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {Colors.GRAY_400};
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
    """


# ============================================================
# DARK THEME QSS STYLE HELPERS (Voice Studio)
# ============================================================

def get_dark_glass_card_style(with_hover=True):
    """Glass card style for dark theme"""
    base = f"""
        QFrame {{
            background-color: {DarkColors.GLASS_BG};
            border: 1px solid {DarkColors.GLASS_BORDER};
            border-radius: {Radius.XL}px;
        }}
    """
    if with_hover:
        base += f"""
        QFrame:hover {{
            background-color: {DarkColors.GLASS_BG_HOVER};
            border-color: {DarkColors.GLASS_BORDER_HOVER};
        }}
        """
    return base


def get_dark_button_primary_style():
    """Primary button style for dark theme with glow"""
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {DarkColors.PRIMARY}, stop:1 #FF8E53);
            color: {DarkColors.TEXT_ON_PRIMARY};
            border: none;
            border-radius: {Radius.MD}px;
            padding: {Spacing.SM}px {Spacing.XL}px;
            font-size: {Typography.SIZE_MD}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {DarkColors.PRIMARY_HOVER}, stop:1 #FFA068);
        }}
        QPushButton:pressed {{
            background: {DarkColors.PRIMARY_ACTIVE};
        }}
        QPushButton:disabled {{
            background: {DarkColors.BG_ELEVATED};
            color: {DarkColors.TEXT_MUTED};
        }}
    """


def get_dark_button_secondary_style():
    """Secondary button style for dark theme"""
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {DarkColors.TEXT_SECONDARY};
            border: 1px solid {DarkColors.BORDER_DEFAULT};
            border-radius: {Radius.MD}px;
            padding: {Spacing.SM}px {Spacing.XL}px;
            font-size: {Typography.SIZE_MD}px;
        }}
        QPushButton:hover {{
            background-color: {DarkColors.GLASS_BG_HOVER};
            border-color: {DarkColors.PRIMARY};
            color: {DarkColors.PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: {DarkColors.BG_TERTIARY};
        }}
    """


def get_dark_input_style():
    """Input field style for dark theme"""
    return f"""
        QLineEdit, QTextEdit {{
            background-color: {DarkColors.BG_TERTIARY};
            color: {DarkColors.TEXT_SECONDARY};
            border: 1px solid {DarkColors.BORDER_DEFAULT};
            border-radius: {Radius.MD}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
            font-size: {Typography.SIZE_MD}px;
            selection-background-color: {DarkColors.PRIMARY};
            selection-color: {DarkColors.TEXT_ON_PRIMARY};
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {DarkColors.BORDER_FOCUS};
            background-color: {DarkColors.BG_ELEVATED};
        }}
        QLineEdit:disabled, QTextEdit:disabled {{
            background-color: {DarkColors.BG_SECONDARY};
            color: {DarkColors.TEXT_MUTED};
        }}
    """


def get_dark_scrollbar_style():
    """Scrollbar style for dark theme"""
    return f"""
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {DarkColors.BORDER_STRONG};
            min-height: 30px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {DarkColors.TEXT_MUTED};
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
            height: 8px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {DarkColors.BORDER_STRONG};
            min-width: 30px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {DarkColors.TEXT_MUTED};
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
    """


def get_dark_combo_style():
    """ComboBox style for dark theme"""
    return f"""
        QComboBox {{
            background-color: {DarkColors.BG_TERTIARY};
            border: 1px solid {DarkColors.BORDER_DEFAULT};
            border-radius: {Radius.MD}px;
            padding: 8px 14px;
            font-size: {Typography.SIZE_MD}px;
            color: {DarkColors.TEXT_SECONDARY};
        }}
        QComboBox:hover {{
            background-color: {DarkColors.BG_ELEVATED};
            border-color: {DarkColors.BORDER_STRONG};
        }}
        QComboBox:focus {{
            border-color: {DarkColors.BORDER_FOCUS};
        }}
        QComboBox::drop-down {{
            border: none;
            background: transparent;
            width: 32px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {DarkColors.BG_TERTIARY};
            border: 1px solid {DarkColors.BORDER_DEFAULT};
            border-radius: {Radius.LG}px;
            padding: {Spacing.XS}px;
            selection-background-color: {DarkColors.GLASS_BG_HOVER};
            selection-color: {DarkColors.PRIMARY};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: {Spacing.SM}px {Spacing.MD}px;
            border-radius: {Radius.SM}px;
            min-height: 28px;
            color: {DarkColors.TEXT_SECONDARY};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {DarkColors.GLASS_BG_HOVER};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {DarkColors.PRIMARY_GLOW_SOFT};
            color: {DarkColors.PRIMARY};
        }}
    """
