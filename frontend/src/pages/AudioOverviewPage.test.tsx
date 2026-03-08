import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AudioOverviewPage from './AudioOverviewPage';
import { createAudioOverviewController } from '../test/factories';

describe('AudioOverviewPage', () => {
    it('renders the podcast architecture appropriately', () => {
        render(
            <AudioOverviewPage
                audioOverview={createAudioOverviewController()}
                errorRuntimeContext={{}}
            />
        );

        // Assertions from header
        expect(screen.getByText('播客工作台')).toBeInTheDocument();

        // Assertions from topic step
        expect(screen.getByDisplayValue('AI 对个人学习习惯的影响')).toBeInTheDocument();

        // Assertions from script editor
        expect(screen.getByText('第一段内容')).toBeInTheDocument();

        // Assertions from synth bar
        expect(screen.getByRole('button', { name: /合成/ })).toBeInTheDocument();

        // Assertions from sidebar
        expect(screen.getByText(/播客脚本测试/)).toBeInTheDocument();
    });

    it('displays error and info messages globally', () => {
        render(
            <AudioOverviewPage
                audioOverview={createAudioOverviewController({
                    audioOverviewError: 'Test error message',
                    audioOverviewInfo: 'Test info message'
                })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('Test info message')).toBeInTheDocument();
        expect(screen.getByText('Test error message')).toBeInTheDocument();
    });
});
