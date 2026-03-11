import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ChatPage from './ChatPage';
import { createChatController, createVoiceChatController } from '../test/factories';

describe('ChatPage', () => {
    it('renders correctly empty state', () => {
        render(
            <ChatPage
                chat={createChatController()}
                voiceChat={createVoiceChatController()}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('你好，有什么可以帮你的？')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '发送' })).toBeInTheDocument();
        expect(screen.getByText('实时语音入口')).toBeInTheDocument();
        expect(screen.getByText(/麦克风按钮已同步/)).toBeInTheDocument();
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

        expect(screen.getByText('实时语音不可用')).toBeInTheDocument();
        expect(screen.getByText('Google API Key 未配置，无法启动实时语音会话。')).toBeInTheDocument();
    });

    it('blocks text sending when a realtime voice model is selected', () => {
        render(
            <ChatPage
                chat={createChatController({
                    chatProvider: 'DashScope',
                    chatModel: 'qwen3-omni-flash-realtime-2025-12-01'
                })}
                voiceChat={createVoiceChatController()}
                errorRuntimeContext={{}}
            />
        );

        expect(screen.getByText(/当前是实时语音模型/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '发送' })).toBeDisabled();
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
        expect(screen.getByText('已存入记忆')).toBeInTheDocument();
    });
});
