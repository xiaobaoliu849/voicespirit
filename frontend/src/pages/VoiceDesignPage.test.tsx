import { render, screen } from '@testing-library/react';
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
        expect(screen.getByText('音色设计工作室 (Voice Design)')).toBeInTheDocument();
        expect(screen.getByDisplayValue('test-voice')).toBeInTheDocument();
        expect(screen.getByDisplayValue('en')).toBeInTheDocument();
        expect(screen.getByDisplayValue('A test prompt')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Hello world')).toBeInTheDocument();
        expect(screen.getByText('创造全新音色')).toBeInTheDocument();
        expect(screen.getByText('暂无您设计的自定义音色。')).toBeInTheDocument();
    });

    it('displays error and info messages', () => {
        render(
            <VoiceDesignPage
                design={createVoiceDesignController({
                    designError: 'Test error message',
                    designInfo: 'Test info message'
                })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('Test info message')).toBeInTheDocument();
        expect(screen.getByText('Test error message')).toBeInTheDocument();
    });
});
