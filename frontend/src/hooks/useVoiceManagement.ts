import { FormEvent, useEffect, useState } from "react";
import {
  createVoiceClone,
  createVoiceDesign,
  deleteCustomVoice,
  listCustomVoices,
  type CustomVoice,
  type VoiceType
} from "../api";
import type { FormatErrorMessage } from "../utils/errorFormatting";

type Options = {
  formatErrorMessage: FormatErrorMessage;
};

const DESIGN_PROMPT_PRESETS = [
  {
    id: "warm_narrator",
    label: "温暖旁白",
    prompt: "温暖、亲和、清晰，适合知识讲解、播客开场和故事叙述。"
  },
  {
    id: "professional_host",
    label: "专业主持",
    prompt: "专业、稳重、节奏清楚，适合访谈主持、品牌介绍和正式播报。"
  },
  {
    id: "youthful_social",
    label: "轻快社媒",
    prompt: "年轻、自然、轻快，适合短视频口播、产品安利和生活方式内容。"
  }
];

const CLONE_ACCEPTED_TYPES = [
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/x-wav",
  "audio/flac",
  "audio/x-flac",
  "audio/mp4",
  "audio/aac",
  "audio/ogg",
  "audio/webm"
];

const MAX_CLONE_FILE_BYTES = 20 * 1024 * 1024;

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function useVoiceManagement({ formatErrorMessage }: Options) {
  const [designPrompt, setDesignPrompt] = useState(
    "温柔、清晰、语速适中，适合讲解和对话。"
  );
  const [designPreviewText, setDesignPreviewText] = useState(
    "你好，我是 VoiceSpirit 新创建的音色，很高兴为你服务。"
  );
  const [designName, setDesignName] = useState("voice_design_demo");
  const [designLanguage, setDesignLanguage] = useState("zh");
  const [designBusy, setDesignBusy] = useState(false);
  const [designListBusy, setDesignListBusy] = useState(false);
  const [designError, setDesignError] = useState("");
  const [designInfo, setDesignInfo] = useState("");
  const [designPreviewAudio, setDesignPreviewAudio] = useState("");
  const [designVoices, setDesignVoices] = useState<CustomVoice[]>([]);

  const [cloneName, setCloneName] = useState("voice_clone_demo");
  const [cloneAudioFile, setCloneAudioFile] = useState<File | null>(null);
  const [cloneBusy, setCloneBusy] = useState(false);
  const [cloneListBusy, setCloneListBusy] = useState(false);
  const [cloneError, setCloneError] = useState("");
  const [cloneInfo, setCloneInfo] = useState("");
  const [cloneVoices, setCloneVoices] = useState<CustomVoice[]>([]);

  async function refreshCustomVoices(voiceType: VoiceType) {
    try {
      if (voiceType === "voice_design") {
        setDesignListBusy(true);
      } else {
        setCloneListBusy(true);
      }
      const result = await listCustomVoices(voiceType);
      if (voiceType === "voice_design") {
        setDesignVoices(result.voices);
      } else {
        setCloneVoices(result.voices);
      }
    } catch (err) {
      const message = formatErrorMessage(err, "加载音色列表失败。");
      if (voiceType === "voice_design") {
        setDesignError(message);
      } else {
        setCloneError(message);
      }
    } finally {
      if (voiceType === "voice_design") {
        setDesignListBusy(false);
      } else {
        setCloneListBusy(false);
      }
    }
  }

  useEffect(() => {
    void refreshCustomVoices("voice_design");
    void refreshCustomVoices("voice_clone");
  }, []);

  async function onDesignSubmit(event: FormEvent) {
    event.preventDefault();
    setDesignError("");
    setDesignInfo("");
    if (!designName.trim()) {
      setDesignError("请先填写音色名称。");
      return;
    }
    if (designPrompt.trim().length < 10) {
      setDesignError("请提供更具体的音色描述，至少 10 个字。");
      return;
    }
    if (designPreviewText.trim().length < 6) {
      setDesignError("请填写足够长的试听文本，方便判断音色效果。");
      return;
    }
    setDesignBusy(true);
    try {
      const result = await createVoiceDesign({
        voice_prompt: designPrompt.trim(),
        preview_text: designPreviewText.trim(),
        preferred_name: designName.trim(),
        language: designLanguage.trim() || "zh"
      });
      setDesignInfo(`已创建音色：${result.voice}`);
      const previewAudioData = result.preview_audio_data || "";
      setDesignPreviewAudio(
        previewAudioData ? `data:audio/wav;base64,${previewAudioData}` : ""
      );
      await refreshCustomVoices("voice_design");
    } catch (err) {
      setDesignError(formatErrorMessage(err, "创建音色设计失败。"));
    } finally {
      setDesignBusy(false);
    }
  }

  async function onCloneSubmit(event: FormEvent) {
    event.preventDefault();
    setCloneError("");
    setCloneInfo("");
    if (!cloneName.trim()) {
      setCloneError("请先填写克隆音色名称。");
      return;
    }
    if (!cloneAudioFile) {
      setCloneError("请先选择一个音频文件。");
      return;
    }
    setCloneBusy(true);
    try {
      const result = await createVoiceClone({
        preferred_name: cloneName.trim(),
        audio_file: cloneAudioFile
      });
      setCloneInfo(`已创建音色：${result.voice}`);
      await refreshCustomVoices("voice_clone");
    } catch (err) {
      setCloneError(formatErrorMessage(err, "创建克隆音色失败。"));
    } finally {
      setCloneBusy(false);
    }
  }

  async function onDeleteVoice(voiceName: string, voiceType: VoiceType) {
    try {
      await deleteCustomVoice(voiceName, voiceType);
      await refreshCustomVoices(voiceType);
    } catch (err) {
      const message = formatErrorMessage(err, "删除音色失败。");
      if (voiceType === "voice_design") {
        setDesignError(message);
      } else {
        setCloneError(message);
      }
    }
  }

  function onApplyDesignPreset(prompt: string) {
    setDesignPrompt(prompt);
    setDesignError("");
    setDesignInfo("已应用音色描述预设。");
  }

  function onCloneAudioFileChange(file: File | null) {
    setCloneAudioFile(file);
    setCloneError("");
    if (!file) {
      return;
    }
    if (file.size > MAX_CLONE_FILE_BYTES) {
      setCloneError("音频文件过大，建议控制在 20MB 以内。");
      return;
    }
    if (file.type && !CLONE_ACCEPTED_TYPES.includes(file.type)) {
      setCloneError("暂不支持该音频格式，请使用 mp3、wav、flac、m4a、ogg 或 webm。");
      return;
    }
    setCloneInfo(`已载入样本：${file.name} (${formatBytes(file.size)})`);
  }

  const designCanSubmit =
    !designBusy &&
    designName.trim().length > 0 &&
    designPrompt.trim().length >= 10 &&
    designPreviewText.trim().length >= 6;

  const cloneCanSubmit =
    !cloneBusy &&
    cloneName.trim().length > 0 &&
    cloneAudioFile !== null &&
    cloneAudioFile.size <= MAX_CLONE_FILE_BYTES &&
    (!cloneAudioFile.type || CLONE_ACCEPTED_TYPES.includes(cloneAudioFile.type));

  const cloneFileSummary = cloneAudioFile
    ? `${cloneAudioFile.name} · ${formatBytes(cloneAudioFile.size)}`
    : "";

  return {
    design: {
      designPrompt,
      designPreviewText,
      designName,
      designLanguage,
      designBusy,
      designListBusy,
      designError,
      designInfo,
      designPreviewAudio,
      designVoices,
      designCanSubmit,
      designPromptPresets: DESIGN_PROMPT_PRESETS,
      designGuidelines: [
        "描述音色的人设、语气、节奏和使用场景。",
        "试听文本最好覆盖陈述句、疑问句和情绪起伏。",
        "先做 2 到 3 个方向，再挑最接近产品场景的音色。"
      ],
      onSubmit: onDesignSubmit,
      onRefresh: () => refreshCustomVoices("voice_design"),
      onDeleteVoice: (voiceName: string) => onDeleteVoice(voiceName, "voice_design"),
      onPromptChange: setDesignPrompt,
      onPreviewTextChange: setDesignPreviewText,
      onNameChange: setDesignName,
      onLanguageChange: setDesignLanguage,
      onApplyPreset: onApplyDesignPreset
    },
    clone: {
      cloneName,
      cloneAudioFile,
      cloneBusy,
      cloneListBusy,
      cloneError,
      cloneInfo,
      cloneVoices,
      cloneCanSubmit,
      cloneFileSummary,
      cloneAcceptedFormats: ["mp3", "wav", "flac", "m4a", "ogg", "webm"],
      cloneRequirements: [
        "建议 10 到 30 秒的干净人声，不要混背景音乐。",
        "尽量单人说话，避免重叠和混响。",
        "录音音量稳定，语句完整，采样清晰。"
      ],
      onSubmit: onCloneSubmit,
      onRefresh: () => refreshCustomVoices("voice_clone"),
      onDeleteVoice: (voiceName: string) => onDeleteVoice(voiceName, "voice_clone"),
      onNameChange: setCloneName,
      onAudioFileChange: onCloneAudioFileChange
    }
  };
}

export type UseVoiceManagementResult = ReturnType<typeof useVoiceManagement>;
export type VoiceDesignController = UseVoiceManagementResult["design"];
export type VoiceCloneController = UseVoiceManagementResult["clone"];
