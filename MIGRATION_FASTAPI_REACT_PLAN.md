# VoiceSpirit 去 PySide6 改造检查与迁移方案

更新时间：2026-03-04（晚）

## 1. 备份结果

已完成可用备份：

- 全量备份（可恢复整个当前项目）
  - `/tmp/voicespirit_backups/voicespirit_full_20260304_002901.tar`
  - 校验：`tar -tf ...` 通过
- 源码精简备份（不含大体积构建产物）
  - `/tmp/voicespirit_backups/voicespirit_source_20260304_002634.tar.gz`
  - 校验：`tar -tzf ...` 通过

说明：
- `/tmp/voicespirit_backups/voicespirit_20260304_002329.tar.gz` 为中断产生的损坏包（`Unexpected EOF`），不要使用。

## 2. 参考项目检查结论（D:\\Projects\\vocabbook-modern）

不是 “fastpython”，实际是 **FastAPI**。

技术栈：

- 后端：FastAPI + Uvicorn
  - 入口：`/mnt/d/Projects/vocabbook-modern/backend/main.py`
  - 依赖：`/mnt/d/Projects/vocabbook-modern/backend/requirements.txt`
- 前端：React + TypeScript + Vite
  - 入口：`/mnt/d/Projects/vocabbook-modern/frontend/src/main.tsx`
  - 构建：`/mnt/d/Projects/vocabbook-modern/frontend/package.json`
- 桌面壳：Electron
  - 主进程：`/mnt/d/Projects/vocabbook-modern/electron/main.js`
  - 启动后端 + 加载前端 URL 的模式已可复用

## 3. VoiceSpirit 当前状态

当前项目核心能力可迁移，但实现高度绑定 PySide6（Signals/QThread/UI 组件）：

- UI 页面：`app/ui/pages/*`
- API 调用与实时会话：`app/core/api_client.py`
- TTS 逻辑：`utils/tts_handler.py`
- 配置/数据库：`app/core/config.py`, `app/core/database.py`

迁移原则：

- 保留业务能力（Chat/Translate/TTS/Voice Design/Voice Clone/Audio Overview）
- 去掉 PySide6 依赖，改为 HTTP API + Web 前端状态管理

## 4. 目标架构（建议）

- `backend/`（Python FastAPI）
  - `main.py`：应用入口与生命周期
  - `routers/`：`chat.py`, `translate.py`, `tts.py`, `voices.py`, `audio_overview.py`, `settings.py`
  - `services/`：从 `api_client.py` 与 `tts_handler.py` 中抽纯业务逻辑
  - `models/`：Pydantic 请求/响应模型
- `frontend/`（React + Vite + TS）
  - 页面映射当前功能模块
  - `src/utils/api.ts` 风格统一 API 封装
- `electron/`（可选）
  - 桌面壳，仅负责窗口/托盘/全局快捷键/进程管理

## 5. 分阶段落地

### Phase A（先跑通最小可用）

1. 建立 FastAPI 骨架与健康检查接口。
2. 先迁移 `TTS speak` 与 `voice list`（最容易独立）。
3. 前端起 React 页面，仅接这两个接口。

### Phase B（核心功能迁移）

1. 迁移 Chat/Translate API（含流式输出）。
2. 迁移 Voice Design/Clone 接口（创建/列表/删除）。
3. 迁移配置读写接口（替代桌面设置页直读本地配置）。

### Phase C（桌面能力恢复）

1. 用 Electron 恢复系统托盘、全局热键、窗口行为。
2. 打包发布链路替换 PyInstaller。

## 6. 最新进展

- Phase A 已落地：`TTS voices/speak` + React 最小页面可跑通。
- Phase B 已推进（前两步完成）：
  - 新增 `POST /api/chat/completions`
  - 新增 `POST /api/chat/completions/stream`（SSE）
  - 新增 `POST /api/translate/`
  - 前端新增 `Chat`、`Translate` 面板并完成 Chat 逐字流式渲染。
- Phase B 第三步已完成（Voice APIs 基础迁移）：
  - 新增 `POST /api/voices/design`
  - 新增 `POST /api/voices/clone`
  - 新增 `GET /api/voices/`（按 `voice_type` 列表）
  - 新增 `DELETE /api/voices/{voice_name}`
  - 前端新增 `Voice Design`、`Voice Clone` 联调页（创建/列表/删除）
- Phase B 第四步已完成（Settings API 基础迁移）：
  - 新增 `GET /api/settings/`
  - 新增 `PUT /api/settings/`
  - 前端新增 `Settings` 联调页（Provider 配置读取/保存）
- Phase B 第五步已完成（Audio Overview 基础迁移）：
  - 新增 `/api/audio-overview/podcasts*` 系列接口（项目/脚本 CRUD）
  - 新增 `backend/services/audio_overview_service.py`
  - 新增后端 smoke tests（9 个接口用例）
- Phase B 第六步已完成（Audio Overview 业务接口迁移）：
  - 新增 `POST /api/audio-overview/scripts/generate`（LLM 生成播客脚本）
  - 新增 `POST /api/audio-overview/podcasts/{podcast_id}/synthesize`（双声线逐句合成）
  - 新增 `GET /api/audio-overview/podcasts/{podcast_id}/audio`（音频下载/预览）
  - 前端新增 `Audio Overview` 面板（脚本生成、编辑保存、合成、回放、历史加载）
- Phase B 第七步已完成（音频合并增强）：
  - 合成接口新增 `gap_ms` 与 `merge_strategy(auto|pydub|ffmpeg|concat)`
  - 合并策略自动回退：`pydub -> ffmpeg -> concat`
  - 返回值增加 `merge_strategy` 与 `gap_ms_applied`
  - 合并/分段失败返回结构化错误：`code/message/meta`
  - 前端 Audio Overview 合成面板新增间隔与策略配置

## 7. 下一步建议

1. 为合并失败场景增加后端日志落盘与可观测错误码（便于线上排障）。
2. 为 API 增加鉴权/权限控制策略（如后续上云场景）。
3. 完善 OpenAPI 文档与请求参数校验规则。
