import logging
from PySide6.QtCore import QObject, QIODevice, QByteArray
from PySide6.QtMultimedia import QAudioSink, QMediaDevices, QAudioFormat, QAudio

class AudioStreamBuffer(QIODevice):
    """Simple internal buffer that acts as an IO Device for QAudioSink."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = QByteArray()
        self.open(QIODevice.ReadOnly) # We read FROM this buffer TO the sink

    def readData(self, maxlen):
        """Read data from buffer to sink."""
        if self._data.isEmpty():
            return b""
        
        # Determine how much to read
        length = min(maxlen, self._data.size())
        chunk = self._data[:length]
        self._data = self._data[length:] # Remove read data
        return chunk.data() # Return bytes

    def writeData(self, data):
        """Not used for ReadOnly device."""
        return 0
    
    def append_data(self, data: bytes):
        """External method to add data."""
        self._data.append(data)
        self.readyRead.emit() # Notify sink new data is available

    def bytesAvailable(self):
        return self._data.size() + super().bytesAvailable()

    def isSequential(self):
        return True


class AudioStreamPlayer(QObject):
    """
    Plays raw PCM audio chunks in real-time.
    Designed to work with Qwen Omni's 24kHz/16-bit Mono output.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_sink = None
        self.io_device = None
        self.buffer_device = AudioStreamBuffer(self)
        
        # Audio Format Settings (Must match API output)
        self.format = QAudioFormat()
        self.format.setSampleRate(24000)
        self.format.setChannelCount(1)
        self.format.setSampleFormat(QAudioFormat.Int16)

        self._init_sink()

    def _init_sink(self):
        device = QMediaDevices.defaultAudioOutput()
        if not device:
            logging.error("No default audio output device found.")
            return

        self.audio_sink = QAudioSink(device, self.format)
        # We start the sink immediately, pulling from our buffer device
        self.audio_sink.start(self.buffer_device)

    def append_audio_chunk(self, chunk: bytes):
        """Add raw PCM bytes to the playback queue."""
        if not self.audio_sink:
            self._init_sink()
        
        if self.audio_sink.state() == QAudio.State.StoppedState:
            self.audio_sink.start(self.buffer_device)
            
        self.buffer_device.append_data(chunk)

    def stop(self):
        if self.audio_sink:
            self.audio_sink.stop()
            self.buffer_device._data.clear()
