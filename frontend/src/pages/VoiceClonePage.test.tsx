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
        expect(screen.getByText('通过上传音频样板复刻特定人声')).toBeInTheDocument();
        expect(screen.getByDisplayValue('cloned-voice')).toBeInTheDocument();
        expect(screen.getByText('test-audio.mp3')).toBeInTheDocument();
        expect(screen.getByText('开始克隆音色')).toBeInTheDocument();
        expect(screen.getByText('暂无克隆成功的音色。')).toBeInTheDocument();
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
