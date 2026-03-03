import asyncio
import edge_tts

async def main():
    text = "Hello, this is a test."
    voice = "en-US-AriaNeural"
    output = "test.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output)
        print(f"Success! Saved to {output}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
