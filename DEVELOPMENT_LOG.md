# Voice Spirit 开发日志

## 项目概述
Voice Spirit 2.0 是一个基于PySide6的语音合成和AI助手桌面应用程序，支持多种TTS引擎（Edge, Google, Qwen等）和AI模型API。

## 2026-03-05 暂停记录（明日续做）

### 当前停点
- 已完成 Audio Overview 的脚本生成、音频合成、音频下载、前端联调。
- 已完成音频合并增强：`gap_ms` + `merge_strategy(auto|pydub|ffmpeg|concat)`，并支持自动回退。
- 已完成结构化错误返回：`code/message/meta`，前端已兼容解析。
- 后端单测与前端构建均通过：
  - `backend/.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v`
  - `frontend/npm run build`

### 明日建议起手
- 优先补“错误码文档 + 前端按错误码给出可执行修复提示（如 ffmpeg/pydub 缺失）”。
- 然后再做鉴权/权限控制与 OpenAPI 参数文档补全。

## 2026-03-05 续做记录（错误码文档 + 前端修复提示）

### 本次完成
- 新增 Audio Overview 错误码文档：
  - `backend/docs/audio_overview_error_codes.md`
  - 明确 `AUDIO_MERGE_*` / `AUDIO_SEGMENT_SYNTHESIS_FAILED` 的含义、`meta` 字段与修复建议。
- 前端 API 错误模型升级：
  - `frontend/src/api.ts` 新增 `ApiRequestError`，保留后端结构化错误 `code/message/meta`。
  - 各 API 请求失败统一抛 `ApiRequestError`，不再仅返回字符串错误。
- 前端 Audio Overview 错误修复提示：
  - `frontend/src/App.tsx` 新增错误码到“可执行建议”的映射逻辑。
  - 在 Audio Overview Tab 中，当合成失败时展示 `Suggested fixes`（如切换策略、安装 ffmpeg/pydub、检查 API Key/网络等）。
- 文档入口补充：
  - `WEB_PHASE_A_README.md` 增加错误码文档入口与前端提示能力说明。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（9/9）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（鉴权/权限控制 + OpenAPI 参数文档）

### 本次完成
- 新增后端可选 Bearer 鉴权：
  - 新增 `backend/services/auth_service.py`
  - 所有 `/api/*` 路由已统一接入鉴权依赖（`/` 与 `/health` 保持免鉴权）
  - token 来源支持：
    - 环境变量：`VOICESPIRIT_API_TOKEN`
    - 配置文件：`config.json -> auth_settings.api_token`
  - 鉴权失败返回结构化错误：
    - `AUTH_TOKEN_MISSING`（401）
    - `AUTH_TOKEN_INVALID`（403）
- Settings 模板扩展：
  - `backend/services/settings_service.py` 新增 `auth_settings` section，并允许通过 Settings API 更新。
- 前端联调兼容：
  - `frontend/src/api.ts` 新增 `VITE_API_TOKEN` 支持，自动附加 `Authorization: Bearer ...`。
- OpenAPI 参数文档增强：
  - `backend/routers/audio_overview.py` 为 `PodcastSynthesizeRequest` 增加字段说明。
  - 为 `POST /api/audio-overview/podcasts/{podcast_id}/synthesize` 增加 `400/403/404/503` 响应文档模型。
- 文档补充：
  - 新增 `backend/docs/authentication.md`
  - 更新 `WEB_PHASE_A_README.md`，补充 auth 启用方式和文档入口。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（10/10）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（鉴权细化 + OpenAPI 错误响应扩展）

### 本次完成
- 鉴权粒度调整为 write-only：
  - `backend/main.py` 改为中间件鉴权，仅拦截 `/api/*` 的 `POST/PUT/PATCH/DELETE`。
  - `GET` 类读取接口默认可匿名访问，便于本地联调。
  - root 信息新增 `auth_mode: "write-only"`。
