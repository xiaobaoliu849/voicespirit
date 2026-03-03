"""
Audio Overview - 播客式双人对话音频生成模块

该模块提供将话题转换为播客式双人对话音频的功能。
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from PySide6.QtCore import QObject, Signal, QThreadPool, Qt
import logging
import re


# ============== Prompt Templates ==============

PROMPT_TEMPLATE_ZH = """你是一个播客脚本编写专家。请根据以下话题生成一段双人对话脚本。

话题：{topic}

要求：
1. 对话包含两个角色：A（主持人）和 B（嘉宾专家）
2. 生成 {turn_count} 轮对话（每轮包含 A 和 B 各说一段）
3. 对话自然流畅，像真实的播客节目
4. A 负责引导话题、提问；B 负责解答、分享见解
5. 包含开场白和结束语
6. 每句话控制在 50-150 字之间，适合语音朗读

输出格式（严格遵循，每行一句）：
A: [主持人的话]
B: [嘉宾的话]
A: [主持人的话]
B: [嘉宾的话]
...

请直接输出对话内容，不要添加其他说明。"""

PROMPT_TEMPLATE_EN = """You are a podcast script writing expert. Please generate a two-person dialogue script based on the following topic.

Topic: {topic}

IMPORTANT: You MUST write ALL dialogue content in English, even if the topic is in another language. Translate the topic if needed.

Requirements:
1. The dialogue includes two roles: A (Host) and B (Guest Expert)
2. Generate {turn_count} rounds of dialogue (each round includes one statement from A and one from B)
3. The dialogue should be natural and fluent, like a real podcast
4. A is responsible for guiding the topic and asking questions; B is responsible for answering and sharing insights
5. Include an opening and closing
6. Keep each statement between 30-100 words, suitable for voice reading
7. ALL content MUST be in English

