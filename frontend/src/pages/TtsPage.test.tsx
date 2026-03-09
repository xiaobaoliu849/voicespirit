import { fireEvent, render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TtsPage from './TtsPage';
import { createTtsController } from '../test/factories';

describe('TtsPage', () => {
    it('renders workstation layout', () => {
        render(
            <TtsPage
                tts={createTtsController()}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('文本转语音工作台')).toBeInTheDocument();
        expect(screen.getByText('声音引擎配置')).toBeInTheDocument();
        expect(screen.getByText('合成结果及监视器')).toBeInTheDocument();
        expect(screen.getByText('生成音频')).toBeInTheDocument();
        expect(screen.getByText('Qwen TTS Flash')).toBeInTheDocument();
    });

    it('renders voice selector', () => {
        render(
            <TtsPage
                tts={createTtsController()}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('Xiaoxiao (zh-CN)')).toBeInTheDocument();
    });

    it('renders text content in textarea', () => {
        render(
            <TtsPage
                tts={createTtsController({ text: 'Sample test text' })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByDisplayValue('Sample test text')).toBeInTheDocument();
    });

    it('shows placeholder when no audio', () => {
        render(
            <TtsPage
                tts={createTtsController({ audioUrl: '' })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('暂无成果')).toBeInTheDocument();
    });

    it('wires submit and parameter controls to the tts controller', () => {
        const tts = createTtsController();

        render(
            <TtsPage
                tts={tts}
                errorRuntimeContext={{}}
            />
        );

        fireEvent.change(screen.getByDisplayValue('Sample test text'), {
            target: { value: 'Updated script' }
        });
        fireEvent.change(screen.getByDisplayValue('+0%'), {
            target: { value: '+10%' }
        });
        const combos = screen.getAllByRole('combobox');
        fireEvent.change(combos[0], {
            target: { value: 'edge' }
        });
        fireEvent.change(combos[1], {
            target: { value: 'zh-CN-XiaoxiaoNeural' }
        });
        fireEvent.click(screen.getByRole('button', { name: '生成音频' }));

        expect(tts.onEngineChange).toHaveBeenCalledWith('edge');
        expect(tts.onTextChange).toHaveBeenCalledWith('Updated script');
        expect(tts.onRateChange).toHaveBeenCalledWith('+10%');
        expect(tts.onVoiceChange).toHaveBeenCalledWith('zh-CN-XiaoxiaoNeural');
        expect(tts.onSubmit).toHaveBeenCalledTimes(1);
        expect(tts.onSubmit).toHaveBeenCalledWith(expect.any(Object));
    });

    it('switches into dialogue mode editor', () => {
        const tts = createTtsController();
        render(
            <TtsPage
                tts={tts}
                errorRuntimeContext={{}}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: '对话转语音' }));
        expect(tts.onTtsModeChange).toHaveBeenCalledWith('dialogue');
    });

    it('downloads generated audio through an anchor element', () => {
        const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { });

        render(
            <TtsPage
                tts={createTtsController({ audioUrl: 'blob:test-url' })}
                errorRuntimeContext={{}}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: /导出 MP3 音频/ }));

        expect(clickSpy).toHaveBeenCalledTimes(1);
        clickSpy.mockRestore();
    });
});
