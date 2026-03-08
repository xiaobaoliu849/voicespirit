import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import VoiceClonePage from './VoiceClonePage';
import { createVoiceCloneController } from '../test/factories';

describe('VoiceClonePage', () => {
    it('renders correctly', () => {
        const mockFile = new File(['dummy content'], 'test-audio.mp3', { type: 'audio/mpeg' });

        render(
            <VoiceClonePage
                clone={createVoiceCloneController({
                    cloneName: 'cloned-voice',
                    cloneAudioFile: mockFile
                })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('创建克隆音色')).toBeInTheDocument();
        expect(screen.getByDisplayValue('cloned-voice')).toBeInTheDocument();
        expect(screen.getByText('已选择：test-audio.mp3')).toBeInTheDocument();
        expect(screen.getByText('暂无音色。')).toBeInTheDocument();
    });

    it('displays error and info messages', () => {
        render(
            <VoiceClonePage
                clone={createVoiceCloneController({
                    cloneError: 'Test error message',
                    cloneInfo: 'Test info message'
                })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('Test info message')).toBeInTheDocument();
        expect(screen.getByText('Test error message')).toBeInTheDocument();
    });
});
