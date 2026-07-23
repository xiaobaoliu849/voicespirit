# Qwen 实时翻译模型 (LiveTranslate) 接入方案

## 目标
接入阿里云 DashScope 的实时语音翻译模型 `qwen3.5-livetranslate-flash-realtime`
（2026-05 最新版，60 语种，2.8s 延迟），对标现有 Google
`gemini-3.5-live-translate-preview` 的实时同传能力。

## 调研结论（官方文档已核实）
- **模型 ID**：`qwen3.5-livetranslate-flash-realtime`（最新，settings.py:168 已列名）。
  旧版 `qwen3-livetranslate-flash-realtime` 仍可用。
- **协议**：DashScope Realtime WebSocket（与 Qwen-Omni 同族），但翻译模型有差异：
  - 无 instructions / tools / turn_detection 对话参数
  - `session.update` 用 `session.translation.language`（目标语种）、
    `session.input_audio_transcription.language`（源语种）、`session.translation.corpus.phrases`（热词）
  - 服务端事件：译文 `response.audio_transcript.text`(`text`+`stash`) /
    `response.audio_transcript.done`(`transcript`)；纯文本 `response.text.text`/`response.text.done`；
    源文 `conversation.item.input_audio_transcription.text/completed`；音频 `response.audio.delta`
  - 结束须发 `session.finish`
  - 输入 PCM16/16kHz，输出 PCM16/24kHz
- **endpoint**：`wss://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime?model=...`
  （现有 `_resolve_dashscope_settings` 的 wss URL 校验已兼容）
- **认证**：WebSocket header `Authorization: Bearer <key>`

## 现状
- DashScope 实时 WS 地基已就绪（`realtime_dashscope_client.py` 裸 WS + `DashScopeRealtimeCallback`）。
- Google live-translate 已完整实现（`realtime_google_provider.py`），作为模板。
- 前端 `isLiveTranslateModel` 只认 Google；WS URL 已会在 live-translate 时透传
  `translation_mode/source_language_code/target_language_code/echo_target_language`。
- 断点：`voice_chat.py` DashScope 分支丢弃了这 4 个翻译参数；`_resolve_dashscope_settings`
  会因 livetranslate 不支持 native tools 而拒绝；callback 不识别翻译事件。

## 改动清单

### 后端
1. `realtime_constants.py`
   - 新增 `_is_dashscope_live_translate_model(model)`（正则匹配 `qwen3(.5)?-livetranslate-*-realtime`）
   - 新增 `DEFAULT_DASHSCOPE_LIVETRANSLATE_VOICE = "Tina"`
   - 新增 `normalize_qwen_translate_language(code)`：`zh-Hans`→`zh`、`pt-BR`→`pt` 等
2. `realtime_dashscope_client.py`
   - callback `on_event` 增加翻译事件映射（`response.audio_transcript.text/done`、
     `response.text.text/done`、`conversation.item.input_audio_transcription.text`）
   - 新增 `DashScopeLiveTranslateConversation`（继承裸 WS 类）：翻译专用
     `update_session(...)` + `finish_session()`
3. `realtime_dashscope_provider.py`
   - `_configure_dashscope_live_translate(...)`：构造翻译 session
   - `stream_dashscope_session(...)` 增加 translation 参数；检测 livetranslate →
     用 `DashScopeLiveTranslateConversation`，`is_live_translate=True`
   - `_client_to_dashscope_loop` / `_dashscope_to_client_loop` 增加 `is_live_translate`
     分支：跳过 tools/memory/interruption，cumulative 译文用 `_merge_streaming_text`
     增量下发，inactivity monitor 触发 turn_complete，结束发 `session.finish`
4. `realtime_voice_service.py`
   - `_resolve_dashscope_settings`：livetranslate 模型豁免 native-tools 校验
5. `routers/voice_chat.py`
   - DashScope 分支透传 translation_mode/source/target/echo 参数
6. `routers/settings.py`
   - 去掉 :168 "future: not yet integrated" 注释（模型名已列）

### 前端
7. `useVoiceChatHelpers.ts`
   - `isLiveTranslateModel`：识别 DashScope + `livetranslate`（无连字符）

### 测试
8. 后端 `tests/test_realtime_livetranslate.py`（新建）：
   - 模型检测、语言归一化、callback 翻译事件映射、session.update 构造、
     settings 豁免 native-tools、voice_chat 参数透传
9. 前端：`useVoiceChatHelpers` / `VoiceCallSettingsPopover` 既有测试补充 DashScope 用例

## 测试约束
用户当前无 DashScope 额度，无法联调真实 API。所有后端测试采用 mock（patch callback 事件 /
conversation 方法），符合现有 `test_realtime_tool_protocol.py`、`test_realtime_voice_memory.py` 模式。
