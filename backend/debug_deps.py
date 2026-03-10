import sys
print(f"Python Executable: {sys.executable}")
print(f"Python Path: {sys.path}")

print("\n--- Checking DashScope ---")
try:
    from dashscope.audio.qwen_omni import AudioFormat, MultiModality, OmniRealtimeConversation
    print("DashScope Realtime Imports: SUCCESS")
except ImportError as e:
    print(f"DashScope Realtime Import Error: {e}")
except Exception as e:
    print(f"DashScope Realtime Unexpected Error: {e}")

print("\n--- Checking Google GenAI ---")
try:
    from google import genai
    print("Google GenAI Import: SUCCESS")
except ImportError as e:
    print(f"Google GenAI Import Error: {e}")
except Exception as e:
    print(f"Google GenAI Unexpected Error: {e}")
