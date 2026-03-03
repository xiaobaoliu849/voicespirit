# type: ignore
import edge_tts
import asyncio
import logging
import os
import tempfile
# Removed pygame import
from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QThreadPool, QTimer  # type: ignore
from pathlib import Path
import tempfile
from pydub import AudioSegment  # type: ignore
import aiohttp  # type: ignore
from datetime import datetime
from PySide6.QtCore import QMetaObject, Qt, Q_ARG  # type: ignore
import ssl
import sys
import threading
import time
import base64
from app.core.config import ConfigManager
from utils.audio_player import AudioPlayer
from utils.system_player import SystemAudioPlayer

# Google GenAI imports for Gemini TTS
try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except ImportError:
    genai = None
    types = None
    logging.warning("google-genai library not found. Gemini TTS will not be available.")

# MiniMax TTS imports
try:
    import httpx  # type: ignore
except ImportError:
    httpx = None
    logging.warning("httpx library not found. MiniMax TTS will not be available.")

# TTS Engine constants
TTS_ENGINE_EDGE = "edge"
TTS_ENGINE_GEMINI = "gemini"
TTS_ENGINE_MINIMAX = "minimax"
TTS_ENGINE_QWEN_FLASH = "qwen_flash"
TTS_ENGINE_QWEN_VD = "qwen_vd"
TTS_ENGINE_QWEN_VC = "qwen_vc"

# Gemini TTS available voices (based on official Google documentation)
GEMINI_TTS_VOICES = [
    {"Name": "Puck", "ShortName": "Puck", "Gender": "Male", "Locale": "multi", "Style": "Upbeat"},
    {"Name": "Charon", "ShortName": "Charon", "Gender": "Male", "Locale": "multi", "Style": "Informative"},
    {"Name": "Kore", "ShortName": "Kore", "Gender": "Male", "Locale": "multi", "Style": "Firm"},
    {"Name": "Fenrir", "ShortName": "Fenrir", "Gender": "Male", "Locale": "multi", "Style": "Excitable"},
    {"Name": "Aoede", "ShortName": "Aoede", "Gender": "Female", "Locale": "multi", "Style": "Breezy"},
    {"Name": "Leda", "ShortName": "Leda", "Gender": "Female", "Locale": "multi", "Style": "Youthful"},
    {"Name": "Orus", "ShortName": "Orus", "Gender": "Male", "Locale": "multi", "Style": "Firm"},
    {"Name": "Zephyr", "ShortName": "Zephyr", "Gender": "Female", "Locale": "multi", "Style": "Bright"},
    {"Name": "Lyra", "ShortName": "Lyra", "Gender": "Female", "Locale": "multi", "Style": "Clear"},
    {"Name": "Callirrhoe", "ShortName": "Callirrhoe", "Gender": "Female", "Locale": "multi", "Style": "Easy-going"},
    {"Name": "Autonoe", "ShortName": "Autonoe", "Gender": "Female", "Locale": "multi", "Style": "Bright"},
    {"Name": "Enceladus", "ShortName": "Enceladus", "Gender": "Male", "Locale": "multi", "Style": "Breathy"},
    {"Name": "Iapetus", "ShortName": "Iapetus", "Gender": "Male", "Locale": "multi", "Style": "Clear"},
    {"Name": "Umbriel", "ShortName": "Umbriel", "Gender": "Male", "Locale": "multi", "Style": "Easy-going"},
    {"Name": "Algieba", "ShortName": "Algieba", "Gender": "Male", "Locale": "multi", "Style": "Smooth"},
    {"Name": "Despina", "ShortName": "Despina", "Gender": "Female", "Locale": "multi", "Style": "Smooth"},
    {"Name": "Erinome", "ShortName": "Erinome", "Gender": "Female", "Locale": "multi", "Style": "Clear"},
    {"Name": "Algenib", "ShortName": "Algenib", "Gender": "Male", "Locale": "multi", "Style": "Gravelly"},
    {"Name": "Rasalgethi", "ShortName": "Rasalgethi", "Gender": "Female", "Locale": "multi", "Style": "Informative"},
    {"Name": "Laomedeia", "ShortName": "Laomedeia", "Gender": "Female", "Locale": "multi", "Style": "Upbeat"},
    {"Name": "Achernar", "ShortName": "Achernar", "Gender": "Male", "Locale": "multi", "Style": "Soft"},
    {"Name": "Alnilam", "ShortName": "Alnilam", "Gender": "Male", "Locale": "multi", "Style": "Firm"},
    {"Name": "Schedar", "ShortName": "Schedar", "Gender": "Female", "Locale": "multi", "Style": "Even"},
    {"Name": "Gacrux", "ShortName": "Gacrux", "Gender": "Female", "Locale": "multi", "Style": "Mature"},
    {"Name": "Pulcherrima", "ShortName": "Pulcherrima", "Gender": "Female", "Locale": "multi", "Style": "Forward"},
    {"Name": "Achird", "ShortName": "Achird", "Gender": "Female", "Locale": "multi", "Style": "Friendly"},
    {"Name": "Zubenelgenubi", "ShortName": "Zubenelgenubi", "Gender": "Male", "Locale": "multi", "Style": "Casual"},
    {"Name": "Vindemiatrix", "ShortName": "Vindemiatrix", "Gender": "Female", "Locale": "multi", "Style": "Gentle"},
    {"Name": "Sadachbia", "ShortName": "Sadachbia", "Gender": "Female", "Locale": "multi", "Style": "Lively"},
    {"Name": "Sadaltager", "ShortName": "Sadaltager", "Gender": "Male", "Locale": "multi", "Style": "Knowledgeable"},
    {"Name": "Sulafat", "ShortName": "Sulafat", "Gender": "Female", "Locale": "multi", "Style": "Warm"},
]

# Qwen TTS Flash voices (from official 音色.txt - qwen3-tts-flash-2025-11-27)
# Format: Name (中文名), ShortName (voice参数), Gender, Locale
QWEN_TTS_FLASH_VOICES = [
    # Standard Chinese voices
    {"Name": "芊悦 (Cherry)", "ShortName": "Cherry", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "苏瑶 (Serena)", "ShortName": "Serena", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "晨煦 (Ethan)", "ShortName": "Ethan", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "千雪 (Chelsie)", "ShortName": "Chelsie", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "茉兔 (Momo)", "ShortName": "Momo", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "十三 (Vivian)", "ShortName": "Vivian", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "月白 (Moon)", "ShortName": "Moon", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "四月 (Maia)", "ShortName": "Maia", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "凯 (Kai)", "ShortName": "Kai", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "不吃鱼 (Nofish)", "ShortName": "Nofish", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "萌宝 (Bella)", "ShortName": "Bella", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "詹妮弗 (Jennifer)", "ShortName": "Jennifer", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "甜茶 (Ryan)", "ShortName": "Ryan", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "卡捷琳娜 (Katerina)", "ShortName": "Katerina", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "艾登 (Aiden)", "ShortName": "Aiden", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "沧明子 (Eldric Sage)", "ShortName": "Eldric Sage", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "乖小妹 (Mia)", "ShortName": "Mia", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "沙小弥 (Mochi)", "ShortName": "Mochi", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "燕铮莺 (Bellona)", "ShortName": "Bellona", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "田叔 (Vincent)", "ShortName": "Vincent", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "萌小姬 (Bunny)", "ShortName": "Bunny", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "阿闻 (Neil)", "ShortName": "Neil", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "墨讲师 (Elias)", "ShortName": "Elias", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "徐大爷 (Arthur)", "ShortName": "Arthur", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "邻家妹妹 (Nini)", "ShortName": "Nini", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "诡婆婆 (Ebona)", "ShortName": "Ebona", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "小婉 (Seren)", "ShortName": "Seren", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "顽屁小孩 (Pip)", "ShortName": "Pip", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "少女阿月 (Stella)", "ShortName": "Stella", "Gender": "Female", "Locale": "zh-CN"},
    # International voices
    {"Name": "博德加 (Bodega)", "ShortName": "Bodega", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "索尼莎 (Sonrisa)", "ShortName": "Sonrisa", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "阿列克 (Alek)", "ShortName": "Alek", "Gender": "Male", "Locale": "ru-RU"},
    {"Name": "多尔切 (Dolce)", "ShortName": "Dolce", "Gender": "Male", "Locale": "it-IT"},
    {"Name": "素熙 (Sohee)", "ShortName": "Sohee", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "小野杏 (Ono Anna)", "ShortName": "Ono Anna", "Gender": "Female", "Locale": "ja-JP"},
    {"Name": "莱恩 (Lenn)", "ShortName": "Lenn", "Gender": "Male", "Locale": "de-DE"},
    {"Name": "埃米尔安 (Emilien)", "ShortName": "Emilien", "Gender": "Male", "Locale": "fr-FR"},
    {"Name": "安德雷 (Andre)", "ShortName": "Andre", "Gender": "Male", "Locale": "multi"},
    {"Name": "拉迪奥·戈尔 (Radio Gol)", "ShortName": "Radio Gol", "Gender": "Male", "Locale": "pt-BR"},
    # Dialect voices (Chinese dialects)
    {"Name": "上海-阿珍 (Jada)", "ShortName": "Jada", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "北京-晓东 (Dylan)", "ShortName": "Dylan", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "南京-老李 (Li)", "ShortName": "Li", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "陕西-秦川 (Marcus)", "ShortName": "Marcus", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "闽南-阿杰 (Roy)", "ShortName": "Roy", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "天津-李彼得 (Peter)", "ShortName": "Peter", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "四川-晴儿 (Sunny)", "ShortName": "Sunny", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "四川-程川 (Eric)", "ShortName": "Eric", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "粤语-阿强 (Rocky)", "ShortName": "Rocky", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "粤语-阿清 (Kiki)", "ShortName": "Kiki", "Gender": "Female", "Locale": "zh-CN"},
]