- 鉴权服务增强：
  - `backend/services/auth_service.py` 新增 `should_enforce_auth()`、`validate_auth_header()`。
  - 统一 Bearer token 解析与结构化错误返回。
- 鉴权测试更新：
  - `backend/tests/test_api_smoke.py` 的 `test_auth_token_protection` 更新为：
    - 读接口免 token 可用
    - 写接口缺 token -> `AUTH_TOKEN_MISSING`（401）
    - 写接口错 token -> `AUTH_TOKEN_INVALID`（403）
- OpenAPI 错误响应补全：
  - `backend/routers/chat.py`
  - `backend/routers/translate.py`
  - `backend/routers/settings.py`
  - 新增结构化错误模型并在 `responses` 中声明；同时将对应异常返回统一为 `code/message/meta`。
- 文档同步：
  - `backend/docs/authentication.md` 补充 write-only 规则。
  - `WEB_PHASE_A_README.md` 补充当前鉴权范围说明。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（10/10）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（管理员权限策略 + 前端 admin token）

### 本次完成
- 权限策略再细化（route-level）：
  - 在 write-only 鉴权基础上，新增管理员权限规则：
    - 当配置了 admin token 时，`PUT /api/settings/` 必须使用 admin token。
  - 相关实现：
    - `backend/services/auth_service.py`
    - `backend/main.py`
  - root 信息更新：`auth_mode = write-only-with-admin-settings`
- 配置模板扩展：
  - `backend/services/settings_service.py` 的 `auth_settings` 增加 `admin_token`。
- 测试补充：
  - `backend/tests/test_api_smoke.py` 新增 `test_settings_admin_token_protection`：
    - 缺 admin token -> 401 `AUTH_ADMIN_TOKEN_MISSING`
    - 非 admin token -> 403 `AUTH_ADMIN_TOKEN_INVALID`
    - admin token -> 200
- 前端支持 admin token：
  - `frontend/src/api.ts` 新增 `VITE_API_ADMIN_TOKEN`
  - `updateSettings()` 优先使用 admin token 发起请求。
- OpenAPI & 文档补充：
  - 为 `chat/translate/audio_overview synthesize/settings update` 增加 `401/403` 鉴权响应说明。
  - 更新 `backend/docs/authentication.md` 与 `WEB_PHASE_A_README.md`，补充 admin token 用法。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（11/11）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（TTS/Voices 错误结构统一）

### 本次完成
- 继续统一接口错误格式为 `code/message/meta` 并补 OpenAPI 响应：
  - `backend/routers/voices.py`
    - `design/clone/list/delete` 全部补齐结构化错误返回。
    - 写接口（POST/DELETE）补 `401/403` 鉴权响应文档。
  - `backend/routers/tts.py`
    - `voices/speak` 异常改为结构化错误。
    - 补充 `400/500`（voices）与 `400/503/500`（speak）响应文档。
- 鉴权文档与说明继续完善：
  - `backend/docs/authentication.md`
  - `WEB_PHASE_A_README.md`
  - 明确 `admin token` 与 `VITE_API_ADMIN_TOKEN` 的行为。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（11/11）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（Audio Overview CRUD OpenAPI 补齐）

### 本次完成
- `backend/routers/audio_overview.py` 继续统一：
  - 新增 router 层结构化错误辅助函数，统一 `code/message/meta`。
  - 为以下接口补齐 OpenAPI 错误响应定义：
    - `GET /podcasts`
    - `GET /podcasts/latest`
    - `GET /podcasts/{podcast_id}`
    - `GET /podcasts/{podcast_id}/audio`
    - `POST /podcasts`
    - `PUT /podcasts/{podcast_id}`
    - `PUT /podcasts/{podcast_id}/script`
    - `POST /scripts/generate`
    - `POST /podcasts/{podcast_id}/synthesize`（补 500 + 404 model）
    - `DELETE /podcasts/{podcast_id}`
  - 写接口统一合并鉴权响应（`401/403`）说明。
  - 非 service 层错误（not found / 参数问题 / 路由层异常）统一映射结构化错误码。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（11/11）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（错误码总览 + 前端统一错误提示组件）

