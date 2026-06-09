import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AudioOverviewPage from './AudioOverviewPage';
import { createAudioOverviewController } from '../test/factories';

describe('AudioOverviewPage', () => {
    it('renders the podcast architecture appropriately', async () => {
        render(
            <AudioOverviewPage
                audioOverview={createAudioOverviewController()}
                errorRuntimeContext={{}}
            />
        );

        // Assertions from header
        expect(await screen.findByText(/播客 #12/)).toBeInTheDocument();

        // Switch to Stage 1 to verify topic step
        fireEvent.click(screen.getByRole('button', { name: /1. 主题与资料/ }));
        expect(await screen.findByDisplayValue('AI 对个人学习习惯的影响')).toBeInTheDocument();

        // Switch to Stage 2 to verify script editor and synth controls
        fireEvent.click(screen.getByRole('button', { name: /2. 剧本与配音/ }));
        expect(await screen.findByText('第一段内容')).toBeInTheDocument();

        // Assertions from synth bar
        expect(await screen.findByRole('button', { name: /合成/ })).toBeInTheDocument();

        // Click back button to return to library and verify the podcast list
        fireEvent.click(screen.getByTitle('返回列表'));
        expect(await screen.findByText(/播客脚本测试/)).toBeInTheDocument();
    });

    it('displays error and info messages globally', async () => {
        render(
            <AudioOverviewPage
                audioOverview={createAudioOverviewController({
                    audioOverviewError: 'Test error message',
                    audioOverviewInfo: 'Test info message'
                })}
                errorRuntimeContext={{}}
            />
        );
        expect(await screen.findByText('Test info message')).toBeInTheDocument();
        expect(await screen.findByText('Test error message')).toBeInTheDocument();
    });
});
