from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

class VoiceSelector(QWidget):
    """
    A reusable widget for selecting a TTS voice with language filtering.
    """
    voice_changed = Signal(str)  # Emits the ShortName of the selected voice

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.all_voices = []

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Language Filter
        layout.addWidget(QLabel("语言:"))
        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(100)
        self.lang_combo.addItems(["全部", "中文", "英语", "日语", "韩语", "法语", "德语", "西班牙语", "俄语"])
        self.lang_combo.currentTextChanged.connect(self._filter_voices)
        layout.addWidget(self.lang_combo)

        # Voice Selection
        layout.addWidget(QLabel("语音:"))
        self.voice_combo = QComboBox()
        self.voice_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.voice_combo.setMaxVisibleItems(12)  # Limit height
        self.voice_combo.setEditable(True)      # Allow search
        self.voice_combo.setInsertPolicy(QComboBox.NoInsert)
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        layout.addWidget(self.voice_combo)

    def populate_voices(self, voices):
        """
        Populate the voice combo box with a list of voice dictionaries.
        Expected format: {'Name': '...', 'ShortName': '...', 'Locale': '...', 'Gender': '...'}
        """
        self.all_voices = voices
        self._filter_voices(self.lang_combo.currentText())

    def _filter_voices(self, language_name):
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        
        current_short_name = self.voice_combo.currentData()

        # Define mapping from display name to locale codes
        # Matches TtsHandler.LANGUAGE_CODES keys
        lang_map = {
            "中文": ["zh", "zh-CN", "zh-TW"],
            "英语": ["en", "en-US", "en-GB", "en-AU"],
            "日语": ["ja", "ja-JP"],
            "韩语": ["ko", "ko-KR"],
            "法语": ["fr", "fr-FR"],
            "德语": ["de", "de-DE"],
            "西班牙语": ["es", "es-ES"],
            "俄语": ["ru", "ru-RU"],
            "意大利语": ["it", "it-IT"],
            "葡萄牙语": ["pt", "pt-BR", "pt-PT"]
        }

        filtered_voices = []
        if language_name == "全部":
            filtered_voices = self.all_voices
        else:
            codes = lang_map.get(language_name, [])
            for voice in self.all_voices:
                locale = voice.get("Locale", "")
                if any(code.lower() in locale.lower() for code in codes):
                    filtered_voices.append(voice)

        # Add to combo box
        for voice in filtered_voices:
            # Prioritize 'Name' if available, otherwise use 'ShortName'
            name = voice.get("Name")
            short_name = voice.get("ShortName", voice.get("Name"))
            gender = voice.get("Gender", "Unknown")
            
            if name:
                display_name = name
            else:
                # Fallback to simplified short_name
                display_name = short_name
                if "-" in short_name:
                    parts = short_name.split("-")
                    if len(parts) >= 3: # e.g. zh-CN-Name
                         display_name = parts[-1]
            
            display_text = f"{display_name} ({gender})"
            
            self.voice_combo.addItem(display_text, short_name)

        self.voice_combo.blockSignals(False)
        
        # Try to restore previous selection if it exists in new list
        index = self.voice_combo.findData(current_short_name)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        elif self.voice_combo.count() > 0:
            self.voice_combo.setCurrentIndex(0)
            # Emit change since we auto-selected the first one
            self._on_voice_changed(0)
        
        # Update completer for the new list
        from PySide6.QtWidgets import QCompleter
        completer = QCompleter([self.voice_combo.itemText(i) for i in range(self.voice_combo.count())])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.voice_combo.setCompleter(completer)

    def _on_voice_changed(self, index):
        if index >= 0:
            voice_short_name = self.voice_combo.itemData(index)
            self.voice_changed.emit(voice_short_name)

    def get_selected_voice(self):
        return self.voice_combo.currentData()

    def set_selected_voice(self, voice_short_name):
        index = self.voice_combo.findData(voice_short_name)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