### 本次完成
- 新增跨模块错误码总览文档：
  - `backend/docs/error_codes_catalog.md`
  - 覆盖 Auth / Audio Overview / Chat / Translate / Settings / TTS / Voices。
- 前端错误提示组件化：
  - 新增 `frontend/src/components/ErrorNotice.tsx`
  - 新增 `frontend/src/error_hints.ts`（统一错误码解析与建议映射）
  - `App.tsx` 中各 Tab 错误展示统一改为 `ErrorNotice`：
    - TTS / Chat / Translate / Voice Design / Voice Clone / Audio Overview / Settings
- 清理历史特化逻辑：
  - 移除 `Audio Overview` 独立错误提示状态与专用映射函数，避免重复维护。
- 文档入口更新：
  - `WEB_PHASE_A_README.md` 新增 `error_codes_catalog.md` 引用，并更新前端提示说明。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（11/11）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（Request ID 追踪 + 统一错误提示）

### 本次完成
- 后端请求追踪：
  - `backend/main.py` 增加全局 `X-Request-ID`：
    - 客户端传入则透传
    - 未传入则自动生成
    - 所有响应都回写该响应头
  - 鉴权失败响应新增 `detail.meta.request_id`，便于排障定位。
- 测试覆盖：
  - `backend/tests/test_api_smoke.py`
    - 新增 `test_request_id_passthrough`
    - 鉴权失败断言补充 `request_id` 与响应头检查
- 文档补充：
  - 新增 `backend/docs/request_tracing.md`
  - 更新 `backend/docs/error_codes_catalog.md`（标注 Request-ID 行为）
  - 更新 `WEB_PHASE_A_README.md` 文档入口
- 前端错误展示统一：
  - 新增 `frontend/src/components/ErrorNotice.tsx`（统一错误 + 建议）
  - 新增 `frontend/src/error_hints.ts`（错误码到修复建议映射）
  - `frontend/src/App.tsx` 各 Tab 全部改为复用 `ErrorNotice`
  - 错误文本自动附带 `request_id`（当后端返回时）

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（12/12）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（结构化请求日志）

### 本次完成
- `backend/main.py` 增加请求级结构化日志（logger: `voicespirit.request`）：
  - 每个请求输出一行 JSON，包含：
    - `request_id`, `method`, `path`, `status`, `duration_ms`, `auth_result`
  - 鉴权拒绝请求也会记录日志（`auth_result=denied`）。
  - 未鉴权接口记录 `auth_result=not_required`，鉴权通过记录 `auth_result=passed`。
- `backend/docs/request_tracing.md` 补充日志格式与字段说明。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（12/12）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-05 续做记录（错误业务日志统一 request_id）

### 本次完成
- `backend/main.py` 新增错误日志通道：
  - logger: `voicespirit.error`
  - 对所有 `status >= 400` 响应追加结构化错误日志（JSON），字段包含：
    - `request_id`, `method`, `path`, `status`, `code`, `message`
  - 未处理异常统一记录 `UNHANDLED_EXCEPTION`。
- 与既有请求日志形成双轨：
  - `voicespirit.request`：每个请求一条（成功/失败均有）
  - `voicespirit.error`：仅错误请求
- 测试增强：
  - `backend/tests/test_api_smoke.py` 新增 `test_error_log_contains_request_id`
  - 验证错误日志包含 `event=http_error` + `request_id` + `status`
- 文档补充：
  - `backend/docs/request_tracing.md` 增加 `voicespirit.error` 日志格式样例

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（13/13）。
- 前端构建：
  - `cd frontend && npm run build` 已在上一步通过，本次未改前端代码。

## 2026-03-05 续做记录（错误码提取稳定化 + 诊断模板）

