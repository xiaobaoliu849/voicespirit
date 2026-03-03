import asyncio
import edge_tts

async def main():
    text = "你好，这是一个测试。"
    voice = "zh-CN-XiaoxiaoNeural"
    output = "test_zh.mp3"
    print(f"Testing voice: {voice}")
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output)
        print(f"Success! Saved to {output}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
