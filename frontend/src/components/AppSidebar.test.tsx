import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AppSidebar from './AppSidebar';
import type { ActiveTab } from '../appConfig';

describe('AppSidebar', () => {
    it('renders correctly', () => {
        render(
            <AppSidebar
                activeTab={"chat" as ActiveTab}
                chatHistoryItems={[]}
                onTabChange={vi.fn()}
                onNewChatSession={vi.fn()}
                onHistorySelect={vi.fn()}
            />
        );
        expect(screen.getByText('VoiceSpirit')).toBeInTheDocument();
        expect(screen.getByText('聊天')).toBeInTheDocument();
    });
});