### 本次完成
- 错误码提取稳定化（解决 `voicespirit.error` 偶发 `code` 为空）：
  - `backend/main.py`
    - 增加全局 `HTTPException` 与 `RequestValidationError` handler
    - 在异常处理阶段直接记录 `voicespirit.error`（不再依赖响应体反解析）
    - 中间件新增 `error_logged` 标记，避免重复记错
  - 结果：错误日志中的 `code/message/request_id` 一致性显著提升。
- 新增诊断导出模板文档：
  - `backend/docs/diagnostic_export_template.md`
- 文档入口补充：
  - `WEB_PHASE_A_README.md` 增加诊断模板入口。

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（13/13）。
- 前端构建：
  - `cd frontend && npm run build` 通过。

## 2026-03-04 Web 迁移续做记录（Phase B Audio Overview Synthesis）

### 本次完成
- 新增 Audio Overview 脚本生成接口：
  - `POST /api/audio-overview/scripts/generate`
  - 支持 `topic/language/turn_count/provider/model`
  - 使用 `LLMService` 生成并解析 `A:/B:` 对话行
- 新增 Audio Overview 音频合成接口：
  - `POST /api/audio-overview/podcasts/{podcast_id}/synthesize`
  - 按脚本角色分配 `voice_a/voice_b`，逐句调用 Edge TTS 合成并合并
  - 合成后回写 `podcasts.audio_path`
- 音频合并能力增强：
  - 合成参数新增 `gap_ms`（句间静音）与 `merge_strategy`（`auto/pydub/ffmpeg/concat`）
  - 合并链路支持自动回退：`pydub -> ffmpeg -> concat`
  - 合成响应新增 `merge_strategy`、`gap_ms_applied`
  - 合并失败新增结构化错误码：
    - `AUDIO_MERGE_STRATEGY_INVALID`
    - `AUDIO_MERGE_PYDUB_FAILED`
    - `AUDIO_MERGE_FFMPEG_FAILED`
    - `AUDIO_MERGE_ALL_FAILED`
    - `AUDIO_SEGMENT_SYNTHESIS_FAILED`
- 新增 Audio Overview 音频下载接口：
  - `GET /api/audio-overview/podcasts/{podcast_id}/audio`
- 前端新增 `Audio Overview` Tab：
  - 支持话题生成脚本、脚本行编辑/增删、保存、合成、播放、历史播客加载/删除
  - 合成区域新增 `Gap(ms)` 与 `Merge Strategy` 配置
- 修复后端测试阻塞：
  - 将音频下载接口返回由 `FileResponse` 调整为 `Response(bytes)`，避免测试环境流式文件响应阻塞
- 同步更新 `backend/main.py` 阶段标识：
  - root `phase` -> `B-audio-overview-synthesis`

