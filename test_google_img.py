
import os
import sys
import logging
from app.core.config import ConfigManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_google_image_gen():
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logging.error("google-genai library not found.")
        return

    config_manager = ConfigManager()
    api_key = config_manager.config.get("api_keys", {}).get("google_api_key")

    if not api_key:
        logging.error("Google API Key not found in config.")
        return

    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})

    logging.info("Listing available models...")
    try:
        found_models = []
        for m in client.models.list():
            logging.info(f"Model: {m.name}")
            found_models.append(m.name)
    except Exception as e:
        logging.error(f"Error listing models: {e}")
        return

    prompt = "A futuristic city with flying cars, digital art style"

    # Test generate_content for image generation (Gemini 2.0 Native)
    logging.info("\n--- Testing generate_content for Image Generation (Gemini 2.0) ---")
    test_model = "gemini-2.0-flash-001"
    try:
        logging.info(f"Sending prompt to {test_model}: '{prompt}'")
        response = client.models.generate_content(
            model=test_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"] # Request IMAGE modality if supported
            )
        )
        
        # Check response parts
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    logging.info("SUCCESS: Received inline image data!")
                    filename = f"test_gen_content_{test_model}.jpg" # Guessing extension
                    with open(filename, "wb") as f:
                        f.write(part.inline_data.data) # Assuming data is bytes
                    logging.info(f"Saved to {filename}")
                    return
                elif part.text:
                    logging.info(f"Received text instead: {part.text[:100]}...")
        else:
            logging.warning("No content parts received.")

    except Exception as e:
        # Retry without response_modalities config
        logging.warning(f"generate_content with config failed: {e}")
        try:
             logging.info("Retrying without explicit modality config...")
             response = client.models.generate_content(
                model=test_model,
                contents=f"Generate an image of {prompt}"
             )
             if response.text:
                  logging.info(f"Received text: {response.text[:100]}...")
             # Check for other attributes
        except Exception as e2:
             logging.error(f"Retry failed: {e2}")

if __name__ == "__main__":
    test_google_image_gen()
