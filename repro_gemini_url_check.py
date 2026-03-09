
import os
import inspect
import logging

try:
    from google import genai
    from google.genai import types
    print("google.genai imported successfully.")
    
    # Check Client signature
    sig = inspect.signature(genai.Client)
    print(f"genai.Client signature: {sig}")
    
    # Try to instantiate with different options to see if they are accepted (without making calls)
    try:
        print("Attempting to instantiate with http_options={'base_url': 'https://test.com'}...")
        client = genai.Client(api_key="TEST_KEY", http_options={'base_url': 'https://test.com'})
        print("Success! 'base_url' in http_options is accepted (at least in constructor).")
        # print(f"Client: {client.__dict__}")
    except Exception as e:
        print(f"Failed with 'base_url': {e}")

    try:
        print("Attempting to instantiate with http_options={'api_endpoint': 'https://test.com'}...")
        client = genai.Client(api_key="TEST_KEY", http_options={'api_endpoint': 'https://test.com'})
        print("Success! 'api_endpoint' in http_options is accepted.")
    except Exception as e:
        print(f"Failed with 'api_endpoint': {e}")
        
    try:
        print("Attempting to instantiate with transport options (if applicable)...")
        # Some older clients used transport options
        pass
    except Exception as e:
        print(f"Failed: {e}")

except ImportError:
    print("google-genai library not found.")