### 验证结果
- 后端测试：
  - `.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（9/9）
- 前端构建：
  - `npm run build` 通过

## 2026-03-04 Web 迁移续做记录（Phase B Audio Overview Baseline）

### 本次完成
- 新增 Chat 流式接口：
  - `POST /api/chat/completions/stream`（SSE）
- 新增 Voice Design / Voice Clone API：
  - `POST /api/voices/design`
  - `POST /api/voices/clone`
  - `GET /api/voices/?voice_type=voice_design|voice_clone`
  - `DELETE /api/voices/{voice_name}?voice_type=...`
- `backend/services/llm_service.py` 新增流式调用能力：
  - 读取 OpenAI-compatible `data: ...` 分片
  - 提取 `delta.content` 并按分片返回
- 新增 `backend/services/qwen_voice_service.py`：
  - 封装 Qwen 自定义音色 create/list/delete 调用
  - 复用 `config.json` 的 DashScope API Key
- 新增 Settings API：
  - `GET /api/settings/`
  - `PUT /api/settings/`
  - 支持按 section 合并更新 `config.json`（api_keys/api_urls/default_models 等）
- 新增 `backend/services/settings_service.py`：
  - 配置模板补全（缺省字段补齐）
  - 更新字段白名单校验（防止写入未知 section）
- 前端 Chat 改为逐字渲染：
  - 发送后先插入 assistant 占位消息
  - 按 SSE 分片持续更新最后一条 assistant 内容
- 前端新增 `Voice Design` / `Voice Clone` 两个联调面板：
  - 支持创建、列表刷新、删除
  - 设计音色支持返回预览音频播放
- 前端新增 `Settings` 联调面板：
  - 支持按 provider 编辑 `API Key / API URL / Default Model / Available Models`
  - 支持读取配置与保存回写
- 新增 Audio Overview 基础 API：
  - `GET /api/audio-overview/podcasts`
  - `GET /api/audio-overview/podcasts/latest`
  - `GET /api/audio-overview/podcasts/{podcast_id}`
  - `POST /api/audio-overview/podcasts`
  - `PUT /api/audio-overview/podcasts/{podcast_id}`
  - `PUT /api/audio-overview/podcasts/{podcast_id}/script`
  - `DELETE /api/audio-overview/podcasts/{podcast_id}`
- 新增 `backend/services/audio_overview_service.py`：
  - 复用 `voice_spirit.db` 中 `podcasts/podcast_scripts` 表结构
  - 支持播客项目与脚本的基础 CRUD
- 新增后端 API smoke 测试：
  - `backend/tests/test_api_smoke.py`（9 个用例）
  - 覆盖 Health/TTS/Chat/Translate/Voices/Settings/AudioOverview
- 构建/语法验证：
  - `npm run build` 通过
  - `python3 -m compileall backend` 通过
  - `backend/.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过

### 当前状态
- Phase A（TTS 最小可用）完成。
- Phase B 第五步（Audio Overview 基础 API + smoke tests）完成。

### 下次直接续做建议
- 迁移 Audio Overview 的“脚本生成 + 音频合成”业务接口（目前仅 CRUD）。
- 为 API 增加鉴权/权限控制与更细粒度输入校验。

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

## 2026-03-05 前端错误可观测性增强（request_id 直达）

### 本次改动
- `frontend/src/error_hints.ts`：
  - 新增 `parseRequestId(message)`，从错误文本中提取 `request_id`。
- `frontend/src/components/ErrorNotice.tsx`：
  - 在错误消息下方展示结构化元信息（`code` / `request_id`）。
  - 新增 “Copy request_id” 按钮，便于用户把请求 ID 发给后端排障。
  - 复制失败时显示兜底提示，避免静默失败。
- `frontend/src/styles.css`：
  - 新增错误元信息与复制状态样式（`errorMeta` / `errorMetaTag` / `errorCopyBtn` / `errorCopyStatus`）。

