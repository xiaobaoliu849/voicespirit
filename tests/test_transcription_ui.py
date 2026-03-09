import os
import pytest
from PySide6.QtWidgets import QApplication
from app.ui.pages.transcription_page import TranscriptionPage
from app.core.api_client import ApiClient
from app.core.config import ConfigManager
from app.core.translation import TranslationManager
from PySide6.QtCore import QThreadPool, Signal

class MockApiClient(ApiClient):
    """Mock API Client to simulate transcription success without real API hits."""
    # Override signal just for the mock to avoid meta object issues
    transcription_finished = Signal(str)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_transcription_called = False

    def start_transcription_request_async(self, file_path):
        self.mock_transcription_called = True
        # Simulate an immediate finish instead of a real thread worker
        self.transcription_finished.emit(f"Mocked transcription for: {os.path.basename(file_path)}")

def test_transcription_page_smoke(qtbot):
    """
    Smoke test to verify TranscriptionPage layout loads,
    accepts a mock file, triggers the UI state change,
    and handles the mock api success signal.
    """
    # Setup mocks
    config = ConfigManager()
    translation = TranslationManager(config)
    mock_api = MockApiClient(config, QThreadPool.globalInstance())

    # Initialize Page
    page = TranscriptionPage(
        api_client=mock_api,
        translation_manager=translation,
        config_manager=config
    )
    qtbot.addWidget(page)

    # 1. Initial State Check
    assert not page.transcribe_btn.isEnabled(), "Transcribe button should be disabled initially."
    assert page.text_area.toPlainText() == "", "Text area should be empty initially."

    # 2. Simulate File Drop/Selection
    dummy_file = "dummy_audio.mp3"
    page._on_file_selected(dummy_file)
    
    # State should update to ready
    assert page.transcribe_btn.isEnabled(), "Transcribe button should be enabled after file selection."
    assert dummy_file in page.status_label.text(), "Status label should reflect the selected file."

    # 3. Simulate Clicking Transcribe
    page.transcribe_btn.click()
    
    # The mock API should have been called
    assert mock_api.mock_transcription_called, "The API client should have been invoked."
    
    # Check the result of the mocked signal emitting
    # (Since it's emitted synchronously in our mock, we check state immediately)
    assert not page.is_transcribing, "Page should not be transcribing after success signal."
    assert "Mocked transcription for: dummy_audio.mp3" in page.text_area.toPlainText()
    assert "✅" in page.status_label.text(), "Status label should show success."
    assert page.transcribe_btn.isEnabled(), "Button should be re-enabled after completion."
