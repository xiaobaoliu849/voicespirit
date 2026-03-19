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

## 2026-03-19 续做记录（Audio Agent 最小闭环）

### 本次完成
- 新增 Audio Agent 架构设计文档：
  - `docs/Audio_Agent_Architecture_Plan.md`
- 后端新增轻量 agent runtime 骨架：
  - `backend/services/audio_agent_repository.py`
  - `backend/services/audio_agent_service.py`
  - `backend/services/audio_retrieval_service.py`
  - `backend/services/audio_script_writer.py`
  - `backend/routers/audio_agent.py`
- 新增并挂载 API：
  - `POST /api/audio-agent/runs`
  - `GET /api/audio-agent/runs`
  - `GET /api/audio-agent/runs/{id}`
  - `GET /api/audio-agent/runs/{id}/events`
  - `POST /api/audio-agent/runs/{id}/execute`
  - `POST /api/audio-agent/runs/{id}/synthesize`
- SQLite 新增 agent 运行时表：
  - `audio_agent_runs`
  - `audio_agent_steps`
  - `audio_agent_sources`
  - `audio_agent_events`
- 生成链路升级为固定 agent 流程：
  - `prepare -> retrieve -> assemble_evidence -> generate_script -> persist_draft -> synthesize_audio`
- `Audio Overview` 前端已切到新的 agent run 流程：
  - 生成脚本时创建并轮询 run
  - 自动载入 run 生成的播客草稿
  - 有 run 时优先走 run 级合成
- UI 新增 agent 信息展示：
  - 顶部 run 状态
  - 主区域 Agent 运行状态条
  - 右侧步骤列表、来源列表、最近事件、失败信息
  - 失败后支持 retry
- 高级设置新增可控输入：
  - 手动资料
  - 来源 URL 列表
  - 生成约束
  - 以上字段已接入后端 run 和脚本提示词

