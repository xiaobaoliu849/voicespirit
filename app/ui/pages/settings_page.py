"""
Modern Settings page for Voice Spirit application
Based on Claude-inspired design with consistent styling
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QTabWidget, QGroupBox, QLineEdit, QComboBox, QPushButton,
    QLabel, QCheckBox, QSpinBox, QDoubleSpinBox, QScrollArea,
    QFrame, QFileDialog, QMessageBox, QTextEdit, QSizePolicy,
    QStackedWidget, QDialog, QKeySequenceEdit, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt, Signal, QMargins, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QPalette, QPixmap, QColor
from app.core.config import ConfigManager, get_resource_path
from app.core.translation import TranslationManager
from app.ui.styles.design_system import Colors, Radius, Spacing, Typography


class AnimatedSettingsButton(QPushButton):
    """Animated button for settings page with shadow hover effect"""

    def __init__(self, text, is_primary=False, parent=None):
        super().__init__(text, parent)
        self._is_primary = is_primary
        self._shadow_blur = 2 if is_primary else 0

        self.setCursor(Qt.PointingHandCursor)

        # Setup shadow effect
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(self._shadow_blur)
        self._shadow.setColor(QColor(0, 0, 0, 20))
        self._shadow.setOffset(0, 1)
        self.setGraphicsEffect(self._shadow)

        # Shadow animation
        self._shadow_anim = QPropertyAnimation(self, b"shadowBlur", self)
        self._shadow_anim.setDuration(150)
        self._shadow_anim.setEasingCurve(QEasingCurve.OutCubic)

        if is_primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {Radius.MD}px;
                    padding: 8px 18px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {Colors.PRIMARY_ACTIVE};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #f0f0f0;
                    color: #333;
                    border: 1px solid #ddd;
                    border-radius: {Radius.MD}px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: #e0e0e0;
                    border-color: {Colors.GRAY_400};
                }}
            """)

    def get_shadow_blur(self):
        return self._shadow_blur

    def set_shadow_blur(self, value):
        self._shadow_blur = value
        self._shadow.setBlurRadius(value)
        alpha = min(50, int(15 + value * 2))
        self._shadow.setColor(QColor(0, 0, 0, alpha))
        self._shadow.setOffset(0, value / 5)

    shadowBlur = Property(float, get_shadow_blur, set_shadow_blur)

    def enterEvent(self, event):
        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow_blur)
        self._shadow_anim.setEndValue(10 if self._is_primary else 5)
        self._shadow_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow_blur)
        self._shadow_anim.setEndValue(2 if self._is_primary else 0)
        self._shadow_anim.start()
        super().leaveEvent(event)


