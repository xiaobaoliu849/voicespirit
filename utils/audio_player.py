import logging
import os
import time
import threading
import sys
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from pathlib import Path  # Ensure Path is imported

# 资源路径辅助函数
def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹并将路径存储在_MEIPASS中
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path is None:
            # 如果不是PyInstaller环境，使用当前目录
            base_path = os.path.abspath(".")
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Handle miniaudio import error
try:
    import miniaudio
except ImportError:
    logging.error("miniaudio library not found. Audio playback will be disabled. Install with: pip install miniaudio")
    miniaudio = None

class AudioPlayer(QObject):
    """Handles audio playback using miniaudio."""

    # Signals
    playback_started = Signal()
    playback_finished = Signal()
    playback_error = Signal(str)
    position_changed = Signal(float, float)  # (elapsed_seconds, total_seconds)

    def __init__(self, parent=None):
        super().__init__(parent)
        if not miniaudio:
            logging.warning("AudioPlayer initialized but miniaudio is not available.")
            return

        self.device = None
        self.stream = None
        self._playback_thread = None
        self._stop_event = threading.Event()
        self._current_file_path = None # Store path for cleanup
        self._is_paused = False
        self._elapsed_time = 0.0
        self._total_duration = 0.0

    def is_available(self):
        """Check if miniaudio was imported successfully."""
        return miniaudio is not None

    def supports_pause(self):
        """Returns True if the player supports pausing."""
        return True

    @Slot(str)
    def play_file(self, file_path):
        """Plays the audio file at the given path in a separate thread."""
        if not self.is_available():
            self.playback_error.emit("miniaudio library not found. Please install it using 'pip install miniaudio'.")
            return
        if not Path(file_path).exists() or os.path.getsize(file_path) == 0:
            logging.error(f"Audio file invalid or empty: {file_path}")
            self.playback_error.emit(f"Audio file invalid or empty: {file_path}")
            return

        try:
            self.stop()  # Stop any previous playback first
            self._current_file_path = file_path
            self._stop_event.clear()
            self._playback_thread = threading.Thread(target=self._play_in_thread, args=(file_path,))
            self._playback_thread.daemon = True  # Allow app to exit even if thread is running
            self._playback_thread.start()
        except Exception as e:
            logging.error(f"Error starting playback thread: {e}", exc_info=True)
            self.playback_error.emit(f"Error starting playback: {e}")

    def _play_in_thread(self, file_path):
        """Internal method to handle playback within the thread."""
        try:
            logging.info(f"AudioPlayer Thread: Starting playback for {file_path}")
            
            # Get audio duration for proper completion detection
            try:
                file_info = miniaudio.mp3_get_file_info(file_path)
                duration_seconds = file_info.duration
                logging.info(f"Audio duration: {duration_seconds:.2f} seconds")
            except Exception as e:
                logging.warning(f"Could not get audio duration: {e}, using fallback")
                duration_seconds = 60  # Fallback to 60 seconds max
            
            self.playback_started.emit()

            self.stream = miniaudio.stream_file(file_path)
            self.device = miniaudio.PlaybackDevice()
            self.device.start(self.stream)
            self._is_paused = False
            
            # Track elapsed time for completion detection
            start_time = time.time()
            self._total_duration = duration_seconds
            self._elapsed_time = 0.0
            last_position_emit = 0.0

            # Wait for playback to complete (either naturally by duration or by stop request)
            while not self._stop_event.is_set():
                time.sleep(0.1)
                if not self._is_paused:
                    elapsed = time.time() - start_time
                    self._elapsed_time = elapsed
                    
                    # Emit position every ~100ms
                    if elapsed - last_position_emit >= 0.1:
                        self.position_changed.emit(elapsed, duration_seconds)
                        last_position_emit = elapsed
                    
                    # Add small buffer (0.5s) to ensure audio fully plays
                    if elapsed >= duration_seconds + 0.5:
                        break
                
            if self._stop_event.is_set():
                logging.info(f"AudioPlayer Thread: Playback stopped by request for {file_path}")
            else:
                logging.info(f"AudioPlayer Thread: Playback finished naturally for {file_path}")

            self.playback_finished.emit()

        except miniaudio.DecodeError as de:
            logging.error(f"Miniaudio Decode Error playing {file_path}: {de}", exc_info=True)
            self.playback_error.emit(f"Playback failed (Decode Error): {de}")
        except Exception as e:
            logging.error(f"AudioPlayer Thread: Error during playback of {file_path}: {e}", exc_info=True)
            self.playback_error.emit(f"Playback failed: {e}")
        finally:
            # Ensure resources are released
            if self.device and hasattr(self.device, 'close') and callable(self.device.close):
                 try: self.device.close()
                 except Exception as ce: logging.warning(f"Error closing audio device: {ce}")
            # Clear references
            self.device = None
            self.stream = None
            self._is_paused = False
            logging.debug(f"AudioPlayer Thread: Playback thread finished for {file_path}")


    @Slot()
    def stop(self):
        """Stops the currently playing audio."""
        if not self.is_available(): return

        if self._playback_thread and self._playback_thread.is_alive():
            logging.info("AudioPlayer: Requesting playback stop...")
            self._stop_event.set()
            # Wait briefly for the thread to potentially finish cleanup
            self._playback_thread.join(timeout=0.5)
            if self._playback_thread.is_alive():
                 logging.warning("AudioPlayer: Playback thread did not stop gracefully.")
            self._playback_thread = None
        else:
            # Ensure stop event is set even if thread is already finished/not started
            self._stop_event.set()

    def pause(self):
        """Pause playback if supported. Returns True if successful."""
        if not self.is_available():
            return False
        if self.device and hasattr(self.device, 'stop') and not self._is_paused:
            try:
                self.device.stop()
                self._is_paused = True
                logging.info("Audio playback paused.")
                return True
            except Exception as e:
                logging.error(f"Failed to pause playback: {e}")
                return False
        return False

    def resume(self):
        """Resume playback if supported. Returns True if successful."""
        if not self.is_available():
            return False
        if self.device and self.stream and self._is_paused:
            try:
                self.device.start(self.stream)
                self._is_paused = False
                logging.info("Audio playback resumed.")
                return True
            except Exception as e:
                logging.error(f"Failed to resume playback: {e}")
                return False
        return False