### 验证结果
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest tests.test_api_smoke.ApiSmokeTests.test_audio_agent_run_endpoints` 通过
- 前端测试：
  - `cd frontend && npx vitest run src/components/podcast/PodcastTopicStep.test.tsx src/components/podcast/PodcastSidebar.test.tsx src/components/podcast/PodcastHeader.test.tsx src/pages/AudioOverviewPage.test.tsx` 通过
- 前端构建：
  - `cd frontend && npm run build` 通过

### 当前停点
- 当前已具备最小可用的 audio-agent 产品闭环，但 URL 仍只是“显式来源记录”，尚未升级为“抓取并摘要网页内容”。
- 事件进度目前采用轮询 `get_run/events`，尚未升级到 SSE。
- run 级合成已接通，但更细的恢复动作（如按失败步骤 retry）还未实现。

### 明日建议起手
- 优先把 URL 来源从记录模式升级为抓取/抽取/摘要模式。
- 然后再考虑 SSE 实时进度或更细粒度的失败恢复。
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

## 2026-03-07 桌面壳增强（PyWebView launcher）

### 本次改动
- `run_web_desktop.py`
  - 新增单实例锁，避免重复启动多个桌面窗口和后端进程竞争。
  - 新增窗口状态持久化：记录窗口大小、位置、最大化状态，并在下次启动时恢复。
  - 新增 WebView 存储目录持久化，桌面态本地数据不再默认使用私有临时模式。
  - 运行态目录支持“优先系统目录，失败回退项目内 `.voicespirit-desktop/`”。
- `.gitignore`
  - 忽略 `.voicespirit-desktop/` 运行态目录，避免状态文件进入版本控制。
- `WEB_PHASE_A_README.md`
  - 补充桌面启动器的单实例和状态持久化说明。

### 验证结果
- 语法校验：`python3 -m py_compile run_web_desktop.py` 通过。
- 启动器导入检查：`python3 -c "import run_web_desktop as r; print(r.RUNTIME_DIR); print(r.load_window_state())"` 通过。

### 当前结论
- 桌面壳从“可启动”提升为“可重复使用”的状态，窗口行为和本地状态管理更加接近正式桌面应用。

## 2026-03-07 桌面壳增强（原生菜单）

### 本次改动
- `run_web_desktop.py`
  - 新增原生桌面菜单：
    - `VoiceSpirit`：刷新应用、浏览器打开、打开桌面数据目录、打开项目目录、退出
    - `Window`：重置窗口布局
    - `Help`：打开项目目录
  - 新增 `DesktopController` 统一处理菜单动作，避免桌面逻辑散落在启动函数中。
  - `Reset Window Layout` 现在会立即恢复默认窗口尺寸，并尝试居中主屏幕。

### 验证结果
- 语法校验：`python3 -m py_compile run_web_desktop.py` 通过。
- 菜单构造自检通过。
- 窗口重置逻辑自检通过（恢复、缩放、移动到主屏幕居中）。

## 2026-03-07 Web 桌面端 UI 续做（按根目录设计稿）

### 本次改动
- 设计参考确认：
  - 根目录 `新建文本文档.txt` 为聊天页 HTML 设计稿。
  - 根目录 `1.png` 为目标视觉参考图。
- `frontend/src/App.tsx`
  - 聊天页继续收敛到设计稿：内联 SVG 图标替代文字占位，Provider 顶栏、快捷卡片、输入条、历史列表与品牌区细节同步更新。
  - `TTS` 升级为“语音工作台”布局：页头信息卡、主编辑区、右侧音频预览区。
  - `Translate` 升级为“翻译工作台”布局：页头信息卡、参数编辑区、右侧结果面板。
- `frontend/src/styles.css`
  - 聊天页视觉进一步贴近设计稿：外边框、深色窄侧栏、浅色主画布、工具栏、空态卡片、悬浮输入区。
  - 新增 `vsToolWorkspace / vsToolHeader / vsSurfaceCard / vsResultPanel / vsEmptyPanel` 等桌面端工作台样式。
  - 移动端断点同步适配新工作台布局。

### 验证结果
- 前端构建：
  - `cd frontend && npm run build` 通过。
- 前端测试：
  - `cd frontend && npm run test -- --run` 通过（2 files / 13 tests）。

### 当前结论
- Web 桌面端当前已完成统一视觉的页面：
  - 聊天页
  - 语音页
  - 翻译页
- 下一步可继续将 `Audio Overview / Settings / Voice Design / Voice Clone` 迁移到同一套桌面工作台设计语言。

## 2026-03-07 Web 桌面端 UI 续做（剩余工作台统一）

### 本次改动
- `frontend/src/App.tsx`
  - 为语音模块补充二级工作台切换：`文本转语音 / 音色设计 / 音色克隆`。
  - 侧边栏“语音”高亮范围扩展到 `TTS / Voice Design / Voice Clone` 三个页面。
  - `Voice Design` 从旧 `legacyPanel` 迁移为统一工作台布局：页头指标卡、创建表单、右侧预览卡和列表卡。
  - `Voice Clone` 迁移为统一工作台布局：样本上传表单、样本摘要卡、克隆列表卡。
  - `Audio Overview` 迁移为统一工作台布局：页头状态卡、脚本/合成参数面板、右侧音频预览与历史播客面板。
  - `Settings` 迁移为统一工作台布局：Provider 配置区、后端运行态面板、配置摘要卡。
- `frontend/src/styles.css`
  - 新增语音二级导航样式：`vsWorkspaceTabs / vsWorkspaceTab`。
  - 新增堆叠式右侧面板与内嵌卡片样式：`vsStackedPanels / vsInsetPanel / vsInsetPanelHeader`。
  - 新增状态胶囊与设置摘要卡样式：`vsStatusRow / vsStatusPill / vsMetricList / vsMetricCard`。
  - 新增 `rose / emerald` 主题变体，并为新工作台补充响应式适配。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（2 files / 13 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

### 当前结论
- Web 桌面端五个主入口现在都已切到同一套工作台视觉语言：
  - Chat
  - Translate
  - TTS
  - Audio Overview
  - Settings
- 语音相关扩展页 `Voice Design / Voice Clone` 也已并入统一工作台风格，并补上入口切换。
- 下一步更适合继续做：
  - 为这些工作台补充更细的交互测试；或
  - 继续把运行态 / 导出 / 复制等动作补齐到 Audio Overview 与语音扩展页。

## 2026-03-07 Web 桌面端 UI 续做（前端交互补齐）

### 本次改动
- `frontend/src/App.tsx`
  - 新增通用前端动作辅助：复制文本、导出文本文件、播客脚本转纯文本。
  - `Voice Design` 增加：
    - `Copy Prompt`
    - `Use Preview in TTS`
  - `Voice Clone` 增加：
    - `Clear Sample`
  - `Audio Overview` 增加：
    - `Copy Script`
    - `Export JSON`
- `frontend/src/App.interactions.test.tsx`
  - 新增前端交互测试：
    - `Voice Design -> Use Preview in TTS`
    - `Audio Overview -> Copy Script`

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 15 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

### 当前结论
- 这轮优先补齐了不依赖后端改动的高价值本地交互。
- 下一步适合继续做：
  - `Translate` 结果复制 / 导出；
  - `TTS / Audio Overview` 音频显式下载；
  - 更多工作台级交互测试。

## 2026-03-07 Web 桌面端 UI 续做（前端交互二批）

### 本次改动
- `frontend/src/App.tsx`
  - `Translate` 增加：
    - `Copy Result`
    - `Export TXT`
  - `TTS` 增加：
    - `Download Audio`
    - 生成成功后的本地提示文案
  - `Audio Overview` 合成区增加：
    - `Download Audio`
- `frontend/src/App.interactions.test.tsx`
  - 追加前端交互测试：
    - `Translate -> Copy Result`
    - `TTS -> Download Audio`

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 17 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

### 当前结论
- 当前已补齐的本地交互包括：
  - Voice Design：复制 Prompt、把预览文本送入 TTS
  - Voice Clone：清空样本
  - Audio Overview：复制脚本、导出 JSON、下载音频
  - Translate：复制结果、导出 TXT
  - TTS：下载音频

## 2026-03-07 Web 桌面端 UI 续做（前端交互三批）

### 本次改动
- `frontend/src/App.tsx`
  - `Chat` 顶栏动作接入真实交互：
    - `复制会话`
    - `Export chat`
  - `Settings` 增加：
    - `Copy Summary`
  - 新增聊天转录构建逻辑与设置摘要复制逻辑。
- `frontend/src/App.interactions.test.tsx`
  - 追加前端交互测试：
    - `Chat -> 复制会话`
    - `Settings -> Copy Summary`

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 19 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

### 当前结论
- 聊天页顶栏不再只是占位按钮，已具备会话复制/导出能力。
- 设置页现在支持快速复制当前 Provider / 模型 / 配置路径 / 后端运行态摘要。

## 2026-03-07 Web 桌面端 UI 续做（前端交互四批）

### 本次改动
- `frontend/src/App.tsx`
  - 聊天历史项点击时，现改为回填完整原始提问，而不是截断后的短文本。
- `frontend/src/App.interactions.test.tsx`
  - 追加导出与历史交互测试：
    - `Chat -> Export chat`
    - `Translate -> Export TXT`
    - `Audio Overview -> Export JSON`
    - `Chat history -> restore full prompt`

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 23 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

### 当前结论
- 当前主要本地复制/导出/下载交互已基本有测试覆盖。
- 聊天历史的回填体验也比之前更完整。

## 2026-03-07 Web 桌面端 UI 续做（前端交互五批）

### 本次改动
- `frontend/src/App.interactions.test.tsx`
  - 追加交互测试：
    - `Settings -> Show backend runtime / Copy backend runtime`
    - `Audio Overview -> Download Audio`
  - 同时把 Audio Overview mock 数据改为带音频路径，覆盖“载入后可直接下载”的链路。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 25 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

### 当前结论
- 设置页运行态面板与复制动作已纳入自动化覆盖。
- 播客页“载入历史 -> 下载音频”链路也已纳入自动化覆盖。

## 2026-03-08 Web 桌面端修正（聊天提供商与默认模型）

### 本次改动
- `frontend/src/App.tsx`
  - 移除聊天/翻译/播客工作台里后端当前不支持的 `Google` 提供商入口。
  - 聊天工作台默认提供商从 `Google` 改为 `DashScope`。
  - 聊天模型占位从 `gemini-2.5-flash` 改为 `qwen-plus`。
  - 新增基于设置页配置的默认模型回填：
    - Chat
    - Translate
    - Audio Overview
- `frontend/src/App.interactions.test.tsx`
  - 新增测试：聊天页默认使用受支持提供商，并从设置中回填默认模型。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 26 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

### 当前结论
- 之前你看到的 `Unsupported provider: Google` 属于前端默认值错误，不是你操作有问题。
- 刷新前端后，聊天页默认应改为 `DashScope + qwen-plus`。

## 2026-03-08 Web 桌面端修正（翻译页回归简洁翻译器）

### 本次改动
- `frontend/src/App.tsx`
  - 将翻译页从“工作台卡片布局”改回更接近原桌面端的简洁翻译器：
    - 顶部简洁参数条
    - 左侧原文
    - 右侧译文
  - 移除翻译页中的提供商/模型编辑控件，改为只读提示：
    - 使用设置中的默认提供商 / 模型
  - 翻译页 provider/model 运行时与 Settings 页面同步。
- `frontend/src/styles.css`
  - 新增简洁翻译器样式：
    - `vsTranslateConfigHint`
    - 收紧 `vsTranslateToolbar`
    - 保持双栏工具布局

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 26 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

### 当前结论
- 翻译页现在更接近你给的 `1.png` 方向，而不是之前的 `2.png` 工作台卡片风格。
- 如果继续收敛，下一步应该做的是：
  - 更细地对齐顶部控件尺寸、留白和按钮色值；
  - 弱化标题区，让整体更像“工具”而不是“页面模块”。

## 2026-03-08 Web 桌面端增强（专业翻译器 + 图片翻译）

### 本次改动
- `backend/services/llm_service.py`
  - 扩展多模态消息支持。
  - 新增 `translate_image()`，可将图片作为 `image_url` 内容发送给兼容模型。
- `backend/routers/translate.py`
  - 新增 `POST /api/translate/image`，支持图片翻译上传。
- `frontend/src/api.ts`
  - 新增 `translateImage()`。
- `frontend/src/App.tsx`
  - 翻译页升级为 `文本翻译 / 图片翻译` 双模式。
  - 文本模式保持极简双栏。
  - 图片模式支持上传、预览、替换、清空，并调用后端图片翻译接口。
  - 翻译页 provider/model 与 Settings 保持同步，不在页面内重复编辑。
- `frontend/src/App.interactions.test.tsx`
  - 新增图片翻译模式前端测试。
- `backend/tests/test_api_smoke.py`
  - 新增图片翻译接口 smoke test。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 27 tests）。
- 前端构建：`cd frontend && npm run build` 通过。
- 后端测试：`cd backend && .venv/bin/python -m unittest tests.test_api_smoke -v` 通过（14 tests）。

### 当前结论
- 翻译页现在更接近“专业翻译工具”的信息层级：
  - 设置页管模型/provider
  - 翻译页专注源内容、语言、结果
- 图片翻译链路已打通，但实际效果依赖你在 Settings 中选择/配置支持视觉的模型。

## 2026-03-08 Web 翻译器精修（统一专业界面）

### 本次改动
- `frontend/src/App.tsx`
  - 移除翻译页顶部说明块，改成单一工作区布局。
  - 将 `文本翻译 / 图片翻译`、语言选择、交换按钮、Translate 主按钮收拢到一条专业工具栏。
  - 将 provider/model 改成只读设置徽标，弱化存在感，不再抢主流程注意力。
  - 将结果区操作挪到译文面板头部，主流程变为“输入 / 上传 → 翻译 → 复制 / 导出”。
- `frontend/src/styles.css`
  - 重做翻译页容器、顶部条、双栏面板、图片上传区和结果区样式。
  - 统一圆角、阴影、边框、留白和响应式行为，减少“页面模块感”，增强“工具面板感”。

### 设计依据
- 参考主流专业翻译工具的当前模式：主界面聚焦源语言、目标语言、源内容、结果内容。
- 多模态能力使用轻量模式切换承载，而不是额外堆叠设置块。
- 模型和提供商属于系统配置，应退到次要层级，只保留只读提示。

### 验证结果
- 前端测试：`cd frontend && npm run test:run` 通过（3 files / 27 tests）。
- 前端构建：`cd frontend && npm run build` 通过。

## 2026-03-08 前端验证补记（Codex 意外中断后续收尾）

### 情况说明
- 上一轮在更新翻译页交互文案与测试过程中，`codex` CLI 发生 `Segmentation fault`，任务中断在 `Run frontend validation` 之前。

### 本次收尾
- `frontend/src/App.tsx`
  - 确认翻译页字符计数文案为中文：`个字符`。
  - 删除 2 个未使用的 state，修复 TypeScript 构建失败。
- `frontend/src/App.interactions.test.tsx`
  - 保留并验证新增交互测试覆盖。

### 验证结果
- 前端构建：`cd frontend && npm run build` 通过。
- 新增交互测试：`cd frontend && npm run test:run -- src/App.interactions.test.tsx --reporter=dot` 通过（15 tests）。
- 前端全量测试：`cd frontend && npm run test:run` 通过（3 files / 28 tests）。

### 结论
- 这次中断是 CLI 进程异常退出，不是代码执行卡死。
- 当前前端改动已完成收尾验证，可以从这个状态继续下一步开发。

## 2026-03-09 续做记录（VoiceSpirit 记忆分层 + 桌面语音链路）

### 本次完成
- Web 端长期记忆继续向语音场景延伸：
  - 播客脚本生成接入 EverMem 检索与写回。
  - TTS 语音合成成功后回写语音偏好摘要。
- 桌面端新增本地记忆策略层：
  - 新增 `app/core/desktop_memory.py`
  - 将长期记忆拆分为“本地 transcript 资产”与“结构化长期记忆”
  - 语音聊天、录音转写、普通文本聊天都接入同一策略入口
- 本地数据库扩展：
  - `app/core/database.py` 新增 `voice_transcripts` 表，用于保存原始语音转写资产
- 配置模板扩展：
  - `app/core/config.py`
  - `backend/services/settings_service.py`
  - 新增 `memory_settings`，包括：
    - `enabled`
    - `temporary_session`
    - `remember_chat / remember_voice_chat / remember_recordings / remember_podcast / remember_tts`
    - `store_transcript_fulltext`
- 桌面设置页接线：
  - `app/ui/pages/settings_page.py` 新增 Memory Settings 区块
  - 可直接配置 EverMem URL/Key/Scope，以及桌面端场景开关
  - `app/core/translation.py` 补齐中英文文案

### 当前策略
- 录音转写默认不把全文写入长期记忆，只保存本地 transcript 资产。
- 实时语音与桌面聊天只在识别到“偏好 / 语音偏好 / 任务上下文”时才写入 EverMem。
- `temporary_session=true` 时不检索也不写入长期记忆。

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile app/core/desktop_memory.py app/core/database.py app/core/config.py app/ui/pages/chat_page.py app/ui/pages/settings_page.py app/core/translation.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（15/15）
- 前端测试：
  - `cd frontend && npm run test:run` 通过（19 files / 45 tests）
- 前端构建：
  - `cd frontend && npm run build` 通过

## 2026-03-09 续做补记（记忆抽取器收紧 + 配置字段归一化）

### 本次完成
- `app/core/desktop_memory.py`
  - 将原本“命中关键词就整句写入”的策略升级成按句分段、去重、按优先级筛选的结构化提炼。
  - 只在明确识别到 `用户偏好 / 语音偏好 / 当前任务上下文` 时写入 EverMem。
  - `store_transcript_fulltext` 现在只对语音 transcript 生效，不会把普通文本聊天误当成全文记忆写入。
- `backend/services/settings_service.py`
  - 为 `memory_settings` 增加字段别名归一化：
    - `url -> api_url`
    - `key -> api_key`
    - `tempSession -> temporary_session`
    - `sceneChat -> remember_chat`
    - `sceneVoiceChat -> remember_voice_chat`
    - `sceneTranscription -> remember_recordings`
    - `scenePodcast -> remember_podcast`
    - `sceneTts -> remember_tts`
- `app/core/config.py`
  - 桌面端加载 `config.json` 时同步兼容上述别名，避免前端写入后桌面端读不到。
- `backend/tests/test_api_smoke.py`
  - 新增 `memory_settings` 别名归一化回归测试。

### 当前效果
- Web 前端保存到 `/api/settings/` 的 Memory Center 字段，即使还没完全统一命名，也会被后端落成桌面端能识别的规范字段。
- 桌面端的长期记忆写入比之前更保守，误记概率显著下降。

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile app/core/desktop_memory.py app/core/config.py backend/services/settings_service.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（16/16）

## 2026-03-09 续做补记（待办 / 约束 / 摘要抽取 + 单测覆盖）

### 本次完成
- `app/core/desktop_memory.py`
  - 在原有 `用户偏好 / 语音偏好 / 当前任务上下文` 之外，新增：
    - `待办事项`
    - `约束条件`
    - `会话摘要`
  - 将 transcript 提炼粒度从“整句”收紧到“分句 + 分逗号子句”，更适合从口语输入里提炼明确的行动项和限制条件。
  - 保留保守策略：
    - 问句不进入长期记忆
    - 普通文本聊天不会走 transcript 全文兜底
    - transcript 全文兜底仍仅对语音来源生效
- `backend/tests/test_desktop_memory.py`
  - 新增桌面记忆提炼单测，覆盖：
    - 语音偏好抽取
    - 待办事项抽取
    - 约束条件抽取
    - 显式摘要抽取
    - 问句过滤
    - transcript 全文兜底仅限语音来源

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile app/core/desktop_memory.py backend/tests/test_desktop_memory.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（21/21）

## 2026-03-09 续做补记（任务上下文 vs 摘要边界收紧）

### 本次完成
- `app/core/desktop_memory.py`
  - 新增 `task_context` 专用模式，只认更稳定的项目上下文表述，例如：
    - `当前在做`
    - `最近在做`
    - `主要在`
    - `正在`
    - `项目是 / 项目叫 / 主题是`
  - 增加抽取后处理：
    - 如果同一段内容里已经有 `待办事项` 或 `约束条件`，则不再额外保留泛化的 `会话摘要`
    - 避免把同一条行动项同时重复记成 `任务上下文`
- `backend/tests/test_desktop_memory.py`
  - 新增边界回归：
    - `待办事项` 优先于重叠的 `会话摘要`
    - 稳定项目上下文可被正确提炼为 `当前任务上下文`

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile app/core/desktop_memory.py backend/tests/test_desktop_memory.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（23/23）

## 2026-03-09 续做补记（近期重复记忆去重）

### 本次完成
- `app/core/desktop_memory.py`
  - 新增近期记忆去重缓存，避免用户在多轮聊天、实时语音、录音转写里重复说同一偏好或同一行动项时，短时间内连续写入 EverMem。
  - 当前策略：
    - 去重窗口：10 分钟
    - 最大缓存条目：64
    - 去重粒度：按最终写入的记忆文本内容归一化后判重
- `backend/tests/test_desktop_memory.py`
  - 新增回归：
    - 同一条记忆在窗口内重复出现会被抑制
    - 不同内容的记忆不会被误杀

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile app/core/desktop_memory.py backend/tests/test_desktop_memory.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（25/25）

## 2026-03-09 续做补记（录音转写主链切到 Qwen-ASR）

### 本次完成
- `backend/services/transcription_service.py`
  - 新增共享转写服务，统一封装 DashScope `Qwen-ASR-Flash` 的短音频同步转写调用。
  - 支持自动识别本地音频 MIME 类型，并从多模态响应里抽取 transcript 文本。
- `app/core/api_client.py`
  - 桌面端录音转写不再直接调用旧的 `sensevoice-v1 Recognition` 逻辑。
  - 现已改为走共享 `TranscriptionService`，为后续独立的 `Transcription Center` 和 Web API 复用打底。
- `backend/tests/test_api_smoke.py`
  - 新增转写结果解析单测，覆盖多模态响应中 transcript 文本提取。

### 当前状态
- 聊天页录音转写主链已经从旧 SenseVoice 方向切换到 Qwen-ASR 主线。
- 这一步先解决“主实现老旧、难维护、后续难扩展”的问题；长音频异步转写和独立转写工作台放到下一阶段接。

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_service.py app/core/api_client.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（26/26）

## 2026-03-09 续做补记（转写稳定性补丁）

### 本次完成
- `app/core/audio_recorder.py`
  - 修正录音 WAV 文件头采样率，保存时不再错误写成 `24000Hz`。
  - 现在会写入真实输入采样率 `16000Hz`，避免 downstream ASR 因文件元数据错误而识别异常。
- `backend/services/transcription_service.py`
  - 增加音频文件格式校验，先拒绝不支持的后缀。
  - 预留 `prepare_long_transcription_job()`，作为长音频异步转写入口骨架。
- `backend/tests/test_api_smoke.py`
  - 新增不支持格式的转写校验回归。

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_service.py app/core/audio_recorder.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（27/27）

## 2026-03-09 续做补记（长音频异步任务骨架）

### 本次完成
- `backend/services/transcription_service.py`
  - 为长音频异步转写补了可持久化的任务骨架：
    - `TranscriptionJob`
    - `prepare_long_transcription_job()`
    - `get_job()`
    - `update_job()`
  - 任务状态会落到本地 JSON 文件，包含：
    - `job_id`
    - `file_path`
    - `mode`
    - `status`
    - `created_at / updated_at`
    - `transcript_path`
    - `error`
- `backend/tests/test_api_smoke.py`
  - 新增异步转写任务持久化回归，覆盖创建、读取、更新状态。

### 当前意义
- 这一步还不是完整的长音频转写任务流，但已经把前端真正需要消费的最小状态模型搭出来了。
- 后续只需要再把“提交到 Qwen 异步接口 / 轮询远端状态 / 落 transcript 文件”补进去，就能直接接 `Transcription Center`。

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_service.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（28/28）

## 2026-03-09 续做补记（异步提交 / 刷新状态流）

### 本次完成
- `backend/services/transcription_service.py`
  - 为长音频任务补上了更接近真实产品流的服务接口：
    - `submit_long_transcription_job()`
    - `refresh_long_transcription_job()`
  - 新增状态字段：
    - `remote_job_id`
  - 新增远端状态映射与 transcript 落盘逻辑：
    - `submitted -> running -> completed/failed`
    - 任务完成后会把 transcript 写到本地 `.txt`
- `backend/tests/test_api_smoke.py`
  - 新增异步提交与刷新回归，覆盖：
    - 提交后拿到 `remote_job_id`
    - 刷新后进入 `completed`
    - transcript 文件真实落盘

### 当前状态
- 这一步仍是服务层骨架，但已经不是“空任务对象”了。
- 前端现在理论上已经可以消费：
  - 本地 `job_id`
  - 远端 `remote_job_id`
  - 轮询后的状态变化
  - transcript 文件路径

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_service.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（29/29）

## 2026-03-09 续做补记（转写正式 API）

### 本次完成
- `backend/routers/transcription.py`
  - 将转写服务正式暴露为 API：
    - `POST /api/transcription/`：同步短音频转写
    - `POST /api/transcription/jobs`：创建并提交长音频异步任务
    - `GET /api/transcription/jobs/{job_id}`：查询任务状态，并在完成后直接返回 transcript 文本
  - 统一了上传校验、结构化错误响应和上传文件持久化策略。
- `backend/tests/test_api_smoke.py`
  - 新增同步转写接口回归
  - 新增异步任务接口回归

### 当前状态
- 现在前端不必直接依赖本地类了，`Transcription Center` 已经有真实后端 API 可以接：
  - 同步转写适合短音频
  - 异步任务适合长音频和轮询状态

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/routers/transcription.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（31/31）

## 2026-03-09 续做补记（URL 型真异步入口）

### 本次完成
- `backend/services/transcription_service.py`
  - 新增 `prepare_long_transcription_url_job()`，支持基于 `http/https/oss` 的远端音频地址创建长音频异步任务。
  - 新增 DashScope 异步基础 URL 归一化逻辑：
    - 会把现有 `compatible-mode/v1` 配置自动转换为 `api/v1`
  - 新增真实远端异步提交和状态查询方法骨架：
    - `_submit_remote_job_from_url()`
    - `_fetch_remote_job_status()`
    - `_download_remote_transcript()`
- `backend/routers/transcription.py`
  - 新增 `POST /api/transcription/jobs/from-url`
  - 现在长音频异步转写有两条入口：
    - 本地上传任务接口（当前仍主要用于产品联调）
    - URL 型真异步接口（更贴近 DashScope 官方约束）
- `backend/tests/test_api_smoke.py`
  - 新增 URL 型异步任务接口回归
  - 新增异步基础 URL 归一化回归

### 当前状态
- 现在后端已经能同时支撑：
  - 短音频同步转写
  - 长音频异步任务状态流
  - 面向 DashScope 官方约束的 URL 型真异步入口

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_service.py backend/routers/transcription.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（33/33）

## 2026-03-09 续做补记（转写 -> EverMem 记忆链）

### 本次完成
- `backend/services/transcription_service.py`
  - 新增 `maybe_save_memory()`，支持把转写结果提炼成简短记忆条目后写入 EverMem。
  - 新增转写记忆摘要构建逻辑，默认将 transcript 压缩成简短摘要后写入。
  - `TranscriptionJob` 增加 `memory_saved` 字段，避免异步任务每次轮询都重复写记忆。
- `backend/routers/transcription.py`
  - `POST /api/transcription/` 现在会在成功转写后尝试写入 EverMem，并返回 `memory_saved`
  - `GET /api/transcription/jobs/{job_id}` 在异步任务第一次完成时会尝试写入 EverMem，之后不会重复写入
- `backend/tests/test_api_smoke.py`
  - 新增同步转写写入记忆回归
  - 新增异步任务完成后只写一次记忆的回归

### 当前状态
- 现在转写链已经不只是“拿 transcript”：
  - 同步转写可选写入长期记忆
  - 异步转写在完成时也能沉淀为长期记忆
  - 且异步轮询不会重复记忆污染

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_service.py backend/routers/transcription.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（34/34）

## 2026-03-09 续做补记（前端 API 任务流补线）

### 本次完成
- `frontend/src/api.ts`
  - 新增正式的转写任务类型：
    - `TranscriptionResponse`
    - `TranscriptionJobResponse`
  - 新增长音频任务 API：
    - `createTranscriptionJob(file)`
    - `createTranscriptionJobFromUrl(fileUrl)`
    - `fetchTranscriptionJob(jobId, { refresh })`
- `frontend/src/App.interactions.test.tsx`
  - 补齐上述 API 的 mock 接线，保证前端在接长音频任务流前不会先因测试或类型断掉。

### 当前状态
- 前端 API 层已经具备消费长音频任务流的能力。
- 下一步可以直接把 `TranscriptionPage` 从“同步上传一次拿结果”升级成“支持 async job + 轮询”。

### 验证结果
- 前端测试：
  - `cd frontend && npm run test:run -- --reporter=dot` 通过（19 files / 45 tests）
- 前端构建：
  - `cd frontend && npm run build` 通过

## 2026-03-09 续做补记（本地异步上传状态纠偏）

### 本次完成
- `backend/services/transcription_service.py`
  - 移除了对本地文件异步远端提交的伪造 stub。
  - 现在 `submit_long_transcription_job()` 对本地路径会明确报错：
    - DashScope 真异步要求公网 `file_url`
    - 本地上传不能再假装已经拿到远端任务
- `backend/routers/transcription.py`
  - `POST /api/transcription/jobs` 改为“本地文件已接收 / staged”语义：
    - 返回 `uploaded` 状态
    - 明确提示应改用 `/api/transcription/jobs/from-url` 才能走真异步
- `backend/tests/test_api_smoke.py`
  - 回归更新为匹配上述真实约束

### 当前状态
- 转写链现在更诚实：
  - 本地短音频：同步转写
  - 本地长音频：已接收/待后续对象存储方案
  - URL 长音频：真异步

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_service.py backend/routers/transcription.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（33/33）

### 下一步建议
- 将关键词级别的结构化抽取升级为更稳的“摘要 / 偏好 / 待办 / 约束”提炼器。
- 修复前端 Memory Center 当前仅存本地状态、尚未真正约束请求头的问题。
- 为桌面端补一份记忆功能说明文档，供 `Memory Docs` 菜单直接打开。

## 2026-03-09 续做补记（Web 转写中心接入异步任务流）

### 本次完成
- `frontend/src/pages/TranscriptionPage.tsx`
  - 将转写中心从“单次同步上传”升级为双通道工作台：
    - 本地音频：同步转写
    - 远端 URL：真实异步 job + 自动轮询
  - 页面现在会展示：
    - 本地文件信息
    - 异步任务 `job_id / remote_job_id / status`
    - 转写结果区
    - `memory_saved` 状态提示
  - 保留了 `复制文本 / 导出 TXT / 预留后续动作` 能力
- `frontend/src/components/AudioDropZone.tsx`
  - 增加 `inputLabel` 和 `isProcessing`，便于测试和页面状态控制
- `frontend/src/pages/TranscriptionPage.test.tsx`
  - 新增页面级回归：
    - 本地同步转写
    - URL 异步任务轮询完成
- `frontend/src/App.interactions.test.tsx`
  - 保留 App 级转写入口 smoke test，避免整 App 交互测试被轮询定时器干扰

### 当前状态
- Web 转写中心已经能直接消费现有后端转写链：
  - 本地短音频同步转写
  - URL 长音频异步任务轮询
- 前端已能显示转写结果是否写入 EverMem

### 验证结果
- 前端测试：
  - `cd frontend && npm run test:run -- --reporter=dot` 通过（20 files / 48 tests）
- 前端构建：
  - `cd frontend && npm run build` 通过

### 下一步建议
- 继续把本地长音频接到对象存储/可访问 URL 适配层，避免只能 staged。
- 在转写中心补任务历史列表和失败重试入口。

## 2026-03-09 续做补记（转写任务历史与重试后端）

### 本次完成
- `backend/services/transcription_service.py`
  - 新增 `list_jobs()`：
    - 支持按状态筛选
    - 按 `updated_at / created_at` 倒序返回
  - 新增 `retry_long_transcription_job()`：
    - 仅支持 URL 型异步任务
    - 重试前会清理旧 transcript 文件
    - 会重置 `error / remote_job_id / memory_saved`
- `backend/routers/transcription.py`
  - 新增 `GET /api/transcription/jobs`
    - 支持 `status=completed,failed` 这种逗号分隔筛选
    - 支持 `limit`
  - 新增 `POST /api/transcription/jobs/{job_id}/retry`
    - 供前端历史面板和失败恢复 UI 直接调用
- `backend/tests/test_api_smoke.py`
  - 新增服务层与 API 层回归：
    - 任务列表排序/筛选
    - URL 异步任务重试

### 当前状态
- 转写主链不再只有“创建任务 / 查单个任务”
- 现在已经具备：
  - 任务列表
  - 状态筛选
  - URL 异步任务重试
- 前端后续可以直接做 `Transcription History` 和 `Retry` 按钮，无需再发明后端协议

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_service.py backend/routers/transcription.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（37/37）

### 下一步建议
- 为任务列表补“是否有 transcript / 是否已写入 memory”的快速标识字段。
- 继续推进本地长音频 -> 可访问 URL / 对象存储适配层。

## 2026-03-09 续做补记（本地长音频公开 URL 适配）

### 本次完成
- `backend/services/settings_service.py`
  - 新增 `transcription_settings.public_base_url`
  - 后端配置现在可以显式声明“本地上传转写文件的公开访问基址”
- `backend/services/transcription_service.py`
  - 新增 `published_dir`
  - 新增 `can_publish_local_async()`
  - 新增 `publish_local_job_for_async()`
    - 将本地上传文件复制到公开目录
    - 基于 `public_base_url` 生成 `/public/transcription/...` URL
- `backend/main.py`
  - 新增静态挂载：
    - `/public/transcription`
  - 供公开转写上传文件使用
- `backend/routers/transcription.py`
  - `POST /api/transcription/jobs`
    - 当未配置 `transcription_settings.public_base_url` 时：
      - 继续返回 `uploaded`，保持 staged 语义
    - 当已配置 `public_base_url` 时：
      - 自动发布本地长音频
      - 自动提交远端异步任务
      - 直接返回 `submitted`
- `backend/tests/test_api_smoke.py`
  - 新增回归：
    - 服务层发布本地文件
    - 路由在配置 `public_base_url` 时自动提交本地长音频异步任务

### 当前状态
- 本地长音频链不再永远卡在 staged：
  - 无 `public_base_url`：诚实 staged
  - 有 `public_base_url`：自动发布并提交异步任务
- 后续如果接 OSS / S3 / 自建文件服务，只需要继续沿这条适配层扩展，不用重写转写主链

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/main.py backend/services/transcription_service.py backend/routers/transcription.py backend/services/settings_service.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（39/39）

### 下一步建议
- 把 `public_base_url` 暴露到前端设置页和文档里。
- 继续做 OSS / S3 / 对象存储适配，替代“仅靠静态目录公开”这条过渡方案。

## 2026-03-09 续做补记（前端设置页接入 public_base_url）

### 本次完成
- `frontend/src/api.ts`
  - `AppSettings` 增加 `transcription_settings`
- `frontend/src/hooks/useSettings.ts`
  - 增加 `transcriptionPublicBaseUrl` 状态
  - 读取后端 `transcription_settings.public_base_url`
  - 保存设置时一并提交 `transcription_settings.public_base_url`
- `frontend/src/pages/SettingsPage.tsx`
  - 新增 `Transcription Async Upload` 设置区
  - 允许直接填写 `Public Base URL`
  - 明确说明：
    - 配置后，本地长音频会先发布到 `/public/transcription/*`
    - 然后自动走异步转写
    - 留空则继续 staged
- `frontend/src/App.interactions.test.tsx`
  - 保存设置时新增 `transcription_settings.public_base_url` 断言
- `frontend/src/hooks/useSettings.test.ts`
  - 测试 mock 更新为包含 `transcription_settings`

### 当前状态
- 本地长音频自动异步提交链已经不是“只能后端手改 config.json”
- 用户现在可以直接在 Web 设置页配置 `public_base_url`

### 验证结果
- 前端测试：
  - `cd frontend && npm run test:run -- --reporter=dot` 通过（20 files / 48 tests）
- 前端构建：
  - `cd frontend && npm run build` 通过

### 下一步建议
- 为 `public_base_url` 增加格式校验和保存成功后的提示文案优化。
- 继续推进 OSS / S3 / 对象存储适配，替代静态目录公开方案。

## 2026-03-09 续做补记（转写任务元数据与 transcript 下载）

### 本次完成
- `backend/routers/transcription.py`
  - `TranscriptionJobResponse` 新增：
    - `has_transcript`
    - `transcript_download_url`
    - `source_url`
  - 新增 `GET /api/transcription/jobs/{job_id}/transcript.txt`
    - 直接下载已完成任务的 transcript 文本
- `frontend/src/api.ts`
  - `TranscriptionJobResponse` 类型同步补齐上述字段
- `backend/tests/test_api_smoke.py`
  - 新增 transcript 下载接口回归
  - 钉住 `has_transcript / transcript_download_url / source_url`

### 当前状态
- 转写任务接口现在不只是“返回 transcript 字符串”
- 还具备了历史面板需要的关键元数据：
  - 是否已有 transcript
  - transcript 下载入口
  - 原始 source URL

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/routers/transcription.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（40/40）
- 前端构建：
  - `cd frontend && npm run build` 通过

### 下一步建议
- 让前端转写历史列表直接消费这些元数据，补下载和载入结果按钮。
- 继续推进对象存储适配，减少对静态公开目录的依赖。

## 2026-03-09 续做补记（转写发布适配器抽离）

### 本次完成
- 新增 `backend/services/transcription_publish_adapter.py`
  - 抽出了转写文件发布适配层
  - 当前支持：
    - `upload_mode=static`
    - `upload_mode=disabled/off/none`
  - 对不支持的模式会明确返回 disabled，而不是把逻辑硬编码在转写服务里
- `backend/services/transcription_service.py`
  - 本地长音频发布逻辑改为通过适配器执行
  - `can_publish_local_async()` 和 `publish_local_job_for_async()` 不再自己拼 URL 和拷贝文件
- `backend/services/settings_service.py`
  - `transcription_settings` 新增 `upload_mode`
  - 当前默认值为 `static`
- `backend/tests/test_api_smoke.py`
  - 新增适配器回归：
    - `upload_mode=oss` 这类未支持模式会被显式禁用

### 当前状态
- 本地长音频的“公开发布”已经不是散落在转写服务里的特例
- 后续接 OSS / S3 / MinIO 时，只需要新增 publisher，不用重写主链

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_publish_adapter.py backend/services/transcription_service.py backend/services/settings_service.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（41/41）

### 下一步建议
- 增加真正的 OSS / S3 publisher。
- 将 `upload_mode` 和后续存储配置暴露到前端设置页。

## 2026-03-09 续做补记（S3 转写发布适配）

### 本次完成
- `backend/services/transcription_publish_adapter.py`
  - 新增 `S3TranscriptionPublisher`
  - 采用可选依赖方式接入：
    - 装了 `boto3` 才启用
    - 没装时不会影响当前 `static` 主链
  - 支持配置：
    - `upload_mode=s3`
    - `public_base_url`
    - `s3_bucket`
    - `s3_region`
    - `s3_endpoint_url`
    - `s3_access_key_id`
    - `s3_secret_access_key`
    - `s3_key_prefix`
- `backend/services/settings_service.py`
  - `transcription_settings` 默认模板补齐了上述 S3 字段
- `backend/tests/test_api_smoke.py`
  - 新增两条回归：
    - 未安装 `boto3` 时，`s3` 模式会安全禁用
    - `s3` 模式下会正确调用上传客户端，并返回 `public_base_url/key`

### 当前状态
- 转写发布适配层现在已经不只是“为将来做准备”
- 已经具备两条发布模式：
  - `static`
  - `s3`（可选依赖）

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile backend/services/transcription_publish_adapter.py backend/services/settings_service.py backend/tests/test_api_smoke.py`
- 后端测试：
  - `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` 通过（43/43）

### 下一步建议
- 将 `upload_mode` 和 S3 参数暴露到前端设置页。
- 在 `backend/requirements.txt` 中补充 `boto3` 安装说明或可选依赖说明。

## 2026-03-09 续做补记（前端设置页接入 upload_mode 与 S3 配置）

### 本次完成
- `frontend/src/hooks/useSettings.ts`
  - 新增转写发布相关状态：
    - `transcriptionUploadMode`
    - `transcriptionS3Bucket`
    - `transcriptionS3Region`
    - `transcriptionS3EndpointUrl`
    - `transcriptionS3AccessKeyId`
    - `transcriptionS3SecretAccessKey`
    - `transcriptionS3KeyPrefix`
  - 设置保存时会把这些字段一起提交到 `transcription_settings`
- `frontend/src/pages/SettingsPage.tsx`
  - `Transcription Async Upload` 区块新增：
    - `Upload Mode`
    - `Public Base URL`
    - S3 条件字段表单
- `frontend/src/App.interactions.test.tsx`
  - 保存设置时新增 `upload_mode=s3` 和 S3 参数断言

### 当前状态
- 对象存储链已经不再停留在后端配置层
- 前端设置页现在可以直接配置：
  - `static`
  - `s3`
  - `disabled`

### 验证结果
- 前端测试：
  - `cd frontend && npm run test:run -- --reporter=dot` 通过（20 files / 48 tests）
- 前端构建：
  - `cd frontend && npm run build` 通过

### 下一步建议
- 为 `upload_mode` 增加更友好的说明文档。
- 补 `boto3` 可选依赖说明，并考虑桌面端设置页同步这一组参数。

## 2026-03-09 续做补记（桌面快速上手文档与帮助入口）

### 本次完成
- 新增 `docs/Desktop_Quickstart.md`
  - 覆盖：
    - 推荐桌面入口
    - 首次安装步骤
    - 转写模式说明
    - `upload_mode`
    - `s3` 可选依赖
    - 常见故障排查
- `WEB_PHASE_A_README.md`
  - 补充了桌面 quickstart 文档入口
  - 补充了 `boto3` 可选安装说明
  - 补充了 `Transcription Async Upload` 三种模式说明
- `desktop_requirements.txt`
  - 增加 `boto3` 可选依赖说明注释
- `run_web_desktop.py`
  - 帮助菜单新增：
    - `打开桌面使用说明 (Desktop Guide)`
  - 优先打开 `docs/Desktop_Quickstart.md`

### 当前状态
- 桌面端不再只有“能启动”
- 现在已经有完整的本地使用说明和菜单入口
- 对象存储配置也有明确文档可查

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile run_web_desktop.py`
- 前端构建：
  - `cd frontend && npm run build` 通过

### 下一步建议
- 进入桌面端最终收口：
  - 联调一遍完整使用路径
  - 整理一版“桌面测试版使用清单”

## 2026-03-09 续做补记（桌面预检模式）

### 本次完成
- `run_web_desktop.py`
  - 新增 `--check` 预检模式
  - 现在可以在不开 GUI 的情况下验证：
    - `frontend/dist`
    - `pywebview`
    - desktop docs
    - backend process startup
    - desktop app route readiness
  - 启动链拆成：
    - 启动后端进程
    - 等待健康检查
  - 预检在受限环境下会回退到“进程级判断”，避免误判
- `docs/Desktop_Quickstart.md`
  - 补充 `python run_web_desktop.py --check`
- `WEB_PHASE_A_README.md`
  - 补充桌面预检说明

### 当前状态
- 在当前环境里执行 `python run_web_desktop.py --check`
  - 已确认：
    - `frontend/dist` 存在
    - backend 能启动
    - desktop docs 存在
  - 当前唯一明确缺口是：
    - `pywebview` 未安装

### 验证结果
- Python 语法检查通过：
  - `python3 -m py_compile run_web_desktop.py`
- 预检执行结果：
  - `python3 run_web_desktop.py --check`
  - 当前显示 `pywebview` 缺失，其余核心启动链已通过

### 下一步建议
- 安装 `pywebview` 后，直接拉起一次桌面窗口做最终联调。
