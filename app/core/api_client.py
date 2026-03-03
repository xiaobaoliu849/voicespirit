import logging
import base64
import mimetypes
import os
import re
from typing import List
import time
import requests
import httpx
from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QThreadPool
from tenacity import retry, stop_after_attempt, wait_fixed
try:
    import websockets.exceptions
except ImportError:
    websockets = None
from app.core.config import ConfigManager # Updated import

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from openai import OpenAI, APIError, RateLimitError, AuthenticationError
    from openai.types.chat import ChatCompletionChunk # Explicit import for type hinting
except ImportError:
    logging.error("OpenAI library not found. Please install it: pip install openai")
    OpenAI = None # Placeholder
    ChatCompletionChunk = None # Placeholder

try:
    from groq import Groq, APIError as GroqAPIError, RateLimitError as GroqRateLimitError
except ImportError:
    logging.error("Groq library not found. Please install it: pip install groq")
    Groq = None # Placeholder
    GroqAPIError = Exception
    GroqRateLimitError = Exception

# Gemini Live Imports
import asyncio
import traceback
import queue
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
    logging.error("google-genai library not found. Please install it: pip install google-genai")

try:
    import dashscope
    print("Dashscope导入成功")
    print("Dashscope位置：", dashscope.__file__)
    # 检查ImageSynthesis是否可用
    if hasattr(dashscope, 'ImageSynthesis'):
        print("ImageSynthesis导入成功")
        from dashscope import ImageSynthesis
        # 使用更通用的错误处理
        DashScopeAPIError = Exception
        RequestError = Exception
        RateLimitExceededError = Exception
        InternalServerError = Exception
        logging.info("Using generic exceptions for DashScope error handling")
    else:
        print("ImageSynthesis未找到")
        ImageSynthesis = None
        DashScopeException = Exception
        logging.error("DashScope SDK not完整 - ImageSynthesis未找到")
except ImportError as e:
    print("Dashscope导入失败：", str(e))
    print("详细错误：", e)
    # Keep existing fallback logic
    ImageSynthesis = None
    DashScopeException = Exception
    logging.error("DashScope SDK not found. Please install it: pip install dashscope")

# Import Worker from tts_handler (or define it here if preferred)
# Assuming it's accessible or defined elsewhere if needed for async calls within ApiClient
# from .tts_handler import AsyncWorker, WorkerSignals # Example if defined there

# --- Worker Definition (Copied from tts_handler for self-containment if needed) ---
# Or better, create a shared utils/worker.py
class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int) # Or other types as needed
    models_fetched = Signal(str, list) # provider_name, models_list
    translation_result = Signal(str) # translated_text
    transcription_finished = Signal(str) # NEW
    stream_finished = Signal()
    # Image Generation Signals
    image_urls_fetched = Signal(list) # List of image URLs
    image_generation_error = Signal(str) # Error message during image generation

class AsyncWorker(QRunnable): 
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals() # Create signals

    @Slot()
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs) # 修正这里

            # --- Emit specific signals based on function called ---
            if self.func.__name__ == '_fetch_models':
                # Expect result to be model_ids list, args[0] is provider_name
                provider_name = self.args[0]
                if isinstance(result, list):
                    self.signals.models_fetched.emit(provider_name, result)
                else:
                    # Handle unexpected result type from _fetch_models
                    err_msg = f"Model fetch for {provider_name} returned unexpected type: {type(result)}"
                    logging.error(err_msg)
                    self.signals.error.emit(err_msg)
            elif self.func.__name__ == '_execute_translation_request':
                # Expect result to be translated_text string
                if isinstance(result, str):
                    self.signals.translation_result.emit(result)
                else:
                    # Handle unexpected result type from translation
                    err_msg = f"Translation request returned unexpected type: {type(result)}"
                    logging.error(err_msg)
                    self.signals.error.emit(err_msg) # Emit generic error
            elif self.func.__name__ == '_execute_image_translation_request':
                # Expect result to be translated_text string
                if isinstance(result, str):
                    self.signals.translation_result.emit(result) # Use the existing signal name for consistency
                else:
                    # Handle unexpected result type from image translation
                    err_msg = f"Image translation request returned unexpected type: {type(result)}"
                    logging.error(err_msg)
                    self.signals.error.emit(err_msg) # Emit generic error
            elif self.func.__name__ == '_execute_chat_request':
                 # This function handles streaming internally and emits chunks directly.
                 # It returns None when done. We emit stream_finished here.
                self.signals.stream_finished.emit()
            elif self.func.__name__ in ('generate_image_dashscope', '_generate_image_dashscope'):
                # Expect result to be a list of URLs
                if isinstance(result, list):
                    self.signals.image_urls_fetched.emit(result)
                else:
                    # Handle unexpected result type from image generation
                    err_msg = f"Image generation returned unexpected type: {type(result)}"
                    logging.error(err_msg)
                    # Emit specific image error signal
                    self.signals.image_generation_error.emit(err_msg)
            elif self.func.__name__ == '_execute_transcription_request':
                self.signals.transcription_finished.emit(result)
            elif self.func.__name__ in ('_list_qwen_voices', '_create_voice_design', '_create_voice_clone', '_delete_qwen_voice'):
                self.signals.finished.emit(result)
            else:
                # Fallback for unknown functions (if any)
                logging.warning(f"AsyncWorker finished unknown function: {self.func.__name__}")
                # self.signals.finished.emit(result) # Emit generic if needed

        except Exception as e:
            logging.error(f"ApiClient Worker error running {self.func.__name__}: {e}", exc_info=True)
            # --- Emit specific error signal if possible ---
            error_msg = str(e)
            # Add context if possible (e.g., provider name from args)
            provider_ctx = ""
            func_name = self.func.__name__
            if self.args: provider_ctx = f" ({self.args[0]})" if isinstance(self.args[0], str) else ""

            # Route error to the correct signal
            if func_name == '_fetch_models':
                self.signals.error.emit(f"Error in {func_name}{provider_ctx}: {error_msg}") # Use generic error for now
            elif func_name == '_execute_translation_request' or func_name == '_execute_image_translation_request': # Handle both text and image translation errors
                self.signals.error.emit(f"Error in {func_name}{provider_ctx}: {error_msg}") # Use generic error for now
            elif func_name == '_execute_chat_request':
                self.signals.error.emit(f"Error in {func_name}{provider_ctx}: {error_msg}") # Use generic error for now
            elif func_name in ('generate_image_dashscope', '_generate_image_dashscope'):
                # Emit specific image generation error signal
                self.signals.image_generation_error.emit(f"Error in {func_name}{provider_ctx}: {error_msg}")
            else:
                # Fallback for unknown function errors
                self.signals.error.emit(f"Error in {func_name}{provider_ctx}: {error_msg}")