### 验证结果
- 前端构建：`npm run build` 通过。
- 后端接口测试：`backend/.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（13/13）。

## 2026-03-05 前端错误交互与单测补齐

### 本次改动
- `frontend/src/components/ErrorNotice.tsx`
  - 新增复制成功状态自动复位（1.5s 后 `Copied` 恢复为 `Copy request_id`）。
- 前端测试基础设施：
  - `frontend/package.json` 新增脚本：`test` / `test:run`。
  - `frontend/vite.config.ts` 新增 `vitest` 配置（`jsdom` + `setupFiles`）。
  - 新增 `frontend/src/test/setup.ts`（`jest-dom` + `cleanup`）。
- 新增单测：
  - `frontend/src/error_hints.test.ts`：覆盖错误码提取、`request_id` 提取、exact/prefix hints。
  - `frontend/src/components/ErrorNotice.test.tsx`：覆盖空消息、元信息展示、复制成功自动复位、复制失败兜底提示。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 9 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 错误诊断复制增强（toast + diagnostics）

### 本次改动
- `frontend/src/components/ErrorNotice.tsx`
  - 新增 “Copy diagnostics” 按钮，复制 `code/request_id/message` 组合文本。
  - 新增轻量 toast（`role=status`）用于复制成功/失败反馈。
  - `Copy request_id` 保留并支持 1.5 秒后自动复位文案。
- `frontend/src/styles.css`
  - 新增 toast 样式（成功/失败状态区分）。
- `frontend/src/components/ErrorNotice.test.tsx`
  - 新增 diagnostics 复制测试。
  - 复制成功/失败断言切换为 toast 状态断言。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 10 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 错误详情折叠面板（上下文可视化）

### 本次改动
- `frontend/src/components/ErrorNotice.tsx`
  - 新增 `Show details / Hide details` 折叠切换。
  - 新增可视化详情块，展示 `code/request_id/message/hints` 完整诊断文本。
  - `Copy diagnostics` 的复制内容同步扩展为包含 `hints`。
- `frontend/src/styles.css`
  - 新增错误详情面板样式（`errorDetails`）。
- `frontend/src/components/ErrorNotice.test.tsx`
  - 新增折叠面板开关测试。
  - 更新 diagnostics 复制断言（包含 `hints`）。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 11 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 diagnostics 附加 tab 与时间戳

### 本次改动
- `frontend/src/components/ErrorNotice.tsx`
  - `ErrorNotice` 新增 `scope` 入参（由页面传入当前 tab 标识）。
  - 详情/复制内容新增 `scope` 与 `path` 字段。
  - `Copy diagnostics` 复制时附加 `generated_at`（ISO 时间戳）。
- `frontend/src/App.tsx`
  - 各 tab 的 `ErrorNotice` 调用点全部传入 `scope`：
    - `tts` / `chat` / `translate` / `voice_design` / `voice_clone` / `audio_overview` / `settings`
- `frontend/src/components/ErrorNotice.test.tsx`
  - diagnostics 复制断言更新为包含 `scope/path/generated_at`。
  - 详情面板断言新增 `scope` 可见性检查。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 11 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 diagnostics 附加业务上下文（provider/model）

### 本次改动
- `frontend/src/components/ErrorNotice.tsx`
  - 新增可选 `context` 入参，支持业务上下文字段透传。
  - diagnostics 文本新增 `context.<key>=<value>` 行（按 key 排序，忽略空值）。
- `frontend/src/App.tsx`
  - 各 tab 的 `ErrorNotice` 补充上下文参数，重点包含 provider/model（并附带部分关键字段）：
    - `chat`: provider/model
    - `translate`: provider/model/source_language/target_language
    - `audio_overview`: provider/model/language/podcast_id/merge_strategy
    - 其余 tab 补充对应关键输入字段
- `frontend/src/components/ErrorNotice.test.tsx`
  - 更新 diagnostics 复制断言，覆盖 `context.model/context.provider` 输出。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 11 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 request_id 日志跳转链接（可配置）

### 本次改动
- `frontend/src/components/ErrorNotice.tsx`
  - 新增 `VITE_LOG_SEARCH_BASE_URL` 支持（可选）。
  - 当存在 `request_id` 且配置了日志检索地址时，`request_id` 标签变为可点击链接（新窗口打开）。
  - `Copy diagnostics` 新增 `log_search_url` 字段，便于工单中直接附上日志检索入口。
  - 支持两种 URL 拼接方式：
    - 直接追加 `?request_id=...`（或 `&request_id=...`）
    - 若配置中包含 `{request_id}` 占位符，则直接替换。
- `frontend/src/components/ErrorNotice.test.tsx`
  - 新增 `request_id` 链接渲染测试（含 `href` 断言）。
  - 更新 diagnostics 复制断言（包含 `log_search_url`）。
- `frontend/src/styles.css`
  - 新增 `errorMetaTagLink` 样式。
- `WEB_PHASE_A_README.md`
  - 新增 `VITE_LOG_SEARCH_BASE_URL` 配置说明。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 12 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 一键工单模板复制（Markdown）

### 本次改动
- `frontend/src/components/ErrorNotice.tsx`
  - 新增 “Copy issue template” 按钮。
  - 复制内容为 Markdown 工单模板，包含：
    - `generated_at/scope/path/code/request_id/log_search_url`
    - `Message` 原始错误文本
    - `Context`（`context.*` 字段）
    - `Suggested Fixes`（当前错误码提示）
- `frontend/src/components/ErrorNotice.test.tsx`
  - 新增 issue template 复制测试（固定时间戳断言）。
- `WEB_PHASE_A_README.md`
  - 增补错误面板支持一键复制工单模板说明。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 13 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 诊断模板补充前端版本与 UA

### 本次改动
- `frontend/vite.config.ts`
  - 增加 `__APP_VERSION__` 注入（默认来自 `frontend/package.json` 的 `version`，可由 `VITE_APP_VERSION` 覆盖）。
- `frontend/src/vite-env.d.ts`
  - 增加 `__APP_VERSION__` 类型声明。
- `frontend/src/components/ErrorNotice.tsx`
  - diagnostics 增加 `frontend_version` 与 `user_agent` 字段。
  - issue template 增加 `frontend_version` 与 `user_agent` 字段。
- `frontend/src/components/ErrorNotice.test.tsx`
  - 更新 diagnostics 与 issue template 复制断言，覆盖新增字段（采用关键字段匹配，降低脆弱性）。
- `WEB_PHASE_A_README.md`
  - 补充文档说明：诊断复制包含前端版本与 UA。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 13 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 diagnostics 附加后端运行模式（phase/auth_mode）

### 本次改动
- `frontend/src/api.ts`
  - 新增 `fetchApiRuntimeInfo()`，读取后端根接口 `GET /` 的运行元信息（`phase/auth_mode/version/status`）。
- `frontend/src/App.tsx`
  - 启动后异步拉取后端 runtime 信息并缓存到状态。
  - 各 tab 的 `ErrorNotice context` 自动注入：
    - `backend_phase`
    - `backend_auth_mode`
    - `backend_version`
    - `backend_status`
- `WEB_PHASE_A_README.md`
  - 文档补充：当后端根接口可达时，diagnostics 会自动附加上述后端运行元信息。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 13 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 Backend Mode 可视化 + auth_enabled 透传

### 本次改动
- `frontend/src/App.tsx`
  - 新增 `backend_auth_enabled` 运行状态缓存（来自 `fetchApiRuntimeInfo()`）。
  - 所有 `ErrorNotice context` 新增 `backend_auth_enabled` 字段。
  - 页面头部新增只读 `Backend Mode` 标签，实时显示：
    - `status`
    - `phase`
    - `auth_mode`
    - `auth_enabled`
    - `version`
- `frontend/src/styles.css`
  - 新增 `runtimeBadge` 样式。
- `frontend/src/components/ErrorNotice.test.tsx`
  - 诊断与工单模板复制断言新增 `backend_auth_enabled=false` 覆盖。
- `WEB_PHASE_A_README.md`
  - 文档补充 diagnostics 的后端字段清单（含 `backend_auth_enabled`）。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 13 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 后端运行态 JSON 展开与复制

### 本次改动
- `frontend/src/api.ts`
  - `fetchApiRuntimeInfo()` 新增 `raw` 字段返回，保留后端根接口完整 JSON。
- `frontend/src/App.tsx`
  - 头部新增 `Show backend runtime / Hide backend runtime` 开关。
  - 新增 `Copy backend runtime` 按钮（复制完整 root JSON）。
  - 复制成功后按钮文案临时切换为 `Runtime copied`，失败显示兜底提示。
  - 拉取失败时默认回退为 `{}`。
- `frontend/src/styles.css`
  - 新增 `runtimeActions` / `runtimeCopyStatus` / `runtimeDetails` 样式。
- `WEB_PHASE_A_README.md`
  - 新增说明：支持展开与复制后端运行态 JSON。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 13 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-05 桌面化过渡方案落地（PyWebView）

### 本次改动
- `backend/main.py`
  - 新增 `/app` 前端静态托管：
    - 当 `frontend/dist` 存在时，自动提供 `GET /app/` 与 SPA fallback。
    - `assets` 通过 `/app/assets` 暴露。
  - 保持 `/` 与 `/api/*` 行为不变，避免影响现有接口。
- 新增桌面启动器：
  - `run_web_desktop.py`
  - 能力：
    - 检查 `frontend/dist/index.html` 是否存在
    - 自动启动后端（若本地 8000 未运行）
    - 打开 `PyWebView` 原生窗口加载 `http://127.0.0.1:8000/app/`
    - 关闭窗口后自动回收由启动器拉起的后端进程
- 新增依赖清单：
  - `desktop_requirements.txt`（`backend/requirements + pywebview`）
- 新增 Windows 一键启动：
  - `run_web_desktop.bat`
- 文档更新：
  - `WEB_PHASE_A_README.md` 增加 Browser mode / Desktop mode 双入口说明。

### 验证结果
- 前端构建：`cd frontend && npm run build` 通过。
- 后端语法：`cd backend && .venv/bin/python -m compileall main.py` 通过。

## 2026-03-05 续做记录（功能体检，界面冻结）

### 本次约束
- 按当前要求，未进行任何界面样式改动，仅检查功能可用性与链路状态。

### 已验证（通过）
- 后端接口烟测（mock 外部依赖）通过：
  - `cd backend && .venv/bin/python -m unittest tests/test_api_smoke.py`
  - 结果：13/13 通过
  - 覆盖：health/request-id、auth、TTS、Chat（含 stream）、Translate、Voices CRUD、Settings、Audio Overview CRUD+合成流程。
- 前端测试通过：
  - `cd frontend && npm run test:run`
  - 结果：13/13 通过
- 本地运行态接口检查通过（真实服务）：
  - `GET /health` -> 200
  - `GET /app/` -> 200（已返回前端 index.html）
  - `GET /api/settings/` -> 200
  - `GET /api/tts/voices` -> 200（返回语音列表）
  - `POST /api/chat/completions` 空 payload -> 422（参数校验生效）
  - `POST /api/translate/` 空 payload -> 422（参数校验生效）
  - `GET /api/audio-overview/podcasts?limit=5` -> 200
  - `GET /assets/index-*.js` -> 200（静态资源别名可用，桌面白屏修复链路有效）

### 未做（有意保留）
- 未执行真实第三方模型调用（Chat/Translate/Voice Design/Voice Clone/真实合成），避免在未确认预算和配额前产生外部 API 费用。

### 当前结论
- 当前架构下“桌面壳 + FastAPI + React”主链路已通，核心 API 和前端基础能力可运行。
- 现阶段主要剩余风险在“真实外部模型端到端可用性”与“生产安全策略（鉴权启用）”而非页面渲染链路。

## 2026-03-06 聊天页 UI 改版（参照新建文本文档）

### 本次改动
- `frontend/src/App.tsx`
  - 聊天页结构重做：深色侧边栏、顶部提供商/模型区、空状态引导卡片、底部输入区。
  - 侧边栏新增应用图标位、最近会话空态、底部用户信息卡。
  - 空状态新增 4 个快捷动作按钮（起草邮件/编写代码/头脑风暴/总结文本），点击可填充输入框。
  - 保留原有聊天请求/流式渲染逻辑与其他标签页功能逻辑。
- `frontend/src/styles.css`
  - 新增整套 `vs*` 聊天页样式（布局、配色、圆角卡片、渐变按钮、移动端响应式）。
  - 同步调整消息气泡视觉，保留其他功能页通用表单样式。
  - 更新移动端断点逻辑，适配新侧边栏与聊天输入区布局。

### 验证结果
- 前端构建：`cd frontend && npm run build` 通过（Vite 构建成功）。

### 明天续做建议
- 聊天页可继续补齐：顶部“分享/更多”按钮真实行为、侧边栏历史会话分组与持久化、空状态卡片图标替换为正式 icon 资源。
