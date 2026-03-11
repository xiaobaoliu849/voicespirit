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
});