# --- Gemini Live Session Worker ---
class GeminiLiveSession(QObject, QRunnable):
    """
    Worker for Google Gemini Live API (WebSockets)
    Wraps the asyncio loop for the google-genai library in a QRunnable.
    Supports session resumption for long-running conversations.
    """
    # Signals
    connection_opened = Signal()
    connection_closed = Signal()
    connection_error = Signal(str)
    audio_output_ready = Signal(bytes)  # Received audio from AI
    text_output_ready = Signal(str)     # AI's speech transcribed to text
    user_transcript_ready = Signal(str) # User's speech transcribed to text
    interrupted = Signal()               # AI was interrupted by user
    turn_complete = Signal()             # AI finished speaking (turn ended)
    goaway_received = Signal()           # Server sending GoAway (disconnect warning)
    session_resumption_update = Signal(str)  # New resumption token received

    def __init__(self, api_key, model, api_url=None, config=None, resumption_token=None, voice_name="Zephyr"):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.setAutoDelete(True) # Auto-delete when run() finishes
        self.api_key = api_key
        self.model = model
        self.api_url = api_url # Store custom API URL
        self.config = config
        self.voice_name = voice_name  # TTS voice selection
        
        # Session resumption state
        self.resumption_token = resumption_token  # Token for reconnection
        self.latest_resumption_token = None       # Updated by server during session
        
        # Thread-safe queue for input from main thread
        self.input_queue = queue.Queue() 
        self.stopping = False
        self.loop = None
        self.session = None

    @Slot()
    def run(self):
        # Create a new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
             self.loop.run_until_complete(self._run_async_session())
        except Exception as e:
            self.connection_error.emit(str(e))
            logging.error(f"Gemini Live Session Error: {e}", exc_info=True)
        finally:
            self.loop.close()
            self.connection_closed.emit()
            logging.info("Gemini Live Session Loop Closed.")

    async def _run_async_session(self):
        if not genai:
             raise ImportError("google-genai library not installed.")
        
        logging.info(f"Connecting to Gemini Live: {self.model}")
        
        # Configure HTTP options
        http_options = {"api_version": "v1beta"}
        if self.api_url:
            logging.info(f"Using custom API URL for Gemini Live: {self.api_url}")
            http_options["base_url"] = self.api_url
            
        client = genai.Client(api_key=self.api_key, http_options=http_options)
        
        # Configure Live Connect (based on official documentation)
        # NOTE: Gemini Live API only supports one response modality at a time (TEXT or AUDIO)
        # Enable transcription for both input (user) and output (AI) audio
        # Configure VAD (Voice Activity Detection) for natural conversation
        
        # Build session resumption config
        if self.resumption_token:
            logging.info("Using resumption token for reconnection")
            session_resumption_config = types.SessionResumptionConfig(
                handle=self.resumption_token
            )
        else:
            # Enable session resumption to receive tokens for future reconnections
            session_resumption_config = types.SessionResumptionConfig()
        
        live_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            session_resumption=session_resumption_config,  # Enable session resumption
            system_instruction="You are a helpful, friendly, and intelligent AI assistant. Respond naturally and conversationally in the same language the user speaks.",
            input_audio_transcription=types.AudioTranscriptionConfig(),   # User's speech to text
            output_audio_transcription=types.AudioTranscriptionConfig(),  # AI's speech to text
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice_name)
                )
            ),
            # VAD Configuration - enables automatic speech detection
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,  # Enable automatic VAD
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,  # Quickly detect when user starts speaking
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,  # Quickly detect when user stops speaking
                    prefix_padding_ms=300,  # Include 300ms of audio before speech detected
                    silence_duration_ms=500,  # 500ms of silence = end of speech (shorter for faster response)
                )
            )
        )
        
        async with client.aio.live.connect(model=self.model, config=live_config) as session:
            self.session = session
            self.connection_opened.emit()
            logging.info("Gemini Live Session Connected.")
            
            # Start parallel tasks using asyncio.gather (Python 3.10 compatible)
            try:
                await asyncio.gather(
                    self._send_loop(),
                    self._receive_loop()
                )
            except Exception as e:
                logging.error(f"Error in Gemini Live tasks: {e}")
                
            logging.info("Gemini Live Session TaskGroup Finished.")

    async def _send_loop(self):
        logging.info("Send loop started")
        while not self.stopping:
            try:
                try:
                    item = await asyncio.to_thread(self.input_queue.get, timeout=0.1)
                except: # queue.Empty
                    await asyncio.sleep(0.01)
                    continue

                if item is None: # Sentinel
                    logging.info("Send loop received stop sentinel")
                    break
                
                if isinstance(item, bytes):
                    # Only log occasionally to reduce noise
                    # logging.debug(f"Sending audio chunk: {len(item)} bytes")
                    # Official API: use send_realtime_input for real-time audio streaming
                    # IMPORTANT: Must include sample rate in MIME type per official docs
                    await self.session.send_realtime_input(
                        audio=types.Blob(data=item, mime_type="audio/pcm;rate=16000")
                    )
                elif isinstance(item, str):
                    logging.info(f"Sending text: {item}")
                    await self.session.send(input=item, end_of_turn=True)
                
            except websockets.exceptions.ConnectionClosedError as e:
                logging.error(f"WebSocket connection closed: {e}")
                self.connection_error.emit(f"连接已断开: {e}")
                break
            except Exception as e:
                logging.error(f"Error in send loop: {e}", exc_info=True)
                # Don't break on all errors, only on connection errors
                if "ConnectionReset" in str(type(e).__name__) or "closed" in str(e).lower():
                    self.connection_error.emit(f"连接错误: {e}")
                    break
                # For other errors, continue trying
                await asyncio.sleep(0.1)
                
        logging.info("Send loop ended")

    async def _receive_loop(self):
        """Receive loop following official Google AI Studio example pattern."""
        logging.info("Receive loop started")
        try:
            while not self.stopping:
                turn = self.session.receive()
                async for response in turn:
                    if self.stopping:
                        break
                    
                    # DEBUG: Log response attributes to understand structure
                    resp_attrs = [a for a in dir(response) if not a.startswith('_') and getattr(response, a, None)]
                    logging.debug(f"Response attrs with values: {resp_attrs}")
                    
                    # Primary: Direct data/text (official API pattern)
                    if data := response.data:
                        logging.debug(f"Received audio: {len(data)} bytes")
                        self.audio_output_ready.emit(data)
                        continue
                    
                    if text := response.text:
                        logging.info(f"Received text: {text}")
                        self.text_output_ready.emit(text)
                        continue
                    
                    # Handle session resumption update (token for reconnection)
                    if hasattr(response, 'session_resumption_update') and response.session_resumption_update:
                        update = response.session_resumption_update
                        if hasattr(update, 'new_handle') and update.new_handle:
                            self.latest_resumption_token = update.new_handle
                            self.session_resumption_update.emit(update.new_handle)
                            logging.info(f"Session resumption token updated (len={len(update.new_handle)})")
                        continue
                    
                    # Handle GoAway message (connection will close soon)
                    if hasattr(response, 'go_away') and response.go_away:
                        logging.warning("Received GoAway - connection will close in ~1 minute")
                        self.goaway_received.emit()
                        continue
                    
                    # Handle server_content for transcriptions and interruptions
                    if hasattr(response, 'server_content') and response.server_content:
                        sc = response.server_content
                        
                        # DEBUG: Log server_content attributes
                        sc_attrs = [a for a in dir(sc) if not a.startswith('_')]
                        logging.debug(f"server_content attrs: {sc_attrs}")
                        
                        # Handle interruption - user started speaking while AI was responding
                        if hasattr(sc, 'interrupted') and sc.interrupted:
                            logging.info("AI was interrupted by user - emitting signal")
                            self.interrupted.emit()  # Signal UI to stop playback
                            continue
                        
                        # Handle turn complete - AI finished its response
                        if hasattr(sc, 'turn_complete') and sc.turn_complete:
                            logging.info("AI turn complete - ready for user input")
                            self.turn_complete.emit()  # Signal UI that AI is done
                            continue
                        
                        # User's speech transcription (try multiple attribute names)
                        user_text = None
                        for attr in ['input_transcription', 'input_audio_transcription', 'transcription']:
                            if hasattr(sc, attr):
                                val = getattr(sc, attr)
                                if val:
                                    # Handle both string and object with .text
                                    user_text = val.text if hasattr(val, 'text') else str(val)
                                    break
                        if user_text:
                            logging.info(f"User said: {user_text}")
                            self.user_transcript_ready.emit(user_text)
                        
                        # AI's speech transcription (try multiple attribute names)
                        ai_text = None
                        for attr in ['output_transcription', 'output_audio_transcription']:
                            if hasattr(sc, attr):
                                val = getattr(sc, attr)
                                if val:
                                    ai_text = val.text if hasattr(val, 'text') else str(val)
                                    break
                        if ai_text:
                            logging.info(f"AI said: {ai_text}")
                            self.text_output_ready.emit(ai_text)
                    
        except Exception as e:
            if not self.stopping:
                logging.error(f"Error in receive loop: {e}", exc_info=True)

    def send_data(self, data):
        """Thread-safe method to put data into the queue."""
        self.input_queue.put(data)

    def stop(self):
        """Signals the session to stop."""
        self.stopping = True
        self.input_queue.put(None) # Wake up send loop


# --- Qwen Realtime Session Worker ---
class QwenRealtimeSession(QObject, QRunnable):
    """
    Worker for Qwen Realtime API (WebSockets)
    Implements real-time voice conversation with VAD support.
    """
    # Signals
    connection_opened = Signal()
    connection_closed = Signal()
    connection_error = Signal(str)
    audio_output_ready = Signal(bytes)  # Received audio from AI
    text_output_ready = Signal(str)     # AI's speech transcribed to text
    user_transcript_ready = Signal(str) # User's speech transcribed to text
    interrupted = Signal()               # AI was interrupted by user
    turn_complete = Signal()             # AI finished speaking (turn ended)
    
    def __init__(self, api_key, model, voice="Cherry", region="cn"):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.setAutoDelete(True)
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.region = region  # "cn" for China, "intl" for Singapore
        
        # Thread-safe queue for input from main thread
        self.input_queue = queue.Queue()
        self.stopping = False
        self.loop = None
        self.conversation = None
        self._is_first_response = True
        
        # Audio format constants
        self.input_sample_rate = 16000  # PCM 16kHz for input
        self.output_sample_rate = 24000  # PCM 24kHz for output
        
        # Check dashscope availability
        self._dashscope_available = False
        self._check_dashscope()
    
    def _check_dashscope(self):
        """Check if DashScope SDK with Omni Realtime is available."""
        try:
            from dashscope.audio.qwen_omni import OmniRealtimeConversation, OmniRealtimeCallback, MultiModality, AudioFormat
            self._OmniRealtimeConversation = OmniRealtimeConversation
            self._OmniRealtimeCallback = OmniRealtimeCallback
            self._MultiModality = MultiModality
            self._AudioFormat = AudioFormat
            self._dashscope_available = True
            logging.info("DashScope Omni Realtime API available")
        except ImportError as e:
            logging.warning(f"DashScope Omni Realtime not available: {e}")
            self._dashscope_available = False
    
    @Slot()
    def run(self):
        if not self._dashscope_available:
            self.connection_error.emit("DashScope Omni Realtime API not available")
            return

        # Set dashscope API key globally for the SDK
        import dashscope
        dashscope.api_key = self.api_key

        # Create a new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._run_async_session())
        except Exception as e:
            self.connection_error.emit(str(e))
            logging.error(f"Qwen Realtime Session Error: {e}", exc_info=True)
        finally:
            self.loop.close()
            self.connection_closed.emit()
            logging.info("Qwen Realtime Session Loop Closed.")
    
    async def _run_async_session(self):
        """Main async session runner."""
        logging.info(f"Connecting to Qwen Realtime: {self.model} with voice: {self.voice}")
        
        # Build URL based on region
        base_domain = 'dashscope.aliyuncs.com' if self.region == 'cn' else 'dashscope-intl.aliyuncs.com'
        url = f'wss://{base_domain}/api-ws/v1/realtime'
        
        # Create callback instance
        callback = QwenRealtimeCallback(self)
        
        try:
            self.conversation = self._OmniRealtimeConversation(
                model=self.model,
                callback=callback,
                url=url
            )
            
            # Connect to server
            self.conversation.connect()
            
            # Wait for connection
            await asyncio.sleep(0.5)
            
            # Emit connection opened
            self.connection_opened.emit()
            logging.info("Qwen Realtime Session Connected.")
            
            # Configure session with VAD enabled
            self.conversation.update_session(
                output_modalities=[self._MultiModality.AUDIO, self._MultiModality.TEXT],
                voice=self.voice,
                input_audio_format=self._AudioFormat.PCM_16000HZ_MONO_16BIT,
                output_audio_format=self._AudioFormat.PCM_24000HZ_MONO_16BIT,
                enable_input_audio_transcription=True,
                enable_turn_detection=True,
                instructions="You are a helpful, friendly, and intelligent AI assistant. Respond naturally and conversationally."
            )
            
            # Wait for session to be ready
            await asyncio.sleep(0.5)
            
            # Run send and receive loops concurrently
            await asyncio.gather(
                self._send_loop(),
                self._receive_loop()
            )
            
        except Exception as e:
            logging.error(f"Error in Qwen Realtime session: {e}", exc_info=True)
            self.connection_error.emit(str(e))
    
    async def _send_loop(self):
        """Send audio data from queue to the conversation."""
        logging.info("Qwen Realtime send loop started")
        while not self.stopping:
            try:
                try:
                    item = await asyncio.to_thread(self.input_queue.get, timeout=0.1)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                
                if item is None:
                    logging.info("Send loop received stop sentinel")
                    break
                
                if isinstance(item, bytes):
                    # Send audio chunk to Qwen Realtime
                    try:
                        import base64
                        audio_b64 = base64.b64encode(item).decode('ascii')
                        self.conversation.append_audio(audio_b64)
                    except Exception as e:
                        logging.error(f"Error sending audio: {e}")
                
            except Exception as e:
                logging.error(f"Error in send loop: {e}", exc_info=True)
                await asyncio.sleep(0.1)
        
        logging.info("Send loop ended")
    
    async def _receive_loop(self):
        """Handle incoming messages from Qwen Realtime."""
        logging.info("Qwen Realtime receive loop started")
        # The callback handles incoming messages, so this is a placeholder
        # for any additional receive logic if needed
        while not self.stopping:
            await asyncio.sleep(0.1)
        logging.info("Receive loop ended")
    
    def send_audio(self, audio_data: bytes):
        """Thread-safe method to send audio data."""
        self.input_queue.put(audio_data)

    def send_data(self, text_data: str):
        """Thread-safe method to send text data (for Qwen Realtime)."""
        if self.conversation:
            try:
                # Qwen Realtime uses create_response() after committing audio
                # For text input, we need to use conversation.item
                logging.warning("Qwen Realtime doesn't support direct text input after connection")
            except Exception as e:
                logging.error(f"Error sending text data: {e}")

    def stop(self):
        """Signals the session to stop."""
        self.stopping = True
        self.input_queue.put(None)
        if self.conversation:
            try:
                self.conversation.close()
            except Exception as e:
                logging.error(f"Error closing conversation: {e}")