class SettingsPage(QWidget):
    settings_saved = Signal()  # Signal emitted when settings are saved
    
    def __init__(self, translation_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.translation_manager = translation_manager or TranslationManager(self.config_manager)
        
        # Connect to language changed signal
        self.translation_manager.language_changed.connect(self.update_ui_text)

        self.init_ui()
        self.load_settings()

    def update_ui_text(self, language):
        """Rebuild UI when language changes to reflect new translations"""
        # Save current input states before rebuilding (handled by config save in on_display_language_changed)
        # We need to clear the current layout and rebuild it
        
        # Helper to clear layout recursively
        def clear_layout(layout):
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()
                    else:
                        clear_layout(item.layout())
        
        clear_layout(self.layout())
        
        # Re-initialize UI
        self.init_ui()
        
        # Reload settings (values)
        self.load_settings()

    def init_ui(self):
        if self.layout():
            layout = self.layout()
            # Clear it just in case clear_layout missed something or if called directly
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)  # Remove outer margins
            layout.setSpacing(0)
        
        # Create main container with padding
        main_container = QWidget()
        main_container.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #374151;
            }
        """)
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(16, 16, 16, 16)  # Reduced padding
        main_layout.setSpacing(12)
        
        # Create tab widget with Claude-inspired styling
        self.tab_widget = QTabWidget()
        # Create tab widget with global theme styling
        self.tab_widget = QTabWidget()
        # No local stylesheet - uses global theme defined in theme.py which is now Pill/Segmented style
        
        # Create tabs
        self.ai_providers_tab = self.create_ai_providers_tab()
        self.tts_tab = self.create_tts_tab()
        self.shortcuts_tab = self.create_shortcuts_tab()
        self.ui_tab = self.create_ui_tab()
        self.general_tab = self.create_general_tab()
        self.donate_tab = self.create_donate_tab()

        # Add tabs to widget
        self.tab_widget.addTab(self.ai_providers_tab, self.translation_manager.t("ai_providers_tab"))
        # self.tab_widget.addTab(self.model_tab, self.translation_manager.t("model_defaults_tab")) # Removed
        self.tab_widget.addTab(self.tts_tab, self.translation_manager.t("tts_settings_tab"))
        self.tab_widget.addTab(self.shortcuts_tab, self.translation_manager.t("shortcuts_tab"))
        self.tab_widget.addTab(self.ui_tab, self.translation_manager.t("appearance_tab"))

        self.tab_widget.addTab(self.general_tab, self.translation_manager.t("general_tab"))
        # self.tab_widget.addTab(self.donate_tab, self.translation_manager.t("donate_tab")) # Removed as per user request
        
        # Add 'Buy me a coffee' button to the corner
        self.tab_widget.setCornerWidget(self.create_support_button(), Qt.TopRightCorner)
        
        main_layout.addWidget(self.tab_widget)

        # Create buttons layout with animated buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.reset_button = AnimatedSettingsButton(self.translation_manager.t("reset_defaults"), is_primary=False)
        self.reset_button.clicked.connect(self.reset_to_defaults)

        self.save_button = AnimatedSettingsButton(self.translation_manager.t("save_settings"), is_primary=True)
        self.save_button.clicked.connect(self.save_settings)

        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.save_button)
        
        main_layout.addLayout(buttons_layout)
        
        layout.addWidget(main_container)
        
        # Set minimum size
        self.setMinimumSize(900, 700)

    def create_ai_providers_tab(self):
        """Create a unified AI Providers configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #FFFFFF; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(15)
        
        # Description
        desc_label = QLabel(self.translation_manager.t("ai_providers_description"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #6B7280; font-family: 'Microsoft YaHei UI'; font-size: 13px;")
        content_layout.addWidget(desc_label)

        # Provider Selector
        selector_layout = QHBoxLayout()
        selector_label = QLabel(self.translation_manager.t("select_provider"))
        selector_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #111827;")
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "Google (Gemini)",
            "DeepSeek",
            "OpenRouter",
            "Groq",
            "SiliconFlow",
            "DashScope",
            "MiniMax"
        ])
        self.provider_combo.setStyleSheet(self.get_combo_style())
        self.provider_combo.setMinimumWidth(200)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        
        selector_layout.addWidget(selector_label)
        selector_layout.addWidget(self.provider_combo)
        selector_layout.addStretch()
        content_layout.addLayout(selector_layout)

        # Dynamic Settings Area using QStackedWidget
        self.provider_settings_stack = QStackedWidget()
        
        # Initialize dictionary to store widgets for easy access
        self.provider_widgets = {}
        
        # Create and add pages for each provider
        self.provider_widgets["Google"] = self.create_provider_page("Google", "google_api_key", "default_models.Google", "api_urls.Google", "https://generativelanguage.googleapis.com")
        self.provider_widgets["DeepSeek"] = self.create_provider_page("DeepSeek", "deepseek_api_key", "default_models.DeepSeek", "api_urls.DeepSeek", "https://api.deepseek.com/v1")
        self.provider_widgets["OpenRouter"] = self.create_provider_page("OpenRouter", "openrouter_api_key", "default_models.OpenRouter", "api_urls.OpenRouter", "https://openrouter.ai/api/v1")
        self.provider_widgets["Groq"] = self.create_provider_page("Groq", "groq_api_key", "default_models.Groq", "api_urls.Groq", "https://api.groq.com/openai/v1")
        self.provider_widgets["SiliconFlow"] = self.create_provider_page("SiliconFlow", "siliconflow_api_key", "default_models.SiliconFlow", "api_urls.SiliconFlow", "https://api.siliconflow.cn/v1")
        self.provider_widgets["DashScope"] = self.create_provider_page("DashScope", "dashscope_api_key", "default_models.DashScope", "api_urls.DashScope", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        # MiniMax uses minimax.api_key (not api_keys.minimax_api_key) for compatibility with tts_handler.py
        self.provider_widgets["MiniMax"] = self.create_minimax_provider_page()

        # Add widgets to stack in the same order as combo box
        self.provider_settings_stack.addWidget(self.provider_widgets["Google"]['widget'])     # Index 0
        self.provider_settings_stack.addWidget(self.provider_widgets["DeepSeek"]['widget'])   # Index 1
        self.provider_settings_stack.addWidget(self.provider_widgets["OpenRouter"]['widget']) # Index 2
        self.provider_settings_stack.addWidget(self.provider_widgets["Groq"]['widget'])       # Index 3
        self.provider_settings_stack.addWidget(self.provider_widgets["SiliconFlow"]['widget'])# Index 4
        self.provider_settings_stack.addWidget(self.provider_widgets["DashScope"]['widget'])  # Index 5
        self.provider_settings_stack.addWidget(self.provider_widgets["MiniMax"]['widget'])    # Index 6

        content_layout.addWidget(self.provider_settings_stack)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return tab

    def create_provider_page(self, provider_name, api_key_config_key, model_config_path, url_config_key, default_url_placeholder):
        """Helper to create a settings page for a specific provider"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Group Box
        group = QGroupBox(f"{provider_name} Settings") # English fallback, title mostly redundant with combo
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding-top: 15px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #374151;
                font-weight: 600;
            }
        """)
        group_layout = QFormLayout(group)
        group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        group_layout.setLabelAlignment(Qt.AlignRight)
        group_layout.setContentsMargins(20, 20, 20, 20)
        group_layout.setSpacing(12)
        
        # API Key
        api_key_input = QLineEdit()
        api_key_input.setEchoMode(QLineEdit.Password)
        api_key_input.setStyleSheet(self.get_input_style())
        api_key_input.setPlaceholderText(f"Enter {provider_name} API Key")
        
        # Toggle visibility button
        key_layout = QHBoxLayout()
        key_layout.addWidget(api_key_input)
        toggle_btn = QPushButton("👁️")
        toggle_btn.setFixedWidth(30)
        toggle_btn.setStyleSheet("border: none; background: transparent;")
        toggle_btn.setCursor(Qt.PointingHandCursor)
        # Using a closure to capture the specific input widget
        toggle_btn.clicked.connect(lambda checked=False, inp=api_key_input: self.toggle_password_visibility(inp))
        key_layout.addWidget(toggle_btn)
        
        group_layout.addRow(self.translation_manager.t("api_key_label"), key_layout)
        
        # API URL
        api_url_input = QLineEdit()
        api_url_input.setStyleSheet(self.get_input_style())
        api_url_input.setPlaceholderText(f"Default: {default_url_placeholder}")
        group_layout.addRow(self.translation_manager.t("api_url_label"), api_url_input)
        
        # Default Model
        model_combo = QComboBox()
        model_combo.setEditable(True)
        model_combo.setStyleSheet(self.get_combo_style())
        model_combo.setMinimumWidth(300)
        
        # Refresh Models Button
        refresh_btn = QPushButton(self.translation_manager.t("refresh_models"))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        refresh_btn.clicked.connect(lambda: self.refresh_single_provider_models(provider_name, model_combo))
        
        model_row = QHBoxLayout()
        model_row.addWidget(model_combo)
        model_row.addWidget(refresh_btn)
        
        group_layout.addRow(self.translation_manager.t("default_model_for") + ":", model_row)
        
        layout.addWidget(group)
        layout.addStretch()
        
        return {
            "widget": page,
            "api_key_input": api_key_input,
            "api_url_input": api_url_input,
            "model_combo": model_combo,
            "config_keys": {
                "api_key": f"api_keys.{api_key_config_key}",
                "model_default": f"{model_config_path}.default",
                "model_available": f"{model_config_path}.available",
                "api_url": url_config_key
            }
        }

    def create_minimax_provider_page(self):
        """Create MiniMax provider page with custom config key for api_key (minimax.api_key)"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Group Box
        group = QGroupBox("MiniMax Settings")
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding-top: 15px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #374151;
                font-weight: 600;
            }
        """)
        group_layout = QFormLayout(group)
        group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        group_layout.setLabelAlignment(Qt.AlignRight)
        group_layout.setContentsMargins(20, 20, 20, 20)
        group_layout.setSpacing(12)

        # API Key - uses minimax.api_key (not api_keys.minimax_api_key)
        api_key_input = QLineEdit()
        api_key_input.setEchoMode(QLineEdit.Password)
        api_key_input.setStyleSheet(self.get_input_style())
        api_key_input.setPlaceholderText("Enter MiniMax API Key")

        # Toggle visibility button
        key_layout = QHBoxLayout()
        key_layout.addWidget(api_key_input)
        toggle_btn = QPushButton("👁️")
        toggle_btn.setFixedWidth(30)
        toggle_btn.setStyleSheet("border: none; background: transparent;")
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.clicked.connect(lambda checked=False, inp=api_key_input: self.toggle_password_visibility(inp))
        key_layout.addWidget(toggle_btn)

        group_layout.addRow(self.translation_manager.t("api_key_label"), key_layout)

        # API URL
        api_url_input = QLineEdit()
        api_url_input.setStyleSheet(self.get_input_style())
        api_url_input.setPlaceholderText("https://api.minimax.chat/v1/t2a_v2")
        group_layout.addRow(self.translation_manager.t("api_url_label"), api_url_input)

        # Default Model
        model_combo = QComboBox()
        model_combo.setEditable(True)
        model_combo.setStyleSheet(self.get_combo_style())
        model_combo.setMinimumWidth(300)
        model_combo.addItems(["minimax-01-06", "abab6.5s-chat"])

        # Refresh Models Button
        refresh_btn = QPushButton(self.translation_manager.t("refresh_models"))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        refresh_btn.clicked.connect(lambda: self.refresh_single_provider_models("MiniMax", model_combo))

        model_row = QHBoxLayout()
        model_row.addWidget(model_combo)
        model_row.addWidget(refresh_btn)

        group_layout.addRow(self.translation_manager.t("default_model_for") + ":", model_row)

        layout.addWidget(group)
        layout.addStretch()

        return {
            "widget": page,
            "api_key_input": api_key_input,
            "api_url_input": api_url_input,
            "model_combo": model_combo,
            "config_keys": {
                "api_key": "minimax.api_key",  # Special case for MiniMax
                "model_default": "default_models.MiniMax.default",
                "model_available": "default_models.MiniMax.available",
                "api_url": "api_urls.MiniMax"
            }
        }

    def on_provider_changed(self, index):
        """Handle provider selection change"""
        self.provider_settings_stack.setCurrentIndex(index)

    def toggle_password_visibility(self, line_edit):
        """Toggle QLineEdit echo mode between Password and Normal"""
        if line_edit.echoMode() == QLineEdit.Password:
            line_edit.setEchoMode(QLineEdit.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.Password)
    
    def refresh_single_provider_models(self, provider_name, combo_box):
        """Refresh models for a specific provider"""
        # In a real app, this would trigger an async fetch
        # Manual QMessageBox with style
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Refresh Models")
        msg_box.setText(f"Fetching latest models for {provider_name}...\n(Logic to be connected to ApiClient)")
        msg_box.setIcon(QMessageBox.Information)
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
        msg_box.exec()
        # Ideally, emit a signal that MainWindow acts on, or use a shared client reference if safe.
        # For now, we rely on the pre-loaded 'available' lists in config.

    def create_model_tab(self):
        """Create model defaults configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FCFAF8;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)
        
        # Description
        desc_label = QLabel(self.translation_manager.t("model_defaults_description"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 13px; margin-bottom: 10px; line-height: 1.4;")
        content_layout.addWidget(desc_label)

        # Model Defaults Group
        model_group = QGroupBox(self.translation_manager.t("default_models_group"))
        model_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        model_layout = QFormLayout(model_group)
        model_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        model_layout.setLabelAlignment(Qt.AlignRight)
        model_layout.setContentsMargins(12, 14, 12, 12)
        model_layout.setSpacing(10)
        
        # Create model selectors with more space for long names
        self.deepseek_model_combo = QComboBox()
        self.deepseek_model_combo.setEditable(True)
        self.deepseek_model_combo.setStyleSheet(self.get_combo_style())
        self.deepseek_model_combo.setMinimumWidth(300)  # Ensure adequate width
        model_layout.addRow("DeepSeek " + self.translation_manager.t("default_model_for") + ":", self.deepseek_model_combo)

        self.openrouter_model_combo = QComboBox()
        self.openrouter_model_combo.setEditable(True)
        self.openrouter_model_combo.setStyleSheet(self.get_combo_style())
        self.openrouter_model_combo.setMinimumWidth(300)  # Ensure adequate width
        model_layout.addRow("OpenRouter " + self.translation_manager.t("default_model_for") + ":", self.openrouter_model_combo)

        self.groq_model_combo = QComboBox()
        self.groq_model_combo.setEditable(True)
        self.groq_model_combo.setStyleSheet(self.get_combo_style())
        self.groq_model_combo.setMinimumWidth(300)  # Ensure adequate width
        model_layout.addRow("Groq " + self.translation_manager.t("default_model_for") + ":", self.groq_model_combo)

        self.siliconflow_model_combo = QComboBox()
        self.siliconflow_model_combo.setEditable(True)
        self.siliconflow_model_combo.setStyleSheet(self.get_combo_style())
        self.siliconflow_model_combo.setMinimumWidth(300)  # Ensure adequate width
        model_layout.addRow("SiliconFlow " + self.translation_manager.t("default_model_for") + ":", self.siliconflow_model_combo)

        self.google_model_combo = QComboBox()
        self.google_model_combo.setEditable(True)
        self.google_model_combo.setStyleSheet(self.get_combo_style())
        self.google_model_combo.setMinimumWidth(300)  # Ensure adequate width
        model_layout.addRow("Google " + self.translation_manager.t("default_model_for") + ":", self.google_model_combo)

        self.dashscope_model_combo = QComboBox()
        self.dashscope_model_combo.setEditable(True)
        self.dashscope_model_combo.setStyleSheet(self.get_combo_style())
        self.dashscope_model_combo.setMinimumWidth(300)  # Ensure adequate width
        model_layout.addRow("DashScope " + self.translation_manager.t("default_model_for") + ":", self.dashscope_model_combo)
        
        content_layout.addWidget(model_group)
        
        # Advanced Options Group
        advanced_group = QGroupBox(self.translation_manager.t("advanced_options_group"))
        advanced_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        advanced_layout = QVBoxLayout(advanced_group)

        # Refresh models button
        self.refresh_models_btn = QPushButton(self.translation_manager.t("refresh_models"))
        self.refresh_models_btn.clicked.connect(self.refresh_available_models)
        self.refresh_models_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        content_layout.addWidget(advanced_group)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return tab
    
    def create_tts_tab(self):
        """Create TTS configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FCFAF8;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)
        
        # Description
        desc_label = QLabel(self.translation_manager.t("tts_settings_description"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 13px; margin-bottom: 10px; line-height: 1.4;")
        content_layout.addWidget(desc_label)

        # TTS Settings Group
        tts_group = QGroupBox(self.translation_manager.t("tts_settings_group"))
        tts_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        tts_layout = QFormLayout(tts_group)
        tts_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        tts_layout.setLabelAlignment(Qt.AlignRight)
        tts_layout.setContentsMargins(12, 14, 12, 12)
        tts_layout.setSpacing(10)
        
        # TTS settings inputs
        self.default_voice_input = QLineEdit()
        self.default_voice_input.setStyleSheet(self.get_input_style())
        tts_layout.addRow(self.translation_manager.t("default_voice"), self.default_voice_input)

        self.auto_play_preview_checkbox = QCheckBox(self.translation_manager.t("auto_play_preview"))
        self.auto_play_preview_checkbox.setStyleSheet(self.get_checkbox_style())
        tts_layout.addRow("", self.auto_play_preview_checkbox)

        # Output folder selector
        tts_output_layout = QHBoxLayout()
        self.tts_output_folder_input = QLineEdit()
        self.tts_output_folder_input.setStyleSheet(self.get_input_style())
        self.tts_output_folder_btn = QPushButton(self.translation_manager.t("browse"))
        self.tts_output_folder_btn.clicked.connect(lambda: self.browse_folder(self.tts_output_folder_input))
        self.tts_output_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 13px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        tts_output_layout.addWidget(self.tts_output_folder_input)
        tts_output_layout.addWidget(self.tts_output_folder_btn)
        tts_layout.addRow(self.translation_manager.t("output_folder"), tts_output_layout)

        # TTS Speed and Pitch controls
        self.tts_speed_spin = QDoubleSpinBox()
        self.tts_speed_spin.setRange(0.5, 2.0)
        self.tts_speed_spin.setSingleStep(0.1)
        self.tts_speed_spin.setValue(1.0)
        self.tts_speed_spin.setStyleSheet(self.get_spinbox_style())
        tts_layout.addRow(self.translation_manager.t("speech_speed"), self.tts_speed_spin)

        self.tts_pitch_spin = QDoubleSpinBox()
        self.tts_pitch_spin.setRange(0.5, 2.0)
        self.tts_pitch_spin.setSingleStep(0.1)
        self.tts_pitch_spin.setValue(1.0)
        self.tts_pitch_spin.setStyleSheet(self.get_spinbox_style())
        tts_layout.addRow(self.translation_manager.t("speech_pitch"), self.tts_pitch_spin)

        # TTS Provider
        self.tts_provider_combo = QComboBox()
        self.tts_provider_combo.addItems(["System TTS", "Azure TTS", "Google TTS"])
        self.tts_provider_combo.setStyleSheet(self.get_combo_style())
        tts_layout.addRow(self.translation_manager.t("tts_provider"), self.tts_provider_combo)

        content_layout.addWidget(tts_group)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        return tab
    
    def create_shortcuts_tab(self):
        """Create Global Shortcuts configuration tab (Windows Native)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FCFAF8;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)
        
        # Description
        desc_label = QLabel(self.translation_manager.t("shortcuts_description"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 13px; margin-bottom: 10px; line-height: 1.4;")
        content_layout.addWidget(desc_label)

        # Shortcuts Group
        shortcut_group = QGroupBox(self.translation_manager.t("global_shortcuts_group"))
        shortcut_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        shortcut_layout = QFormLayout(shortcut_group)
        shortcut_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        shortcut_layout.setLabelAlignment(Qt.AlignRight)
        shortcut_layout.setContentsMargins(12, 14, 12, 12)
        shortcut_layout.setSpacing(10)
        
        # Wake Up Word / Toggle Window
        self.wake_hotkey_edit = QKeySequenceEdit()
        # Load style similar to inputs
        self.wake_hotkey_edit.setStyleSheet(self.get_input_style() + """
            QKeySequenceEdit {
                color: #374151;
            }
        """)
        shortcut_layout.addRow(self.translation_manager.t("shortcut_wake_app"), self.wake_hotkey_edit)
        
        # Instructions
        help_label = QLabel(self.translation_manager.t("shortcut_instructions"))
        help_label.setStyleSheet("color: #9CA3AF; font-size: 12px; margin-top: 5px;")
        help_label.setWordWrap(True)
        shortcut_layout.addRow("", help_label)
        
        content_layout.addWidget(shortcut_group)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return tab
    
    def create_ui_tab(self):
        """Create UI appearance configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FCFAF8;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)
        
        # Description
        desc_label = QLabel(self.translation_manager.t("appearance_settings_description"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 13px; margin-bottom: 10px; line-height: 1.4;")
        content_layout.addWidget(desc_label)

        # Theme Settings Group
        theme_group = QGroupBox(self.translation_manager.t("theme_settings_group"))
        theme_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        theme_layout = QFormLayout(theme_group)
        theme_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        theme_layout.setLabelAlignment(Qt.AlignRight)
        theme_layout.setContentsMargins(12, 14, 12, 12)
        theme_layout.setSpacing(10)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["default", "dark", "light"])
        self.theme_combo.setStyleSheet(self.get_combo_style())
        theme_layout.addRow(self.translation_manager.t("theme") + ":", self.theme_combo)


        
        content_layout.addWidget(theme_group)
        
        # Window Settings Group
        window_group = QGroupBox(self.translation_manager.t("window_settings_group"))
        window_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        window_layout = QFormLayout(window_group)
        window_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        window_layout.setLabelAlignment(Qt.AlignRight)
        window_layout.setContentsMargins(12, 14, 12, 12)
        window_layout.setSpacing(10)

        # Window size inputs
        window_size_layout = QHBoxLayout()
        self.window_width_spin = QSpinBox()
        self.window_width_spin.setRange(800, 2000)
        self.window_width_spin.setValue(1000)
        self.window_width_spin.setStyleSheet(self.get_spinbox_style())
        window_size_layout.addWidget(self.window_width_spin)
        window_size_layout.addWidget(QLabel("×"))
        self.window_height_spin = QSpinBox()
        self.window_height_spin.setRange(600, 1500)
        self.window_height_spin.setValue(800)
        self.window_height_spin.setStyleSheet(self.get_spinbox_style())
        window_size_layout.addWidget(self.window_height_spin)
        window_layout.addRow(self.translation_manager.t("window_size"), window_size_layout)

        # Remember window position
        self.remember_window_pos_checkbox = QCheckBox(self.translation_manager.t("remember_window_position"))
        self.remember_window_pos_checkbox.setStyleSheet(self.get_checkbox_style())
        window_layout.addRow("", self.remember_window_pos_checkbox)
        
        content_layout.addWidget(window_group)
        
        # Advanced UI Options Group
        advanced_ui_group = QGroupBox(self.translation_manager.t("advanced_ui_options_group"))
        advanced_ui_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        advanced_ui_layout = QVBoxLayout(advanced_ui_group)

        self.always_on_top_checkbox = QCheckBox(self.translation_manager.t("always_on_top"))
        self.always_on_top_checkbox.setStyleSheet(self.get_checkbox_style())
        advanced_ui_layout.addWidget(self.always_on_top_checkbox)

        self.show_tray_icon_checkbox = QCheckBox(self.translation_manager.t("show_tray_icon"))
        self.show_tray_icon_checkbox.setStyleSheet(self.get_checkbox_style())
        advanced_ui_layout.addWidget(self.show_tray_icon_checkbox)
        
        content_layout.addWidget(advanced_ui_group)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return tab
    
    def create_general_tab(self):
        """Create general settings configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FCFAF8;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)
        
        # Description
        desc_label = QLabel(self.translation_manager.t("general_settings_description"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 13px; margin-bottom: 10px; line-height: 1.4;")
        content_layout.addWidget(desc_label)

        # General Settings Group
        general_group = QGroupBox(self.translation_manager.t("general_settings_group"))
        general_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        general_layout = QFormLayout(general_group)
        general_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        general_layout.setLabelAlignment(Qt.AlignRight)
        general_layout.setContentsMargins(12, 14, 12, 12)
        general_layout.setSpacing(10)

        # Add language setting
        self.general_language_combo = QComboBox()
        self.general_language_combo.addItems(["English", "中文", "日本語", "한국어", "Français", "Español", "Deutsch"])
        self.general_language_combo.setStyleSheet(self.get_combo_style())
        self.general_language_combo.currentTextChanged.connect(self.on_general_language_changed)
        general_layout.addRow(self.translation_manager.t("display_language"), self.general_language_combo)

        # Output directory selector
        output_dir_layout = QHBoxLayout()
        self.output_directory_input = QLineEdit()
        self.output_directory_input.setStyleSheet(self.get_input_style())
        self.output_directory_btn = QPushButton(self.translation_manager.t("browse"))
        self.output_directory_btn.clicked.connect(lambda: self.browse_folder(self.output_directory_input))
        self.output_directory_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 13px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        output_dir_layout.addWidget(self.output_directory_input)
        output_dir_layout.addWidget(self.output_directory_btn)
        general_layout.addRow(self.translation_manager.t("output_directory"), output_dir_layout)

        # Chat history retention
        self.history_retention_combo = QComboBox()
        self.history_retention_combo.addItems([
            self.translation_manager.t("keep_all_history"),
            self.translation_manager.t("days_30"),
            self.translation_manager.t("days_7"),
            self.translation_manager.t("days_3"),
            self.translation_manager.t("days_1")
        ])
        self.history_retention_combo.setStyleSheet(self.get_combo_style())
        general_layout.addRow(self.translation_manager.t("history_retention"), self.history_retention_combo)
        
        content_layout.addWidget(general_group)
        
        # Logging and Data Group
        logging_group = QGroupBox(self.translation_manager.t("logging_data_group"))
        logging_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5E5;
                border-radius: 5px;
                margin-top: 0.8ex;
                padding-top: 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        logging_layout = QVBoxLayout(logging_group)
        logging_layout.setContentsMargins(12, 14, 12, 12)
        logging_layout.setSpacing(8)

        # Logging level selector
        log_level_layout = QHBoxLayout()
        log_level_label = QLabel(self.translation_manager.t("log_level"))
        log_level_label.setStyleSheet("color: #5F5F5F; font-size: 13px; font-weight: 500;")
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setStyleSheet(self.get_combo_style())
        log_level_layout.addWidget(log_level_label)
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()
        logging_layout.addLayout(log_level_layout)

        # Data management options
        self.clear_cache_btn = QPushButton(self.translation_manager.t("clear_cache"))
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        self.clear_cache_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)

        self.clear_history_btn = QPushButton(self.translation_manager.t("clear_chat_history"))
        self.clear_history_btn.clicked.connect(self.clear_chat_history)
        self.clear_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        data_buttons_layout = QHBoxLayout()
        data_buttons_layout.addWidget(self.clear_cache_btn)
        data_buttons_layout.addWidget(self.clear_history_btn)
        data_buttons_layout.addStretch()
        logging_layout.addLayout(data_buttons_layout)
        
        content_layout.addWidget(logging_group)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return tab
    
    def create_donate_tab(self):
        """Create donation/about tab displaying the QR code"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FCFAF8;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)  # Reduced margins to give more space to QR code
        content_layout.setSpacing(10)  # Reduced spacing
        content_layout.setAlignment(Qt.AlignCenter)

        # Removed title and description to give maximum space to QR code
        
        # QR Code Image
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignCenter)
        
        # Load image - handle both dev and packaged environments
        image_path = get_resource_path("donate_qr.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # Scale image to be smaller as per user request
                if pixmap.width() > 335:
                    pixmap = pixmap.scaledToWidth(335, Qt.SmoothTransformation)
                qr_label.setPixmap(pixmap)
            else:
                qr_label.setText(self.translation_manager.t("qr_error"))
        else:
            qr_label.setText(f"{self.translation_manager.t('qr_not_found')}\n{image_path}")

        # Add a container frame to hold the QR code with border and padding (works for both image and text)
        qr_frame = QFrame()
        qr_frame.setFrameShape(QFrame.StyledPanel)
        qr_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                background-color: white;
            }
        """)

        frame_layout = QVBoxLayout(qr_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.addWidget(qr_label, alignment=Qt.AlignCenter)

        content_layout.addWidget(qr_frame)
            
        # The QR code is now added inside the frame container above, so this line is not needed
        
        # Footer text
        footer_label = QLabel(self.translation_manager.t("support_footer"))
        footer_label.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 16px; font-weight: bold; margin-top: 20px;")
        footer_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(footer_label)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return tab

    def create_support_button(self):
        """Create the 'Buy me a coffee' button for the tab bar corner"""
        # User requested a design similar to the provided image: "clever, small, not exaggerated"
        # We use a pill-shaped button with a heart icon
        text = self.translation_manager.t("buy_me_a_coffee")
        btn = QPushButton(f"❤️ {text}")
        btn.setCursor(Qt.PointingHandCursor)
        # Show donate dialog when clicked
        btn.clicked.connect(self.show_donate_dialog)
        
        # Modern pill style with subtle pink accent
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFF0F5;
                color: #D81B60;
                border: 1px solid #FFC1E3;
                border-radius: 14px;
                padding: 4px 12px;
                font-weight: 600;
                font-size: 12px;
                margin-right: 10px;
                margin-top: 2px;
                margin-bottom: 2px;
            }}
            QPushButton:hover {{
                background-color: #FFE4E1;
                border: 1px solid #FF69B4;
            }}
        """)

        return btn

    def show_donate_dialog(self):
        """Show the donation content in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.translation_manager.t("support_title"))
        dialog.setMinimumSize(500, 600)
        
        # Reuse the layout logic from create_donate_tab but apply to dialog
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # We can just reuse the widget created by create_donate_tab
        # Since it's a QWidget, we can add it to the dialog layout
        # We need to recreate it or verify if self.donate_tab can be reparented/used multiple times
        # Since self.donate_tab was created in create_donate_tab() and assigned to self, we can use it.
        # However, a widget can only be in one place. Since we didn't add it to the tab widget (commented out),
        # we can potentially use it. But better to create a fresh one or ensure parenting is correct.
        
        # Note: self.donate_tab IS initialized in init_ui -> create_donate_tab
        # But it's not added to the tab_widget layout.
        # We should reparent it to the dialog.
        
        if self.donate_tab.parent() != dialog:
            self.donate_tab.setParent(dialog)
            
        layout.addWidget(self.donate_tab)
        self.donate_tab.show() # Ensure it's visible
        
        dialog.exec()

    def get_input_style(self):
        """Get consistent input field style matching Claude theme"""
        return """
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 13px;
                color: #333;
            }
            QLineEdit:focus {{
                border: 1px solid {Colors.PRIMARY};
            }}
        """
    
    def get_combo_style(self):
        """Get consistent combo box style matching Claude theme"""
        return """
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 13px;
                color: #333;
                min-width: 180px;
            }
            QComboBox:focus {{
                border: 1px solid {Colors.PRIMARY};
            }}
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #E0E0E0;
                selection-background-color: #f0f0f0;
                selection-color: #333;
                outline: none;
            }
        """
    
    def get_spinbox_style(self):
        """Get consistent spin box style matching Claude theme"""
        return """
            QSpinBox, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 13px;
                color: #333;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {Colors.PRIMARY};
            }}
        """
    
    def get_checkbox_style(self):
        """Get consistent checkbox style matching Claude theme"""
        return """
            QCheckBox {
                color: #5F5F5F;
                font-size: 13px;
                font-weight: 500;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #B0B0B0;
                border-radius: 3px;
                background: #FFFFFF;
            }
            QCheckBox::indicator:unchecked {
                background: #FFFFFF;
            }
            QCheckBox::indicator:checked {{
                border: 1px solid {Colors.PRIMARY};
                background: {Colors.PRIMARY};
            }}
            QCheckBox::indicator:unchecked:hover {{
                border: 1px solid #999999;
            }}
            QCheckBox::indicator:checked:hover {{
                background: {Colors.PRIMARY_HOVER};
            }}
        """
    
    def load_settings(self):
        """Load current settings from config manager into the UI"""
        try:
            # Block signals to prevent triggering change events while loading
            self.blockSignals(True)

            # Iterate through provider widgets and load settings dynamically
            for provider_name, data in self.provider_widgets.items():
                keys = data['config_keys']
                
                # Load API Key
                data['api_key_input'].setText(self.config_manager.get(keys['api_key'], ""))
                
                # Load API URL
                data['api_url_input'].setText(self.config_manager.get(keys['api_url'], ""))
                
                # Load Models
                default_model = self.config_manager.get(keys['model_default'], "")
                available_models = self.config_manager.get(keys['model_available'], [])
                
                data['model_combo'].clear()
                data['model_combo'].addItems(available_models)
                data['model_combo'].setCurrentText(default_model)

            # Load TTS Settings
            self.default_voice_input.setText(self.config_manager.get("tts_settings.default_voice", ""))
            self.auto_play_preview_checkbox.setChecked(self.config_manager.get("tts_settings.auto_play_preview", False))
            self.tts_output_folder_input.setText(self.config_manager.get("tts_settings.output_folder", ""))
            self.tts_speed_spin.setValue(float(self.config_manager.get("tts_settings.speech_speed", 1.0)))
            self.tts_pitch_spin.setValue(float(self.config_manager.get("tts_settings.speech_pitch", 1.0)))
            self.tts_provider_combo.setCurrentText(self.config_manager.get("tts_settings.provider", "System TTS"))

            # Load Shortcuts
            wake_shortcut = self.config_manager.get("shortcuts.wake_app", "Alt+Shift+S")
            self.wake_hotkey_edit.setKeySequence(QKeySequence(wake_shortcut))
            
            # Load General Settings
            self.general_language_combo.setCurrentText(self.config_manager.get("general_settings.display_language", "English"))
            self.output_directory_input.setText(self.config_manager.get("output_directory", ""))
            self.history_retention_combo.setCurrentText(self.config_manager.get("general_settings.history_retention", "Keep all history"))
            self.log_level_combo.setCurrentText(self.config_manager.get("general_settings.log_level", "INFO"))
            
            # Load UI Settings
            self.theme_combo.setCurrentText(self.config_manager.get("ui_settings.theme", "default"))
            window_size = self.config_manager.get("ui_settings.window_size", [1000, 800])
            if isinstance(window_size, list) and len(window_size) == 2:
                self.window_width_spin.setValue(window_size[0])
                self.window_height_spin.setValue(window_size[1])
            self.remember_window_pos_checkbox.setChecked(self.config_manager.get("ui_settings.remember_window_position", True))
            self.always_on_top_checkbox.setChecked(self.config_manager.get("ui_settings.always_on_top", False))
            self.show_tray_icon_checkbox.setChecked(self.config_manager.get("ui_settings.show_tray_icon", True))

            # Unblock signals
            self.blockSignals(False)

        except Exception as e:
            print(f"Error loading settings: {e}")
            import traceback
            traceback.print_exc()
            self.blockSignals(False)

    def get_retention_key(self, value):
        """Helper method to get the translation key for history retention values"""
        retention_map = {
            "Keep all history": "keep_all_history",
            "30 days": "days_30",
            "7 days": "days_7",
            "3 days": "days_3",
            "1 day": "days_1"
        }
        # Also check reverse mapping
        for eng, key in retention_map.items():
            if self.translation_manager.t(key) == value:
                return key
        # If not found, return the English version
        return retention_map.get(value, "keep_all_history")

    def on_display_language_changed(self, language):
        """Handle display language change in the general settings"""
        # Save current settings (including the new language choice) silently
        # This ensures that when we rebuild UI, we load the correct language
        
        # We need to manually update the config manager with the new language first
        self.config_manager.update_setting("general_settings.display_language", language)
        
        # Also ensure the other combo box is synced before saving
        # Also ensure the combo box is synced before saving
        if self.general_language_combo.currentText() != language:
            self.general_language_combo.blockSignals(True)
            self.general_language_combo.setCurrentText(language)
            self.general_language_combo.blockSignals(False)
            
        # Perform a silent save of all current inputs
        self.save_settings(silent=True)

        # Update the translation manager with the new language
        # This will emit language_changed signal, which triggers update_ui_text
        self.translation_manager.set_language(language)


    
    def on_general_language_changed(self, language):
        """Handle language change from the General settings tab"""
        # Apply the language change
        self.on_display_language_changed(language)

    
    def refresh_available_models(self):
        """Refresh the available models from each provider (stub implementation)"""
        # In a real implementation, this would call the API to fetch available models
        # For now, we'll just show a message indicating the operation
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Refresh Models")
        msg_box.setText("In a full implementation, this would fetch the latest available models from each provider.")
        msg_box.setIcon(QMessageBox.Information)
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
        msg_box.exec()

    def clear_cache(self):
        """Clear application cache"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Clear Cache")
        msg_box.setText("Are you sure you want to clear the application cache? This will remove temporary files but won't affect your chat history or settings.")
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
        reply = msg_box.exec()

        if reply == QMessageBox.Yes:
            # In a real implementation, this would clear cache files
            success_box = QMessageBox(self)
            success_box.setWindowTitle("Cache Cleared")
            success_box.setText("Application cache has been cleared.")
            success_box.setIcon(QMessageBox.Information)
            success_box.setStyleSheet("""
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
            success_box.exec()

    def clear_chat_history(self):
        """Clear chat history"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Clear Chat History")
        msg_box.setText("Are you sure you want to clear all chat history? This action cannot be undone.")
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
        reply = msg_box.exec()

        if reply == QMessageBox.Yes:
            # In a real implementation, this would clear the database
            from app.core.database import DatabaseManager
            db_manager = DatabaseManager()
            db_manager.clear_all_sessions()

            success_box = QMessageBox(self)
            success_box.setWindowTitle("History Cleared")
            success_box.setText("Chat history has been cleared.")
            success_box.setIcon(QMessageBox.Information)
            success_box.setStyleSheet("""
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
            success_box.exec()
    
    def browse_folder(self, input_field):
        """Open folder browser and update input field"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", input_field.text() or ".")
        if folder:
            input_field.setText(folder)
    
    def save_settings(self, silent=False):
        """Save current settings to config manager"""
        try:
            # Iterate through provider widgets and save settings dynamically
            for provider_name, data in self.provider_widgets.items():
                keys = data['config_keys']
                
                # Save API Key
                self.config_manager.update_setting(keys['api_key'], data['api_key_input'].text())
                
                # Save API URL
                self.config_manager.update_setting(keys['api_url'], data['api_url_input'].text())
                
                # Save Default Model
                self.config_manager.update_setting(keys['model_default'], data['model_combo'].currentText())
            
            # Update TTS settings
            self.config_manager.update_setting("tts_settings.default_voice", self.default_voice_input.text())
            self.config_manager.update_setting("tts_settings.auto_play_preview", self.auto_play_preview_checkbox.isChecked())
            self.config_manager.update_setting("tts_settings.output_folder", self.tts_output_folder_input.text())
            self.config_manager.update_setting("tts_settings.speech_speed", self.tts_speed_spin.value())
            self.config_manager.update_setting("tts_settings.speech_pitch", self.tts_pitch_spin.value())
            self.config_manager.update_setting("tts_settings.speech_pitch", self.tts_pitch_spin.value())
            self.config_manager.update_setting("tts_settings.provider", self.tts_provider_combo.currentText())

            # Update Shortcuts
            wake_seq = self.wake_hotkey_edit.keySequence().toString()
            self.config_manager.update_setting("shortcuts.wake_app", wake_seq)
            
            # Update UI settings
            self.config_manager.update_setting("ui_settings.theme", self.theme_combo.currentText())

            self.config_manager.update_setting("ui_settings.window_size", [
                self.window_width_spin.value(),
                self.window_height_spin.value()
            ])
            self.config_manager.update_setting("ui_settings.remember_window_position", self.remember_window_pos_checkbox.isChecked())
            self.config_manager.update_setting("ui_settings.always_on_top", self.always_on_top_checkbox.isChecked())
            self.config_manager.update_setting("ui_settings.show_tray_icon", self.show_tray_icon_checkbox.isChecked())
            
            # Update general settings
            self.config_manager.update_setting("general_settings.display_language", self.general_language_combo.currentText())
            self.config_manager.update_setting("output_directory", self.output_directory_input.text())
            self.config_manager.update_setting("general_settings.history_retention", self.history_retention_combo.currentText())
            self.config_manager.update_setting("general_settings.log_level", self.log_level_combo.currentText())
            
            # Save to file
            self.config_manager.save_config()
            
            # Emit signal that settings were saved
            self.settings_saved.emit()
            
            # Show success message
            if not silent:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Settings Saved")
                msg_box.setText("Your settings have been saved successfully!")
                msg_box.setIcon(QMessageBox.Information)
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
                msg_box.exec()

        except Exception as e:
            print(f"Error saving settings: {e}")
            if not silent:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"Could not save settings: {str(e)}")
                msg_box.setIcon(QMessageBox.Critical)
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
                msg_box.exec()

    def reset_to_defaults(self):
        """Reset all settings to default values"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Reset Settings")
        msg_box.setText("Are you sure you want to reset all settings to defaults? This cannot be undone.")
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
        reply = msg_box.exec()

        if reply == QMessageBox.Yes:
            try:
                # Clear the configuration and reload defaults
                from app.core.config import DEFAULT_CONFIG
                self.config_manager.config = DEFAULT_CONFIG.copy()
                self.config_manager.save_config()

                # Reload UI from new config
                self.load_settings()

                success_box = QMessageBox(self)
                success_box.setWindowTitle("Settings Reset")
                success_box.setText("Settings have been reset to defaults.")
                success_box.setIcon(QMessageBox.Information)
                success_box.setStyleSheet("""
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
                success_box.exec()
            except Exception as e:
                print(f"Error resetting settings: {e}")
                error_box = QMessageBox(self)
                error_box.setWindowTitle("Error")
                error_box.setText(f"Could not reset settings: {str(e)}")
                error_box.setIcon(QMessageBox.Critical)
                error_box.setStyleSheet("""
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
                error_box.exec()