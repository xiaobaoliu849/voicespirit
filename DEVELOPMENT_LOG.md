# Voice Spirit 开发日志

## 项目概述
Voice Spirit 2.0 是一个基于PySide6的语音合成和AI助手桌面应用程序，支持多种TTS引擎（Edge, Google, Qwen等）和AI模型API。

## 2026-01-11 UI/UX 重构与功能完成

### 核心变更：UI/UX Overhaul (Dark Glass Theme)
为了提升用户体验，我们对Voice Design（音色设计）和Voice Clone（音色克隆）界面进行了全面的视觉升级和代码重构。

#### 1. 新增设计系统组件 (`app/ui/components/`)
- **`glass_panel.py`**:
  - `GlassPanel`: 基础容器，实现半透明磨砂玻璃效果。
  - `GlassCard`: 交互式卡片组件，支持悬停光效和点击状态。
- **`voice_card.py`**:
  - `VoiceCardV2`: 全新的音色展示卡片。
  - 特性：性别区分头像（青色/粉色霓虹光效）、悬停播放按钮、删除功能、选中高亮。
- **`audio_drop_zone.py`**:
  - `AudioDropZoneV2`: 现代化的音频拖放区域。
  - 特性：虚线霓虹边框、拖入动画反馈、支持文件选择。
- **`style_preset_card.py`**:
  - `StylePresetCard`: 快速风格预设选择器（如"Young Female", "Narrator"等）。
- **`waveform_widget.py`**:
  - `WaveformWidget`: 升级版音频波形可视化，支持物理平滑动画和播放/静止状态切换。

#### 2. 页面模块化重构 (`app/ui/pages/`)
我们将原 `TtsPage` 中的内联类重构为独立的模块化页面文件，提高了代码的可维护性。

- **`voice_design_page.py` (VoiceDesignWidget)**:
  - **功能**: 自定义音色生成。
  - **界面**:
    - 顶部：水平滚动的 "Quick Presets"（快速预设）。
    - 中部："Creation Studio"（创作工坊），包含提示词输入、预览文本、名称输入（玻璃态面板）。
    - 底部："My Voices" 网格展示。
  - **逻辑**: 集成 `api_client.create_voice_design_async`，支持实时预览和列表刷新。

- **`voice_clone_page.py` (VoiceCloneWidget)**:
  - **功能**: 音色克隆。
  - **界面**:
    - 顶部："Clone Laboratory"（克隆实验室），包含 `AudioDropZoneV2`、样本预览播放器。
    - 底部："Cloned Specimens" 网格展示。
  - **逻辑**: 集成 `api_client.create_voice_clone_async`，支持音频上传和克隆。

#### 3. 主页面更新 (`app/ui/pages/tts_page.py`)
- 移除了旧的 `VoiceDesignWidget`, `VoiceCloneWidget`, `VoiceCard`, `AudioDropZone`, `PresetChip` 等内联类。
- 引入了新的模块化导入：
  ```python
  from app.ui.pages.voice_design_page import VoiceDesignWidget
  from app.ui.pages.voice_clone_page import VoiceCloneWidget
  ```
- 保持了 `SingleTtsWidget` 和 `DialogTtsWidget` 的功能稳定性。

### Qwen TTS 集成状态
- **Voice Design**: ✅ UI完成，✅ API对接完成。
- **Voice Clone**: ✅ UI完成，✅ API对接完成。
- **音频预览**: ✅ 支持生成并播放预览音频。

### 启动说明
推荐使用 Conda 环境启动：
```bash
conda activate whisperx
python main_new.py
```
或使用绝对路径（如用户环境）：
```bash
d:\conda\envs\whisperx\python.exe main_new.py
```

### 待办事项 / 下一步
- [ ] 在 `AudioOverviewPage` 中集成新的 `WaveformWidget`。
- [ ] 全面测试深色模式下的所有组件显示效果。
- [ ] 优化音频生成的缓存机制。

---
*版本: 2.1 (UI Overhaul)*
*最后更新: 2026-01-11*