class QwenRealtimeCallback:
    """Callback handler for Qwen Realtime events."""
    
    def __init__(self, session):
        self.session = session
    
    def on_open(self):
        logging.info("Qwen Realtime connection opened")
    
    def on_event(self, response):
        """Handle incoming events from Qwen Realtime."""
        if not isinstance(response, dict):
            return
        
        event_type = response.get('type', '')
        
        try:
            # Connection events
            if event_type == 'session.created':
                logging.info("Qwen Realtime session created")
            
            elif event_type == 'session.updated':
                logging.info("Qwen Realtime session updated")
            
            # User speech events
            elif event_type == 'input_audio_buffer.speech_started':
                logging.info("User started speaking")
                self.session.interrupted.emit()  # Signal that user is speaking
            
            elif event_type == 'input_audio_buffer.speech_stopped':
                logging.info("User stopped speaking")
            
            # User transcript
            elif event_type == 'conversation.item.input_audio_transcription.completed':
                transcript = response.get('transcript', '')
                if transcript:
                    logging.info(f"User transcript: {transcript}")
                    self.session.user_transcript_ready.emit(transcript)
            
            # AI response events
            elif event_type == 'response.created':
                logging.info("AI started responding")
                self.session._is_first_response = False
            
            elif event_type == 'response.audio.delta':
                # AI audio output
                audio_b64 = response.get('delta', '')
                if audio_b64:
                    try:
                        import base64
                        audio_data = base64.b64decode(audio_b64)
                        self.session.audio_output_ready.emit(audio_data)
                    except Exception as e:
                        logging.error(f"Error decoding audio: {e}")
            
            elif event_type == 'response.audio_transcript.delta':
                # AI text output (transcribed from audio)
                text_delta = response.get('delta', '')
                if text_delta:
                    self.session.text_output_ready.emit(text_delta)
            
            elif event_type == 'response.done':
                logging.info("AI response completed")
                self.session.turn_complete.emit()
            
            elif event_type == 'response.audio_transcript.done':
                # Complete AI transcript
                transcript = response.get('transcript', '')
                if transcript:
                    logging.info(f"AI complete transcript: {transcript}")
            
            elif event_type == 'error':
                error_data = response.get('error')
                if error_data is None:
                    error_msg = str(response)
                elif isinstance(error_data, dict):
                    error_msg = error_data.get('message', str(response))
                else:
                    error_msg = str(error_data) if error_data else str(response)
                logging.error(f"Qwen Realtime error: {error_msg}")
                self.session.connection_error.emit(error_msg)
            
            else:
                # Log other events for debugging
                logging.debug(f"Qwen Realtime event: {event_type}")
        
        except Exception as e:
            logging.error(f"Error handling Qwen event: {e}", exc_info=True)
    
    def on_close(self, close_status_code, close_msg):
        logging.info(f"Qwen Realtime connection closed: {close_status_code} - {close_msg}")
        self.session.connection_closed.emit()


