import logging
import base64
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect, QFrame, QSizePolicy, QComboBox
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QRect, QSize, QPoint
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QPen
from app.ui.styles.design_system import Colors

from app.core.audio_recorder import AudioRecorder
from app.core.audio_stream_player import AudioStreamPlayer

# Import Qwen TTS Flash voices and Gemini TTS voices
try:
    from utils.tts_handler import QWEN_TTS_FLASH_VOICES, GEMINI_TTS_VOICES
except ImportError:
    QWEN_TTS_FLASH_VOICES = []
    GEMINI_TTS_VOICES = []


class PulseButton(QPushButton):
    """A button that pulses (animates size/halo) when active."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: none;
                border-radius: 40px;
                color: #333;
                font-size: 32px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.setIcon(QIcon.fromTheme("audio-input-microphone")) 
        self.setIconSize(QSize(40, 40))
        
        # Animation setup
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self.update) # Trigger repaint for manual pulsing if needed
        # Or we can use QPropertyAnimation on specific properties if we expose them
        
        self.is_pulsing = False
        self.pulse_phase = 0.0

    def start_pulsing(self):
        if not self.is_pulsing:
            self.is_pulsing = True
            self._pulse_timer.start(50) # 20fps

    def stop_pulsing(self):
        self.is_pulsing = False
        self._pulse_timer.stop()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.is_pulsing:
            self.pulse_phase += 0.2
            if self.pulse_phase > 3.14159 * 2:
                self.pulse_phase = 0
            
            # Draw Ripple
            import math
            scale = 1.0 + 0.2 * abs(math.sin(self.pulse_phase))

            painter.save()
            center = self.rect().center()
            radius = 40 * scale

            color = QColor(Colors.PRIMARY)
            color.setAlpha(100) # Semi-transparent ripple
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, radius, radius)
            painter.restore()
            
        super().paintEvent(event)


class VoiceCallOverlay(QWidget):
    """
    Copilot-style Large Voice Call Overlay.
    """
    closed = Signal()
    ai_response_text = Signal(str)  # AI's text for chat display
    ai_response_finished = Signal()  # AI finished speaking - save to DB
    user_transcript = Signal(str)   # User's speech transcript for chat display
    tts_request = Signal(str, str)  # Request TTS playback: (text, voice_name)

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.recorder = AudioRecorder(self)
        self.player = AudioStreamPlayer(self)

        self.is_active = False
        self.current_state = "IDLE" # IDLE, LISTENING, THINKING, SPEAKING
        self.history_provider = None  # Callback to get conversation history
        self.use_custom_tts = False  # Use native API audio (both Google and DashScope Omni have native audio output)  # Flag to use Qwen3 TTS Flash instead of API audio
        self._pending_tts_text = ""  # Accumulate text for TTS

        self._init_ui()
        self._connect_signals()
        
        # Speaking timeout timer
        self._speaking_timeout_timer = QTimer(self)
        self._speaking_timeout_timer.setSingleShot(True)
        self._speaking_timeout_timer.timeout.connect(self._on_speaking_timeout)
        self._speaking_timeout_ms = 1500
        
        # User transcript accumulation (Gemini sends in chunks)
        self._user_transcript_buffer = ""
        self._user_transcript_timer = QTimer(self)
        self._user_transcript_timer.setSingleShot(True)
        self._user_transcript_timer.timeout.connect(self._flush_user_transcript)
        self._user_transcript_delay_ms = 2000  # Fallback: 2s after last chunk (normally flushed when AI responds)

    def _init_ui(self):
        self.resize(500, 600) # Large window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog) # Overlay/Dialog style
        self.setAttribute(Qt.WA_TranslucentBackground) # Semi-transparent if needed, but we use solid card
        
        # Main Card Style
        self.setStyleSheet("""
            QWidget#VoiceCallOverlay {
                background-color: transparent; 
            }
            QFrame#MainCard {
                background-color: #ffffff;
                border-radius: 24px;
                border: 1px solid #e0e0e0;
            }
            QLabel {
                color: #333;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        self.setObjectName("VoiceCallOverlay")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # The Card Container
        self.card = QFrame()
        self.card.setObjectName("MainCard")
        # Add slight shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(20)
        
        # 1. Top Controls (Close, etc.)
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(36, 36)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                font-size: 18px;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                color: #333;
            }
        """)
        self.close_btn.clicked.connect(self.close_overlay)
        top_layout.addWidget(self.close_btn)
        
        card_layout.addLayout(top_layout)
        
        # 2. Status Text
        self.status_label = QLabel("Listening...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 24px; font-weight: 600; color: #202124;")
        card_layout.addWidget(self.status_label)

        # 2.5 Voice Selector Row
        voice_row = QHBoxLayout()
        voice_row.addStretch()

        self.voice_label = QLabel("AI 音色:")
        self.voice_label.setStyleSheet("font-size: 14px; color: #5f6368;")
        voice_row.addWidget(self.voice_label)

        combo_style = """
            QComboBox {
                background-color: #f8f9fa;
                border: 1px solid #dadce0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                color: #202124;
            }
            QComboBox:hover {
                border-color: #1a73e8;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #dadce0;
                selection-background-color: #e8f0fe;
            }
        """

        # Qwen TTS Voice Combo (for DashScope)
        self.voice_combo = QComboBox()
        self.voice_combo.setFixedWidth(220)
        self.voice_combo.setStyleSheet(combo_style)
        self.voice_combo.setEditable(True)
        self.voice_combo.setInsertPolicy(QComboBox.NoInsert)
        self._selected_voice = "Cherry"  # Default Qwen voice
        self._populate_voice_combo_grouped(self.voice_combo)
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        voice_row.addWidget(self.voice_combo)

        # Gemini TTS Voice Combo (for Google Live)
        self.gemini_voice_combo = QComboBox()
        self.gemini_voice_combo.setFixedWidth(180)
        self.gemini_voice_combo.setStyleSheet(combo_style)
        # Add voices first, then set default
        for voice in GEMINI_TTS_VOICES:
            name = voice.get("Name", voice.get("ShortName", "Unknown"))
            gender = voice.get("Gender", "")
            short_name = voice.get("ShortName", "Zephyr")
            display_name = f"{name} ({gender})" if gender else name
            self.gemini_voice_combo.addItem(display_name, short_name)
        # Set default to match the first item (Puck) to avoid sync issues
        self._selected_gemini_voice = self.gemini_voice_combo.itemData(0)  # Puck
        self.gemini_voice_combo.setCurrentIndex(0)
        self.gemini_voice_combo.currentIndexChanged.connect(self._on_gemini_voice_changed)
        voice_row.addWidget(self.gemini_voice_combo)
        self.gemini_voice_combo.hide()  # Hidden by default, shown for Google

        voice_row.addStretch()
        card_layout.addLayout(voice_row)

        card_layout.addStretch(1) # Spacer
        
        # 3. Main Microphone Graphic (Pulse Button)
        center_row = QHBoxLayout()
        center_row.addStretch()
        
        self.mic_btn = PulseButton()
        self.mic_btn.clicked.connect(self.toggle_listening)
        center_row.addWidget(self.mic_btn)
        
        center_row.addStretch()
        card_layout.addLayout(center_row)
        
        card_layout.addStretch(1) # Spacer
        
        # 4. Footer hint
        self.hint_label = QLabel("Tap to interrupt")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("font-size: 14px; color: #5f6368;")
        card_layout.addWidget(self.hint_label)
        
        main_layout.addWidget(self.card)
        
        # Drag Logic Variables
        self._dragging = False
        self._drag_pos = None

    # ===== Dragging Logic =====
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def center_in_window(self):
        """Centers the overlay in the parent window."""
        if self.parent():
            # Get parent's global center (ChatPage -> QStackedWidget -> MainWindow)
            parent_window = self.parent().window()
            if parent_window:
                parent_center = parent_window.geometry().center()
            else:
                # Fallback
                parent_center = self.parent().mapToGlobal(self.parent().rect().center())
            
            geo = self.frameGeometry()
            geo.moveCenter(parent_center)
            self.move(geo.topLeft())

    def _connect_signals(self):
        # Recorder Signals
        self.recorder.recording_stopped.connect(self._on_recording_stopped)
        self.recorder.input_level.connect(self._update_input_visual)
        self.recorder.audio_chunk_ready.connect(self._on_recorder_chunk_ready)
        
        # API Signals
        self.api_client.transcription_finished.connect(self._on_transcription_finished)
        self.api_client.chat_stream_chunk.connect(self._on_text_chunk_received)
        self.api_client.chat_stream_finished.connect(self._on_stream_finished)
        
        # Live Session Signals
        self.api_client.session_started.connect(self._on_live_session_started)
        self.api_client.session_stopped.connect(self._on_live_session_stopped)
        self.api_client.chat_audio_chunk.connect(self._on_api_audio_received)
        self.api_client.live_text_chunk.connect(self._on_live_text_received)
        self.api_client.live_user_transcript.connect(self._on_user_transcript_received)
        
        # VAD signals - for proper turn management
        self.api_client.live_interrupted.connect(self._on_ai_interrupted)
        self.api_client.live_turn_complete.connect(self._on_ai_turn_complete)
        
        # Session resumption signals
        self.api_client.live_goaway.connect(self._on_goaway_warning)
        self.api_client.chat_response_error.connect(self._on_connection_error)

    def _on_goaway_warning(self):
        """Handle GoAway warning - connection will close soon."""
        logging.warning("GoAway warning received - connection will close in ~1 minute")
        self.status_label.setText("Reconnecting soon...")
    
    def _on_connection_error(self, error_msg):
        """Handle connection error - try to resume if possible."""
        if not self.is_active:
            return
        
        logging.error(f"Connection error: {error_msg}")
        
        # Try to resume session if we have a token
        if hasattr(self, 'is_live_mode') and self.is_live_mode:
            if self.api_client.has_resumption_token():
                logging.info("Attempting to resume Gemini Live session...")
                self.status_label.setText("Reconnecting...")
                self.api_client.resume_live_session()
                return
        
        # If we can't resume, show the error
        self.status_label.setText("Connection lost")

    def _on_voice_changed(self, index):
        """Handle Qwen voice selection change."""
        self._selected_voice = self.voice_combo.itemData(index)
        logging.info(f"Qwen voice changed to: {self._selected_voice}")

    def _populate_voice_combo_grouped(self, combo_box):
        """Populate voice combo with grouped categories for better UX."""
        combo_box.clear()
        
        locale_names = {
            "zh-CN": "中文",
            "en-US": "English",
            "es-ES": "Español",
            "ru-RU": "Русский",
            "it-IT": "Italiano",
            "ko-KR": "한국어",
            "ja-JP": "日本語",
            "de-DE": "Deutsch",
            "fr-FR": "Français",
            "pt-BR": "Português",
        }
        
        voices_by_locale = {}
        for voice in QWEN_TTS_FLASH_VOICES:
            locale = voice.get("Locale", "zh-CN")
            if locale not in voices_by_locale:
                voices_by_locale[locale] = []
            voices_by_locale[locale].append(voice)
        
        for locale in ["zh-CN", "en-US", "es-ES", "ru-RU", "it-IT", "ko-KR", "ja-JP", "de-DE", "fr-FR", "pt-BR"]:
            if locale not in voices_by_locale:
                continue
                
            locale_name = locale_names.get(locale, locale)
            group_name = f"═══ {locale_name} ═══"
            combo_box.addItem(group_name, "")
            combo_box.model().item(combo_box.count() - 1).setEnabled(False)
            
            for voice in voices_by_locale[locale]:
                display_name = voice.get("Name", voice.get("ShortName", "Unknown"))
                short_name = voice.get("ShortName", "")
                gender = voice.get("Gender", "")
                gender_mark = "♀" if gender == "Female" else "♂"
                final_name = f"{display_name} ({gender_mark})"
                combo_box.addItem(final_name, short_name)
        
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == self._selected_voice:
                combo_box.setCurrentIndex(i)
                break
        else:
            combo_box.setCurrentIndex(0)

    def _on_gemini_voice_changed(self, index):
        """Handle Gemini voice selection change - reconnect with new voice if active."""
        self._selected_gemini_voice = self.gemini_voice_combo.itemData(index)
        logging.info(f"Gemini voice changed to: {self._selected_gemini_voice}")
        
        # If we're in an active Google Live session, reconnect with the new voice
        if hasattr(self, 'is_live_mode') and self.is_live_mode and self.is_active:
            logging.info(f"Reconnecting with new voice: {self._selected_gemini_voice}")
            self.status_label.setText(f"Switching to {self._selected_gemini_voice}...")
            # Stop current session and start new one with selected voice
            self.api_client.stop_live_session()
            self.api_client.start_live_session(
                "Google", 
                self.current_model, 
                voice=self._selected_gemini_voice
            )

    def get_selected_voice(self):
        """Get the currently selected TTS voice."""
        voice = getattr(self, '_selected_voice', None)
        return voice if voice else 'Cherry'

    def get_selected_gemini_voice(self):
        """Get the currently selected Gemini voice."""
        voice = getattr(self, '_selected_gemini_voice', None)
        return voice if voice else 'Zephyr'

    def start_call(self, provider=None, model=None, voice=None):
        """Start voice call with specified provider/model/voice."""
        self.show()
        self.raise_()
        self.center_in_window()
        self.is_active = True
        
        self.current_provider = provider or "DashScope"
        self.current_model = model or "qwen3-omni-flash-2025-12-01"
        
        # Set voice if provided (from chat page header)
        # Also sync the combo box to show the correct voice
        if self.current_provider == "Google":
            if voice:
                self._selected_gemini_voice = voice
            # Sync combo box to match _selected_gemini_voice
            current_voice = self._selected_gemini_voice
            found = False
            for i in range(self.gemini_voice_combo.count()):
                if self.gemini_voice_combo.itemData(i) == current_voice:
                    self.gemini_voice_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found and self.gemini_voice_combo.count() > 0:
                # Voice not found, keep current selection but update _selected_gemini_voice
                actual_voice = self.gemini_voice_combo.currentData()
                if actual_voice:
                    self._selected_gemini_voice = actual_voice
                    logging.info(f"Voice '{current_voice}' not found, using current combo selection: {actual_voice}")
        elif self.current_provider == "DashScope":
            if voice:
                self._selected_voice = voice
            # Sync combo box
            current_voice = self._selected_voice
            for i in range(self.voice_combo.count()):
                if self.voice_combo.itemData(i) == current_voice:
                    self.voice_combo.setCurrentIndex(i)
                    break
        
        logging.info(f"Starting Copilot Voice Call: {self.current_provider} / {self.current_model}")
        
        # Show appropriate voice selector based on provider
        is_google = (self.current_provider == "Google")
        is_dashscope = (self.current_provider == "DashScope")
        self.voice_combo.setVisible(is_dashscope)
        self.gemini_voice_combo.setVisible(is_google)
        self.voice_label.setVisible(is_dashscope or is_google)  # Show label for both
        
        self.is_live_mode = False
        
        # Check if using Qwen Realtime model (supports VAD and real-time transcription)
        is_qwen_realtime = (
            self.current_provider == "DashScope" and 
            "realtime" in self.current_model.lower()
        )
        
        if self.current_provider == "Google":
            self.status_label.setText("Connecting...")
            self.is_live_mode = True
            selected_voice = self.get_selected_gemini_voice()
            logging.info(f"Using Gemini voice: {selected_voice}")
            self.api_client.start_live_session("Google", self.current_model, voice=selected_voice)
            self.mic_btn.start_pulsing() # Pulse while connecting
            return
        
        # Qwen Realtime mode - uses WebSocket with VAD support
        if is_qwen_realtime:
            self.status_label.setText("Connecting...")
            self.is_live_mode = True
            selected_voice = self.get_selected_voice()
            logging.info(f"Using Qwen Realtime with voice: {selected_voice}")
            # Start Qwen Realtime session with VAD enabled
            self.api_client.start_qwen_realtime_session(
                model=self.current_model,
                voice=selected_voice,
                region="cn"  # TODO: Make this configurable
            )
            self.mic_btn.start_pulsing()
            return

        self.toggle_listening() # Auto-start for normal mode

    def close_overlay(self):
        self.is_active = False
        self.stop_all()
        self.hide()
        self.closed.emit()

    def stop_all(self):
        self.recorder.stop_recording()
        self.player.stop()
        if hasattr(self, 'is_live_mode') and self.is_live_mode:
            self.api_client.stop_live_session()
        self.current_state = "IDLE"
        self.update_status_ui()
        self.mic_btn.stop_pulsing()
        # Clear transcript buffer
        self._user_transcript_timer.stop()
        self._user_transcript_buffer = ""

    def toggle_listening(self):
        if self.current_state == "LISTENING":
            self.recorder.stop_recording()
        elif self.current_state == "SPEAKING":
            logging.info("User interrupted AI during SPEAKING state")
            self.player.stop()
            self._speaking_timeout_timer.stop()
            self.recorder.start_recording()
            self.current_state = "LISTENING"
            self.update_status_ui()
        else:
            self.recorder.start_recording()
            self.current_state = "LISTENING"
            self.update_status_ui()

    def _on_recording_stopped(self, file_path):
        if not self.is_active: return
        if hasattr(self, 'is_live_mode') and self.is_live_mode: return 

        self.current_state = "THINKING"
        self.update_status_ui()
        self.status_label.setText("Thinking...")
        self.mic_btn.stop_pulsing()
        
        # Emit a placeholder for user input (fast, no separate ASR)
        self.user_transcript.emit("[🎤 语音输入]")
        
        provider = getattr(self, 'current_provider', 'DashScope')
        model = getattr(self, 'current_model', 'qwen3-omni-flash-2025-12-01')
        
        # Get conversation history from provider callback
        history = []
        if self.history_provider and callable(self.history_provider):
            history = self.history_provider()
        
        # Send directly to Omni API for fastest response
        self.api_client.start_chat_request_async(
            provider, model, user_message="", 
            file_path=file_path, file_type='audio', 
            audio_output=True, history=history,
            voice=self._selected_voice
        )

    def _on_transcription_finished(self, text):
        if not self.is_active: return
        # Not used in fast Omni flow - kept for potential future use
        pass

    def _on_live_session_started(self):
        self.status_label.setText("Listening...")
        self.is_live_mode = True
        self.recorder.set_continuous_mode(True)
        self.recorder.start_recording()
        self.current_state = "LISTENING"
        self.update_status_ui()
        
        # AI greets first - like Siri/Google Assistant
        # Send a prompt to make the AI greet the user naturally
        self._send_ai_greeting()
    
    def _on_live_session_stopped(self):
        self.status_label.setText("Disconnected")
        self.recorder.set_continuous_mode(False)
        self.recorder.stop_recording()
        self.current_state = "IDLE"
        self.update_status_ui()
        self.mic_btn.stop_pulsing()

    def _on_recorder_chunk_ready(self, chunk):
        if not self.is_active: return
        if hasattr(self, 'is_live_mode') and self.is_live_mode:
            # Check if it's a Qwen Realtime session
            if hasattr(self.api_client, 'live_session') and self.api_client.live_session:
                from app.core.api_client import QwenRealtimeSession
                if isinstance(self.api_client.live_session, QwenRealtimeSession):
                    self.api_client.send_qwen_realtime_audio(chunk)
                else:
                    self.api_client.send_live_audio_chunk(chunk)
            else:
                self.api_client.send_live_audio_chunk(chunk)

    def _on_api_audio_received(self, chunk):
        if not self.is_active: return

        if self.current_state != "SPEAKING":
            # AI started responding - flush user transcript NOW
            self._user_transcript_timer.stop()
            self._flush_user_transcript()

            self.current_state = "SPEAKING"
            self.update_status_ui()

        # Only play API audio if not using custom TTS
        if not self.use_custom_tts:
            self.player.append_audio_chunk(chunk)

        if hasattr(self, 'is_live_mode') and self.is_live_mode:
            self._speaking_timeout_timer.start(self._speaking_timeout_ms)

    def _on_live_text_received(self, text):
        if not self.is_active: return
        self.ai_response_text.emit(text)
        # Accumulate text for custom TTS
        if self.use_custom_tts:
            self._pending_tts_text += text
    
    def _on_user_transcript_received(self, text):
        if not self.is_active: return
        # Accumulate transcript chunks instead of emitting immediately
        self._user_transcript_buffer += text
        # Reset timer on each new chunk
        self._user_transcript_timer.start(self._user_transcript_delay_ms)
    
    def _flush_user_transcript(self):
        """Emit accumulated user transcript after delay."""
        if self._user_transcript_buffer.strip():
            self.user_transcript.emit(self._user_transcript_buffer.strip())
            self._user_transcript_buffer = ""
    
    def _on_speaking_timeout(self):
        if not self.is_active: return
        if self.current_state == "SPEAKING":
            logging.info("Speaking timeout - restoring LISTENING state")
            self.ai_response_finished.emit()  # Notify to save AI response to DB
            # Trigger custom TTS if enabled and we have text
            self._trigger_custom_tts()
            self.current_state = "LISTENING"
            self.update_status_ui()
    
    def _on_ai_interrupted(self):
        """Handle AI being interrupted by user speech (VAD detected)."""
        if not self.is_active: return
        logging.info("AI was interrupted - stopping playback and switching to LISTENING")
        self._speaking_timeout_timer.stop()  # Cancel timeout
        self.player.stop()  # Stop audio playback
        self.current_state = "LISTENING"
        self.update_status_ui()
    
    def _on_ai_turn_complete(self):
        """Handle AI finishing its turn (VAD: ready for user input)."""
        if not self.is_active: return
        if self.current_state == "SPEAKING":
            logging.info("AI turn complete - switching to LISTENING")
            self._speaking_timeout_timer.stop()  # Cancel timeout since we got proper signal
            self.ai_response_finished.emit()  # Notify to save AI response to DB
            # Trigger custom TTS if enabled and we have text
            self._trigger_custom_tts()
            self.current_state = "LISTENING"
            self.update_status_ui()

    def _trigger_custom_tts(self):
        """Trigger TTS for accumulated AI text if custom TTS is enabled."""
        if self.use_custom_tts and self._pending_tts_text.strip():
            voice = self.get_selected_voice()
            logging.info(f"Triggering custom TTS with voice: {voice}, text: {self._pending_tts_text[:50]}...")
            self.tts_request.emit(self._pending_tts_text.strip(), voice)
            self._pending_tts_text = ""

    def _update_input_visual(self, level):
        # Could adjust ripple size based on level
        pass

    def update_status_ui(self):
        if self.current_state == "LISTENING":
            self.status_label.setText("Listening...")
            self.mic_btn.start_pulsing()
            # Set Pulse Color to burnt orange to match app theme
        elif self.current_state == "THINKING":
            self.status_label.setText("Thinking...")
            self.mic_btn.start_pulsing()
            # Set Pulse Color to burnt orange to match app theme
        elif self.current_state == "SPEAKING":
            self.status_label.setText("Speaking...")
            self.mic_btn.start_pulsing()
            # Set Pulse Color to burnt orange to match app theme
        else:
            self.status_label.setText("Get Started")
            self.mic_btn.stop_pulsing()

    def _on_text_chunk_received(self, text_chunk):
        pass
    
    def _on_stream_finished(self):
        if not self.is_active: return
        self.current_state = "IDLE"
        self.update_status_ui()

    def _send_ai_greeting(self):
        """Send a prompt to make the AI greet the user naturally.
        
        This creates a friendly experience like Siri/Google Assistant.
        The greeting will be spoken by AI but won't affect session title
        since title is based on user's first message.
        """
        if not hasattr(self, 'is_live_mode') or not self.is_live_mode:
            return
        
        # Send a hidden prompt to initiate greeting
        # The AI will respond naturally with a greeting
        greeting_prompt = (
            "[System: The user just connected. Please greet them briefly and naturally "
            "in English, like 'Hi there! How can I help you today?' - keep it short and friendly.]"
        )
        
        if self.api_client.live_session:
            logging.info("Sending AI greeting prompt")
            self.api_client.live_session.send_data(greeting_prompt)
