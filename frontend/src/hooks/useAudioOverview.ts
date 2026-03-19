import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createAudioAgentRun,
  type AudioAgentEvent,
  createAudioOverviewPodcast,
  deleteAudioOverviewPodcast,
  type AudioAgentRunDetail,
  type AudioAgentSource,
  type AudioAgentStep,
  executeAudioAgentRun,
  fetchAudioOverviewPodcastAudio,
  getAudioAgentRun,
  getEverMemRuntimeConfig,
  getAudioOverviewPodcast,
  listAudioAgentRunEvents,
  listAudioOverviewPodcasts,
  saveAudioOverviewScript,
  synthesizeAudioAgentRun,
  synthesizeAudioOverviewPodcast,
  updateAudioOverviewPodcast,
  type AudioOverviewPodcast,
  type AudioOverviewScriptLine,
  type VoiceInfo
} from "../api";
import { createInlineTranslator, type UiLanguage } from "../i18n";
import type { FormatErrorMessage } from "../utils/errorFormatting";

type MergeStrategy = "auto" | "pydub" | "ffmpeg" | "concat";
export type AudioOverviewWorkspaceMode = "podcast" | "multi_dialogue";

type Options = {
  voices: VoiceInfo[];
  formatErrorMessage: FormatErrorMessage;
  language?: UiLanguage;
};