# Example usage (for testing standalone)
if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
    import sys

    logging.basicConfig(level=logging.INFO)

    # Create a dummy mp3 file for testing
    dummy_file = "dummy_audio.mp3"
    try:
        # This requires ffmpeg to be installed and in PATH
        # Or use a real short mp3 file
        os.system(f"ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 1 -q:a 9 {dummy_file} -y")
        if not os.path.exists(dummy_file): raise FileNotFoundError
    except Exception:
        print(f"Could not create dummy audio file '{dummy_file}'. Place a real MP3 file with this name for testing.")
        sys.exit(1)


    app = QApplication(sys.argv)

    class TestWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.player = AudioPlayer()
            if not self.player.is_available():
                 print("Miniaudio not available, exiting test.")
                 QTimer.singleShot(0, app.quit) # Quit immediately
                 return

            self.layout = QVBoxLayout(self)
            self.play_button = QPushButton("Play Dummy Audio")
            self.stop_button = QPushButton("Stop Audio")
            self.layout.addWidget(self.play_button)
            self.layout.addWidget(self.stop_button)

            self.play_button.clicked.connect(lambda: self.player.play_file(dummy_file))
            self.stop_button.clicked.connect(self.player.stop)

            self.player.playback_started.connect(lambda: print("Event: Playback Started"))
            self.player.playback_finished.connect(lambda: print("Event: Playback Finished"))
            self.player.playback_error.connect(lambda err: print(f"Event: Playback Error: {err}"))

        def closeEvent(self, event):
             print("Stopping player on close...")
             self.player.stop()
             # Clean up dummy file
             if os.path.exists(dummy_file):
                 try: os.remove(dummy_file)
                 except Exception as e: print(f"Could not remove dummy file: {e}")
             event.accept()


    widget = TestWidget()
    if widget.player.is_available(): # Only show if player is usable
        widget.setWindowTitle("Audio Player Test")
        widget.show()
        sys.exit(app.exec())
