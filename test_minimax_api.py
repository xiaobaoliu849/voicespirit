"""测试 MiniMax TTS API 响应格式"""
import httpx
import json
import sys
import base64
sys.path.insert(0, 'd:/voicespirit')

from app.core.config import ConfigManager

config = ConfigManager()
api_key = config.get("minimax.api_key", "")

if not api_key:
    print("MiniMax API Key not configured!")
    sys.exit(1)

print(f"API Key: {api_key[:10]}...")

base_url = "https://api.minimax.chat/v1/t2a_v2"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "speech-02-turbo",
    "text": "Hello, this is a test.",
    "voice_setting": {
        "voice_id": "male-qn-qingse",
        "speed": 1.0,
        "vol": 1.0,
        "pitch": 0
    },
    "stream": False,
    "audio_setting": {
        "sample_rate": 32000,
        "format": "mp3"
    }
}

print(f"Sending request...")

try:
    with httpx.Client(timeout=60.0) as client:
        response = client.post(base_url, json=payload, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            sys.exit(1)
        
        resp_json = response.json()
        print(f"Keys: {list(resp_json.keys())}")
        
        base_resp = resp_json.get("base_resp", {})
        print(f"base_resp: {base_resp}")
        
        data = resp_json.get("data", {})
        audio_str = data.get("audio", "")
        
        print(f"audio type: {type(audio_str)}, length: {len(audio_str)}")
        print(f"audio first 100 chars: {audio_str[:100]}")
        
        # Try hex decode
        try:
            audio_bytes = bytes.fromhex(audio_str)
            print(f"Hex decode SUCCESS! Size: {len(audio_bytes)} bytes")
            
            test_file = "d:/voicespirit/test_minimax_hex.mp3"
            with open(test_file, 'wb') as f:
                f.write(audio_bytes)
            print(f"Saved to: {test_file}")
            
            # Check file header
            print(f"File header (hex): {audio_bytes[:16].hex()}")
            
        except Exception as e:
            print(f"Hex decode failed: {e}")
            
            # Try base64
            try:
                audio_bytes = base64.b64decode(audio_str)
                print(f"Base64 decode SUCCESS! Size: {len(audio_bytes)} bytes")
                
                test_file = "d:/voicespirit/test_minimax_b64.mp3"
                with open(test_file, 'wb') as f:
                    f.write(audio_bytes)
                print(f"Saved to: {test_file}")
                
                print(f"File header (hex): {audio_bytes[:16].hex()}")
                
            except Exception as e2:
                print(f"Base64 decode also failed: {e2}")
                
except Exception as e:
    print(f"Request failed: {e}")
    import traceback
    traceback.print_exc()
