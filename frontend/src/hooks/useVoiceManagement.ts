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
    setDesignBusy(true);
    try {
      const result = await createVoiceDesign({
        voice_prompt: designPrompt,
        preview_text: designPreviewText,
        preferred_name: designName,
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
    if (!cloneAudioFile) {
      setCloneError("请先选择一个音频文件。");
      return;
    }
    setCloneBusy(true);
    try {
      const result = await createVoiceClone({
        preferred_name: cloneName,
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
      onSubmit: onDesignSubmit,
      onRefresh: () => refreshCustomVoices("voice_design"),
      onDeleteVoice: (voiceName: string) => onDeleteVoice(voiceName, "voice_design"),
      onPromptChange: setDesignPrompt,
      onPreviewTextChange: setDesignPreviewText,
      onNameChange: setDesignName,
      onLanguageChange: setDesignLanguage
    },
    clone: {
      cloneName,
      cloneAudioFile,
      cloneBusy,
      cloneListBusy,
      cloneError,
      cloneInfo,
      cloneVoices,
      onSubmit: onCloneSubmit,
      onRefresh: () => refreshCustomVoices("voice_clone"),
      onDeleteVoice: (voiceName: string) => onDeleteVoice(voiceName, "voice_clone"),
      onNameChange: setCloneName,
      onAudioFileChange: setCloneAudioFile
    }
  };
}

export type UseVoiceManagementResult = ReturnType<typeof useVoiceManagement>;
export type VoiceDesignController = UseVoiceManagementResult["design"];
export type VoiceCloneController = UseVoiceManagementResult["clone"];