Output format (strictly follow, one statement per line):
A: [Host's statement in English]
B: [Guest's statement in English]
A: [Host's statement in English]
B: [Guest's statement in English]
...

Please output the dialogue content directly in English without any additional explanation."""

PROMPT_TEMPLATE_LONG_TOPIC_ZH = """你是一个播客脚本编写专家。以下是一个较长的话题，请先理解其核心要点，然后生成一段双人对话脚本。

话题内容：
{topic}

要求：
1. 对话包含两个角色：A（主持人）和 B（嘉宾专家）
2. 生成 {turn_count} 轮对话
3. 对话结构：开场介绍 -> 核心要点讨论 -> 总结展望
4. A 负责引导话题、提问；B 负责解答、分享见解
5. 每句话控制在 50-150 字之间

输出格式：
A: [主持人的话]
B: [嘉宾的话]
...

请直接输出对话内容。"""


def get_prompt_template(language: str, is_long_topic: bool = False) -> str:
    """获取对应语言的 prompt 模板
    
    Args:
        language: 语言 ("zh" 或 "en")
        is_long_topic: 是否为长话题 (>500字符)
        
    Returns:
        str: prompt 模板
    """
    if language == "zh":
        return PROMPT_TEMPLATE_LONG_TOPIC_ZH if is_long_topic else PROMPT_TEMPLATE_ZH
    else:
        return PROMPT_TEMPLATE_EN


def parse_script_from_text(text: str) -> List["DialogLine"]:
    """从 LLM 响应文本解析对话脚本
    
    支持的格式：
    - "A: 内容" 或 "A：内容"
    - "B: 内容" 或 "B：内容"
    
    Args:
        text: LLM 响应文本
        
    Returns:
        List[DialogLine]: 解析后的对话列表
    """
    lines = []
    # 匹配 A: 或 B: 开头的行（支持中英文冒号）
    pattern = r'^([AB])[：:]\s*(.+)$'
    
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        match = re.match(pattern, line)
        if match:
            role = match.group(1)
            content = match.group(2).strip()
            if content:  # 确保内容非空
                lines.append(DialogLine(role=role, text=content))
    
    return lines


def validate_topic(topic: str) -> Tuple[bool, str]:
    """验证话题输入
    
    Args:
        topic: 话题文本
        
    Returns:
        Tuple[bool, str]: (是否有效, 错误信息或空字符串)
    """
    if not topic:
        return False, "话题不能为空"
    
    if not topic.strip():
        return False, "话题不能只包含空白字符"
    
    return True, ""


@dataclass
class DialogLine:
    """对话行数据类"""
    role: str  # "A" (主持人) 或 "B" (嘉宾)
    text: str  # 对话内容
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {"role": self.role, "text": self.text}
    
    @classmethod
    def from_dict(cls, data: dict) -> "DialogLine":
        """从字典创建实例"""
        return cls(role=data.get("role", "A"), text=data.get("text", ""))
    
    def is_valid(self) -> bool:
        """验证对话行是否有效"""
        return self.role in ("A", "B") and bool(self.text.strip())


@dataclass
class AudioOverviewConfig:
    """音频概览配置"""
    language: str = "zh"           # "zh" 中文 或 "en" 英文
    voice_a: str = ""              # 角色A的声音
    voice_b: str = ""              # 角色B的声音
    turn_count: int = 10           # 对话轮数 (每轮包含A和B各一句)
    
    # 默认声音配置
    DEFAULT_VOICES = {
        "zh": ("zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural"),      # 男声, 女声
        "en": ("en-US-GuyNeural", "en-US-JennyNeural"),           # 男声, 女声
    }
    
    def get_default_voices(self) -> Tuple[str, str]:
        """获取当前语言的默认声音对
        
        Returns:
            Tuple[str, str]: (角色A声音, 角色B声音)
        """
        return self.DEFAULT_VOICES.get(self.language, self.DEFAULT_VOICES["zh"])
    
    def get_voice_a(self) -> str:
        """获取角色A的声音，如果未设置则返回默认值"""
        if self.voice_a:
            return self.voice_a
        return self.get_default_voices()[0]
    
    def get_voice_b(self) -> str:
        """获取角色B的声音，如果未设置则返回默认值"""
        if self.voice_b:
            return self.voice_b
        return self.get_default_voices()[1]
    
    def validate_voice_locale(self, voice_name: str) -> bool:
        """验证声音是否匹配当前语言
        
        Args:
            voice_name: 声音名称
            
        Returns:
            bool: 是否匹配
        """
        locale_prefix = "zh-CN" if self.language == "zh" else "en-US"
        return voice_name.startswith(locale_prefix)


class AudioOverviewController(QObject):
    """音频概览控制器
    
    协调脚本生成和音频合成的核心控制器。
    """
    
    # 信号定义
    script_generated = Signal(list)      # 脚本生成完成，参数为 List[DialogLine]
    synthesis_progress = Signal(int)     # 合成进度 (0-100)
    synthesis_complete = Signal(str)     # 合成完成，参数为输出文件路径
    error_occurred = Signal(str)         # 发生错误，参数为错误信息
    
    def __init__(self, api_client=None, tts_handler=None, config_manager=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.tts_handler = tts_handler
        self.config_manager = config_manager
        self.thread_pool = QThreadPool.globalInstance()
        
        self.config = AudioOverviewConfig()
        self.current_script: List[DialogLine] = []
        self._is_generating = False
        self._is_synthesizing = False
        self._active_workers = []
    
    def set_config(self, config: AudioOverviewConfig) -> None:
        """设置配置"""
        self.config = config
    
    def generate_script(self, topic: str, language: str = "zh", provider: str = None, model: str = None) -> None:
        """异步生成对话脚本
        
        Args:
            topic: 话题内容
            language: 语言 ("zh" 或 "en")
            provider: AI 提供商 (如 "deepseek", "dashscope" 等)
            model: 模型名称
        """
        # 验证话题
        is_valid, error_msg = validate_topic(topic)
        if not is_valid:
            self.error_occurred.emit(error_msg)
            return
        
        self.config.language = language
        self._is_generating = True
        self._accumulated_response = ""
        
        # 判断是否为长话题
        is_long_topic = len(topic) > 500
        
        # 获取 prompt 模板并填充
        template = get_prompt_template(language, is_long_topic)
        prompt = template.format(topic=topic, turn_count=self.config.turn_count)
        
        logging.info(f"开始生成脚本: topic={topic[:50]}..., language={language}, provider={provider}, model={model}")
        
        # 连接 ApiClient 信号
        if self.api_client:
            # 使用 UniqueConnection 避免重复连接，无需手动断开
            self.api_client.chat_stream_chunk.connect(self._on_script_chunk, Qt.UniqueConnection)
            self.api_client.chat_stream_finished.connect(self._on_script_finished, Qt.UniqueConnection)
            self.api_client.chat_response_error.connect(self._on_script_error, Qt.UniqueConnection)
            
            # 使用传入的 provider 和 model，如果没有则使用配置中的默认值
            if not provider:
                provider = self.config_manager.get("audio_overview.provider", "deepseek") if self.config_manager else "deepseek"
            if not model:
                model = self.config_manager.get("audio_overview.model", "deepseek-chat") if self.config_manager else "deepseek-chat"
            
            logging.info(f"使用 provider={provider}, model={model} 生成脚本")
            
            # 发起请求
            self.api_client.start_chat_request_async(provider, model, prompt)
        else:
            self.error_occurred.emit("API 客户端未初始化")
            self._is_generating = False
    
    def _on_script_chunk(self, chunk: str) -> None:
        """处理脚本生成的流式响应"""
        if self._is_generating:
            self._accumulated_response += chunk
    
    def _on_script_finished(self) -> None:
        """脚本生成完成"""
        if not self._is_generating:
            return
        
        self._is_generating = False
        
        # 解析脚本
        dialog_lines = parse_script_from_text(self._accumulated_response)
        
        if not dialog_lines:
            self.error_occurred.emit("无法解析生成的脚本，请重试")
            return
        
        self.current_script = dialog_lines
        self.script_generated.emit([line.to_dict() for line in dialog_lines])
        logging.info(f"脚本生成完成: {len(dialog_lines)} 行对话")
    
    def _on_script_error(self, error_msg: str) -> None:
        """脚本生成错误"""
        if not self._is_generating:
            return
        
        self._is_generating = False
        self.error_occurred.emit(f"脚本生成失败: {error_msg}")
    
    def synthesize_audio(self, dialog_lines: List[DialogLine], output_path: str, tts_engine: str = "edge") -> None:
        """异步合成音频
        
        Args:
            dialog_lines: 对话脚本
            output_path: 输出文件路径
            tts_engine: TTS 引擎 ("edge" 或 "gemini")
        """
        # 验证对话数量
        if len(dialog_lines) < 2:
            self.error_occurred.emit("对话至少需要2行")
            return
        
        # 验证每行对话
        for i, line in enumerate(dialog_lines):
            if not line.is_valid():
                self.error_occurred.emit(f"第 {i+1} 行对话无效")
                return
        
        self._is_synthesizing = True
        self.current_script = dialog_lines
        
        # 获取声音配置
        voice_a = self.config.get_voice_a()
        voice_b = self.config.get_voice_b()
        
        logging.info(f"开始合成音频 ({tts_engine}): {len(dialog_lines)} 行对话 -> {output_path}")
        logging.info(f"声音配置: A={voice_a}, B={voice_b}")
        
        # 转换为 DialogTtsGenerateWorker 需要的格式
        lines_for_worker = [line.to_dict() for line in dialog_lines]
        
        from utils.tts_handler import DialogTtsGenerateWorker, GeminiDialogTtsWorker, TTS_ENGINE_GEMINI
        
        if tts_engine == TTS_ENGINE_GEMINI:
            # Use Gemini worker
            worker = GeminiDialogTtsWorker(
                dialog_lines=lines_for_worker,
                role_a_voice=voice_a,
                role_b_voice=voice_b,
                output_path=output_path,
                config_manager=self.config_manager
            )
        else:
            # Use Edge-TTS worker
            worker = DialogTtsGenerateWorker(
                dialog_lines=lines_for_worker,
                role_a_voice=voice_a,
                role_b_voice=voice_b,
                output_path=output_path,
                config_manager=self.config_manager
            )
        
        # Keep reference to worker to prevent GC
        self._active_workers.append(worker)

        # Cleanup callbacks
        def on_finished(path, success, w=worker):
            self._on_synthesis_finished(path, success)
            if w in self._active_workers:
                self._active_workers.remove(w)

        def on_error(msg, w=worker):
            self._on_synthesis_error(msg)
            if w in self._active_workers:
                self._active_workers.remove(w)
        
        # 连接信号
        worker.signals.progress.connect(self._on_synthesis_progress, Qt.QueuedConnection)
        worker.signals.finished.connect(on_finished, Qt.QueuedConnection)
        worker.signals.error.connect(on_error, Qt.QueuedConnection)
        
        # 启动任务
        self.thread_pool.start(worker)
    
    def _on_synthesis_progress(self, progress: int) -> None:
        """合成进度更新"""
        self.synthesis_progress.emit(progress)
    
    def _on_synthesis_finished(self, file_path: str, success: bool) -> None:
        """合成完成"""
        self._is_synthesizing = False
        if success:
            self.synthesis_complete.emit(file_path)
            logging.info(f"音频合成完成: {file_path}")
        else:
            self.error_occurred.emit("音频合成失败")
    
    def _on_synthesis_error(self, error_msg: str) -> None:
        """合成错误"""
        self._is_synthesizing = False
        self.error_occurred.emit(f"音频合成失败: {error_msg}")
    
    def cancel(self) -> None:
        """取消当前操作"""
        self._is_generating = False
        self._is_synthesizing = False
        logging.info("操作已取消")
    
    @property
    def is_busy(self) -> bool:
        """是否正在执行操作"""
        return self._is_generating or self._is_synthesizing