# MiniMax TTS voices (from https://platform.minimaxi.com/docs/faq/system-voice-id)
# Format: Name (display name), ShortName (voice_id), Gender, Locale
MINIMAX_TTS_VOICES = [
    # Chinese (Mandarin) - 58 voices
    {"Name": "青涩青年音色", "ShortName": "male-qn-qingse", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "精英青年音色", "ShortName": "male-qn-jingying", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "霸道青年音色", "ShortName": "male-qn-badao", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "青年大学生音色", "ShortName": "male-qn-daxuesheng", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "少女音色", "ShortName": "female-shaonv", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "御姐音色", "ShortName": "female-yujie", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "成熟女性音色", "ShortName": "female-chengshu", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "甜美女性音色", "ShortName": "female-tianmei", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "青涩青年音色-beta", "ShortName": "male-qn-qingse-jingpin", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "精英青年音色-beta", "ShortName": "male-qn-jingying-jingpin", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "霸道青年音色-beta", "ShortName": "male-qn-badao-jingpin", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "青年大学生音色-beta", "ShortName": "male-qn-daxuesheng-jingpin", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "少女音色-beta", "ShortName": "female-shaonv-jingpin", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "御姐音色-beta", "ShortName": "female-yujie-jingpin", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "成熟女性音色-beta", "ShortName": "female-chengshu-jingpin", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "甜美女性音色-beta", "ShortName": "female-tianmei-jingpin", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "聪明男童", "ShortName": "clever_boy", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "可爱男童", "ShortName": "cute_boy", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "萌萌女童", "ShortName": "lovely_girl", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "卡通猪小琪", "ShortName": "cartoon_pig", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "病娇弟弟", "ShortName": "bingjiao_didi", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "俊朗男友", "ShortName": "junlang_nanyou", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "纯真学弟", "ShortName": "chunzhen_xuedi", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "冷淡学长", "ShortName": "lengdan_xiongzhang", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "霸道少爷", "ShortName": "badao_shaoye", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "甜心小玲", "ShortName": "tianxin_xiaoling", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "俏皮萌妹", "ShortName": "qiaopi_mengmei", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "妩媚御姐", "ShortName": "wumei_yujie", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "嗲嗲学妹", "ShortName": "diadia_xuemei", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "淡雅学姐", "ShortName": "danya_xuejie", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "沉稳高管", "ShortName": "Chinese (Mandarin)_Reliable_Executive", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "新闻女声", "ShortName": "Chinese (Mandarin)_News_Anchor", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "傲娇御姐", "ShortName": "Chinese (Mandarin)_Mature_Woman", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "不羁青年", "ShortName": "Chinese (Mandarin)_Unrestrained_Young_Man", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "嚣张小姐", "ShortName": "Arrogant_Miss", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "机械战甲", "ShortName": "Robot_Armor", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "热心大婶", "ShortName": "Chinese (Mandarin)_Kind-hearted_Antie", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "港普空姐", "ShortName": "Chinese (Mandarin)_HK_Flight_Attendant", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "搞笑大爷", "ShortName": "Chinese (Mandarin)_Humorous_Elder", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "温润男声", "ShortName": "Chinese (Mandarin)_Gentleman", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "温暖闺蜜", "ShortName": "Chinese (Mandarin)_Warm_Bestie", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "播报男声", "ShortName": "Chinese (Mandarin)_Male_Announcer", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "甜美女声", "ShortName": "Chinese (Mandarin)_Sweet_Lady", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "南方小哥", "ShortName": "Chinese (Mandarin)_Southern_Young_Man", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "阅历姐姐", "ShortName": "Chinese (Mandarin)_Wise_Women", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "温润青年", "ShortName": "Chinese (Mandarin)_Gentle_Youth", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "温暖少女", "ShortName": "Chinese (Mandarin)_Warm_Girl", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "花甲奶奶", "ShortName": "Chinese (Mandarin)_Kind-hearted_Elder", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "憨憨萌兽", "ShortName": "Chinese (Mandarin)_Cute_Spirit", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "电台男主播", "ShortName": "Chinese (Mandarin)_Radio_Host", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "抒情男声", "ShortName": "Chinese (Mandarin)_Lyrical_Voice", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "率真弟弟", "ShortName": "Chinese (Mandarin)_Straightforward_Boy", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "真诚青年", "ShortName": "Chinese (Mandarin)_Sincere_Adult", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "温柔学姐", "ShortName": "Chinese (Mandarin)_Gentle_Senior", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "嘴硬竹马", "ShortName": "Chinese (Mandarin)_Stubborn_Friend", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "清脆少女", "ShortName": "Chinese (Mandarin)_Crisp_Girl", "Gender": "Female", "Locale": "zh-CN"},
    {"Name": "清澈邻家弟弟", "ShortName": "Chinese (Mandarin)_Pure-hearted_Boy", "Gender": "Male", "Locale": "zh-CN"},
    {"Name": "软软女孩", "ShortName": "Chinese (Mandarin)_Soft_Girl", "Gender": "Female", "Locale": "zh-CN"},

    # Cantonese - 6 voices
    {"Name": "专业女主持", "ShortName": "Cantonese_ProfessionalHost（F)", "Gender": "Female", "Locale": "yue-CN"},
    {"Name": "温柔女声", "ShortName": "Cantonese_GentleLady", "Gender": "Female", "Locale": "yue-CN"},
    {"Name": "专业男主持", "ShortName": "Cantonese_ProfessionalHost（M)", "Gender": "Male", "Locale": "yue-CN"},
    {"Name": "活泼男声", "ShortName": "Cantonese_PlayfulMan", "Gender": "Male", "Locale": "yue-CN"},
    {"Name": "可爱女孩", "ShortName": "Cantonese_CuteGirl", "Gender": "Female", "Locale": "yue-CN"},
    {"Name": "善良女声", "ShortName": "Cantonese_KindWoman", "Gender": "Female", "Locale": "yue-CN"},

    # English - 16 voices
    {"Name": "Santa Claus", "ShortName": "Santa_Claus", "Gender": "Male", "Locale": "en-US"},
    {"Name": "Grinch", "ShortName": "Grinch", "Gender": "Male", "Locale": "en-US"},
    {"Name": "Rudolph", "ShortName": "Rudolph", "Gender": "Male", "Locale": "en-US"},
    {"Name": "Arnold", "ShortName": "Arnold", "Gender": "Male", "Locale": "en-US"},
    {"Name": "Charming Santa", "ShortName": "Charming_Santa", "Gender": "Male", "Locale": "en-US"},
    {"Name": "Charming Lady", "ShortName": "Charming_Lady", "Gender": "Female", "Locale": "en-US"},
    {"Name": "Sweet Girl", "ShortName": "Sweet_Girl", "Gender": "Female", "Locale": "en-US"},
    {"Name": "Cute Elf", "ShortName": "Cute_Elf", "Gender": "Female", "Locale": "en-US"},
    {"Name": "Attractive Girl", "ShortName": "Attractive_Girl", "Gender": "Female", "Locale": "en-US"},
    {"Name": "Serene Woman", "ShortName": "Serene_Woman", "Gender": "Female", "Locale": "en-US"},
    {"Name": "Trustworthy Man", "ShortName": "English_Trustworthy_Man", "Gender": "Male", "Locale": "en-US"},
    {"Name": "Graceful Lady", "ShortName": "English_Graceful_Lady", "Gender": "Female", "Locale": "en-US"},
    {"Name": "Aussie Bloke", "ShortName": "English_Aussie_Bloke", "Gender": "Male", "Locale": "en-US"},
    {"Name": "Whispering girl", "ShortName": "English_Whispering_girl", "Gender": "Female", "Locale": "en-US"},
    {"Name": "Diligent Man", "ShortName": "English_Diligent_Man", "Gender": "Male", "Locale": "en-US"},
    {"Name": "Gentle-voiced man", "ShortName": "English_Gentle-voiced_man", "Gender": "Male", "Locale": "en-US"},

    # Japanese - 15 voices
    {"Name": "Intellectual Senior", "ShortName": "Japanese_IntellectualSenior", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Decisive Princess", "ShortName": "Japanese_DecisivePrincess", "Gender": "Female", "Locale": "ja-JP"},
    {"Name": "Loyal Knight", "ShortName": "Japanese_LoyalKnight", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Dominant Man", "ShortName": "Japanese_DominantMan", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Serious Commander", "ShortName": "Japanese_SeriousCommander", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Cold Queen", "ShortName": "Japanese_ColdQueen", "Gender": "Female", "Locale": "ja-JP"},
    {"Name": "Dependable Woman", "ShortName": "Japanese_DependableWoman", "Gender": "Female", "Locale": "ja-JP"},
    {"Name": "Gentle Butler", "ShortName": "Japanese_GentleButler", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Kind Lady", "ShortName": "Japanese_KindLady", "Gender": "Female", "Locale": "ja-JP"},
    {"Name": "Calm Lady", "ShortName": "Japanese_CalmLady", "Gender": "Female", "Locale": "ja-JP"},
    {"Name": "Optimistic Youth", "ShortName": "Japanese_OptimisticYouth", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Generous Izakaya Owner", "ShortName": "Japanese_GenerousIzakayaOwner", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Sporty Student", "ShortName": "Japanese_SportyStudent", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Innocent Boy", "ShortName": "Japanese_InnocentBoy", "Gender": "Male", "Locale": "ja-JP"},
    {"Name": "Graceful Maiden", "ShortName": "Japanese_GracefulMaiden", "Gender": "Female", "Locale": "ja-JP"},

    # Korean - 49 voices
    {"Name": "Sweet Girl", "ShortName": "Korean_SweetGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Cheerful Boyfriend", "ShortName": "Korean_CheerfulBoyfriend", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Enchanting Sister", "ShortName": "Korean_EnchantingSister", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Shy Girl", "ShortName": "Korean_ShyGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Reliable Sister", "ShortName": "Korean_ReliableSister", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Strict Boss", "ShortName": "Korean_StrictBoss", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Sassy Girl", "ShortName": "Korean_SassyGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Childhood Friend Girl", "ShortName": "Korean_ChildhoodFriendGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Playboy Charmer", "ShortName": "Korean_PlayboyCharmer", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Elegant Princess", "ShortName": "Korean_ElegantPrincess", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Brave Female Warrior", "ShortName": "Korean_BraveFemaleWarrior", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Brave Youth", "ShortName": "Korean_BraveYouth", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Calm Lady", "ShortName": "Korean_CalmLady", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Enthusiastic Teen", "ShortName": "Korean_EnthusiasticTeen", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Soothing Lady", "ShortName": "Korean_SoothingLady", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Intellectual Senior", "ShortName": "Korean_IntellectualSenior", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Lonely Warrior", "ShortName": "Korean_LonelyWarrior", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Mature Lady", "ShortName": "Korean_MatureLady", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Innocent Boy", "ShortName": "Korean_InnocentBoy", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Charming Sister", "ShortName": "Korean_CharmingSister", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Athletic Student", "ShortName": "Korean_AthleticStudent", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Brave Adventurer", "ShortName": "Korean_BraveAdventurer", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Calm Gentleman", "ShortName": "Korean_CalmGentleman", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Wise Elf", "ShortName": "Korean_WiseElf", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Cheerful Cool Junior", "ShortName": "Korean_CheerfulCoolJunior", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Decisive Queen", "ShortName": "Korean_DecisiveQueen", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Cold Young Man", "ShortName": "Korean_ColdYoungMan", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Mysterious Girl", "ShortName": "Korean_MysteriousGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Quirky Girl", "ShortName": "Korean_QuirkyGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Considerate Senior", "ShortName": "Korean_ConsiderateSenior", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Cheerful Little Sister", "ShortName": "Korean_CheerfulLittleSister", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Dominant Man", "ShortName": "Korean_DominantMan", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Airheaded Girl", "ShortName": "Korean_AirheadedGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Reliable Youth", "ShortName": "Korean_ReliableYouth", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Friendly Big Sister", "ShortName": "Korean_FriendlyBigSister", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Gentle Boss", "ShortName": "Korean_GentleBoss", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Cold Girl", "ShortName": "Korean_ColdGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Haughty Lady", "ShortName": "Korean_HaughtyLady", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Charming Elder Sister", "ShortName": "Korean_CharmingElderSister", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Intellectual Man", "ShortName": "Korean_IntellectualMan", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Caring Woman", "ShortName": "Korean_CaringWoman", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Wise Teacher", "ShortName": "Korean_WiseTeacher", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Confident Boss", "ShortName": "Korean_ConfidentBoss", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Athletic Girl", "ShortName": "Korean_AthleticGirl", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Possessive Man", "ShortName": "Korean_PossessiveMan", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Gentle Woman", "ShortName": "Korean_GentleWoman", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Cocky Guy", "ShortName": "Korean_CockyGuy", "Gender": "Male", "Locale": "ko-KR"},
    {"Name": "Thoughtful Woman", "ShortName": "Korean_ThoughtfulWoman", "Gender": "Female", "Locale": "ko-KR"},
    {"Name": "Optimistic Youth", "ShortName": "Korean_OptimisticYouth", "Gender": "Male", "Locale": "ko-KR"},

    # Spanish - 47 voices
    {"Name": "Serene Woman", "ShortName": "Spanish_SereneWoman", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Mature Partner", "ShortName": "Spanish_MaturePartner", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Captivating Storyteller", "ShortName": "Spanish_CaptivatingStoryteller", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Narrator", "ShortName": "Spanish_Narrator", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Wise Scholar", "ShortName": "Spanish_WiseScholar", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Kind-hearted Girl", "ShortName": "Spanish_Kind-heartedGirl", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Determined Manager", "ShortName": "Spanish_DeterminedManager", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Bossy Leader", "ShortName": "Spanish_BossyLeader", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Reserved Young Man", "ShortName": "Spanish_ReservedYoungMan", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Confident Woman", "ShortName": "Spanish_ConfidentWoman", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Thoughtful Man", "ShortName": "Spanish_ThoughtfulMan", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Strong-willed Boy", "ShortName": "Spanish_Strong-WilledBoy", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Sophisticated Lady", "ShortName": "Spanish_SophisticatedLady", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Rational Man", "ShortName": "Spanish_RationalMan", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Anime Character", "ShortName": "Spanish_AnimeCharacter", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Deep-toned Man", "ShortName": "Spanish_Deep-tonedMan", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Fussy hostess", "ShortName": "Spanish_Fussyhostess", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Sincere Teen", "ShortName": "Spanish_SincereTeen", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Frank Lady", "ShortName": "Spanish_FrankLady", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Comedian", "ShortName": "Spanish_Comedian", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Debator", "ShortName": "Spanish_Debator", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Tough Boss", "ShortName": "Spanish_ToughBoss", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Wise Lady", "ShortName": "Spanish_Wiselady", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Steady Mentor", "ShortName": "Spanish_Steadymentor", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Jovial Man", "ShortName": "Spanish_Jovialman", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Santa Claus", "ShortName": "Spanish_SantaClaus", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Rudolph", "ShortName": "Spanish_Rudolph", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Intonate Girl", "ShortName": "Spanish_Intonategirl", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Arnold", "ShortName": "Spanish_Arnold", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Ghost", "ShortName": "Spanish_Ghost", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Humorous Elder", "ShortName": "Spanish_HumorousElder", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Energetic Boy", "ShortName": "Spanish_EnergeticBoy", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Whimsical Girl", "ShortName": "Spanish_WhimsicalGirl", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Strict Boss", "ShortName": "Spanish_StrictBoss", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Reliable Man", "ShortName": "Spanish_ReliableMan", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Serene Elder", "ShortName": "Spanish_SereneElder", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Angry Man", "ShortName": "Spanish_AngryMan", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Assertive Queen", "ShortName": "Spanish_AssertiveQueen", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Caring Girlfriend", "ShortName": "Spanish_CaringGirlfriend", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Powerful Soldier", "ShortName": "Spanish_PowerfulSoldier", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Passionate Warrior", "ShortName": "Spanish_PassionateWarrior", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Chatty Girl", "ShortName": "Spanish_ChattyGirl", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Romantic Husband", "ShortName": "Spanish_RomanticHusband", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Compelling Girl", "ShortName": "Spanish_CompellingGirl", "Gender": "Female", "Locale": "es-ES"},
    {"Name": "Powerful Veteran", "ShortName": "Spanish_PowerfulVeteran", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Sensible Manager", "ShortName": "Spanish_SensibleManager", "Gender": "Male", "Locale": "es-ES"},
    {"Name": "Thoughtful Lady", "ShortName": "Spanish_ThoughtfulLady", "Gender": "Female", "Locale": "es-ES"},

    # Portuguese - 76 voices
    {"Name": "Sentimental Lady", "ShortName": "Portuguese_SentimentalLady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Bossy Leader", "ShortName": "Portuguese_BossyLeader", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Wise lady", "ShortName": "Portuguese_Wiselady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Strong-willed Boy", "ShortName": "Portuguese_Strong-WilledBoy", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Deep-voiced Gentleman", "ShortName": "Portuguese_Deep-VoicedGentleman", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Upset Girl", "ShortName": "Portuguese_UpsetGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Passionate Warrior", "ShortName": "Portuguese_PassionateWarrior", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Anime Character", "ShortName": "Portuguese_AnimeCharacter", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Confident Woman", "ShortName": "Portuguese_ConfidentWoman", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Angry Man", "ShortName": "Portuguese_AngryMan", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Captivating Storyteller", "ShortName": "Portuguese_CaptivatingStoryteller", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Godfather", "ShortName": "Portuguese_Godfather", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Reserved Young Man", "ShortName": "Portuguese_ReservedYoungMan", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Smart Young Girl", "ShortName": "Portuguese_SmartYoungGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Kind-hearted Girl", "ShortName": "Portuguese_Kind-heartedGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Pompous lady", "ShortName": "Portuguese_Pompouslady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Grinch", "ShortName": "Portuguese_Grinch", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Debator", "ShortName": "Portuguese_Debator", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Sweet Girl", "ShortName": "Portuguese_SweetGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Attractive Girl", "ShortName": "Portuguese_AttractiveGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Thoughtful Man", "ShortName": "Portuguese_ThoughtfulMan", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Playful Girl", "ShortName": "Portuguese_PlayfulGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Gorgeous Lady", "ShortName": "Portuguese_GorgeousLady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Lovely Lady", "ShortName": "Portuguese_LovelyLady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Serene Woman", "ShortName": "Portuguese_SereneWoman", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Sad Teen", "ShortName": "Portuguese_SadTeen", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Mature Partner", "ShortName": "Portuguese_MaturePartner", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Comedian", "ShortName": "Portuguese_Comedian", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Naughty Schoolgirl", "ShortName": "Portuguese_NaughtySchoolgirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Narrator", "ShortName": "Portuguese_Narrator", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Tough Boss", "ShortName": "Portuguese_ToughBoss", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Fussy hostess", "ShortName": "Portuguese_Fussyhostess", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Dramatist", "ShortName": "Portuguese_Dramatist", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Steady Mentor", "ShortName": "Portuguese_Steadymentor", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Jovial Man", "ShortName": "Portuguese_Jovialman", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Charming Queen", "ShortName": "Portuguese_CharmingQueen", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Santa Claus", "ShortName": "Portuguese_SantaClaus", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Rudolph", "ShortName": "Portuguese_Rudolph", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Arnold", "ShortName": "Portuguese_Arnold", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Charming Santa", "ShortName": "Portuguese_CharmingSanta", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Charming Lady", "ShortName": "Portuguese_CharmingLady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Ghost", "ShortName": "Portuguese_Ghost", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Humorous Elder", "ShortName": "Portuguese_HumorousElder", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Calm Leader", "ShortName": "Portuguese_CalmLeader", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Gentle Teacher", "ShortName": "Portuguese_GentleTeacher", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Energetic Boy", "ShortName": "Portuguese_EnergeticBoy", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Reliable Man", "ShortName": "Portuguese_ReliableMan", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Serene Elder", "ShortName": "Portuguese_SereneElder", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Grim Reaper", "ShortName": "Portuguese_GrimReaper", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Assertive Queen", "ShortName": "Portuguese_AssertiveQueen", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Whimsical Girl", "ShortName": "Portuguese_WhimsicalGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Stressed Lady", "ShortName": "Portuguese_StressedLady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Friendly Neighbor", "ShortName": "Portuguese_FriendlyNeighbor", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Caring Girlfriend", "ShortName": "Portuguese_CaringGirlfriend", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Powerful Soldier", "ShortName": "Portuguese_PowerfulSoldier", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Fascinating Boy", "ShortName": "Portuguese_FascinatingBoy", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Romantic Husband", "ShortName": "Portuguese_RomanticHusband", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Strict Boss", "ShortName": "Portuguese_StrictBoss", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Inspiring Lady", "ShortName": "Portuguese_InspiringLady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Playful Spirit", "ShortName": "Portuguese_PlayfulSpirit", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Elegant Girl", "ShortName": "Portuguese_ElegantGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Compelling Girl", "ShortName": "Portuguese_CompellingGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Powerful Veteran", "ShortName": "Portuguese_PowerfulVeteran", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Sensible Manager", "ShortName": "Portuguese_SensibleManager", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Thoughtful Lady", "ShortName": "Portuguese_ThoughtfulLady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Theatrical Actor", "ShortName": "Portuguese_TheatricalActor", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Fragile Boy", "ShortName": "Portuguese_FragileBoy", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Chatty Girl", "ShortName": "Portuguese_ChattyGirl", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Conscientious Instructor", "ShortName": "Portuguese_Conscientiousinstructor", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Rational Man", "ShortName": "Portuguese_RationalMan", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Wise Scholar", "ShortName": "Portuguese_WiseScholar", "Gender": "Male", "Locale": "pt-BR"},
    {"Name": "Frank Lady", "ShortName": "Portuguese_FrankLady", "Gender": "Female", "Locale": "pt-BR"},
    {"Name": "Determined Manager", "ShortName": "Portuguese_DeterminedManager", "Gender": "Male", "Locale": "pt-BR"},

    # French - 6 voices
    {"Name": "Level-Headed Man", "ShortName": "French_Male_Speech_New", "Gender": "Male", "Locale": "fr-FR"},
    {"Name": "Patient Female Presenter", "ShortName": "French_Female_News Anchor", "Gender": "Female", "Locale": "fr-FR"},
    {"Name": "Casual Man", "ShortName": "French_CasualMan", "Gender": "Male", "Locale": "fr-FR"},
    {"Name": "Movie Lead Female", "ShortName": "French_MovieLeadFemale", "Gender": "Female", "Locale": "fr-FR"},
    {"Name": "Female Anchor", "ShortName": "French_FemaleAnchor", "Gender": "Female", "Locale": "fr-FR"},
    {"Name": "Male Narrator", "ShortName": "French_MaleNarrator", "Gender": "Male", "Locale": "fr-FR"},

    # Indonesian - 10 voices
    {"Name": "Sweet Girl", "ShortName": "Indonesian_SweetGirl", "Gender": "Female", "Locale": "id-ID"},
    {"Name": "Reserved Young Man", "ShortName": "Indonesian_ReservedYoungMan", "Gender": "Male", "Locale": "id-ID"},
    {"Name": "Charming Girl", "ShortName": "Indonesian_CharmingGirl", "Gender": "Female", "Locale": "id-ID"},
    {"Name": "Calm Woman", "ShortName": "Indonesian_CalmWoman", "Gender": "Female", "Locale": "id-ID"},
    {"Name": "Confident Woman", "ShortName": "Indonesian_ConfidentWoman", "Gender": "Female", "Locale": "id-ID"},
    {"Name": "Caring Man", "ShortName": "Indonesian_CaringMan", "Gender": "Male", "Locale": "id-ID"},
    {"Name": "Bossy Leader", "ShortName": "Indonesian_BossyLeader", "Gender": "Male", "Locale": "id-ID"},
    {"Name": "Determined Boy", "ShortName": "Indonesian_DeterminedBoy", "Gender": "Male", "Locale": "id-ID"},
    {"Name": "Gentle Girl", "ShortName": "Indonesian_GentleGirl", "Gender": "Female", "Locale": "id-ID"},

    # German - 3 voices
    {"Name": "Friendly Man", "ShortName": "German_FriendlyMan", "Gender": "Male", "Locale": "de-DE"},
    {"Name": "Sweet Lady", "ShortName": "German_SweetLady", "Gender": "Female", "Locale": "de-DE"},
    {"Name": "Playful Man", "ShortName": "German_PlayfulMan", "Gender": "Male", "Locale": "de-DE"},

    # Russian - 8 voices
    {"Name": "Handsome Childhood Friend", "ShortName": "Russian_HandsomeChildhoodFriend", "Gender": "Male", "Locale": "ru-RU"},
    {"Name": "Bright Queen", "ShortName": "Russian_BrightHeroine", "Gender": "Female", "Locale": "ru-RU"},
    {"Name": "Ambitious Woman", "ShortName": "Russian_AmbitiousWoman", "Gender": "Female", "Locale": "ru-RU"},
    {"Name": "Reliable Man", "ShortName": "Russian_ReliableMan", "Gender": "Male", "Locale": "ru-RU"},
    {"Name": "Crazy Girl", "ShortName": "Russian_CrazyQueen", "Gender": "Female", "Locale": "ru-RU"},
    {"Name": "Pessimistic Girl", "ShortName": "Russian_PessimisticGirl", "Gender": "Female", "Locale": "ru-RU"},
    {"Name": "Attractive Guy", "ShortName": "Russian_AttractiveGuy", "Gender": "Male", "Locale": "ru-RU"},
    {"Name": "Bad-tempered Boy", "ShortName": "Russian_Bad-temperedBoy", "Gender": "Male", "Locale": "ru-RU"},

    # Italian - 4 voices
    {"Name": "Brave Heroine", "ShortName": "Italian_BraveHeroine", "Gender": "Female", "Locale": "it-IT"},
    {"Name": "Narrator", "ShortName": "Italian_Narrator", "Gender": "Male", "Locale": "it-IT"},
    {"Name": "Wandering Sorcerer", "ShortName": "Italian_WanderingSorcerer", "Gender": "Male", "Locale": "it-IT"},
    {"Name": "Diligent Leader", "ShortName": "Italian_DiligentLeader", "Gender": "Male", "Locale": "it-IT"},

    # Arabic - 2 voices
    {"Name": "Calm Woman", "ShortName": "Arabic_CalmWoman", "Gender": "Female", "Locale": "ar-SA"},
    {"Name": "Friendly Guy", "ShortName": "Arabic_FriendlyGuy", "Gender": "Male", "Locale": "ar-SA"},

    # Turkish - 2 voices
    {"Name": "Calm Woman", "ShortName": "Turkish_CalmWoman", "Gender": "Female", "Locale": "tr-TR"},
    {"Name": "Trustworthy man", "ShortName": "Turkish_Trustworthyman", "Gender": "Male", "Locale": "tr-TR"},

    # Ukrainian - 2 voices
    {"Name": "Calm Woman", "ShortName": "Ukrainian_CalmWoman", "Gender": "Female", "Locale": "uk-UA"},
    {"Name": "Wise Scholar", "ShortName": "Ukrainian_WiseScholar", "Gender": "Male", "Locale": "uk-UA"},

    # Dutch - 2 voices
    {"Name": "Kind-hearted girl", "ShortName": "Dutch_kindhearted_girl", "Gender": "Female", "Locale": "nl-NL"},
    {"Name": "Bossy leader", "ShortName": "Dutch_bossy_leader", "Gender": "Male", "Locale": "nl-NL"},

    # Vietnamese - 1 voice
    {"Name": "Kind-hearted girl", "ShortName": "Vietnamese_kindhearted_girl", "Gender": "Female", "Locale": "vi-VN"},

    # Thai - 4 voices
    {"Name": "Serene Man", "ShortName": "Thai_male_1_sample8", "Gender": "Male", "Locale": "th-TH"},
    {"Name": "Friendly Man", "ShortName": "Thai_male_2_sample2", "Gender": "Male", "Locale": "th-TH"},
    {"Name": "Confident Woman", "ShortName": "Thai_female_1_sample1", "Gender": "Female", "Locale": "th-TH"},
    {"Name": "Energetic Woman", "ShortName": "Thai_female_2_sample2", "Gender": "Female", "Locale": "th-TH"},

    # Polish - 4 voices
    {"Name": "Male Narrator", "ShortName": "Polish_male_1_sample4", "Gender": "Male", "Locale": "pl-PL"},
    {"Name": "Male Anchor", "ShortName": "Polish_male_2_sample3", "Gender": "Male", "Locale": "pl-PL"},
    {"Name": "Calm Woman", "ShortName": "Polish_female_1_sample1", "Gender": "Female", "Locale": "pl-PL"},
    {"Name": "Casual Woman", "ShortName": "Polish_female_2_sample3", "Gender": "Female", "Locale": "pl-PL"},

    # Romanian - 4 voices
    {"Name": "Reliable Man", "ShortName": "Romanian_male_1_sample2", "Gender": "Male", "Locale": "ro-RO"},
    {"Name": "Energetic Youth", "ShortName": "Romanian_male_2_sample1", "Gender": "Male", "Locale": "ro-RO"},
    {"Name": "Optimistic Youth", "ShortName": "Romanian_female_1_sample4", "Gender": "Female", "Locale": "ro-RO"},
    {"Name": "Gentle Woman", "ShortName": "Romanian_female_2_sample1", "Gender": "Female", "Locale": "ro-RO"},

    # Greek - 3 voices
    {"Name": "Thoughtful Mentor", "ShortName": "greek_male_1a_v1", "Gender": "Male", "Locale": "el-GR"},
    {"Name": "Gentle Lady", "ShortName": "Greek_female_1_sample1", "Gender": "Female", "Locale": "el-GR"},
    {"Name": "Girl Next Door", "ShortName": "Greek_female_2_sample3", "Gender": "Female", "Locale": "el-GR"},

    # Czech - 3 voices
    {"Name": "Assured Presenter", "ShortName": "czech_male_1_v1", "Gender": "Male", "Locale": "cs-CZ"},
    {"Name": "Steadfast Narrator", "ShortName": "czech_female_5_v7", "Gender": "Female", "Locale": "cs-CZ"},
    {"Name": "Elegant Lady", "ShortName": "czech_female_2_v2", "Gender": "Female", "Locale": "cs-CZ"},

    # Finnish - 3 voices
    {"Name": "Upbeat Man", "ShortName": "finnish_male_3_v1", "Gender": "Male", "Locale": "fi-FI"},
    {"Name": "Friendly Boy", "ShortName": "finnish_male_1_v2", "Gender": "Male", "Locale": "fi-FI"},
    {"Name": "Assetive Woman", "ShortName": "finnish_female_4_v1", "Gender": "Female", "Locale": "fi-FI"},

    # Hindi - 3 voices
    {"Name": "Trustworthy Advisor", "ShortName": "hindi_male_1_v2", "Gender": "Male", "Locale": "hi-IN"},
    {"Name": "Tranquil Woman", "ShortName": "hindi_female_2_v1", "Gender": "Female", "Locale": "hi-IN"},
    {"Name": "News Anchor", "ShortName": "hindi_female_1_v2", "Gender": "Female", "Locale": "hi-IN"},
]


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

# --- Worker for loading voices ---
class LoadVoicesRunnable(QRunnable):
    def __init__(self, tts_handler_instance): # Pass the TtsHandler instance
        super().__init__()
        self.tts_handler = tts_handler_instance

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # 确保调用的是 TtsHandler 类中的异步方法
            loop.run_until_complete(self.tts_handler.load_voices_async())
            loop.close()
        except Exception as e:
            logging.error(f"Error running LoadVoicesRunnable: {e}", exc_info=True)
            try:
                # 修复 QMetaObject.invokeMethod 的调用
                QMetaObject.invokeMethod(
                    self.tts_handler,
                    "use_fallback_voices",
                    Qt.QueuedConnection
                )
            except Exception as inner_e:
                logging.error(f"Failed to invoke fallback voices method: {inner_e}")

# --- Worker for TTS Generation ---
class TtsGenerateWorkerSignals(QObject):
    finished = Signal(str, bool)  # file_path, success
    error = Signal(str)
class TtsGenerateWorker(QRunnable):
    def __init__(self, text, voice_name, output_path, config_manager):
        super().__init__()
        self.signals = TtsGenerateWorkerSignals()
        self.text = text
        self.voice_name = voice_name
        self.output_path = output_path
        # 确保配置管理器存在
        if config_manager is None:
            self.config_manager = ConfigManager()
        else:
            self.config_manager = config_manager

    async def _generate_audio_file_async(self):
        retry_count = 3
        delay = 1
        voice_name_cleaned = self.voice_name.split(" (")[0].strip()

        for attempt in range(retry_count):
            try:
                # 使用代理设置
                proxy = self.config_manager.get("tts_settings.proxy", None)
                if proxy:
                    os.environ['HTTP_PROXY'] = proxy
                    os.environ['HTTPS_PROXY'] = proxy
                    logging.info(f"TTS Worker: Using proxy {proxy}")
                else:
                    # 清除代理设置
                    os.environ.pop('HTTP_PROXY', None)
                    os.environ.pop('HTTPS_PROXY', None)
                    logging.info("TTS Worker: No proxy configured.")

                logging.info(f"TTS Worker: Attempt {attempt+1} - Calling edge_tts.Communicate for voice '{voice_name_cleaned}'...")
                communicate = edge_tts.Communicate(self.text, voice_name_cleaned)

                # 确保输出目录存在
                output_dir = os.path.dirname(self.output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

                logging.info(f"TTS Worker: Attempt {attempt+1} - Calling communicate.save('{self.output_path}')...")
                await communicate.save(self.output_path)
                logging.info(f"TTS Worker: Attempt {attempt+1} - communicate.save completed.")

                # 验证生成的文件
                if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
                    logging.info(f"TTS Worker: Attempt {attempt+1} - File generated successfully.")
                    return True
                else:
                    logging.warning(f"TTS Worker: Attempt {attempt+1} - File generation failed (file missing or empty).")
                    raise Exception("Generated file is empty or missing")

            except Exception as e:
                logging.error(f"TTS generation error (attempt {attempt+1}): {e}", exc_info=True)
                if attempt < retry_count - 1:
                    await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
                else:
                    return False
        return False

    def run(self):
        try:
            success = asyncio.run(self._generate_audio_file_async())
            if success:
                self.signals.finished.emit(self.output_path, True)
            else:
                self.signals.error.emit("音频生成失败")
        except Exception as e:
            logging.error(f"Error in TtsGenerateWorker run: {e}", exc_info=True)
            self.signals.error.emit(str(e))

# --- Worker for Dialog TTS Generation ---
class DialogTtsGenerateWorkerSignals(QObject):
    finished = Signal(str, bool)  # file_path, success
    error = Signal(str)
    progress = Signal(int)
class DialogTtsGenerateWorker(QRunnable):
    def __init__(self, dialog_lines, role_a_voice, role_b_voice, output_path, config_manager=None, current_engine=TTS_ENGINE_EDGE):
        super().__init__()
        self.signals = DialogTtsGenerateWorkerSignals()
        self.dialog_lines = dialog_lines
        self.role_a_voice = role_a_voice
        self.role_b_voice = role_b_voice
        self.output_path = output_path
        self.current_engine = current_engine
        # 确保配置管理器存在
        if config_manager is None:
            self.config_manager = ConfigManager()
        else:
            self.config_manager = config_manager

    def run(self):
        temp_files = []
        try:
            total = len(self.dialog_lines)
            if total == 0:
                raise Exception("没有对话内容需要生成")

            # 确保输出目录存在
            output_dir = os.path.dirname(self.output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 初始化进度
            self.signals.progress.emit(0)

            for idx, line in enumerate(self.dialog_lines):
                text = line['text']
                role = line['role']
                voice = self.role_a_voice if role == 'A' else self.role_b_voice

                if not text.strip():
                    logging.warning(f"第{idx+1}句文本为空，跳过")
                    continue

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.close()

                try:
                    worker = TtsGenerateWorker(text, voice, temp_file.name, self.config_manager)
                    worker.run()

                    if not os.path.exists(temp_file.name) or os.path.getsize(temp_file.name) == 0:
                        raise Exception(f"第{idx+1}句音频生成失败")

                    temp_files.append(temp_file.name)
                    # 更新进度，从0到90%
                    progress = int((idx + 1) / total * 90)
                    self.signals.progress.emit(progress)

                except Exception as e:
                    logging.error(f"生成第{idx+1}句音频时出错: {e}")
                    raise Exception(f"第{idx+1}句音频生成失败: {str(e)}")

            if not temp_files:
                raise Exception("没有成功生成任何音频文件")

            # 合并音频文件
            try:
                self.signals.progress.emit(95)  # 开始合并
                combined = AudioSegment.empty()
                for f in temp_files:
                    combined += AudioSegment.from_file(f)
                combined.export(self.output_path, format="mp3")

                if not os.path.exists(self.output_path) or os.path.getsize(self.output_path) == 0:
                    raise Exception("合并后的音频文件为空")

                # 发送完成信号
                self.signals.progress.emit(100)
                self.signals.finished.emit(self.output_path, True)

            except Exception as e:
                logging.error(f"合并音频文件时出错: {e}")
                raise Exception(f"合并音频文件失败: {str(e)}")

        except Exception as e:
            logging.error(f"对话音频生成失败: {e}")
            self.signals.error.emit(f"对话音频生成失败: {e}")

        finally:
            # 清理临时文件
            for f in temp_files:
                try:
                    os.remove(f)
                except Exception as e:
                    logging.warning(f"清理临时文件失败: {e}")


# --- Worker for Preview Generation ---
class PreviewGenerateWorkerSignals(QObject):
    finished = Signal(str)
    error = Signal(str)

class PreviewGenerateWorker(QRunnable):
    def __init__(self, tts_handler_instance, text, voice_name):
        super().__init__()
        self.tts_handler = tts_handler_instance
        self.text = text
        self.voice_name = voice_name
        self.signals = PreviewGenerateWorkerSignals()

    @Slot()
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def _do_preview():
                try:
                    temp_dir = tempfile.gettempdir()
                    preview_file = os.path.join(temp_dir, f"preview_audio_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.mp3")
                    logging.info(f"Preview Worker: Generating to {preview_file}")
                    
                    proxy = self.tts_handler.config_manager.get("tts_settings.proxy", None)
                    if proxy:
                        os.environ['HTTP_PROXY'] = proxy
                        os.environ['HTTPS_PROXY'] = proxy
                    
                    communicate = edge_tts.Communicate(self.text, self.voice_name)
                    await communicate.save(preview_file)
                    
                    if os.path.exists(preview_file) and os.path.getsize(preview_file) > 0:
                        return preview_file
                    else:
                        raise Exception("Generated file is empty.")
                except Exception as e:
                    raise e

            task = loop.create_task(_do_preview())
            preview_file = loop.run_until_complete(task)
            self.signals.finished.emit(preview_file)

        except Exception as e:
            logging.error(f"Preview worker failed: {e}", exc_info=True)
            self.signals.error.emit(str(e))
        finally:
            loop.close()


# --- Worker for MiniMax Preview Generation ---
class MiniMaxPreviewGenerateWorkerSignals(QObject):
    finished = Signal(str)
    error = Signal(str)

class MiniMaxPreviewGenerateWorker(QRunnable):
    def __init__(self, text, voice_name, config_manager):
        super().__init__()
        self.text = text
        self.voice_name = voice_name
        self.config_manager = config_manager
        self.signals = MiniMaxPreviewGenerateWorkerSignals()

    def run(self):
        logging.info(f"MiniMax Preview Worker: Starting for text='{self.text[:30]}...', voice={self.voice_name}")
        try:
            # Reload config to get latest settings
            self.config_manager.load_config()

            # Get MiniMax API key from config
            api_key = self.config_manager.get("minimax.api_key", "")
            if not api_key:
                self.signals.error.emit("MiniMax API Key 未配置")
                return

            # Check if httpx is available
            if httpx is None:
                self.signals.error.emit("httpx 库未安装")
                return

            # Create temp file for preview
            temp_dir = tempfile.gettempdir()
            preview_file = os.path.join(temp_dir, f"preview_minimax_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.mp3")
            logging.info(f"MiniMax Preview Worker: Generating to {preview_file}")

            # MiniMax TTS API endpoint
            base_url = self.config_manager.get("api_urls.MiniMax", "").strip()
            if not base_url:
                base_url = "https://api.minimax.chat/v1/t2a_v2"
            elif not base_url.startswith(('http://', 'https://')):
                base_url = "https://" + base_url

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "speech-02-turbo",
                "text": self.text,
                "voice_setting": {
                    "voice_id": self.voice_name,
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

            logging.info(f"MiniMax TTS: Generating with payload={payload}, url={base_url}")

            # Make API request
            with httpx.Client(timeout=120.0) as client:
                response = client.post(base_url, json=payload, headers=headers)

                if response.status_code != 200:
                    error_msg = f"MiniMax API 错误: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    self.signals.error.emit(error_msg)
                    return

                # MiniMax API returns JSON with audio data
                try:
                    resp_json = response.json()
                    logging.info(f"MiniMax API response keys: {resp_json.keys() if isinstance(resp_json, dict) else 'not a dict'}")

                    # Check for error in response
                    if resp_json.get("base_resp", {}).get("status_code", 0) != 0:
                        error_msg = f"MiniMax API 错误: {resp_json.get('base_resp', {}).get('status_msg', 'Unknown error')}"
                        logging.error(error_msg)
                        self.signals.error.emit(error_msg)
                        return

                    # Get audio data - MiniMax returns hex-encoded audio in data.audio
                    audio_obj = resp_json.get("data", {}).get("audio")
                    if isinstance(audio_obj, dict):
                        # Format: data.audio.data (hex encoded)
                        audio_hex = audio_obj.get("data", "")
                        if audio_hex:
                            audio_data = bytes.fromhex(audio_hex)
                        else:
                            self.signals.error.emit("未收到音频数据 (data.audio.data)")
                            return
                    elif isinstance(audio_obj, str):
                        # String format: hex encoded directly in data.audio
                        audio_data = bytes.fromhex(audio_obj)
                    elif resp_json.get("audio"):
                        # Alternative: top-level audio field (hex encoded)
                        audio_data = bytes.fromhex(resp_json.get("audio"))
                    else:
                        self.signals.error.emit("未收到音频数据")
                        return

                except Exception as e:
                    logging.error(f"Failed to parse MiniMax response: {e}")
                    # If not JSON, try raw content
                    audio_data = response.content

                if not audio_data:
                    self.signals.error.emit("未收到音频数据")
                    return

                # Save audio to file
                with open(preview_file, 'wb') as f:
                    f.write(audio_data)

            if os.path.exists(preview_file) and os.path.getsize(preview_file) > 0:
                logging.info(f"MiniMax preview generated successfully: {preview_file}")
                self.signals.finished.emit(preview_file)
            else:
                self.signals.error.emit("预览音频生成失败")

        except Exception as e:
            logging.error(f"MiniMax preview generation error: {e}", exc_info=True)
            self.signals.error.emit(str(e))


# --- Worker for Qwen TTS Generation (DashScope) ---
class QwenTtsGenerateWorkerSignals(QObject):
    finished = Signal(str, bool)  # file_path, success
    error = Signal(str)


class QwenTtsGenerateWorker(QRunnable):
    """Worker for generating TTS audio using Qwen/DashScope API."""
    
    def __init__(self, text, voice_name, target_model, output_path, config_manager=None):
        super().__init__()
        self.signals = QwenTtsGenerateWorkerSignals()
        self.text = text
        self.voice_name = voice_name
        self.target_model = target_model
        self.output_path = output_path
        self.config_manager = config_manager or ConfigManager()
    
    def run(self):
        try:
            # Get DashScope API key from config
            api_key = self.config_manager.get("dashscope.api_key", "")
            if not api_key:
                self.signals.error.emit("DashScope API Key 未配置")
                return
            
            # Try to import dashscope
            try:
                import dashscope
                from dashscope.audio.tts_v2 import SpeechSynthesizer
            except ImportError:
                self.signals.error.emit("dashscope 库未安装")
                return
            
            dashscope.api_key = api_key
            
            # Use the synchronous TTS API
            logging.info(f"Qwen TTS: Generating audio with model={self.target_model}, voice={self.voice_name}")
            
            # For qwen3-tts-flash model, use SpeechSynthesizer
            # For voice design/clone models, use MultiModalConversation
            if 'flash' in self.target_model.lower():
                synthesizer = SpeechSynthesizer(model=self.target_model, voice=self.voice_name)
                audio = synthesizer.call(self.text)
                
                # Ensure output directory exists
                output_dir = os.path.dirname(self.output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                
                # Write audio to file
                with open(self.output_path, 'wb') as f:
                    f.write(audio)
            else:
                # For voice design/clone models (qwen3-tts-vd-*, qwen3-tts-vc-*)
                from dashscope import MultiModalConversation
                
                response = MultiModalConversation.call(
                    model=self.target_model,
                    messages=[{
                        "role": "user",
                        "content": [{"text": self.text}]
                    }],
                    voice=self.voice_name,
                    response_format="mp3"
                )
                
                if response.status_code != 200:
                    self.signals.error.emit(f"DashScope API 错误: {response.message}")
                    return
                
                # Extract audio data
                audio_data = response.output.get("audio", {}).get("data", "")
                if not audio_data:
                    self.signals.error.emit("未收到音频数据")
                    return
                
                # Decode base64 and save
                import base64
                audio_bytes = base64.b64decode(audio_data)
                
                output_dir = os.path.dirname(self.output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                
                with open(self.output_path, 'wb') as f:
                    f.write(audio_bytes)
            
            # Verify file was created
            if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
                logging.info(f"Qwen TTS: Audio saved to {self.output_path}")
                self.signals.finished.emit(self.output_path, True)
            else:
                self.signals.error.emit("音频文件生成失败")
                
        except Exception as e:
            logging.error(f"Qwen TTS generation error: {e}", exc_info=True)
            self.signals.error.emit(str(e))


# --- Worker for MiniMax TTS Generation ---
class MiniMaxTtsGenerateWorkerSignals(QObject):
    finished = Signal(str, bool)  # file_path, success
    error = Signal(str)


class MiniMaxTtsGenerateWorker(QRunnable):
    """Worker for generating TTS audio using MiniMax API."""

    def __init__(self, text, voice_name, output_path, config_manager=None):
        super().__init__()
        self.signals = MiniMaxTtsGenerateWorkerSignals()
        self.text = text
        self.voice_name = voice_name
        self.output_path = output_path
        self.config_manager = config_manager or ConfigManager()

    def run(self):
        try:
            # Reload config to get latest settings
            self.config_manager.load_config()

            # Get MiniMax API key from config
            api_key = self.config_manager.get("minimax.api_key", "")
            if not api_key:
                self.signals.error.emit("MiniMax API Key 未配置")
                return

            # Check if httpx is available
            if httpx is None:
                self.signals.error.emit("httpx 库未安装")
                return

            # MiniMax TTS API endpoint
            base_url = self.config_manager.get("api_urls.MiniMax", "").strip()
            if not base_url:
                base_url = "https://api.minimax.chat/v1/t2a_v2"
            elif not base_url.startswith(('http://', 'https://')):
                base_url = "https://" + base_url

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "speech-02-turbo",
                "text": self.text,
                "voice_setting": {
                    "voice_id": self.voice_name,
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

            logging.info(f"MiniMax TTS: Generating audio with voice={self.voice_name}, url={base_url}")

            # Make API request
            with httpx.Client(timeout=120.0) as client:
                response = client.post(base_url, json=payload, headers=headers)

                if response.status_code != 200:
                    error_msg = f"MiniMax API 错误: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    self.signals.error.emit(error_msg)
                    return

                # MiniMax API returns JSON with audio data
                try:
                    resp_json = response.json()
                    logging.info(f"MiniMax API response keys: {resp_json.keys() if isinstance(resp_json, dict) else 'not a dict'}")

                    # Check for error in response
                    if resp_json.get("base_resp", {}).get("status_code", 0) != 0:
                        error_msg = f"MiniMax API 错误: {resp_json.get('base_resp', {}).get('status_msg', 'Unknown error')}"
                        logging.error(error_msg)
                        self.signals.error.emit(error_msg)
                        return

                    # Get audio data - MiniMax returns hex-encoded audio in data.audio
                    audio_obj = resp_json.get("data", {}).get("audio")
                    if isinstance(audio_obj, dict):
                        # Format: data.audio.data (hex encoded)
                        audio_hex = audio_obj.get("data", "")
                        if audio_hex:
                            audio_data = bytes.fromhex(audio_hex)
                        else:
                            self.signals.error.emit("未收到音频数据 (data.audio.data)")
                            return
                    elif isinstance(audio_obj, str):
                        # String format: hex encoded directly in data.audio
                        audio_data = bytes.fromhex(audio_obj)
                    elif resp_json.get("audio"):
                        # Alternative: top-level audio field (hex encoded)
                        audio_data = bytes.fromhex(resp_json.get("audio"))
                    else:
                        self.signals.error.emit("未收到音频数据")
                        return

                except Exception as e:
                    logging.error(f"Failed to parse MiniMax response: {e}")
                    # If not JSON, try raw content
                    audio_data = response.content

                if not audio_data:
                    self.signals.error.emit("未收到音频数据")
                    return

                # Ensure output directory exists
                output_dir = os.path.dirname(self.output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

                # Save audio to file
                with open(self.output_path, 'wb') as f:
                    f.write(audio_data)

            # Verify file was created
            if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
                logging.info(f"MiniMax TTS: Audio saved to {self.output_path}")
                self.signals.finished.emit(self.output_path, True)
            else:
                self.signals.error.emit("音频文件生成失败")

        except Exception as e:
            logging.error(f"MiniMax TTS generation error: {e}", exc_info=True)
            self.signals.error.emit(str(e))


# --- Main TTS Handler ---
class TtsHandler(QObject):
    """Handles TTS operations using edge-tts."""

    voices_loaded = Signal(list)
    preview_ready = Signal(str)
    generation_complete = Signal(str)
    generation_error = Signal(str)
    tts_error = Signal(str)
    playback_generating = Signal()
    playback_started = Signal()
    playback_finished = Signal()
    playback_paused = Signal()
    playback_resumed = Signal()
    engine_changed = Signal(str)  # engine_id

    def __init__(self, config_manager=None, thread_pool=None):
        super().__init__()
        if config_manager is None:
            self.config_manager = ConfigManager()
        else:
            self.config_manager = config_manager

        if thread_pool is None:
            self.thread_pool = QThreadPool.globalInstance()
        else:
            self.thread_pool = thread_pool

        self.voices = []
        self.output_folder = Path("output")
        self.output_folder.mkdir(exist_ok=True)

        self.is_playing = False
        self.current_audio_path = None
        self.all_voices = []
        self.is_loading_voices = False
        self.current_engine = TTS_ENGINE_EDGE  # 默认引擎

        self.player = AudioPlayer()
        self.backup_player = SystemAudioPlayer()
        
        if not self.player.is_available():
            logging.warning("Miniaudio not available, using SystemAudioPlayer")
            self.player = self.backup_player
            
        self.player.playback_started.connect(self.playback_started)
        self.player.playback_finished.connect(self.playback_finished)
        self.backup_player.playback_started.connect(self.playback_started)
        self.backup_player.playback_finished.connect(self.playback_finished)

        self.load_voices()
    
    def supports_pause(self):
        return self.player.supports_pause()

    def pause_playback(self):
        if not self.supports_pause():
            return False
        if self.player.pause():
            self.playback_paused.emit()
            return True
        return False
        
    def resume_playback(self):
        if not self.supports_pause():
            return False
        if self.player.resume():
            self.playback_resumed.emit()
            return True
        return False

    def set_engine(self, engine):
        """设置当前TTS引擎"""
        self.current_engine = engine
        self.engine_changed.emit(engine)

    @Slot(list)
    def _on_voices_loaded(self, loaded_voices):
        self.is_loading_voices = False
        if loaded_voices:
            self.voices = loaded_voices
            logging.info(f"Successfully processed {len(loaded_voices)} voices.")
            self.voices_loaded.emit(loaded_voices)
        else:
            logging.warning("Voice loading failed or returned empty list. Using fallback voices.")
            self.use_fallback_voices()

    def play_audio(self, text, voice_name=None):
        """Generates (if needed) and plays audio for the given text."""
        if not text: 
            return

        import re
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        target_locale = 'zh-CN' if has_chinese else 'en-US'
        
        if not voice_name:
            if self.voices:
                voice = next((v for v in self.voices if target_locale in v.get('Locale', '')), None)
                if not voice and target_locale == 'en-US':
                    voice = self.voices[0]
                elif not voice:
                    voice = self.voices[0]
                voice_name = voice.get('ShortName', voice.get('Name'))
            else:
                voice_name = "zh-CN-XiaoxiaoNeural" if has_chinese else "en-US-JennyNeural"
        else:
            found_voice = next((v for v in self.voices if v.get('Name') == voice_name or v.get('ShortName') == voice_name), None)
            if found_voice:
                voice_name = found_voice.get('ShortName', voice_name)

        import hashlib
        text_hash = hashlib.md5(f"{text}-{voice_name}".encode('utf-8')).hexdigest()
        filename = f"speak_{text_hash}.mp3" 
        output_path = os.path.join(tempfile.gettempdir(), filename)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logging.info(f"Playing cached audio: {output_path}")
            self._play_with_fallback(output_path)
            return

        logging.info(f"Generating new audio for playback: {output_path}")
        self.playback_generating.emit()
        
        worker = TtsGenerateWorker(text, voice_name, output_path, self.config_manager)

        def on_complete(path, success):
            if success:
                self._play_with_fallback(path)
            else:
                self.tts_error.emit("Failed to generate audio for playback.")

        worker.signals.finished.connect(on_complete)
        self.thread_pool.start(worker)

    def _play_with_fallback(self, file_path):
        """Play audio file with fallback to backup player on error."""
        self._current_play_path = file_path
        
        if getattr(self, '_error_handler_connected', False):
            try:
                self.player.playback_error.disconnect(self._on_primary_player_error)
                self._error_handler_connected = False
            except RuntimeError:
                pass
        
        self.player.playback_error.connect(self._on_primary_player_error)
        self._error_handler_connected = True
        self.player.play_file(file_path)
    
    def _on_primary_player_error(self, error_msg):
        """Handle primary player error by trying backup player."""
        logging.warning(f"Primary player failed: {error_msg}, trying backup player...")
        path = getattr(self, '_current_play_path', None)
        if path and self.backup_player != self.player:
            self.backup_player.play_file(path)
        else:
            self.tts_error.emit(f"All players failed: {error_msg}")

    def use_fallback_voices(self):
        """使用备用语音列表"""
        fallback_voices = [
            {"Name": "zh-CN-XiaoxiaoNeural", "ShortName": "zh-CN-XiaoxiaoNeural", "Gender": "Female", "Locale": "zh-CN"},
            {"Name": "zh-CN-YunxiNeural", "ShortName": "zh-CN-YunxiNeural", "Gender": "Male", "Locale": "zh-CN"},
            {"Name": "zh-CN-YunyangNeural", "ShortName": "zh-CN-YunyangNeural", "Gender": "Male", "Locale": "zh-CN"},
            {"Name": "zh-CN-XiaochenNeural", "ShortName": "zh-CN-XiaochenNeural", "Gender": "Female", "Locale": "zh-CN"},
            {"Name": "en-US-JennyNeural", "ShortName": "en-US-JennyNeural", "Gender": "Female", "Locale": "en-US"},
            {"Name": "en-US-GuyNeural", "ShortName": "en-US-GuyNeural", "Gender": "Male", "Locale": "en-US"},
            {"Name": "en-US-AriaNeural", "ShortName": "en-US-AriaNeural", "Gender": "Female", "Locale": "en-US"},
            {"Name": "en-US-DavisNeural", "ShortName": "en-US-DavisNeural", "Gender": "Male", "Locale": "en-US"}
        ]
        self.voices = fallback_voices
        self.voices_loaded.emit(fallback_voices)
        logging.info(f"Using {len(fallback_voices)} fallback voices")
    
    async def load_voices_async(self):
        """异步加载可用的语音列表"""
        try:
            proxy = self.config_manager.get("tts_settings.proxy", None)
            if proxy:
                logging.info(f"Using proxy: {proxy}")
                os.environ['HTTP_PROXY'] = proxy
                os.environ['HTTPS_PROXY'] = proxy

            voices = await edge_tts.list_voices(proxy=proxy)
            if voices:
                self.voices = voices
                self.voices_loaded.emit(voices)
                logging.info(f"Successfully loaded {len(voices)} voices")
            else:
                raise Exception("No voices loaded")
        except Exception as e:
            error_msg = f"Failed to load voices: {str(e)}"
            logging.error(error_msg)
            self.tts_error.emit(error_msg)
            self.use_fallback_voices()

    def load_voices(self):
        """Load all available voices"""
        if self.is_loading_voices:
            return

        self.is_loading_voices = True
        logging.info("Starting voice loading process...")
        try:
            worker = LoadVoicesRunnable(self)
            self.thread_pool.start(worker)
        except Exception as e:
            logging.error(f"Failed to start voice loading: {e}")
            self.is_loading_voices = False

    def generate_preview(self, text: str, voice_name: str):
        """Generates a preview audio using a background worker."""
        if not voice_name:
            logging.warning("generate_preview called with empty voice_name.")
            self.tts_error.emit("Please select a voice first.")
            return
        if not text or not text.strip():
            logging.warning("generate_preview called with empty text.")
            self.tts_error.emit("Please enter text for the preview.")
            return

        try:
            logging.info(f"Queueing preview generation for voice: {voice_name}, engine: {self.current_engine}")
            voice_name_cleaned = voice_name.split(" (")[0].strip()

            # Select appropriate worker based on current engine
            if self.current_engine == TTS_ENGINE_MINIMAX:
                worker = MiniMaxPreviewGenerateWorker(text, voice_name_cleaned, self.config_manager)
            elif self.current_engine == TTS_ENGINE_QWEN_FLASH:
                # Qwen Flash preview uses the same worker as full generation
                temp_dir = tempfile.gettempdir()
                preview_path = os.path.join(temp_dir, f"preview_qwen_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.mp3")
                target_model = self.config_manager.get("dashscope.tts_model", "qwen3-tts-flash-2025-11-27")
                worker = QwenTtsGenerateWorker(text, voice_name_cleaned, target_model, preview_path, self.config_manager)
                # Connect Qwen's (path, success) signal to preview's (path) signal
                def on_qwen_finished(path, success):
                    if success:
                        self.preview_ready.emit(path)
                worker.signals.finished.connect(on_qwen_finished)
                worker.signals.error.connect(self.tts_error)
                self.thread_pool.start(worker)
                return  # Early return since we already connected signals
            else:
                worker = PreviewGenerateWorker(self, text, voice_name_cleaned)

            worker.signals.finished.connect(self.preview_ready)
            worker.signals.error.connect(self.tts_error)

            self.thread_pool.start(worker)
        except Exception as e:
            logging.error(f"Failed to start preview generation worker: {e}")
            self.tts_error.emit(f"Failed to start preview task: {e}")

    async def generate_audio_async(self, text: str, voice_name: str, output_path: str = None) -> str:
        """异步生成语音文件"""
        try:
            if not output_path:
                output_path = os.path.normpath(os.path.join(self.output_folder, "test_audio.mp3"))
            else:
                output_path = os.path.normpath(output_path)

            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            logging.info(f"开始异步生成语音，文本: {text[:50]}..., 语音: {voice_name}, 输出路径: {output_path}")

            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(output_path)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logging.info(f"异步语音生成成功，文件路径: {output_path}")
                self.generation_complete.emit(output_path)
                return output_path
            else:
                raise Exception("生成的音频文件为空或不存在")

        except Exception as e:
            file_exists = os.path.exists(output_path) if output_path else False
            file_size = os.path.getsize(output_path) if file_exists else 0
            error_msg = f"Error generating audio: {e}. Path: '{output_path}'. Exists: {file_exists}. Size: {file_size} bytes."
            logging.error(error_msg, exc_info=True)
            self.generation_error.emit(error_msg)
            raise e

    def generate_audio(self, text: str, voice_name: str, output_path: str = None):
        """Starts background generation of audio (Non-blocking)."""
        if not text:
            self.generation_error.emit("Text cannot be empty.")
            return

        try:
            if not output_path:
                output_path = os.path.join(self.output_folder, f"tts_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3")

            logging.info(f"Queueing TTS generation: text='{text[:20]}...', voice={voice_name}, engine={self.current_engine}, path={output_path}")

            # Select appropriate worker based on current engine
            if self.current_engine == TTS_ENGINE_MINIMAX:
                worker = MiniMaxTtsGenerateWorker(text, voice_name, output_path, self.config_manager)
            elif self.current_engine == TTS_ENGINE_QWEN_FLASH:
                # Get target model from config or use default
                target_model = self.config_manager.get("dashscope.tts_model", "qwen3-tts-flash-2025-11-27")
                worker = QwenTtsGenerateWorker(text, voice_name, target_model, output_path, self.config_manager)
            else:
                # Default to Edge TTS
                worker = TtsGenerateWorker(text, voice_name, output_path, self.config_manager)

            def on_worker_finished(path, success):
                if success:
                    self.generation_complete.emit(path)
                else:
                    self.generation_error.emit(f"Generation failed for {path}")

            worker.signals.finished.connect(on_worker_finished)
            worker.signals.error.connect(self.generation_error)

            self.thread_pool.start(worker)

        except Exception as e:
            logging.error(f"Error starting generate_audio worker: {e}", exc_info=True)
            self.generation_error.emit(str(e))

    def generate_dialog(self, dialog_lines, role_a_voice, role_b_voice, output_path=None):
        """Starts background generation of dialog audio (Non-blocking)."""
        if not dialog_lines:
            self.generation_error.emit("Dialog script cannot be empty.")
            return

        try:
            if not output_path:
                output_path = os.path.join(self.output_folder, f"dialog_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3")

            logging.info(f"Queueing Dialog TTS generation: {len(dialog_lines)} lines, path={output_path}")

            worker = DialogTtsGenerateWorker(dialog_lines, role_a_voice, role_b_voice, output_path, self.config_manager)
            
            def on_dialog_finished(path, success):
                if success:
                    self.generation_complete.emit(path)
                else:
                    self.generation_error.emit(f"Dialog generation failed for {path}")

            worker.signals.finished.connect(on_dialog_finished)
            worker.signals.error.connect(self.generation_error)

            self.thread_pool.start(worker)

        except Exception as e:
            logging.error(f"Error starting generate_dialog worker: {e}", exc_info=True)
            self.generation_error.emit(str(e))

    LANGUAGE_CODES = {
        "中文": ["zh", "zh-CN", "zh-TW"],
        "英语": ["en", "en-US", "en-GB", "en-AU"],
        "日语": ["ja", "ja-JP"],
        "韩语": ["ko", "ko-KR"],
        "法语": ["fr", "fr-FR"],
        "德语": ["de", "de-DE"],
        "西班牙语": ["es", "es-ES"],
        "意大利语": ["it", "it-IT"],
        "俄语": ["ru", "ru-RU"],
        "葡萄牙语": ["pt", "pt-BR", "pt-PT"]
    }

    def filter_voices_by_language(self, language_name):
        """按语言筛选语音"""
        if not self.voices:
            logging.warning(f"No voices available when filtering for {language_name}")
            return []

        language_codes = self.LANGUAGE_CODES.get(language_name, [])
        if not language_codes:
            logging.warning(f"No language codes defined for {language_name}")
            return []

        logging.info(f"Voice list before filtering: {len(self.voices)}")

        filtered_voices = [
            voice for voice in self.voices
            if any(code.lower() in voice.get("Locale", "").lower() for code in language_codes)
        ]

        logging.info(f"Found {len(filtered_voices)} voices for {language_name}")
        return filtered_voices

    def set_qwen_voices(self, voices, voice_type):
        """设置 Qwen 语音列表"""
        # 存储 Qwen 语音用于 Voice Design 或 Voice Clone
        if voice_type == "voice_design":
            self.qwen_voices_design = voices
        elif voice_type == "voice_clone":
            self.qwen_voices_clone = voices
        
        # 合并到 voices 列表用于语音选择
        # 注意：Qwen 语音格式与 Edge 不同，需要转换
        for voice in voices:
            # 转换为标准格式
            self.voices.append({
                "Name": voice.get("voice", ""),
                "ShortName": voice.get("voice", ""),
                "Gender": "Unknown",
                "Locale": "zh-CN",
                "Type": voice_type
            })
        
        self.voices_loaded.emit(self.voices)

    def set_minimax_voices(self):
        """设置 MiniMax 语音列表"""
        # 使用预定义的 MiniMax 音色列表
        self.voices = MINIMAX_TTS_VOICES.copy()
        self.voices_loaded.emit(self.voices)
        logging.info(f"Loaded {len(self.voices)} MiniMax voices")

    def get_available_engines(self):
        """返回可用的TTS引擎列表"""
        engines = [
            {"id": TTS_ENGINE_EDGE, "name": "Edge TTS", "available": True},
            {"id": TTS_ENGINE_QWEN_VD, "name": "Qwen TTS (Voice Design)", "available": True},
            {"id": TTS_ENGINE_QWEN_VC, "name": "Qwen TTS (Voice Clone)", "available": True},
            {"id": TTS_ENGINE_QWEN_FLASH, "name": "Qwen TTS Flash", "available": True},
        ]
        if genai is not None:
            engines.append({"id": TTS_ENGINE_GEMINI, "name": "Gemini TTS", "available": True})
        if httpx is not None:
            engines.append({"id": TTS_ENGINE_MINIMAX, "name": "MiniMax TTS", "available": True})
        return engines
