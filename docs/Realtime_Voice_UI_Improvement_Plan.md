# 实时语音聊天 UI 审查与改进方案

日期：2026-07-17
范围：ChatPage 实时语音通话的模型/音色选择呈现，以及主界面整体复杂度。
证据基于提交 `1eb10c4`（实时通话面板重做）之后的代码。

## 一、问题审查（证据）

### 问题 1：通话中模型/音色选择器完全消失

- `frontend/src/styles.css:7230-7232`：`.vsComposer.liveActive .vsComposerToolbar { display: none !important; }`——通话一开始，整条工具栏（模型、音色、语言、回声开关、按钮）被移除。
- 通话中唯一的型号提示是只读徽章 `.vsVoiceModelBadge`（`frontend/src/pages/ChatPage.tsx:339-341`），只显示 `provider / model`，**音色（voice）在通话中完全不显示**。
- 用户感知："一打电话，选择器的内容就被遮住了"。实际上是被 `display:none` 移除了。

### 问题 2：空闲状态下选择器文字被截断

- 音色选择框固定 `width: 126px`（`styles.css:1850-1853`），去掉左右 padding 只剩约 86px 可见文字。
- 模型选择框 `max-width: 210px`（`styles.css:1855-1858`）。
- `.vsComposerPillSelect` 统一 `overflow: hidden; text-overflow: ellipsis`（`styles.css:1816-1837`）。
- 而实际标签很长：音色如 `Katerina · 卡捷琳娜 · 女声`（`useVoiceChat.ts:212-233`），模型如 `DashScope / qwen3.5-omni-flash-realtime`（`useChat.ts:149`）。选中值常年显示为 `Katerina · 卡…`——"呈现不全"。

### 问题 3：实时翻译模型的整行被硬裁剪

- `.vsComposerToolbarLeft { flex-wrap: nowrap; overflow: hidden; }`（`styles.css:1773-1780`）。
- 桌面窗口默认 1200px（`run_web_desktop.py` 限制 ≤1200×800）：工具栏左区预算约 640px，而实时翻译模型的整行内容（附件 + 模型 210 + 音色 126 + 语言 220 + 回声开关 ≈ 712px）**超出约 70px，语言选择和回声开关被静默裁掉**。
- 换行兜底只在 `@media (max-width: 760px)`（`styles.css:1898-1917`），桌面壳最小宽度 920px，**永远不会触发**。

### 问题 4：主界面整体复杂度高

- 默认视图可见控件约 18–25 个：侧栏 8+（新建、4 个导航、历史条目 "⋯"、底部认证/设置）、输入区 6–9 个、4 个快捷操作。
- 设置入口双轨：SettingsModal（5 大类完整设置）与输入区内联的模型/音色选择职责重叠。
- 消息气泡上的 meta 标签（记忆已存/召回/来源/打断）+ 复制按钮进一步增加视觉噪声。

## 二、设计目标

1. 任何状态下，当前模型和音色都"可见、完整、可理解"。
2. 音色选择从 126px 的截断药丸升级为能展示完整信息的列表（中文名 + 性别 + 描述）。
3. 输入区控件做减法，主界面默认视图降噪。
4. 保持现有行为语义：音色只能在通话开始前选择（服务端第一次 session.update 之后不可改）。

## 三、方案选项

### 方案 A：快速修复（只做必要补救，约半天）

1. 通话中徽章扩展为 `provider / model · 音色名`（音色从 `voiceChatVoiceLabel` 取，纯展示）。
2. 去掉音色/模型选择框的固定像素宽度，改为 `min-width` + 内容自适应，上限放宽（如 320px）。
3. `.vsComposerToolbarLeft` 允许 `flex-wrap: wrap`，删掉永不触发的 760px 媒体查询，消除硬裁剪。

优点：改动小、风险低，立刻消除"被遮住"。
缺点：输入区复杂度没降；音色列表仍受原生 `<select>` 限制，无法展示音色描述。

### 方案 B：通话设置面板（推荐，约 1–2 天）

把模型/音色/语言三个药丸选择器收敛为一个"通话设置"入口：

- **空闲时**：输入区只留一个摘要按钮，如 `qwen3.5-omni-plus · Tina ▾`，点击弹出面板（popover/bottom-sheet）：
  - 模型列表：每个模型一行，带用途说明（实时对话 / 实时翻译 / qwen-audio 原生工具）。
  - 音色列表：按模型系列分组（qwen3.5-omni 的 Tina 系 / qwen-audio 的 longan 系），每条显示中文名、性别标签、风格描述（描述可从 `docs/全模态.txt` 音色表抄录）。后续可扩展试听按钮。
  - 语言与回声开关（仅实时翻译模型显示）。
- **通话中**：摘要按钮保留但变为只读展示 `模型 · 音色`（替代现在的纯模型徽章），点击不弹面板或弹出只读提示"通话中不可更改音色"。

优点：彻底解决截断和遮挡；输入区从 4–5 个控件减到 1 个；音色信息完整可扩展。
缺点：工作量中等，需要新增一个 Popover 组件和分组音色数据结构；要补前端测试。

### 方案 C：音色并入设置页（最省事但不推荐）

音色只在 SettingsModal 里选，输入区不再出现。通话更简洁，但每次想换音色要进设置，违背"通话前快速调整"的高频场景。

## 四、推荐路径

**方案 A 立即做**（三个小修复直接消除当前抱怨），**方案 B 作为第二步**（下周内跟进出面板组件）。方案 C 放弃。

配套降噪（与 A/B 正交，可一起做）：

- 快捷操作 4 个药丸合并进 "+" 菜单或历史欢迎页卡片，输入区默认只保留：输入框、附件、通话设置摘要、麦克风/发送。
- 气泡 meta 标签聚合为一行小字，默认只显示图标 + hover 展开。

## 五、实施清单（方案 A）

| 改动 | 文件 | 说明 |
| --- | --- | --- |
| 通话徽章加音色 | `frontend/src/pages/ChatPage.tsx:339-341` | `vsVoiceModelBadge` 文案改为 `{provider} / {model} · {voiceChatVoiceLabel}` |
| 解除固定宽度 | `styles.css:1850-1863` | `.vsComposerVoiceSelect` / `.vsComposerModelSelect` 改 `min-width` + `width: auto`，上限 320px |
| 允许换行 | `styles.css:1773-1780` | `.vsComposerToolbarLeft` 改 `flex-wrap: wrap`，移除 `overflow: hidden`；删除 `1898-1917` 的失效媒体查询 |
| 测试 | `useVoiceChat.test.ts` / ChatPage 相关测试 | 徽章包含音色名；工具栏换行不裁剪 |

## 六、实施清单（方案 B，后续）

1. `frontend/src/components/` 新增 `VoiceCallSettingsPopover.tsx`：模型分组列表 + 音色分组列表（带描述）+ 语言/回声。
2. `useVoiceChat.ts`：音色常量补充 `description` 字段（来源：官方音色列表的描述列）。
3. `ChatPage.tsx`：空闲时工具栏左区替换为摘要按钮；通话中徽章改为完整 `模型 · 音色`。
4. `styles.css`：新增 popover/sheet 样式，删除旧 pill 宽度规则。
5. 测试：popover 开合、按模型切换音色分组、通话中只读、i18n 双语文案。
