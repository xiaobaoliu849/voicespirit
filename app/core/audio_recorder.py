import logging
import io
import wave
import struct
import math
import tempfile
import os
from PySide6.QtCore import QObject, Signal, QIODevice, QByteArray, QTimer
from PySide6.QtMultimedia import QAudioSource, QMediaDevices, QAudioFormat

class AudioRecorder(QObject):
    """
    Captures audio from the microphone using PySide6.QtMultimedia.
    Provides simple energy-based VAD (Voice Activity Detection) signals.
    """
    input_level = Signal(float) # Emits current RMS level (0.0 to 1.0)
    recording_started = Signal()
    recording_stopped = Signal(str) # Emits path to saved WAV file
    audio_chunk_ready = Signal(bytes) # NEW: Emits raw audio bytes for streaming
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_source = None
        self.io_device = None
        self.buffer = QByteArray()
        self.is_recording = False
        
        # Audio Format Settings (Standard for Gemini Live API)
        # INPUT: 16-bit PCM, 16kHz, mono (REQUIRED by Gemini Live)
        # OUTPUT from Gemini: 24kHz
        self.format = QAudioFormat()
        self.format.setSampleRate(16000)  # CRITICAL: Gemini Live requires 16kHz input
        self.format.setChannelCount(1)
        self.format.setSampleFormat(QAudioFormat.Int16)
        
        # VAD Settings
        self.vad_threshold = 0.02 # Adjustable
        self.silence_timer = QTimer(self)
        self.silence_timer.setInterval(3000) # 3s silence triggers stop (more time for user)
        self.silence_timer.setSingleShot(True)
        self.silence_timer.timeout.connect(self._on_silence_timeout)
        self.voice_detected = False
        
        # Continuous mode: disable VAD auto-stop for Live streaming
        self.continuous_mode = False

    def start_recording(self):
        if self.is_recording:
            return

        device = QMediaDevices.defaultAudioInput()
        if not device:
            logging.error("No default audio input device found.")
            return

        self.audio_source = QAudioSource(device, self.format)
        self.io_device = self.audio_source.start()
        
        if not self.io_device:
            logging.error("Failed to start audio source.")
            return

        self.io_device.readyRead.connect(self._read_data)
        self.buffer.clear()
        self.is_recording = True
        self.voice_detected = False
        self.recording_started.emit()
        logging.info("Audio recording started.")

    def stop_recording(self):
        if not self.is_recording:
            return

        if self.audio_source:
            self.audio_source.stop()
            self.audio_source = None
            self.io_device = None
        
        self.silence_timer.stop()
        self.is_recording = False
        
        # Save to temp file
        if self.buffer.size() > 0:
            file_path = self._save_to_wav()
            self.recording_stopped.emit(file_path)
            logging.info(f"Audio recording stopped. Saved to {file_path}")
        else:
            logging.warning("Audio buffer empty. No file saved.")

    def _read_data(self):
        if not self.io_device:
            return
            
        data = self.io_device.readAll()
        if data.size() > 0:
            self.buffer.append(data)
            # NEW: Emit raw bytes for streaming
            self.audio_chunk_ready.emit(data.data())
            self._process_vad(data)

    def _process_vad(self, data: QByteArray):
        # Calculate RMS
        # Convert QByteArray to bytes, then list of shorts
        raw_bytes = data.data()
        count = len(raw_bytes) // 2
        shorts = struct.unpack(f"{count}h", raw_bytes)
        
        sum_squares = 0.0
        for s in shorts:
            sum_squares += s * s
            
        rms = math.sqrt(sum_squares / count) / 32768.0 # Normalize to 0-1
        self.input_level.emit(rms)
        
        if rms > self.vad_threshold:
            self.voice_detected = True
            self.silence_timer.start() # Reset timer
        
        # Logic: If we haven't detected voice yet, we don't start the silence timer?
        # Or we rely on manual stop for now?
        # User requested VAD loop for "Phone Call" experience.
        # Simple Logic: Once voice is triggered (> threshold), any subsequent silence > 1.5s triggers stop.
        
    def _on_silence_timeout(self):
        # In continuous mode, don't auto-stop on silence
        if self.continuous_mode:
            return
        if self.voice_detected and self.is_recording:
            logging.info("Silence detected. Stopping recording.")
            self.stop_recording()
    
    def set_continuous_mode(self, enabled: bool):
        """Enable/disable continuous recording mode (no VAD auto-stop)."""
        self.continuous_mode = enabled
        logging.info(f"Recorder continuous mode: {enabled}")

    def _save_to_wav(self):
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"mic_input_{os.getpid()}.wav")
        
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2) # 16-bit
                wf.setframerate(24000)
                wf.writeframes(self.buffer.data())
            return file_path
        except Exception as e:
            logging.error(f"Failed to save WAV file: {e}")
            return None
