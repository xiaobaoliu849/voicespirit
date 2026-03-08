import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchSpeakAudio, fetchVoices, type VoiceInfo } from "../api";
import type { FormatErrorMessage } from "../utils/errorFormatting";

type Options = {
  defaultText: string;
  formatErrorMessage: FormatErrorMessage;
};

export default function useTts({ defaultText, formatErrorMessage }: Options) {
  const [text, setText] = useState(defaultText);
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [voice, setVoice] = useState("");
  const [rate, setRate] = useState("+0%");
  const [audioUrl, setAudioUrl] = useState("");
  const [loadingVoices, setLoadingVoices] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [ttsError, setTtsError] = useState("");

  useEffect(() => {
    let disposed = false;

    async function loadVoices() {
      try {
        setLoadingVoices(true);
        const data = await fetchVoices();
        if (disposed) {
          return;
        }
        setVoices(data.voices);
        if (data.voices.length > 0) {
          setVoice(data.voices[0].name);
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
  }, [formatErrorMessage]);

  const voiceOptions = useMemo(() => {
    return voices.map((item) => ({
      value: item.name,
      label: `${item.short_name || item.name} (${item.locale})`
    }));
  }, [voices]);

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
    if (!text.trim()) {
      setTtsError("请输入要合成的文本。");
      return;
    }
    setGenerating(true);
    try {
      const blob = await fetchSpeakAudio({
        text: text.trim(),
        voice: voice || undefined,
        rate
      });
      if (audioUrl.startsWith("blob:")) {
        URL.revokeObjectURL(audioUrl);
      }
      setAudioUrl(URL.createObjectURL(blob));
    } catch (err) {
      setTtsError(formatErrorMessage(err, "语音合成请求失败。"));
    } finally {
      setGenerating(false);
    }
  }

  return {
    text,
    voices,
    voice,
    rate,
    audioUrl,
    loadingVoices,
    generating,
    ttsError,
    voiceOptions,
    onSubmit,
    onTextChange: setText,
    onVoiceChange: setVoice,
    onRateChange: setRate
  };
}

export type UseTtsResult = ReturnType<typeof useTts>;
