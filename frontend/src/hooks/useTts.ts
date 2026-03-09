import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchSpeakAudio, fetchVoices, type TtsEngine, type VoiceInfo } from "../api";
import type { FormatErrorMessage } from "../utils/errorFormatting";

export type TtsWorkspaceMode = "text" | "dialogue" | "pdf";

const TTS_ENGINE_OPTIONS: Array<{ value: TtsEngine; label: string; hint: string }> = [
  { value: "edge", label: "Edge TTS", hint: "系统级稳定合成，适合基础朗读。" },
  { value: "qwen_flash", label: "Qwen TTS Flash", hint: "阿里云 Qwen 音色，更适合中文与角色感。" },
  { value: "minimax", label: "MiniMax TTS", hint: "MiniMax 多风格音色，适合配音与角色化朗读。" },
];

type Options = {
  defaultText: string;
  formatErrorMessage: FormatErrorMessage;
};

export default function useTts({ defaultText, formatErrorMessage }: Options) {
  const [ttsMode, setTtsMode] = useState<TtsWorkspaceMode>("text");
  const [ttsEngine, setTtsEngine] = useState<TtsEngine>("edge");
  const [text, setText] = useState(defaultText);
  const [dialogueText, setDialogueText] = useState("");
  const [pdfText, setPdfText] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [voice, setVoice] = useState("");
  const [rate, setRate] = useState("+0%");
  const [audioUrl, setAudioUrl] = useState("");
  const [loadingVoices, setLoadingVoices] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [ttsError, setTtsError] = useState("");
  const [ttsInfo, setTtsInfo] = useState("");

  useEffect(() => {
    let disposed = false;

    async function loadVoices() {
      try {
        setLoadingVoices(true);
        const data = await fetchVoices(undefined, ttsEngine);
        if (disposed) {
          return;
        }
        setVoices(data.voices);
        if (data.voices.length > 0) {
          setVoice(data.voices[0].name);
        } else {
          setVoice("");
        }
      } catch (err) {
        if (!disposed) {
          setTtsError(formatErrorMessage(err, "未知错误"));
        }
      } finally {
        if (!disposed) {
          setLoadingVoices(false);
        }
      }
    }

    void loadVoices();
    return () => {
      disposed = true;
    };
  }, [formatErrorMessage, ttsEngine]);

  const voiceOptions = useMemo(() => {
    return voices.map((item) => ({
      value: item.name,
      label: `${item.short_name || item.name} (${item.locale})`
    }));
  }, [voices]);

  const activeSourceText = useMemo(() => {
    if (ttsMode === "dialogue") {
      return dialogueText.trim();
    }
    if (ttsMode === "pdf") {
      return pdfText.trim();
    }
    return text.trim();
  }, [dialogueText, pdfText, text, ttsMode]);

  useEffect(() => {
    return () => {
      if (audioUrl.startsWith("blob:")) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTtsError("");
    setTtsInfo("");
    if (!activeSourceText) {
      if (ttsMode === "dialogue") {
        setTtsError("请输入要合成的对话脚本。");
        return;
      }
      if (ttsMode === "pdf") {
        setTtsError("请先选择 PDF 并准备可朗读文本。");
        return;
      }
      setTtsError("请输入要合成的文本。");
      return;
    }
    setGenerating(true);
    try {
      const result = await fetchSpeakAudio({
        text: activeSourceText,
        voice: voice || undefined,
        rate,
        engine: ttsEngine,
      });
      if (audioUrl.startsWith("blob:")) {
        URL.revokeObjectURL(audioUrl);
      }
      setAudioUrl(URL.createObjectURL(result.blob));
      if (result.memorySaved) {
        setTtsInfo("已将本次语音生成偏好写入长期记忆。");
      }
    } catch (err) {
      setTtsError(formatErrorMessage(err, "语音合成请求失败。"));
    } finally {
      setGenerating(false);
    }
  }

  function onTtsModeChange(mode: TtsWorkspaceMode) {
    setTtsMode(mode);
    setTtsError("");
    setTtsInfo("");
  }

  function onEngineChange(engine: TtsEngine) {
    setTtsEngine(engine);
    setTtsError("");
    setTtsInfo("");
    if (audioUrl.startsWith("blob:")) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl("");
  }

  function onTextChange(value: string) {
    setText(value);
    if (ttsMode === "text" && ttsError) {
      setTtsError("");
    }
  }

  function onDialogueTextChange(value: string) {
    setDialogueText(value);
    if (ttsMode === "dialogue" && ttsError) {
      setTtsError("");
    }
  }

  function onPdfFileChange(file: File | null) {
    setPdfFile(file);
    if (!file) {
      setPdfText("");
    }
    if (ttsMode === "pdf" && ttsError) {
      setTtsError("");
    }
  }

  function onPdfTextChange(value: string) {
    setPdfText(value);
    if (ttsMode === "pdf" && ttsError) {
      setTtsError("");
    }
  }

  return {
    ttsMode,
    ttsEngine,
    text,
    dialogueText,
    pdfText,
    pdfFile,
    voices,
    voice,
    rate,
    audioUrl,
    loadingVoices,
    generating,
    ttsError,
    ttsInfo,
    engineOptions: TTS_ENGINE_OPTIONS,
    voiceOptions,
    activeSourceText,
    onSubmit,
    onTtsModeChange,
    onEngineChange,
    onTextChange,
    onDialogueTextChange,
    onPdfFileChange,
    onPdfTextChange,
    onVoiceChange: setVoice,
    onRateChange: setRate
  };
}

export type UseTtsResult = ReturnType<typeof useTts>;
