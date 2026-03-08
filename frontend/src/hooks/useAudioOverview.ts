import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createAudioOverviewPodcast,
  deleteAudioOverviewPodcast,
  fetchAudioOverviewPodcastAudio,
  generateAudioOverviewScript,
  getAudioOverviewPodcast,
  listAudioOverviewPodcasts,
  saveAudioOverviewScript,
  synthesizeAudioOverviewPodcast,
  updateAudioOverviewPodcast,
  type AudioOverviewPodcast,
  type AudioOverviewScriptLine,
  type VoiceInfo
} from "../api";
import type { FormatErrorMessage } from "../utils/errorFormatting";

type MergeStrategy = "auto" | "pydub" | "ffmpeg" | "concat";

type Options = {
  voices: VoiceInfo[];
  formatErrorMessage: FormatErrorMessage;
};

export default function useAudioOverview({ voices, formatErrorMessage }: Options) {
  const [audioOverviewTopic, setAudioOverviewTopic] = useState("AI 对个人学习习惯的影响");
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
      setAudioOverviewError(formatErrorMessage(err, "加载播客列表失败。"));
    } finally {
      setAudioOverviewListBusy(false);
    }
  }

  async function loadAudioOverviewPodcastById(podcastId: number) {
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    try {
      const podcast = await getAudioOverviewPodcast(podcastId);
      applyAudioOverviewPodcast(podcast);
      if (podcast.audio_path) {
        const blob = await fetchAudioOverviewPodcastAudio(podcastId);
        setAudioOverviewAudioBlob(blob);
      } else {
        clearAudioOverviewAudio();
      }
      setAudioOverviewInfo(`已载入播客 #${podcast.id}。`);
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, "加载播客详情失败。"));
    }
  }

  async function ensureAudioOverviewPodcastSaved() {
    const topic = audioOverviewTopic.trim();
    const scriptLines = normalizeAudioOverviewScriptLines(audioOverviewScriptLines);
    if (!topic) {
      throw new Error("请先输入播客主题。");
    }
    if (scriptLines.length < 2) {
      throw new Error("脚本至少需要 2 条非空台词。");
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
      setAudioOverviewError("请先输入播客主题。");
      return;
    }

    setAudioOverviewError("");
    setAudioOverviewInfo("");
    setAudioOverviewBusy(true);
    try {
      const generated = await generateAudioOverviewScript({
        topic,
        language: audioOverviewLanguage,
        turn_count: audioOverviewTurnCount,
        provider: audioOverviewProvider,
        model: audioOverviewModel.trim() || undefined
      });
      const normalized = normalizeAudioOverviewScriptLines(generated.script_lines);
      setAudioOverviewLanguage(generated.language);
      setAudioOverviewScriptLines(normalized);
      clearAudioOverviewAudio();

      if (audioOverviewPodcastId === null) {
        const created = await createAudioOverviewPodcast({
          topic,
          language: generated.language,
          script_lines: normalized
        });
        applyAudioOverviewPodcast(created);
        setAudioOverviewInfo(`脚本已生成，并保存为播客 #${created.id}。`);
      } else {
        const updated = await updateAudioOverviewPodcast(audioOverviewPodcastId, {
          topic,
          language: generated.language,
          script_lines: normalized
        });
        applyAudioOverviewPodcast(updated);
        setAudioOverviewInfo(`播客 #${updated.id} 的脚本已重新生成。`);
      }

      await loadAudioOverviewPodcasts();
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, "生成脚本失败。"));
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
      const podcastId = await ensureAudioOverviewPodcastSaved();
      const result = await synthesizeAudioOverviewPodcast(podcastId, {
        voice_a: audioOverviewVoiceA || undefined,
        voice_b: audioOverviewVoiceB || undefined,
        rate: audioOverviewRate || "+0%",
        language: audioOverviewLanguage,
        gap_ms: audioOverviewGapMs,
        merge_strategy: audioOverviewMergeStrategy
      });
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
    return normalizeAudioOverviewScriptLines(audioOverviewScriptLines)
      .map((line, index) => `${index + 1}. 主播 ${line.role}：${line.text}`)
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
    audioOverviewPodcastId !== null ? `播客 #${audioOverviewPodcastId}` : "未保存草稿";

  return {
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
    audioOverviewScriptLines,
    audioOverviewVoiceOptions,
    audioOverviewVoiceA,
    audioOverviewVoiceB,
    audioOverviewRate,
    audioOverviewGapMs,
    audioOverviewAudioUrl,
    audioOverviewPodcasts,
    currentAudioOverviewLabel,
    onGenerateScript,
    onNewDraft,
    onToggleMenu: () => setAudioOverviewMenuOpen((value) => !value),
    onDeleteCurrent,
    onTopicChange: setAudioOverviewTopic,
    onToggleAdvanced: () => setAudioOverviewAdvancedOpen((value) => !value),
    onLanguageChange: setAudioOverviewLanguage,
    onProviderChange: setAudioOverviewProvider,
    onModelChange: setAudioOverviewModel,
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
    onToggleSynthAdvanced: () => setSynthBarAdvancedOpen((value) => !value),
    onSynthesize,
    onRateChange: setAudioOverviewRate,
    onGapMsChange,
    onMergeStrategyChange: setAudioOverviewMergeStrategy,
    onRefreshList: loadAudioOverviewPodcasts,
    onLoadPodcast: loadAudioOverviewPodcastById
  };
}

export type UseAudioOverviewResult = ReturnType<typeof useAudioOverview>;
