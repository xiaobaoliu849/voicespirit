import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AppSidebar from './AppSidebar';
import type { ActiveTab } from '../appConfig';

describe('AppSidebar', () => {
    it('renders simplified navigation without duplicate chat entry', () => {
        render(
            <AppSidebar
                activeTab={"chat" as ActiveTab}
                authLabel="登录账号"
                authReady={false}
                chatHistoryItems={[]}
                onAuthClick={vi.fn()}
                onTabChange={vi.fn()}
                onNewChatSession={vi.fn()}
                onHistorySelect={vi.fn()}
                onClearHistory={vi.fn()}
                onDeleteHistoryItem={vi.fn()}
                onOpenSettings={vi.fn()}
            />
        );
        expect(screen.getByText('VoiceSpirit')).toBeInTheDocument();
        expect(screen.getByText('新建对话')).toBeInTheDocument();
        expect(screen.queryByText('聊天')).not.toBeInTheDocument();
        expect(screen.queryByText('最近对话')).not.toBeInTheDocument();
    });

    it('shows recent history only when there are chat sessions', () => {
        render(
            <AppSidebar
                activeTab={"translate" as ActiveTab}
                authLabel="demo@example.com"
                authReady={true}
                chatHistoryItems={[{ id: '1', content: '帮我总结今天会议纪要' }]}
                onAuthClick={vi.fn()}
                onTabChange={vi.fn()}
                onNewChatSession={vi.fn()}
                onHistorySelect={vi.fn()}
                onClearHistory={vi.fn()}
                onDeleteHistoryItem={vi.fn()}
                onOpenSettings={vi.fn()}
            />
        );

        expect(screen.getByRole('button', { name: '清除全部' })).toBeInTheDocument();
        expect(screen.getByText('帮我总结今天会议纪要')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '删除历史 帮我总结今天会议纪要' })).toBeInTheDocument();
    });
});