# --- API Client Handler ---
class ApiClient(QObject):
    """Handles interactions with various LLM APIs."""

    # Signals for async operations
    # Chat
    chat_stream_chunk = Signal(str) # Emits a piece of the streamed response
    chat_stream_finished = Signal() # Signals end of stream
    chat_response_error = Signal(str) # Emits error message
    # Translation
    translation_finished = Signal(str) # Emits the full translated text
    translation_error = Signal(str) # Emits error message
    # Image Translation
    image_translation_finished = Signal(str) # Emits the translated text from image
    image_translation_error = Signal(str) # Emits error message for image translation
    # Model Fetching
    models_updated = Signal(str) # Emits provider_name when models are updated/fetched
    models_fetch_error = Signal(str, str) # provider_name, error_message
    # Image Generation
    image_generation_finished = Signal(list) # Emits list of image URLs
    image_generation_error = Signal(str) # Emits error message
    
    # Qwen TTS Voice Design/Clone Signals
    qwen_voice_created = Signal(dict)  # Emits voice info dict {voice, preview_audio, type}
    qwen_voice_list_fetched = Signal(str, list)  # Emits (voice_type, list of voice dicts)
    qwen_voice_deleted = Signal(str)  # Emits deleted voice name
    qwen_tts_error = Signal(str)  # Emits error message

    # Chat Audio (Qwen Omni)
    chat_audio_chunk = Signal(bytes) # Emits raw audio bytes (PCM/WAV)
    transcription_finished = Signal(str) # Emits transcribed text
    
    # Gemini Live Session
    session_started = Signal()
    session_stopped = Signal()
    live_text_chunk = Signal(str)      # AI's text from Live session
    live_user_transcript = Signal(str) # User's speech transcript from Live session
    live_interrupted = Signal()         # AI was interrupted by user
    live_turn_complete = Signal()       # AI finished speaking (turn ended)
    live_goaway = Signal()              # GoAway received - disconnect warning
    live_resumption_token = Signal(str) # Resumption token available for reconnection

    available_models = {} # Stores { "provider_name": ["model1", "model2", ...] }

    def __init__(self, config_manager, thread_pool, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.thread_pool = thread_pool # Store the thread pool instance
        self.api_clients = {}
        self.available_models = {} # Initialize model storage
        self.live_session = None # Active WebSocket session worker
        # Session resumption state
        self._last_resumption_token = None
        self._last_live_model = None
        self._initialize_clients()
        # Trigger fetching models for all initialized clients in the background
        self.fetch_all_models_async()

    def _initialize_clients(self):
        """Initialize API clients based on config."""
        # --- Explicitly remove system proxy environment variables ---
        # This prevents libraries like httpx/openai from automatically using them
        # if they were set by external tools like Outline.
        # if 'HTTP_PROXY' in os.environ:
        #     logging.info(f"Removing HTTP_PROXY environment variable: {os.environ.get('HTTP_PROXY')}")
        #     os.environ.pop('HTTP_PROXY', None)
        # if 'HTTPS_PROXY' in os.environ:
        #     logging.info(f"Removing HTTPS_PROXY environment variable: {os.environ.get('HTTPS_PROXY')}")
        #     os.environ.pop('HTTPS_PROXY', None)
        # --- End proxy removal ---

        self.api_clients = {} # Reset clients
        config = self.config_manager.config
        # Ensure api_keys exists and is a dictionary
        api_keys = config.get("api_keys", {})
        if not isinstance(api_keys, dict):
            logging.error("Config 'api_keys' is not a dictionary. Cannot initialize clients.")
            api_keys = {} # Use empty dict to avoid further errors

        logging.info(f"Initializing API clients with keys: {list(api_keys.keys())}")
        
        # Get custom API URLs
        api_urls = config.get("api_urls", {})

        # DeepSeek
        deepseek_key = api_keys.get("deepseek_api_key") # Correct key name
        if deepseek_key and OpenAI:
            logging.info("Found DeepSeek API key. Attempting to initialize client...")
            try:
                base_url = api_urls.get("DeepSeek") or "https://api.deepseek.com/v1"
                self.api_clients["DeepSeek"] = OpenAI(api_key=deepseek_key, base_url=base_url, http_client=httpx.Client(trust_env=True))
                logging.info(f"DeepSeek client initialized successfully with URL: {base_url}")
            except Exception as e:
                logging.error(f"Failed to initialize DeepSeek client: {e}", exc_info=True)
        elif not OpenAI:
             logging.warning("OpenAI library not available, cannot initialize DeepSeek client.")
        else:
            logging.warning("DeepSeek API key not found or empty in config. Client not initialized.")

        # OpenRouter (OpenAI compatible)
        or_key = api_keys.get("openrouter_api_key") # Correct key name
        if or_key and OpenAI:
            logging.info("Found OpenRouter API key. Attempting to initialize client...")
            try:
                base_url = api_urls.get("OpenRouter") or "https://openrouter.ai/api/v1"
                self.api_clients["OpenRouter"] = OpenAI(api_key=or_key, base_url=base_url, http_client=httpx.Client(trust_env=True))
                logging.info(f"OpenRouter client initialized successfully with URL: {base_url}")
            except Exception as e:
                logging.error(f"Failed to initialize OpenRouter client: {e}", exc_info=True)
        elif not OpenAI:
             logging.warning("OpenAI library not available, cannot initialize OpenRouter client.")
        else:
            logging.warning("OpenRouter API key not found or empty in config. Client not initialized.")

        # Groq
        groq_key = api_keys.get("groq_api_key") # Correct key name
        if groq_key and Groq:
            logging.info("Found Groq API key. Attempting to initialize client...")
            try:
                # Groq client might support base_url for proxying
                base_url = api_urls.get("Groq")
                if base_url:
                    self.api_clients["Groq"] = Groq(api_key=groq_key, base_url=base_url)
                    logging.info(f"Groq client initialized with custom URL: {base_url}")
                else:
                    self.api_clients["Groq"] = Groq(api_key=groq_key)
                    logging.info("Groq client initialized successfully.")
            except Exception as e:
                logging.error(f"Failed to initialize Groq client: {e}", exc_info=True)
        elif not Groq:
             logging.warning("Groq library not available, cannot initialize Groq client.")
        else:
            logging.warning("Groq API key not found or empty in config. Client not initialized.")

        # SiliconFlow (OpenAI compatible)
        sf_key = api_keys.get("siliconflow_api_key") # Correct key name
        if sf_key and OpenAI:
            logging.info("Found SiliconFlow API key. Attempting to initialize client...")
            try:
                base_url = api_urls.get("SiliconFlow") or "https://api.siliconflow.cn/v1"
                self.api_clients["SiliconFlow"] = OpenAI(api_key=sf_key, base_url=base_url, http_client=httpx.Client(trust_env=True))
                logging.info(f"SiliconFlow client initialized successfully with URL: {base_url}")
            except Exception as e:
                logging.error(f"Failed to initialize SiliconFlow client: {e}")
        elif not OpenAI:
             logging.warning("OpenAI library not available, cannot initialize SiliconFlow client.")
        else:
            logging.warning("SiliconFlow API key not found or empty in config. Client not initialized.")

        ds_key = api_keys.get("dashscope_api_key") # Use a consistent key name
        if ds_key and OpenAI:
            logging.info("Found DashScope API key. Attempting to initialize client...")
            try:
                base_url = api_urls.get("DashScope") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
                self.api_clients["DashScope"] = OpenAI(api_key=ds_key, base_url=base_url, http_client=httpx.Client(trust_env=True))
                logging.info(f"DashScope client initialized successfully with URL: {base_url}")
            except Exception as e:
                logging.error(f"Failed to initialize DashScope client: {e}", exc_info=True)
        elif not OpenAI:
             logging.warning("OpenAI library not available, cannot initialize DashScope client.")
        else:
            logging.warning("DashScope API key not found or empty in config. Client not initialized.")

        # Google (Gemini)
        google_key = api_keys.get("google_api_key")
        if google_key and genai:
            logging.info("Found Google API key. Initializing Google GenAI client...")
            try:
                base_url = api_urls.get("Google")
                http_options = {"api_version": "v1beta"}
                if base_url:
                    logging.info(f"Using custom URL for Google: {base_url}")
                    http_options["base_url"] = base_url
                
                self.api_clients["Google"] = genai.Client(api_key=google_key, http_options=http_options)
                logging.info("Google GenAI client initialized successfully.")
            except Exception as e:
                logging.error(f"Failed to initialize Google client: {e}", exc_info=True)
        elif not genai:
            logging.warning("google-genai library not available, cannot initialize Google client.")
        else:
            logging.warning("Google API key not found or empty in config. Client not initialized.")

        logging.info(f"Available API clients after initialization: {list(self.api_clients.keys())}")

    def get_available_providers(self):
        """Returns a list of successfully initialized provider names."""
        return list(self.api_clients.keys())

    # --- Gemini Live Session Methods ---
    def start_live_session(self, provider, model, resumption_token=None, voice="Zephyr"):
        """Start a Gemini Live WebSocket session for real-time audio chat.
        
        Args:
            provider: API provider (must be "Google")
            model: Model name (e.g. "gemini-2.5-flash-native-audio-preview-12-2025")
            resumption_token: Optional token for resuming a previous session
            voice: Voice name for TTS (default: "Zephyr")
        """
        if provider != "Google":
            logging.warning("Live session currently only supported for Google.")
            return

        if self.live_session:
            logging.info("Live session already active. Restarting...")
            self._cleanup_live_session()

        api_keys = self.config_manager.config.get("api_keys", {})
        google_key = api_keys.get("google_api_key", "")
        
        if not google_key:
            logging.error("Google API Key not set.")
            self.session_stopped.emit() # Signal failure
            return

        api_urls = self.config_manager.config.get("api_urls", {})
        google_api_url = api_urls.get("Google")

        # Store for resumption
        self._last_live_model = model
        self._last_live_voice = voice  # Store voice for resumption

        logging.info(f"Starting Gemini Live Session: {model} with voice: {voice}" + (" (resuming)" if resumption_token else ""))
        self.live_session = GeminiLiveSession(
            google_key, model, api_url=google_api_url, resumption_token=resumption_token, voice_name=voice
        )
        
        # Connect Signals
        self.live_session.connection_opened.connect(self.session_started)
        self.live_session.connection_closed.connect(self._on_live_session_closed)
        self.live_session.connection_error.connect(self._on_live_session_error)
        
        # Audio/Text Output Routing
        self.live_session.audio_output_ready.connect(self.chat_audio_chunk)  # AI audio
        self.live_session.text_output_ready.connect(self.live_text_chunk)    # AI text
        self.live_session.user_transcript_ready.connect(self.live_user_transcript)  # User text
        
        # VAD signals - for proper turn management
        self.live_session.interrupted.connect(self.live_interrupted)  # User interrupted AI
        self.live_session.turn_complete.connect(self.live_turn_complete)  # AI finished speaking
        
        # Session resumption signals
        self.live_session.goaway_received.connect(self._on_goaway_received)
        self.live_session.session_resumption_update.connect(self._on_resumption_update)
        
        # Start in ThreadPool
        self.thread_pool.start(self.live_session)
    
    def _on_goaway_received(self):
        """Handle GoAway message - connection will close soon."""
        logging.warning("GoAway received - connection will close in ~1 minute")
        self.live_goaway.emit()
    
    def _on_resumption_update(self, token):
        """Handle resumption token update from server."""
        self._last_resumption_token = token
        self.live_resumption_token.emit(token)
        logging.info(f"Session resumption token updated (len={len(token)})")
    
    def _on_live_session_closed(self):
        """Handle live session closed - only emit if this is the current session."""
        # Only emit session_stopped if we're not in the middle of a restart
        if self.live_session is None or self.live_session.stopping:
            self.session_stopped.emit()
    
    def _on_live_session_error(self, error_msg):
        """Handle live session error - only emit if this is the current session."""
        if self.live_session and not self.live_session.stopping:
            self.chat_response_error.emit(f"Live Connection Error: {error_msg}")
    
    def _cleanup_live_session(self):
        """Clean up the current live session without emitting signals."""
        if self.live_session:
            logging.info("Cleaning up old Gemini Live Session...")
            # Disconnect signals to prevent spurious emissions
            try:
                self.live_session.connection_opened.disconnect()
                self.live_session.connection_closed.disconnect()
                self.live_session.connection_error.disconnect()
                self.live_session.audio_output_ready.disconnect()
                self.live_session.text_output_ready.disconnect()
                self.live_session.user_transcript_ready.disconnect()
                self.live_session.interrupted.disconnect()
                self.live_session.turn_complete.disconnect()
                self.live_session.goaway_received.disconnect()
                self.live_session.session_resumption_update.disconnect()
            except (RuntimeError, TypeError):
                pass  # Signals may already be disconnected
            self.live_session.stop()
            self.live_session = None

    def stop_live_session(self):
        """Stop the active Gemini Live session."""
        if self.live_session:
            logging.info("Stopping Gemini Live Session...")
            self.live_session.stop()
            self.live_session = None
            # session_stopped will be emitted by _on_live_session_closed

    def send_live_audio_chunk(self, chunk):
        """Send audio data to the active live session."""
        if self.live_session:
            self.live_session.send_data(chunk)
    
    def resume_live_session(self):
        """Resume a previously disconnected Gemini Live session.
        
        Returns:
            bool: True if resumption was initiated, False if not possible
        """
        if not self._last_resumption_token or not self._last_live_model:
            logging.warning("Cannot resume - no resumption token or model available")
            return False
        
        voice = getattr(self, '_last_live_voice', 'Zephyr')
        logging.info(f"Resuming Gemini Live session: {self._last_live_model} with voice: {voice}")
        self.start_live_session("Google", self._last_live_model, 
                               resumption_token=self._last_resumption_token,
                               voice=voice)
        return True
    
    def has_resumption_token(self):
        """Check if we have a valid resumption token for reconnection."""
        return bool(self._last_resumption_token and self._last_live_model)

    # --- Qwen Realtime Session Methods ---
    def start_qwen_realtime_session(self, model="qwen3-omni-flash-realtime", voice="Cherry", region="cn"):
        """Start a Qwen Realtime WebSocket session for real-time voice chat with VAD support.
        
        Args:
            model: Model name (e.g., "qwen3-omni-flash-realtime")
            voice: Voice name for TTS (default: "Cherry")
            region: API region - "cn" for China, "intl" for Singapore
        """
        if self.live_session:
            logging.info("Live session already active. Restarting...")
            self._cleanup_live_session()

        api_keys = self.config_manager.config.get("api_keys", {})
        dashscope_key = api_keys.get("dashscope_api_key", "")
        
        if not dashscope_key:
            logging.error("DashScope API Key not set.")
            self.session_stopped.emit()
            return

        # Store for reference
        self._last_live_model = model
        self._last_live_voice = voice
        self._last_live_region = region

        logging.info(f"Starting Qwen Realtime Session: {model} with voice: {voice} (region: {region})")
        
        # Create Qwen Realtime session (reusing live_session attribute for unified handling)
        self.live_session = QwenRealtimeSession(
            api_key=dashscope_key,
            model=model,
            voice=voice,
            region=region
        )
        
        # Connect Signals (same as Gemini for unified handling)
        self.live_session.connection_opened.connect(self.session_started)
        self.live_session.connection_closed.connect(self._on_live_session_closed)
        self.live_session.connection_error.connect(self._on_live_session_error)
        
        # Audio/Text Output Routing
        self.live_session.audio_output_ready.connect(self.chat_audio_chunk)
        self.live_session.text_output_ready.connect(self.live_text_chunk)
        self.live_session.user_transcript_ready.connect(self.live_user_transcript)
        
        # VAD signals - for proper turn management
        self.live_session.interrupted.connect(self.live_interrupted)
        self.live_session.turn_complete.connect(self.live_turn_complete)
        
        # Start in ThreadPool
        self.thread_pool.start(self.live_session)
    
    def send_qwen_realtime_audio(self, chunk):
        """Send audio data to the active Qwen Realtime session."""
        if self.live_session and isinstance(self.live_session, QwenRealtimeSession):
            self.live_session.send_audio(chunk)

    # --- Model Fetching Functionality ---

    def get_models_for_provider(self, provider_name):
        """Returns the cached list of models for a provider."""
        return self.available_models.get(provider_name, [])

    def fetch_models_for_provider_async(self, provider_name):
        """Starts an asynchronous request to fetch models for a specific provider."""
        # Removed Google specific handling
        if provider_name not in self.api_clients:
            logging.warning(f"Cannot fetch models for uninitialized provider: {provider_name}")
            self.models_fetch_error.emit(provider_name, "Provider not initialized")
            return

        logging.info(f"Queueing model fetch request for: {provider_name}")
        worker = AsyncWorker(self._fetch_models, provider_name)
        worker.signals.models_fetched.connect(self._handle_models_fetched) # Connect specific signal
        worker.signals.error.connect(self._handle_generic_worker_error) # Connect generic error handler
        self.thread_pool.start(worker)

    def fetch_all_models_async(self):
        """Fetches models for all initialized providers."""
        logging.info("Fetching models for all available providers...")
        for provider_name in self.get_available_providers():
            self.fetch_models_for_provider_async(provider_name)

    @Slot(str, list)
    def _handle_models_fetched(self, provider_name, models_result):
        """Handles the successful fetching of models."""
        if isinstance(models_result, list):
            logging.info(f"Successfully fetched {len(models_result)} models for {provider_name}.")
            models = models_result.copy()
            
            # DashScope: 添加图像生成模型（API不返回这些模型，需要手动添加）
            if provider_name == "DashScope":
                image_models = ["qwen-image-plus", "flux-schnell", "flux-dev", "flux-merged"]
                for img_model in image_models:
                    if img_model not in models:
                        models.append(img_model)
                logging.info(f"Added image generation models to DashScope: {image_models}")
            
            # 精确调整顺序: flux-merged -> 第一个, flux-dev -> 第二个, flux-schnell -> 第三个, 其它顺序不变
            merged = [m for m in models if m == "flux-merged"]
            dev = [m for m in models if m == "flux-dev"]
            schnell = [m for m in models if m == "flux-schnell"]
            others = [m for m in models if m not in ("flux-merged", "flux-dev", "flux-schnell")]
            # 只要有 merged/dev/schnell 就按指定顺序排，否则保留原顺序
            new_models = merged + dev + schnell + others if merged or dev or schnell else models
            self.available_models[provider_name] = new_models
            self.models_updated.emit(provider_name)
        else:
            err_msg = f"Model fetch for {provider_name} returned unexpected result type: {type(models_result)}"
            logging.error(err_msg)
            self._handle_models_fetch_error(provider_name, err_msg)

    @Slot(str)
    def _handle_generic_worker_error(self, error_message):
        """Handles generic errors reported by the AsyncWorker."""
        # Try to extract provider context if included in the message
        provider_match = re.match(r"Error in \w+\s?\((.*?)\):", error_message)
        provider_name = provider_match.group(1) if provider_match else "Unknown Provider"
        func_match = re.match(r"Error in (\w+)", error_message)
        func_name = func_match.group(1) if func_match else "unknown function"

        logging.error(f"Received worker error: {error_message}") # Log the raw error

        # Route based on function name embedded in the error message
        if "fetch_models" in func_name:
            self._handle_models_fetch_error(provider_name, error_message)
        elif "translation_request" in func_name:
            # Check if it's image translation or text translation based on func name
            if func_name == '_execute_image_translation_request':
                self.image_translation_error.emit(error_message)
            else: # Assume text translation
                self.translation_error.emit(error_message)
        elif "chat_request" in func_name:
            self.chat_response_error.emit(error_message)
        # Note: Image generation errors are now handled by a separate signal/slot
        # Removed elif for generate_image as it's handled specifically
        else:
            # Fallback for unexpected errors or errors not routed specifically
            logging.error(f"Unhandled worker error (via generic handler): {error_message}")
            # Emit a generic error signal or handle differently? Maybe a dedicated signal?
            # self.generic_api_error.emit(error_message) # Example

    def _handle_models_fetch_error(self, provider_name, error_message):
        """Handles errors during model fetching."""
        logging.error(f"Failed to fetch models for {provider_name}: {error_message}")
        # Ensure the provider key exists with an empty list if fetching failed
        if provider_name not in self.available_models:
            self.available_models[provider_name] = []
        self.models_fetch_error.emit(provider_name, str(error_message))
        # Optionally emit models_updated even on error to signal completion?
        # self.models_updated.emit(provider_name)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_models(self, provider_name):
        """Fetch models for a specific provider."""
        try:
            client_or_module = self.api_clients.get(provider_name)
            if not client_or_module:
                raise ValueError(f"API Client for provider '{provider_name}' not initialized.")

            logging.info(f"Executing model fetch for {provider_name}...")
            model_ids = []

            # --- Google (check first since genai.Client also has models attribute) ---
            if provider_name == "Google":
                # Dynamically fetch models from Google GenAI
                try:
                    # genai.Client has models.list() but returns Model objects with .name, not .id
                    for model in client_or_module.models.list():
                        # Google model names are like "models/gemini-2.0-flash-exp"
                        # Extract just the model name part after "models/"
                        model_name = getattr(model, 'name', None)
                        if model_name:
                            # Remove "models/" prefix if present
                            clean_name = model_name.replace("models/", "") if model_name.startswith("models/") else model_name
                            model_ids.append(clean_name)
                            logging.debug(f"Found Google model: {clean_name}")
                    logging.info(f"Fetched {len(model_ids)} models from Google GenAI")
                except Exception as e:
                    logging.error(f"Error fetching Google models dynamically: {e}")
                    # Fallback to hardcoded list
                    model_ids = ["gemini-2.5-flash-native-audio-preview-12-2025", "gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"]
                    logging.info(f"Using fallback hardcoded models for Google: {model_ids}")

            # --- OpenAI-Compatible APIs (DeepSeek, OpenRouter, SiliconFlow, DashScope) ---
            # Check if the client has a 'models.list()' method (standard for openai>=1.0)
            elif hasattr(client_or_module, 'models') and callable(getattr(client_or_module.models, 'list', None)):
                logging.debug(f"Using models.list() for {provider_name}")
                model_list_response = client_or_module.models.list()
                # The response object might be iterable directly or have a 'data' attribute
                data = getattr(model_list_response, 'data', model_list_response)
                for model in data:
                    logging.debug(f"[Model Debug] model object: {repr(model)}")
                    model_id = getattr(model, 'id', None)
                    if model_id and model_id != provider_name and model_id != "model":
                        model_ids.append(model_id)
                    else:
                        logging.warning(f"Model object from {provider_name} missing or invalid 'id': {repr(model)}")

            # --- Groq ---
            # Groq uses the OpenAI compatible endpoint as well now
            elif provider_name == "Groq" and hasattr(client_or_module, 'models') and callable(getattr(client_or_module.models, 'list', None)):
                 logging.debug(f"Using models.list() for Groq")
                 model_list_response = client_or_module.models.list()
                 data = getattr(model_list_response, 'data', model_list_response)
                 for model in data:
                     model_id = getattr(model, 'id', None)
                     if model_id:
                          model_ids.append(model_id)

            # --- Add other provider-specific logic here if needed ---
            # elif provider_name == "SomeOtherProvider":
            #     # ... custom logic ...

            else:
                logging.warning(f"Model fetching not implemented or client structure unexpected for provider: {provider_name}")
                # Return empty list or raise specific error? Returning empty for now.
                # raise NotImplementedError(f"Model fetching not implemented for {provider_name}")
                return [] # Return empty list if no method found

            logging.info(f"Found {len(model_ids)} models for {provider_name}.")
            return model_ids

        except (APIError, GroqAPIError, RateLimitError, GroqRateLimitError, AuthenticationError) as api_err:
             logging.error(f"API Error fetching models for {provider_name}: {api_err}")
             raise ValueError(f"API Error: {api_err}") # Re-raise for worker error signal
        except Exception as e:
             logging.error(f"Unexpected error fetching models for {provider_name}: {e}", exc_info=True)
             raise # Re-raise for worker error signal
        except httpx.ConnectError as e:
            logging.error(f"Connection error while fetching models for {provider_name}: {e}")
        except httpx.TimeoutException as e:
            logging.error(f"Timeout while fetching models for {provider_name}: {e}")

    # --- Chat Functionality ---
    @Slot(str, str, str, str, str, bool) # provider, model, user_message, file_path, file_type, audio_output
    def start_chat_request_async(self, provider, model, user_message, file_path=None, file_type=None, audio_output=False, history=None, voice="Cherry"):
        """Starts an asynchronous chat request in the thread pool.
        
        Args:
            history: Optional list of previous messages, each dict with 'role' and 'content'
                     Example: [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]
            voice: Voice name for DashScope Omni audio output (e.g., "Cherry", "Dylan", "Sunny")
        """
        logging.info(f"Queueing chat request: Provider={provider}, Model={model}, AudioOut={audio_output}, HistoryLen={len(history) if history else 0}")
        worker = AsyncWorker(self._execute_chat_request, provider, model, user_message, file_path, file_type, audio_output, history, voice)
        # Connect worker signals to ApiClient signals or handler slots
        worker.signals.stream_finished.connect(self._handle_chat_stream_finished) # Assuming stream obj is returned
        worker.signals.error.connect(self._handle_generic_worker_error) # Connect generic error handler
        self.thread_pool.start(worker)

    def _execute_chat_request(self, provider, model, user_message, file_path=None, file_type=None, audio_output=False, history=None, voice="Cherry"):
        """Synchronous function executed by the worker for chat requests (handles streaming).
        
        Args:
            history: Optional list of previous messages for multi-turn context
            voice: Voice name for DashScope Omni audio output (e.g., "Cherry", "Dylan", "Sunny")
        """
        client_or_module = self.api_clients.get(provider)
        if not client_or_module:
            raise ValueError(f"API Client for provider '{provider}' not initialized.")

        messages = []
        google_prompt_parts = None
        image_data = None
        image_mime_type = None
        audio_data = None
        pdf_text = ""
        extra_info = ""

        # --- File Processing ---
        if file_path and file_type == 'pdf':
            if PdfReader:
                try:
                    reader = PdfReader(file_path)
                    extracted_texts = [page.extract_text() for page in reader.pages if page.extract_text()]
                    pdf_text = "\n".join(extracted_texts).strip()
                    if not pdf_text: extra_info = "[Info: Could not extract text from PDF.]"
                except Exception as pdf_err: extra_info = "[Error: Failed to process PDF.]"; logging.error(f"PDF Error: {pdf_err}")
            else: extra_info = "[Error: PyPDF2 not installed.]"
        elif file_path and file_type == 'image':
             try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type and mime_type.startswith("image/"):
                    with open(file_path, "rb") as img_file:
                        image_data = base64.b64encode(img_file.read()).decode('utf-8')
                    image_mime_type = mime_type
                else: extra_info = "[Error: Invalid image type.]"
             except Exception as img_err: extra_info = "[Error: Failed to process image.]"; logging.error(f"Image Error: {img_err}")
        elif file_path and file_type == 'audio':
             # NEW: Process input audio for multimodal request
             try:
                 with open(file_path, "rb") as aud_file:
                     audio_data = base64.b64encode(aud_file.read()).decode('utf-8')
             except Exception as aud_err: extra_info = "[Error: Failed to process audio.]"; logging.error(f"Audio Error: {aud_err}")


        # --- Construct API Payload ---
        combined_text_prompt = user_message if user_message else ""
        if pdf_text: combined_text_prompt = f"PDF Text:\n{pdf_text}\n\nUser:\n{combined_text_prompt}"
        if extra_info: combined_text_prompt += f"\n\n{extra_info}"

        is_vision_model = ("vision" in model.lower() or "gpt-4" in model.lower() or
                           "llava" in model.lower() or
                           "vl" in model.lower() or "qwen" in model.lower())

        # Build messages array with history first
        messages = []
        
        # Add conversation history (previous messages)
        if history:
            for h in history:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        
        # Build current user message content
        current_content = []
        
        # Audio Part (Input Audio)
        if audio_data:
             # DashScope Omni 需要 data:;base64, 前缀
             current_content.append({
                 "type": "input_audio",
                 "input_audio": {
                     "data": f"data:;base64,{audio_data}",
                     "format": "wav" 
                 }
             })

        # Text Part 
        if combined_text_prompt:
             current_content.append({"type": "text", "text": combined_text_prompt})
        
        # Image Part
        if is_vision_model and image_data and image_mime_type:
             current_content.append({
                 "type": "image_url",
                 "image_url": {"url": f"data:{image_mime_type};base64,{image_data}"}
             })
        
        # Add current user message to messages array
        if current_content:
            # For simple text-only messages, use string content format
            if len(current_content) == 1 and current_content[0].get("type") == "text":
                messages.append({"role": "user", "content": current_content[0]["text"]})
            else:
                messages.append({"role": "user", "content": current_content})

        # --- Execute API Call (Streaming) ---
        try:
            logging.info(f"Executing API chat request (Stream): Provider={provider}, Model={model}")
            
            create_args = {
                "model": model,
                "messages": messages,
                "stream": True
            }

            # NEW: Add modalities and audio output settings if requested
            if audio_output and ("qwen" in model.lower() and "omni" in model.lower()):
                 create_args["modalities"] = ["text", "audio"]
                 create_args["audio"] = {"voice": voice, "format": "wav"}
                 create_args["stream_options"] = {"include_usage": True}
            
            logging.info(f"API Payload Messages: {messages}") # DEBUG LOG
            logging.info(f"API Create Args: {create_args}") # DEBUG LOG

            # --- Google GenAI ---
            if provider == "Google" and genai:
                # Google genai uses different API structure
                # For text chat, use generate_content
                try:
                    # Construct content list for Google
                    google_contents = []
                    
                    # Add history
                    if history:
                        for h in history:
                            role = h.get("role", "user")
                            # Map 'assistant' to 'model' for Google
                            if role == "assistant":
                                role = "model"
                            
                            parts = [{"text": h.get("content", "")}]
                            google_contents.append({"role": role, "parts": parts})
                    
                    # Add current message
                    current_parts = []
                    if combined_text_prompt:
                        current_parts.append({"text": combined_text_prompt})
                        
                    if image_data and image_mime_type:
                        # Include image if present
                        from google.genai import types as genai_types
                        current_parts.append(genai_types.Part.from_bytes(
                            data=base64.b64decode(image_data), 
                            mime_type=image_mime_type
                        ))
                    
                    # Add audio data for Google GenAI
                    if audio_data:
                        from google.genai import types as genai_types
                        audio_bytes = base64.b64decode(audio_data)
                        current_parts.append(genai_types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type="audio/wav"
                        ))
                    
                    if current_parts:
                        google_contents.append({"role": "user", "parts": current_parts})

                    # Stream response
                    # Note: contents can be a single string, a list of strings, 
                    # or a list of Content objects/dicts.
                    logging.info(f"Google Payload Content Count: {len(google_contents)}")

                    response = client_or_module.models.generate_content_stream(
                        model=model,
                        contents=google_contents
                    )
                    
                    for chunk in response:
                        if hasattr(chunk, 'text') and chunk.text:
                            self.chat_stream_chunk.emit(chunk.text)
                    
                    return None
                except Exception as e:
                    logging.error(f"Google GenAI chat error: {e}", exc_info=True)
                    self.chat_response_error.emit(f"Google API Error: {e}")
                    return None
            
            elif isinstance(client_or_module, (OpenAI, Groq)):
                response_stream = client_or_module.chat.completions.create(**create_args)
            else:
                raise ValueError(f"Unsupported client type for streaming: {type(client_or_module)}")

            # --- Process Stream Synchronously within Worker ---
            any_chunk_received = False
            for chunk in response_stream:
                any_chunk_received = True
                
                # Check for Audio Delta
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'audio') and delta.audio:
                         if 'data' in delta.audio:
                              # Decode Base64 audio chunk
                              try:
                                  raw_audio = base64.b64decode(delta.audio['data'])
                                  # Emit direct signal via a new way? 
                                  # Worker doesn't have direct access to 'chat_audio_chunk' on 'self'.
                                  # We need to emit via worker signals.
                                  # Since we are inside ApiClient method but running in Worker thread, 
                                  # we can't emit ApiClient signals directly if they are thread-bound? 
                                  # Actually Signals are thread-safe.
                                  # But better to use the worker signals pattern if possible, 
                                  # OR, add a new signal to ApiClient and emit it here. 
                                  # ApiClient is in main thread (usually), this runs in bg thread. 
                                  # Emitting signal from bg thread is fine.
                                  # BUT, 'self' here IS the ApiClient instance.
                                  self.chat_audio_chunk.emit(raw_audio)
                              except Exception as e:
                                  logging.error(f"Error decoding audio chunk: {e}")
                         
                         # Extract user's speech transcript (input_transcript)
                         if 'transcript' in delta.audio:
                              user_transcript = delta.audio['transcript']
                              if user_transcript:
                                  logging.info(f"User transcript from audio: {user_transcript}")
                                  self.live_user_transcript.emit(user_transcript)

                content = self._extract_content_from_chunk(chunk, provider)
                if content is not None:
                    self.chat_stream_chunk.emit(content)

            if not any_chunk_received:
                logging.warning(f"Stream ended for {provider} without receiving any valid content chunks.")

            return None

        except (APIError, GroqAPIError, RateLimitError, GroqRateLimitError, AuthenticationError) as api_err:
            logging.error(f"API Error during chat request ({provider}): {api_err}")
            self.chat_response_error.emit(f"API Error: {api_err}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error during chat request ({provider}): {e}", exc_info=True)
            self.chat_response_error.emit(f"API调用异常: {e}")
            return None

    def _extract_content_from_chunk(self, chunk, provider):
        """Helper to extract text content from different API stream chunks."""
        content = None
        try:
            # Removed Google specific chunk parsing
            # OpenAI / DeepSeek / SiliconFlow / OpenRouter / Groq structure (adjust Groq if needed)
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if delta:
                    content = delta.content # Will be None if no content in delta
            # Add specific handling for Groq if its chunk structure differs significantly
            # elif provider == "Groq" and hasattr(chunk, ...):
            #    ...
        except AttributeError:
             # Handle cases where expected attributes (like choices, delta, content) are missing
             logging.debug(f"Attribute error parsing stream chunk for {provider}: {repr(chunk)}") # Use repr()
             content = None # Indicate no valid content extracted
        except Exception as e:
            logging.warning(f"Error parsing stream chunk for {provider}: {e} - Chunk: {repr(chunk)}") # Use repr()
            content = "[Error parsing chunk]" # Indicate an error occurred
        return content # Can be string or None

    @Slot()
    def _handle_chat_stream_finished(self):
        """Signals that the chat stream has finished processing."""
        logging.info("Chat stream processing finished in worker.")
        self.chat_stream_finished.emit() # Signal completion

    # --- Transcription Functionality ---
    @Slot(str) 
    def start_transcription_request_async(self, file_path):
        """Starts an asynchronous transcription request using DashScope (or others)."""
        logging.info(f"Queueing transcription request: {file_path}")
        worker = AsyncWorker(self._execute_transcription_request, file_path)
        worker.signals.translation_result.connect(self.translation_finished) # Reuse or new signal? Let's use translation_finished for now as 'text result' or add 'transcription_finished'
        # Actually better to add a dedicated signal
        worker.signals.transcription_finished.connect(self.transcription_finished)
        worker.signals.error.connect(self.translation_error) # Reuse error
        self.thread_pool.start(worker)

    def _execute_transcription_request(self, file_path):
        """Executes ASR using DashScope Recognition."""
        if not dashscope:
            raise ImportError("DashScope SDK not available for ASR.")
            
        api_key = self.config_manager.get("api_keys.dashscope_api_key")
        if not api_key:
            raise ValueError("DashScope API Key missing.")
            
        dashscope.api_key = api_key
        
        try:
            from dashscope.audio.asr import Recognition
            
            # Use 'sensevoice-v1' which is robust and available
            # Note: SenseVoice might return different result structure, checking docs...
            # SenseVoice via Recognition usually returns 'text' in result.
            rec = Recognition(model='sensevoice-v1', format='wav', sample_rate=16000, callback=None) 
            
            result = rec.call(file_path)
            
            if result.status_code == 200:
                # SenseVoice result formatting
                if 'sentences' in result.output:
                    text = "".join([s['text'] for s in result.output['sentences']])
                elif 'text' in result.output:
                     text = result.output['text']
                else:
                    text = "" 
                
                logging.info(f"ASR Result: {text}")
                return text

            else:
                raise Exception(f"ASR Failed: {result.code} - {result.message}")
                
        except Exception as e:
            logging.error(f"ASR Exception: {e}")
            raise

    @Slot(str, str, str, str, str)
    def start_translation_request_async(self, provider, model, text, source_lang_api, target_lang_api):
        """Starts an asynchronous text translation request."""
        logging.info(f"Queueing translation request: Provider={provider}, Model={model}")
        worker = AsyncWorker(self._execute_translation_request, provider, model, text, source_lang_api, target_lang_api)
        # Connect worker signals to INTERMEDIATE slots in ApiClient
        worker.signals.translation_result.connect(self.translation_finished) # Connect specific signal directly
        worker.signals.error.connect(self._handle_generic_worker_error) # Connect generic error handler
        self.thread_pool.start(worker)

    def _execute_translation_request(self, provider, model, text, source_lang_api, target_lang_api):
        """Synchronous function executed by the worker for translation."""
        client_or_module = self.api_clients.get(provider)
        if not client_or_module:
            raise ValueError(f"API Client for provider '{provider}' not initialized.")

        # Construct prompt (adjust based on provider/model best practices)
        prompt = f"Translate the following text from {source_lang_api} to {target_lang_api}. Output only the translated text directly, without any explanations or introductory phrases:\n\n{text}"

        try:
            logging.info(f"Executing API translation request: Provider={provider}, Model={model}")
            if isinstance(client_or_module, (OpenAI, Groq)):
                response = client_or_module.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful translation assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=False # Non-streaming for translation
                )
                translated_text = response.choices[0].message.content.strip()
            else:
                raise ValueError(f"Unsupported client type for translation: {type(client_or_module)}")

            logging.info(f"Translation successful for {provider}.")
            return translated_text

        except (APIError, GroqAPIError, RateLimitError, GroqRateLimitError, AuthenticationError) as api_err:
             logging.error(f"API Error during translation request ({provider}): {api_err}")
             self.translation_error.emit(f"API Error: {api_err}")
             return None
        except Exception as e:
             logging.error(f"Unexpected error during translation request ({provider}): {e}")
             self.translation_error.emit(f"API调用异常: {e}")
             return None

    # --- Image Translation Functionality ---
    @Slot(str, str, str, str, str) # provider, model, image_path, source_lang_api, target_lang_api
    def start_image_translation_async(self, provider, model, image_path, source_lang_api, target_lang_api):
        """Starts an asynchronous image translation request."""
        logging.info(f"Queueing image translation request: Provider={provider}, Model={model}")
        worker = AsyncWorker(self._execute_image_translation_request, provider, model, image_path, source_lang_api, target_lang_api)
        # Connect worker signals to ApiClient signals
        worker.signals.translation_result.connect(self.image_translation_finished) # Reuse translation_result signal from worker
        worker.signals.error.connect(self._handle_generic_worker_error) # Connect generic error handler

        # Model fetching methods are now implemented above.

    def _generate_image_dashscope(self, prompt: str, model: str = "flux-schnell", size: str = "1024*1024") -> List[str]:
        """
        Generates an image using Alibaba Cloud DashScope and returns a list of image URLs.
        Supports both qwen-image-plus (MultiModalConversation) and flux series (ImageSynthesis).
        """
        try:
            api_keys = self.config_manager.config.get("api_keys", {})
            ds_key = api_keys.get("dashscope_api_key", "")
            if not ds_key or ds_key == "YOUR_DASHSCOPE_API_KEY":
                raise Exception("DashScope API Key not configured or is a placeholder.")

            import dashscope
            os.environ["DASHSCOPE_API_KEY"] = ds_key
            dashscope.api_key = ds_key
            dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
        except Exception as e:
            logging.error(f"Unexpected error during DashScope initialization: {e}", exc_info=True)
            raise Exception(f"Initialization error: {e}")

        # 根据模型选择不同的API
        if 'qwen-image' in model.lower():
            return self._generate_image_qwen(prompt, model, size, ds_key)
        else:
            return self._generate_image_flux(prompt, model, size)
    
    def _generate_image_qwen(self, prompt: str, model: str, size: str, api_key: str) -> List[str]:
        """使用 MultiModalConversation API 生成图像 (qwen-image-plus)"""
        try:
            from dashscope import MultiModalConversation
            
            # qwen-image-plus 支持的尺寸: 1664*928, 1472*1140, 1328*1328, 1140*1472, 928*1664
            # 如果传入的尺寸不在支持列表中，使用默认的正方形尺寸
            valid_sizes = ['1664*928', '1472*1140', '1328*1328', '1140*1472', '928*1664']
            if size not in valid_sizes:
                size = '1328*1328'  # 默认正方形
                logging.info(f"Size not in valid list, using default: {size}")
            
            messages = [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ]
            
            logging.info(f"Calling DashScope MultiModalConversation: model={model}, size={size}")
            
            response = MultiModalConversation.call(
                api_key=api_key,
                model=model,
                messages=messages,
                result_format='message',
                stream=False,
                watermark=False,
                prompt_extend=True,
                size=size
            )
            
            if response.status_code == 200:
                # 解析响应获取图片URL
                choices = response.output.get('choices', [])
                if choices:
                    content = choices[0].get('message', {}).get('content', [])
                    for item in content:
                        if 'image' in item:
                            image_url = item['image']
                            logging.info(f"qwen-image generation succeeded: {image_url[:100]}...")
                            return [image_url]
                
                logging.warning(f"qwen-image response has no image URL: {response.output}")
                raise Exception("图像生成成功但未返回图片URL")
            else:
                error_msg = f"HTTP {response.status_code}: {response.code} - {response.message}"
                logging.error(f"qwen-image generation failed: {error_msg}")
                raise Exception(error_msg)
                
        except ImportError:
            raise Exception("DashScope SDK not installed. Please run: pip install dashscope")
        except Exception as e:
            logging.error(f"qwen-image generation error: {e}", exc_info=True)
            raise
    
    def _generate_image_flux(self, prompt: str, model: str, size: str) -> List[str]:
        """使用 ImageSynthesis API 生成图像 (flux 系列)"""
        if ImageSynthesis is None:
            raise Exception("DashScope SDK not installed. Please run: pip install dashscope")
            
        logging.info(f"Calling DashScope ImageSynthesis: model={model}, size={size}, prompt='{prompt[:50]}...'")
        try:
            client = ImageSynthesis()
            response = client.call(
                prompt=prompt,
                model=model,
                size=size,
                n=1
            )
            if response.status_code == 200:
                task_id = response.output.get('task_id')
                if not task_id:
                    raise Exception("DashScope initial call succeeded but did not return a task_id.")

                logging.info(f"DashScope task started: {task_id}")

                max_wait_seconds = 120
                poll_interval_seconds = 4
                start_time = time.time()

                while True:
                    elapsed_time = time.time() - start_time
                    if elapsed_time > max_wait_seconds:
                        logging.error(f"DashScope task {task_id} timed out after {max_wait_seconds} seconds.")
                        raise Exception(f"Image generation task {task_id} timed out.")

                    fetch_rsp = ImageSynthesis.fetch(task=task_id)
                    if fetch_rsp.status_code == 200 and hasattr(fetch_rsp, 'output') and fetch_rsp.output:
                        task_status = fetch_rsp.output.get("task_status", "UNKNOWN")
                        if task_status == "SUCCEEDED":
                            results = fetch_rsp.output.get("results", [])
                            if results and isinstance(results, list) and results[0].get("url"):
                                image_urls = [result["url"] for result in results if result.get("url")]
                                if image_urls:
                                    logging.info(f"DashScope task {task_id} succeeded. Returning URLs: {image_urls}")
                                    return image_urls
                            logging.warning(f"DashScope task {task_id} SUCCEEDED but no valid URLs found")
                            return []
                        elif task_status == "FAILED":
                            error_code = fetch_rsp.output.get("code", "UnknownCode")
                            error_message = fetch_rsp.output.get("message", "Task failed with unknown reason")
                            log_msg = f"DashScope task {task_id} FAILED. Code: {error_code}, Message: {error_message}"
                            logging.error(log_msg)
                            raise Exception(log_msg)
                        elif task_status in ["PENDING", "RUNNING"]:
                            time.sleep(poll_interval_seconds)
                        else:
                            logging.warning(f"DashScope task {task_id} has unexpected status: {task_status}. Full response: {fetch_rsp.output}")
                            time.sleep(poll_interval_seconds * 2)
                    else:
                        time.sleep(poll_interval_seconds)
            else:
                raise Exception(f"ImageSynthesis call failed: {response.status_code} - {response.message}")
        except Exception as e:
            logging.error(f"Unexpected error during DashScope image generation: {e}", exc_info=True)
            raise Exception(f"Unexpected error: {e}")



    @Slot(str, str, str, str) # provider, prompt, model, size
    def start_image_generation_async(self, provider, prompt, model, size=None):
        """Starts an asynchronous image generation request."""
        logging.info(f"Queueing image generation request: Provider={provider}, Model={model}")

        target_func = None
        args = []

        if provider == "DashScope":
            target_func = self._generate_image_dashscope
            # DashScope 需要 "1024*1024" 这种格式
            size = size if size else "1024*1024"
            args = [prompt, model, size]
        else:
            # Only DashScope is supported now
            error_msg = f"Image generation currently only supported for DashScope, not: {provider}"
            logging.error(error_msg)
            self.image_generation_error.emit(error_msg)
            return

        if not target_func: # Should not happen if provider check passed, but good practice
             error_msg = f"Internal error: Could not find target function for provider {provider}"
             logging.error(error_msg)
             self.image_generation_error.emit(error_msg)
             return

        worker = AsyncWorker(target_func, *args)
        # Connect specific image generation signals
        worker.signals.image_urls_fetched.connect(self._handle_image_urls_fetched)
        worker.signals.image_generation_error.connect(self._handle_image_generation_error_signal)
        # Do NOT connect the generic error signal here if we have a specific one
        # worker.signals.error.connect(self._handle_generic_worker_error)
        self.thread_pool.start(worker)

    @Slot(list)
    def _handle_image_urls_fetched(self, urls):
        """Handles successful image generation."""
        logging.info(f"Image generation successful. Received {len(urls)} URL(s).")
        self.image_generation_finished.emit(urls)

    @Slot(str)
    def _handle_image_generation_error_signal(self, error_message):
        """Handles errors specifically from image generation worker signal."""
        logging.error(f"Image generation failed: {error_message}")
        self.image_generation_error.emit(error_message)

    def explain_word_with_llm(self, word):
        # 极简prompt，去除多余格式和符号，要求直接输出简明内容
        prompt = (
            f"请用最简洁直白的方式解释英文单词 '{word}'，仅输出纯文本内容，不要任何符号、列表、markdown、星号、斜杠、分隔线等格式。"
            f"内容包括：拼写、音标、词性、英文释义、中文释义、例句（每项一行，例句最多1条，全部内容合计不超过60字）。"
        )
        preferred_providers = ["DeepSeek", "Groq", "OpenRouter", "SiliconFlow", "DashScope"]
        provider = None
        for p in preferred_providers:
            if p in self.api_clients:
                provider = p
                break
        if provider is None:
            return "未找到可用的大模型API，请检查API配置。"

        client = self.api_clients[provider]
        models = self.get_models_for_provider(provider)
        if not models:
            return f"{provider} 未获取到可用模型，请先刷新模型列表。"
        # 修改：默认用第三个模型（如果有），否则用第一个
        if len(models) >= 3:
            model = models[2]
        else:
            model = models[0]
        messages = [
            {"role": "system", "content": "你是一个英汉词典助手。"},
            {"role": "user", "content": prompt}
        ]
        try:
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=False
                )
                return response.choices[0].message.content.strip()
            else:
                return f"不支持的API客户端类型: {type(client)}"
        except Exception as e:
            return f"查询失败: {e}"

    def _execute_image_translation_request(self, provider, model, image_path, source_lang_api, target_lang_api):
        """
        调用大模型API进行图片识别+翻译，返回翻译文本。
        """
        client_or_module = self.api_clients.get(provider)
        if not client_or_module:
            return "未找到可用的API客户端"

        # 检查模型名
        if not model or model.strip() == "" or model.strip().lower() in ["无可用模型", "加载中", "loading"]:
            return "未选择有效的模型"

        # 读取图片并转为 base64
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith("image/"):
            return "图片格式不支持"
        try:
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            logging.error(f"图片读取失败: {e}", exc_info=True)
            return f"图片读取失败: {e}"

        # 构造 prompt
        prompt = f"请将图片中的内容从{source_lang_api}翻译为{target_lang_api}，只输出翻译后的文本，不要解释。"

        # content 格式
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}}
        ]
        messages = [{"role": "user", "content": content}]

        try:
            logging.info(f"执行图片翻译: Provider={provider}, Model={model}")
            if hasattr(client_or_module, "chat") and hasattr(client_or_module.chat, "completions"):
                response = client_or_module.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=False
                )
                # 健壮性：choices/message 检查
                if hasattr(response, "choices") and response.choices:
                    msg = getattr(response.choices[0], "message", None)
                    if msg and hasattr(msg, "content"):
                        return msg.content.strip()
                    else:
                        logging.error(f"图片翻译API返回内容异常: {response}")
                        return "图片翻译API返回内容异常"
                else:
                    logging.error(f"图片翻译API未返回choices: {response}")
                    return "图片翻译API未返回choices"
            else:
                return f"不支持的API客户端类型: {type(client_or_module)}"
        except Exception as e:
            logging.error(f"图片翻译API调用异常: {e}", exc_info=True)
            # 保留原始错误信息，但移除冗余的返回
            raise  # 重新抛出异常，让调用者处理


    # ==================== Qwen TTS Voice Design & Clone API ====================
    
    QWEN_TTS_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
    QWEN_VOICE_DESIGN_MODEL = "qwen-voice-design"
    QWEN_VOICE_DESIGN_TARGET = "qwen3-tts-vd-realtime-2025-12-16"
    QWEN_VOICE_CLONE_MODEL = "qwen-voice-enrollment"
    QWEN_VOICE_CLONE_TARGET = "qwen3-tts-vc-realtime-2025-11-27"
    
    def _get_dashscope_api_key(self):
        api_keys = self.config_manager.config.get("api_keys", {})
        return api_keys.get("dashscope_api_key", "")
    
    def _qwen_tts_request(self, payload):
        api_key = self._get_dashscope_api_key()
        if not api_key:
            raise ValueError("DashScope API Key 未配置")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        response = requests.post(self.QWEN_TTS_API_URL, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"API请求失败: {response.status_code} - {response.text}")
    
    def create_voice_design_async(self, voice_prompt, preview_text, preferred_name, language="zh"):
        logging.info(f"开始创建设计音色: {preferred_name}")
        worker = AsyncWorker(self._create_voice_design, voice_prompt, preview_text, preferred_name, language)
        worker.signals.finished.connect(self._on_qwen_voice_created)
        worker.signals.error.connect(lambda e: self.qwen_tts_error.emit(str(e)))
        self.thread_pool.start(worker)
    
    def _create_voice_design(self, voice_prompt, preview_text, preferred_name, language="zh"):
        payload = {
            "model": self.QWEN_VOICE_DESIGN_MODEL,
            "input": {
                "action": "create", "target_model": self.QWEN_VOICE_DESIGN_TARGET,
                "voice_prompt": voice_prompt, "preview_text": preview_text,
                "preferred_name": preferred_name, "language": language
            },
            "parameters": {"sample_rate": 24000, "response_format": "wav"}
        }
        result = self._qwen_tts_request(payload)
        output = result.get("output", {})
        voice_name = output.get("voice")
        if not voice_name:
            raise Exception("API返回中缺少voice字段")
        return {
            "voice": voice_name, "preview_audio_data": output.get("preview_audio", {}).get("data"),
            "type": "voice_design", "target_model": self.QWEN_VOICE_DESIGN_TARGET,
            "preferred_name": preferred_name, "language": language
        }
    
    def create_voice_clone_async(self, audio_path, preferred_name):
        logging.info(f"开始创建复刻音色: {preferred_name}")
        worker = AsyncWorker(self._create_voice_clone, audio_path, preferred_name)
        worker.signals.finished.connect(self._on_qwen_voice_created)
        worker.signals.error.connect(lambda e: self.qwen_tts_error.emit(str(e)))
        self.thread_pool.start(worker)
    
    def _create_voice_clone(self, audio_path, preferred_name):
        mime_type, _ = mimetypes.guess_type(audio_path)
        if not mime_type:
            mime_type = "audio/mpeg"
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        payload = {
            "model": self.QWEN_VOICE_CLONE_MODEL,
            "input": {
                "action": "create", "target_model": self.QWEN_VOICE_CLONE_TARGET,
                "preferred_name": preferred_name,
                "audio": {"data": f"data:{mime_type};base64,{audio_b64}"}
            }
        }
        result = self._qwen_tts_request(payload)
        voice_name = result.get("output", {}).get("voice")
        if not voice_name:
            raise Exception("API返回中缺少voice字段")
        return {
            "voice": voice_name, "type": "voice_clone",
            "target_model": self.QWEN_VOICE_CLONE_TARGET, "preferred_name": preferred_name
        }
    
    def list_qwen_voices_async(self, voice_type="voice_design"):
        model = self.QWEN_VOICE_DESIGN_MODEL if voice_type == "voice_design" else self.QWEN_VOICE_CLONE_MODEL
        worker = AsyncWorker(self._list_qwen_voices, model, voice_type)
        worker.signals.finished.connect(self._on_qwen_voice_list_fetched)
        worker.signals.error.connect(lambda e: self.qwen_tts_error.emit(str(e)))
        self.thread_pool.start(worker)
    
    def _list_qwen_voices(self, model, voice_type):
        payload = {"model": model, "input": {"action": "list", "page_index": 0, "page_size": 100}}
        result = self._qwen_tts_request(payload)
        output = result.get("output", {})
        
        # Determine expected target prefix to filter
        expected_target_prefix = "qwen3-tts-vd" if voice_type == "voice_design" else "qwen3-tts-vc"
        
        voices = []
        for v in output.get("voice_list", []):
            voice_id = v.get("voice")
            voice_target_model = v.get("target_model", "")
            
            # Filter based on target model to strictly separate lists
            if expected_target_prefix not in voice_target_model:
                continue
                
            voices.append({
                "voice": voice_id,
                "type": voice_type,
                "target_model": voice_target_model, # Use actual model from API
                # Compatibility keys for VoiceSelector
                "Name": voice_id, 
                "ShortName": voice_id,
                "Gender": "AI" if voice_type == "voice_design" else "Clone",
                "Locale": v.get("language", "zh-CN")
            })
            
        logging.info(f"获取到 {len(voices)} 个 {voice_type} 音色 (Filtered by {expected_target_prefix})")
        return voice_type, voices
    
    def delete_qwen_voice_async(self, voice_name, voice_type="voice_design"):
        model = self.QWEN_VOICE_DESIGN_MODEL if voice_type == "voice_design" else self.QWEN_VOICE_CLONE_MODEL
        worker = AsyncWorker(self._delete_qwen_voice, voice_name, model)
        worker.signals.finished.connect(lambda _: self.qwen_voice_deleted.emit(voice_name))
        worker.signals.error.connect(lambda e: self.qwen_tts_error.emit(str(e)))
        self.thread_pool.start(worker)
    
    def _delete_qwen_voice(self, voice_name, model):
        payload = {"model": model, "input": {"action": "delete", "voice": voice_name}}
        self._qwen_tts_request(payload)
        logging.info(f"音色 {voice_name} 删除成功")
        return voice_name
    
    def _on_qwen_voice_created(self, result):
        if isinstance(result, dict) and "voice" in result:
            logging.info(f"Qwen音色创建成功: {result.get('voice')}")
            self.qwen_voice_created.emit(result)
    
    def _on_qwen_voice_list_fetched(self, result):
        if isinstance(result, tuple) and len(result) == 2:
            self.qwen_voice_list_fetched.emit(result[0], result[1])
        elif isinstance(result, list):
             # Fallback just in case, though structure changed
             self.qwen_voice_list_fetched.emit("unknown", result)