export default function useAudioOverview({
  voices,
  formatErrorMessage,
  language = "zh-CN",
}: Options) {
  const t = createInlineTranslator(language);
  const [audioOverviewWorkspaceMode, setAudioOverviewWorkspaceMode] =
    useState<AudioOverviewWorkspaceMode>("podcast");
  const [audioOverviewTopic, setAudioOverviewTopic] = useState(
    t("AI 对个人学习习惯的影响", "How AI affects personal learning habits")
  );
  const [audioOverviewLanguage, setAudioOverviewLanguage] = useState("zh");
  const [audioOverviewProvider, setAudioOverviewProvider] = useState("DashScope");
  const [audioOverviewModel, setAudioOverviewModel] = useState("");
  const [audioOverviewTurnCount, setAudioOverviewTurnCount] = useState(8);
  const [audioOverviewScriptLines, setAudioOverviewScriptLines] = useState<AudioOverviewScriptLine[]>(
    []
  );
  const [audioOverviewPodcastId, setAudioOverviewPodcastId] = useState<number | null>(null);
  const [audioOverviewPodcasts, setAudioOverviewPodcasts] = useState<AudioOverviewPodcast[]>([]);
  const [audioOverviewVoiceA, setAudioOverviewVoiceA] = useState("");
  const [audioOverviewVoiceB, setAudioOverviewVoiceB] = useState("");
  const [audioOverviewSpeakerA, setAudioOverviewSpeakerA] = useState(t("主播 A", "Host A"));
  const [audioOverviewSpeakerB, setAudioOverviewSpeakerB] = useState(t("主播 B", "Host B"));
  const [audioOverviewRate, setAudioOverviewRate] = useState("+0%");
  const [audioOverviewGapMs, setAudioOverviewGapMs] = useState(250);
  const [audioOverviewMergeStrategy, setAudioOverviewMergeStrategy] =
    useState<MergeStrategy>("auto");
  const [audioOverviewBusy, setAudioOverviewBusy] = useState(false);
  const [audioOverviewSaving, setAudioOverviewSaving] = useState(false);
  const [audioOverviewSynthBusy, setAudioOverviewSynthBusy] = useState(false);
  const [audioOverviewListBusy, setAudioOverviewListBusy] = useState(false);
  const [audioOverviewError, setAudioOverviewError] = useState("");
  const [audioOverviewInfo, setAudioOverviewInfo] = useState("");
  const [audioOverviewAudioUrl, setAudioOverviewAudioUrl] = useState("");
  const [audioOverviewAdvancedOpen, setAudioOverviewAdvancedOpen] = useState(false);
  const [synthBarAdvancedOpen, setSynthBarAdvancedOpen] = useState(false);
  const [audioOverviewMenuOpen, setAudioOverviewMenuOpen] = useState(false);
  const [audioOverviewUseMemory, setAudioOverviewUseMemory] = useState(
    () => getEverMemRuntimeConfig().enabled
  );
  const [audioOverviewMemoryConfigured, setAudioOverviewMemoryConfigured] = useState(
    () => getEverMemRuntimeConfig().enabled
  );
  const [audioOverviewMemoriesRetrieved, setAudioOverviewMemoriesRetrieved] = useState(0);
  const [audioOverviewMemorySaved, setAudioOverviewMemorySaved] = useState(false);
  const [audioAgentSourceText, setAudioAgentSourceText] = useState("");
  const [audioAgentSourceUrlsText, setAudioAgentSourceUrlsText] = useState("");
  const [audioAgentGenerationConstraints, setAudioAgentGenerationConstraints] = useState("");
  const [audioAgentRunId, setAudioAgentRunId] = useState<number | null>(null);
  const [audioAgentStatus, setAudioAgentStatus] = useState("");
  const [audioAgentCurrentStep, setAudioAgentCurrentStep] = useState("");
  const [audioAgentSteps, setAudioAgentSteps] = useState<AudioAgentStep[]>([]);
  const [audioAgentSources, setAudioAgentSources] = useState<AudioAgentSource[]>([]);
  const [audioAgentResultProvider, setAudioAgentResultProvider] = useState("");
  const [audioAgentResultModel, setAudioAgentResultModel] = useState("");
  const [audioAgentEvents, setAudioAgentEvents] = useState<AudioAgentEvent[]>([]);
  const [audioAgentErrorMessage, setAudioAgentErrorMessage] = useState("");

  const audioOverviewVoiceOptions = useMemo(() => {
    const localePrefix = audioOverviewLanguage === "en" ? "en-US" : "zh-CN";
    const preferred = voices.filter((item) =>
      item.locale.toLowerCase().startsWith(localePrefix.toLowerCase())
    );
    return preferred.length ? preferred : voices;
  }, [voices, audioOverviewLanguage]);

  useEffect(() => {
    return () => {
      if (audioOverviewAudioUrl.startsWith("blob:")) {
        URL.revokeObjectURL(audioOverviewAudioUrl);
      }
    };
  }, [audioOverviewAudioUrl]);

  useEffect(() => {
    if (!audioOverviewVoiceOptions.length) {
      return;
    }
    const male = audioOverviewVoiceOptions.find((item) =>
      item.gender.toLowerCase().includes("male")
    );
    const female = audioOverviewVoiceOptions.find((item) =>
      item.gender.toLowerCase().includes("female")
    );
    const defaultA = male?.name || audioOverviewVoiceOptions[0].name;
    const defaultB = female?.name || audioOverviewVoiceOptions[0].name;
    const hasA = audioOverviewVoiceOptions.some((item) => item.name === audioOverviewVoiceA);
    const hasB = audioOverviewVoiceOptions.some((item) => item.name === audioOverviewVoiceB);

    if (!hasA) {
      setAudioOverviewVoiceA(defaultA);
    }
    if (!hasB) {
      setAudioOverviewVoiceB(defaultB);
    }
  }, [audioOverviewVoiceA, audioOverviewVoiceB, audioOverviewVoiceOptions]);

  useEffect(() => {
    if (audioOverviewWorkspaceMode === "multi_dialogue") {
      setAudioOverviewSpeakerA((value) => value || t("角色 A", "Speaker A"));
      setAudioOverviewSpeakerB((value) => value || t("角色 B", "Speaker B"));
      return;
    }

    if (audioOverviewLanguage === "en") {
      setAudioOverviewSpeakerA("Host A");
      setAudioOverviewSpeakerB("Host B");
    } else {
      setAudioOverviewSpeakerA(t("主播 A", "Host A"));
      setAudioOverviewSpeakerB(t("主播 B", "Host B"));
    }
  }, [audioOverviewLanguage, audioOverviewWorkspaceMode, t]);

  useEffect(() => {
    void loadAudioOverviewPodcasts();
  }, []);

  function setAudioOverviewAudioBlob(blob: Blob) {
    if (audioOverviewAudioUrl.startsWith("blob:")) {
      URL.revokeObjectURL(audioOverviewAudioUrl);
    }
    setAudioOverviewAudioUrl(URL.createObjectURL(blob));
  }

  function clearAudioOverviewAudio() {
    if (audioOverviewAudioUrl.startsWith("blob:")) {
      URL.revokeObjectURL(audioOverviewAudioUrl);
    }
    setAudioOverviewAudioUrl("");
  }

  function normalizeAudioOverviewScriptLines(lines: AudioOverviewScriptLine[]) {
    return lines
      .map((line) => ({
        role: line.role === "B" ? "B" : "A",
        text: line.text.trim()
      }))
      .filter((line) => line.text.length > 0);
  }

  function resetAudioAgentState() {
    setAudioAgentRunId(null);
    setAudioAgentStatus("");
    setAudioAgentCurrentStep("");
    setAudioAgentSteps([]);
    setAudioAgentSources([]);
    setAudioAgentResultProvider("");
    setAudioAgentResultModel("");
    setAudioAgentEvents([]);
    setAudioAgentErrorMessage("");
  }

  function applyAudioAgentRun(run: AudioAgentRunDetail) {
    setAudioAgentRunId(run.id);
    setAudioAgentStatus(run.status);
    setAudioAgentCurrentStep(run.current_step);
    setAudioAgentSteps(run.steps);
    setAudioAgentSources(run.sources);
    const resultProvider = typeof run.result_payload.provider === "string" ? run.result_payload.provider : "";
    const resultModel = typeof run.result_payload.model === "string" ? run.result_payload.model : "";
    setAudioAgentResultProvider(resultProvider);
    setAudioAgentResultModel(resultModel);
    setAudioAgentErrorMessage(run.error_message || "");
  }

  function applyAudioAgentEvents(events: AudioAgentEvent[]) {
    setAudioAgentEvents(events);
  }

  function buildAgentStepInfo(run: AudioAgentRunDetail) {
    const stepLabels: Record<string, string> = {
      retrieve: t("正在检索资料...", "Retrieving sources..."),
      assemble_evidence: t("正在整理资料...", "Assembling evidence..."),
      generate_script: t("正在生成脚本...", "Generating script..."),
      persist_draft: t("正在保存草稿...", "Persisting draft..."),
      synthesize_audio: t("正在合成音频...", "Synthesizing audio...")
    };
    return stepLabels[run.current_step] || t("Agent 执行中...", "Agent is running...");
  }

  async function waitForAudioAgentRunCompletion(runId: number) {
    const maxAttempts = 120;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const [current, eventData] = await Promise.all([
        getAudioAgentRun(runId),
        listAudioAgentRunEvents(runId, 50)
      ]);
      applyAudioAgentRun(current);
      applyAudioAgentEvents(eventData.events);
      setAudioOverviewInfo(buildAgentStepInfo(current));
      if (current.status === "draft_ready") {
        return current;
      }
      if (current.status === "failed") {
        const message = current.error_message || t("Agent 执行失败。", "Agent execution failed.");
        throw new Error(message);
      }
      await new Promise((resolve) => window.setTimeout(resolve, 800));
    }
    throw new Error(t("Agent 执行超时，请稍后重试。", "Agent execution timed out. Please try again later."));
  }

  async function syncRunBackToPodcast(run: AudioAgentRunDetail) {
    const nextPodcastId =
      typeof run.podcast_id === "number" && run.podcast_id > 0 ? run.podcast_id : null;
    if (nextPodcastId === null) {
      throw new Error(
        t(
          "Agent 已完成执行，但没有生成播客草稿。",
          "The agent finished but did not create a podcast draft."
        )
      );
    }
    const savedPodcast = await getAudioOverviewPodcast(nextPodcastId);
    applyAudioOverviewPodcast(savedPodcast);
    setAudioOverviewScriptLines(normalizeAudioOverviewScriptLines(savedPodcast.script_lines));
    setAudioOverviewLanguage(savedPodcast.language?.toLowerCase().startsWith("en") ? "en" : "zh");
    return nextPodcastId;
  }

  function applyAudioOverviewPodcast(podcast: AudioOverviewPodcast) {
    setAudioOverviewPodcastId(podcast.id);
    setAudioOverviewTopic(podcast.topic);
    setAudioOverviewLanguage(podcast.language?.toLowerCase().startsWith("en") ? "en" : "zh");
    setAudioOverviewScriptLines(podcast.script_lines);
    setAudioOverviewMenuOpen(false);
  }

  async function loadAudioOverviewPodcasts() {
    setAudioOverviewListBusy(true);
    try {
      const data = await listAudioOverviewPodcasts(30);
      setAudioOverviewPodcasts(data.podcasts);
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, t("加载播客列表失败。", "Failed to load the podcast list.")));
    } finally {
      setAudioOverviewListBusy(false);
    }
  }

  async function loadAudioOverviewPodcastById(podcastId: number) {
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    setAudioOverviewMemoriesRetrieved(0);
    setAudioOverviewMemorySaved(false);
    resetAudioAgentState();
    try {
      const podcast = await getAudioOverviewPodcast(podcastId);
      applyAudioOverviewPodcast(podcast);
      if (podcast.audio_path) {
        const blob = await fetchAudioOverviewPodcastAudio(podcastId);
        setAudioOverviewAudioBlob(blob);
      } else {
        clearAudioOverviewAudio();
      }
      setAudioOverviewInfo(t(`已载入播客 #${podcast.id}。`, `Loaded podcast #${podcast.id}.`));
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, t("加载播客详情失败。", "Failed to load podcast details.")));
    }
  }

  async function ensureAudioOverviewPodcastSaved() {
    const topic = audioOverviewTopic.trim();
    const scriptLines = normalizeAudioOverviewScriptLines(audioOverviewScriptLines);
    if (!topic) {
      throw new Error(t("请先输入播客主题。", "Enter a podcast topic first."));
    }
    if (scriptLines.length < 2) {
      throw new Error(t("脚本至少需要 2 条非空台词。", "The script needs at least 2 non-empty lines."));
    }

    if (audioOverviewPodcastId === null) {
      const created = await createAudioOverviewPodcast({
        topic,
        language: audioOverviewLanguage,
        script_lines: scriptLines
      });
      applyAudioOverviewPodcast(created);
      return created.id;
    }

    const updated = await updateAudioOverviewPodcast(audioOverviewPodcastId, {
      topic,
      language: audioOverviewLanguage,
      script_lines: scriptLines
    });
    applyAudioOverviewPodcast(updated);
    return updated.id;
  }

  async function onGenerateScript(event: FormEvent) {
    event.preventDefault();
    const topic = audioOverviewTopic.trim();
    if (!topic) {
      setAudioOverviewError(t("请先输入播客主题。", "Enter a podcast topic first."));
      return;
    }

    setAudioOverviewError("");
    setAudioOverviewInfo("");
    setAudioOverviewBusy(true);
    setAudioOverviewMemoriesRetrieved(0);
    setAudioOverviewMemorySaved(false);
    resetAudioAgentState();
    try {
      const runtimeMemory = getEverMemRuntimeConfig();
      const memoryConfigured = runtimeMemory.enabled;
      const shouldUseMemory = audioOverviewUseMemory && memoryConfigured;
      setAudioOverviewMemoryConfigured(memoryConfigured);
      setAudioOverviewInfo(
        t("Agent 正在检索资料并生成脚本...", "The agent is retrieving context and generating the script...")
      );

      const run = await createAudioAgentRun({
        topic,
        language: audioOverviewLanguage,
        provider: audioOverviewProvider,
        model: audioOverviewModel.trim() || undefined,
        use_memory: shouldUseMemory,
        source_text: audioAgentSourceText.trim() || undefined,
        source_urls: audioAgentSourceUrlsText
          .split(/\r?\n/)
          .map((item) => item.trim())
          .filter((item) => item.length > 0),
        generation_constraints: audioAgentGenerationConstraints.trim() || undefined,
        turn_count: audioOverviewTurnCount,
        auto_execute: true
      });
      applyAudioAgentRun(run);
      const completedRun =
        run.status === "draft_ready" ? run : await waitForAudioAgentRunCompletion(run.id);
      clearAudioOverviewAudio();
      const nextPodcastId = await syncRunBackToPodcast(completedRun);
      setAudioOverviewInfo(
        t(
          `Agent 已完成检索与写稿，并保存为播客 #${nextPodcastId}。`,
          `The agent finished retrieval and drafting, and saved podcast #${nextPodcastId}.`
        )
      );

      await loadAudioOverviewPodcasts();
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, "生成脚本失败。"));
    } finally {
      setAudioOverviewBusy(false);
    }
  }

  async function onRetryAgentRun() {
    if (audioAgentRunId === null) {
      setAudioOverviewError(t("当前没有可重试的 Agent 任务。", "There is no agent run to retry."));
      return;
    }
    setAudioOverviewError("");
    setAudioOverviewInfo(t("正在重试 Agent 任务...", "Retrying the agent run..."));
    setAudioOverviewBusy(true);
    try {
      const scheduled = await executeAudioAgentRun(audioAgentRunId);
      applyAudioAgentRun(scheduled);
      const completedRun =
        scheduled.status === "draft_ready" || scheduled.status === "completed"
          ? scheduled
          : await waitForAudioAgentRunCompletion(audioAgentRunId);
      const nextPodcastId = await syncRunBackToPodcast(completedRun);
      clearAudioOverviewAudio();
      await loadAudioOverviewPodcasts();
      setAudioOverviewInfo(
        t(
          `Agent 重试完成，已更新播客 #${nextPodcastId}。`,
          `Agent retry completed and updated podcast #${nextPodcastId}.`
        )
      );
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, t("重试 Agent 任务失败。", "Failed to retry the agent run.")));
    } finally {
      setAudioOverviewBusy(false);
    }
  }

  async function onSaveScript() {
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    setAudioOverviewSaving(true);
    try {
      const podcastId = await ensureAudioOverviewPodcastSaved();
      const scriptLines = normalizeAudioOverviewScriptLines(audioOverviewScriptLines);
      const updated = await saveAudioOverviewScript(podcastId, scriptLines);
      applyAudioOverviewPodcast(updated);
      await loadAudioOverviewPodcasts();
      setAudioOverviewInfo(`播客 #${podcastId} 的脚本已保存。`);
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, "保存脚本失败。"));
    } finally {
      setAudioOverviewSaving(false);
    }
  }

  async function onSynthesize() {
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    setAudioOverviewSynthBusy(true);
    try {
      const payload = {
        voice_a: audioOverviewVoiceA || undefined,
        voice_b: audioOverviewVoiceB || undefined,
        rate: audioOverviewRate || "+0%",
        language: audioOverviewLanguage,
        gap_ms: audioOverviewGapMs,
        merge_strategy: audioOverviewMergeStrategy
      } as const;
      let podcastId = await ensureAudioOverviewPodcastSaved();
      let result:
        | {
          line_count: number;
          merge_strategy: string;
          gap_ms_applied: number;
          cache_hits: number;
        }
        | null = null;

      if (audioAgentRunId !== null) {
        setAudioOverviewInfo(
          t("Agent 正在合成音频...", "The agent is synthesizing audio...")
        );
        const run = await synthesizeAudioAgentRun(audioAgentRunId, payload);
        applyAudioAgentRun(run);
        const eventData = await listAudioAgentRunEvents(audioAgentRunId, 50);
        applyAudioAgentEvents(eventData.events);
        podcastId =
          typeof run.podcast_id === "number" && run.podcast_id > 0 ? run.podcast_id : podcastId;
        result = {
          line_count:
            typeof run.result_payload.line_count === "number"
              ? run.result_payload.line_count
              : audioOverviewScriptLines.length,
          merge_strategy:
            typeof run.result_payload.merge_strategy === "string"
              ? run.result_payload.merge_strategy
              : audioOverviewMergeStrategy,
          gap_ms_applied:
            typeof run.result_payload.gap_ms_applied === "number"
              ? run.result_payload.gap_ms_applied
              : 0,
          cache_hits:
            typeof run.result_payload.cache_hits === "number"
              ? run.result_payload.cache_hits
              : 0
        };
      } else {
        const synthResult = await synthesizeAudioOverviewPodcast(podcastId, payload);
        result = {
          line_count: synthResult.line_count,
          merge_strategy: synthResult.merge_strategy,
          gap_ms_applied: synthResult.gap_ms_applied,
          cache_hits: synthResult.cache_hits
        };
      }
      if (podcastId === null) {
        throw new Error(t("当前没有可合成的播客草稿。", "There is no podcast draft to synthesize."));
      }
      const blob = await fetchAudioOverviewPodcastAudio(podcastId);
      setAudioOverviewAudioBlob(blob);
      await loadAudioOverviewPodcasts();
      setAudioOverviewInfo(
        `音频已合成（${result.line_count} 条台词，策略 ${result.merge_strategy}，停顿 ${result.gap_ms_applied}ms，命中缓存 ${result.cache_hits} 次）。`
      );
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, "合成音频失败。"));
    } finally {
      setAudioOverviewSynthBusy(false);
    }
  }

  async function onDeleteCurrent() {
    if (audioOverviewPodcastId === null) {
      setAudioOverviewError("当前没有可删除的播客。");
      return;
    }
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    try {
      await deleteAudioOverviewPodcast(audioOverviewPodcastId);
      setAudioOverviewPodcastId(null);
      setAudioOverviewTopic("");
      setAudioOverviewScriptLines([]);
      setAudioAgentSourceText("");
      setAudioAgentSourceUrlsText("");
      setAudioAgentGenerationConstraints("");
      resetAudioAgentState();
      clearAudioOverviewAudio();
      setAudioOverviewMenuOpen(false);
      await loadAudioOverviewPodcasts();
      setAudioOverviewInfo("当前播客已删除。");
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, "删除播客失败。"));
    }
  }

  function onNewDraft() {
    setAudioOverviewPodcastId(null);
    setAudioOverviewTopic("");
    setAudioOverviewScriptLines([]);
    setAudioOverviewError("");
    setAudioOverviewInfo("已新建草稿。");
    setAudioOverviewAdvancedOpen(false);
    setSynthBarAdvancedOpen(false);
    setAudioOverviewMenuOpen(false);
    setAudioOverviewMemoriesRetrieved(0);
    setAudioOverviewMemorySaved(false);
    setAudioAgentSourceText("");
    setAudioAgentSourceUrlsText("");
    setAudioAgentGenerationConstraints("");
    resetAudioAgentState();
    clearAudioOverviewAudio();
  }

  function onLineRoleChange(index: number, role: string) {
    setAudioOverviewScriptLines((prev) =>
      prev.map((line, idx) =>
        idx === index ? { ...line, role: role === "B" ? "B" : "A" } : line
      )
    );
  }

  function onLineTextChange(index: number, text: string) {
    setAudioOverviewScriptLines((prev) =>
      prev.map((line, idx) => (idx === index ? { ...line, text } : line))
    );
  }

  function onAddLine() {
    const lastRole = audioOverviewScriptLines.length
      ? audioOverviewScriptLines[audioOverviewScriptLines.length - 1].role
      : "B";
    setAudioOverviewScriptLines((prev) => [
      ...prev,
      { role: lastRole === "A" ? "B" : "A", text: "" }
    ]);
  }

  function onRemoveLine(index: number) {
    setAudioOverviewScriptLines((prev) => prev.filter((_, idx) => idx !== index));
  }

  function buildAudioOverviewScriptText() {
    const roleMap: Record<string, string> = {
      A: audioOverviewSpeakerA.trim() || "角色 A",
      B: audioOverviewSpeakerB.trim() || "角色 B"
    };
    return normalizeAudioOverviewScriptLines(audioOverviewScriptLines)
      .map((line, index) => `${index + 1}. ${roleMap[line.role]}：${line.text}`)
      .join("\n\n");
  }

  async function onCopyScript() {
    const scriptText = buildAudioOverviewScriptText();
    if (!scriptText) {
      setAudioOverviewError("当前还没有可复制的脚本。");
      return;
    }
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("剪贴板接口不可用");
      }
      await navigator.clipboard.writeText(scriptText);
      setAudioOverviewError("");
      setAudioOverviewInfo("脚本已复制到剪贴板。");
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, "复制脚本失败。"));
    }
  }

  function onExportScript() {
    const scriptText = buildAudioOverviewScriptText();
    if (!scriptText) {
      setAudioOverviewError("当前还没有可导出的脚本。");
      return;
    }
    const safeTopic = (audioOverviewTopic.trim() || "播客脚本")
      .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
      .slice(0, 48);
    const blob = new Blob([scriptText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${safeTopic || "播客脚本"}.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setAudioOverviewError("");
    setAudioOverviewInfo("脚本已导出为文本文件。");
  }

  function onTurnCountChange(value: string) {
    setAudioOverviewTurnCount(Number.isNaN(Number(value)) ? 8 : Number(value));
  }

  function onGapMsChange(value: string) {
    setAudioOverviewGapMs(Number.isNaN(Number(value)) ? 0 : Number(value));
  }

  const currentAudioOverviewLabel =
    audioOverviewPodcastId !== null
      ? `${audioOverviewWorkspaceMode === "podcast" ? "节目" : "多人对话"} #${audioOverviewPodcastId}`
      : "未保存草稿";

  const audioOverviewWorkspaceTitle =
    audioOverviewWorkspaceMode === "podcast" ? "播客工作台" : "多人对话工作台";

  const audioOverviewWorkspaceDescription =
    audioOverviewWorkspaceMode === "podcast"
      ? "围绕一个主题生成双人节目脚本，并进一步合成为完整音频。"
      : "围绕一个议题生成多轮人物对话脚本，适合演示、角色讨论和场景化内容。";

  return {
    audioOverviewWorkspaceMode,
    audioOverviewWorkspaceTitle,
    audioOverviewWorkspaceDescription,
    audioOverviewBusy,
    audioOverviewSaving,
    audioOverviewSynthBusy,
    audioOverviewListBusy,
    audioOverviewError,
    audioOverviewInfo,
    audioOverviewProvider,
    audioOverviewModel,
    audioOverviewLanguage,
    audioOverviewPodcastId,
    audioOverviewMergeStrategy,
    audioOverviewTopic,
    audioOverviewTurnCount,
    audioOverviewAdvancedOpen,
    audioOverviewMenuOpen,
    synthBarAdvancedOpen,
    audioOverviewUseMemory,
    audioOverviewMemoryConfigured,
    audioOverviewMemoriesRetrieved,
    audioOverviewMemorySaved,
    audioAgentSourceText,
    audioAgentSourceUrlsText,
    audioAgentGenerationConstraints,
    audioAgentRunId,
    audioAgentStatus,
    audioAgentCurrentStep,
    audioAgentSteps,
    audioAgentSources,
    audioAgentResultProvider,
    audioAgentResultModel,
    audioAgentEvents,
    audioAgentErrorMessage,
    audioAgentCanRetry: audioAgentRunId !== null && audioAgentStatus === "failed",
    audioOverviewScriptLines,
    audioOverviewVoiceOptions,
    audioOverviewVoiceA,
    audioOverviewVoiceB,
    audioOverviewSpeakerA,
    audioOverviewSpeakerB,
    audioOverviewRate,
    audioOverviewGapMs,
    audioOverviewAudioUrl,
    audioOverviewPodcasts,
    currentAudioOverviewLabel,
    onGenerateScript,
    onNewDraft,
    onWorkspaceModeChange: setAudioOverviewWorkspaceMode,
    onToggleMenu: () => setAudioOverviewMenuOpen((value) => !value),
    onDeleteCurrent,
    onTopicChange: setAudioOverviewTopic,
    onToggleAdvanced: () => setAudioOverviewAdvancedOpen((value) => !value),
    onLanguageChange: setAudioOverviewLanguage,
    onProviderChange: setAudioOverviewProvider,
    onModelChange: setAudioOverviewModel,
    onUseMemoryChange: setAudioOverviewUseMemory,
    onSourceTextChange: setAudioAgentSourceText,
    onSourceUrlsTextChange: setAudioAgentSourceUrlsText,
    onGenerationConstraintsChange: setAudioAgentGenerationConstraints,
    onTurnCountChange,
    onSaveScript,
    onCopyScript,
    onExportScript,
    onLineRoleChange,
    onRemoveLine,
    onLineTextChange,
    onAddLine,
    onVoiceAChange: setAudioOverviewVoiceA,
    onVoiceBChange: setAudioOverviewVoiceB,
    onSpeakerAChange: setAudioOverviewSpeakerA,
    onSpeakerBChange: setAudioOverviewSpeakerB,
    onToggleSynthAdvanced: () => setSynthBarAdvancedOpen((value) => !value),
    onSynthesize,
    onRateChange: setAudioOverviewRate,
    onGapMsChange,
    onMergeStrategyChange: setAudioOverviewMergeStrategy,
    onRefreshList: loadAudioOverviewPodcasts,
    onLoadPodcast: loadAudioOverviewPodcastById,
    onRetryAgentRun
  };
}

export type UseAudioOverviewResult = ReturnType<typeof useAudioOverview>;
