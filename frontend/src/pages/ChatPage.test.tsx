import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ChatPage from './ChatPage';
import { createChatController } from '../test/factories';

describe('ChatPage', () => {
    it('renders correctly empty state', () => {
        render(
            <ChatPage
                chat={createChatController()}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('开始一段新对话')).toBeInTheDocument();
        expect(screen.getByText('发送')).toBeInTheDocument();
    });
});
