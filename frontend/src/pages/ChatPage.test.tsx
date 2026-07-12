import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChatPage from './ChatPage';
import { createChatController, createVoiceChatController } from '../test/factories';

describe('ChatPage', () => {
    it('opens the reachable voice history workspace from the active chat page', async () => {
        const onLoadVoiceAgentHistory = vi.fn();
        render(
            <ChatPage
                chat={createChatController()}
                voiceChat={createVoiceChatController({ onLoadVoiceAgentHistory })}
                errorRuntimeContext={{}}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: '语音历史' }));
        expect(screen.getByText('语音 Agent 历史与运行')).toBeInTheDocument();
        await waitFor(() => expect(onLoadVoiceAgentHistory).toHaveBeenCalledTimes(1));
        fireEvent.click(screen.getByRole('button', { name: '返回对话' }));
        expect(screen.queryByText('语音 Agent 历史与运行')).not.toBeInTheDocument();
    });

    it('renders correctly empty state', () => {
        render(
            <ChatPage
                chat={createChatController({ chatInput: 'hello' })}
                voiceChat={createVoiceChatController({ voiceChatProvider: "" })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText(/声之灵/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '发送' })).toBeInTheDocument();
        expect(screen.queryByText('实时语音')).not.toBeInTheDocument();
        expect(screen.queryByText(/麦克风按钮当前使用/)).not.toBeInTheDocument();
    });

    it('shows voice chat startup errors even when the realtime session failed to open', () => {
        render(
            <ChatPage
                chat={createChatController()}
                voiceChat={createVoiceChatController({
                    voiceChatStatus: '实时语音不可用',
                    voiceChatError: 'Google API Key 未配置，无法启动实时语音会话。'
                })}
                errorRuntimeContext={{}}
            />
        );

        expect(screen.getByText('实时语音')).toBeInTheDocument();
        expect(screen.getByText('Google API Key 未配置，无法启动实时语音会话。')).toBeInTheDocument();
    });

    it('keeps text input but blocks text sending for realtime models', () => {
        render(
            <ChatPage
                chat={createChatController({
                    chatProvider: 'DashScope',
                    chatModel: 'qwen3-omni-flash-realtime-2025-12-01',
                    chatInput: 'some input'
                })}
                voiceChat={createVoiceChatController()}
                errorRuntimeContext={{}}
            />
        );

        expect(screen.getByPlaceholderText(/输入聊天内容/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '语音转写' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '实时通话' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '发送' })).toBeDisabled();
        expect(screen.getByText(/实时语音\/实时翻译模型/)).toBeInTheDocument();
    });

    it('shows memory badges for realtime voice turns', () => {
        render(
            <ChatPage
                chat={createChatController()}
                voiceChat={createVoiceChatController({
                    sessionSummary: [
                        { role: 'user', content: '这周重点是比赛提交，以后默认用中文回答。', memorySaved: true },
                        {
                            role: 'assistant',
                            content: '记住了，我会默认用中文回答。',
                            memoriesUsed: 1,
                            memorySourceSummary: '来源：本地待同步 1 条，云端 0 条'
                        }
                    ]
                })}
                errorRuntimeContext={{}}
            />
        );

        expect(screen.getByText('✓ 已记忆')).toBeInTheDocument();
        expect(screen.getByText(/🧠 回忆了 1 条/)).toBeInTheDocument();
        expect(screen.getByText('来源：本地待同步 1 条，云端 0 条')).toBeInTheDocument();
    });

    it('shows live translate controls and bilingual streaming labels for Gemini Live Translate', () => {
        render(
            <ChatPage
                chat={createChatController({
                    chatProvider: 'Google',
                    chatModel: 'gemini-3.5-live-translate-preview'
                })}
                voiceChat={createVoiceChatController({
                    voiceChatModel: 'gemini-3.5-live-translate-preview',
                    voiceChatVoiceLabel: 'Puck',
                    voiceChatLiveTranslate: true,
                    voiceChatTargetLanguageCode: 'zh-Hans',
                    voiceChatTargetLanguageLabel: '中文（简体）/ Chinese (Simplified) (zh-Hans)',
                    voiceChatTargetLanguageOptions: [
                        { value: 'en', label: 'English (en)' },
                        { value: 'zh-Hans', label: '中文（简体）(zh-Hans)' }
                    ],
                    voiceChatRecording: true,
                    voiceChatConnected: true,
                    voiceChatTranscript: 'Hello everyone',
                    voiceChatReply: '大家好'
                })}
                errorRuntimeContext={{}}
            />
        );

        expect(screen.getByTitle('翻译目标语言')).toBeInTheDocument();
        expect(screen.getByTitle('当前音色：Puck')).toBeInTheDocument();
        expect(screen.getByText('同语回放')).toBeInTheDocument();
        expect(screen.getByText('原文实时转写')).toBeInTheDocument();
        expect(screen.getByText('译文：中文（简体）/ Chinese (Simplified) (zh-Hans)')).toBeInTheDocument();
        expect(screen.queryByPlaceholderText(/输入聊天内容/)).not.toBeInTheDocument();
        expect(document.querySelector('.vsComposer.liveActive')).toBeInTheDocument();
    });
});
