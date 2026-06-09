import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import VoiceDesignPage from './VoiceDesignPage';
import { createVoiceDesignController } from '../test/factories';

describe('VoiceDesignPage', () => {
    it('renders correctly', () => {
        render(
            <VoiceDesignPage
                design={createVoiceDesignController({
                    designName: 'test-voice',
                    designLanguage: 'en',
                    designPrompt: 'A test prompt',
                    designPreviewText: 'Hello world'
                })}
                errorRuntimeContext={{}}
            />
        );
        
        expect(screen.getByText('暂无设计的音色')).toBeInTheDocument();
        
        fireEvent.click(screen.getByRole('button', { name: /设计新音色/ }));

        expect(screen.getByText(/通过自然语言描述/)).toBeInTheDocument();
        expect(screen.getByDisplayValue('test-voice')).toBeInTheDocument();
        expect(screen.getByDisplayValue('en')).toBeInTheDocument();
        expect(screen.getByDisplayValue('A test prompt')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Hello world')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /开始创造/ })).toBeInTheDocument();
    });

    it('displays error and info messages', () => {
        render(
            <VoiceDesignPage
                design={createVoiceDesignController({
                    designName: 'test-voice',
                    designLanguage: 'zh',
                    designPrompt: 'test prompt',
                    designPreviewText: 'test preview',
                    designError: 'Test error message',
                    designInfo: 'Test info message'
                })}
                errorRuntimeContext={{}}
            />
        );
        
        fireEvent.click(screen.getByRole('button', { name: /设计新音色/ }));
        expect(screen.getByText('Test info message')).toBeInTheDocument();
        
        const form = screen.getByRole('button', { name: /开始创造/ }).closest('form')!;
        fireEvent.submit(form);
        expect(screen.getByText('Test error message')).toBeInTheDocument();
    });
});
