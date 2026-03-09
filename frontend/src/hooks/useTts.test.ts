import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import useTts from './useTts';
import { createFormatErrorMessageStub } from '../test/factories';
import { fetchSpeakAudio } from '../api';

vi.mock('../api', () => ({
    fetchVoices: vi.fn().mockResolvedValue({ voices: [] }),
    fetchSpeakAudio: vi.fn()
}));

describe('useTts', () => {
    it('supports switching to dialogue mode', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useTts({ defaultText: 'Initial text', formatErrorMessage }));

        act(() => {
            result.current.onTtsModeChange('dialogue');
            result.current.onDialogueTextChange('A: 你好\\nB: 你好，今天聊什么？');
        });

        expect(result.current.ttsMode).toBe('dialogue');
        expect(result.current.activeSourceText).toContain('A: 你好');
    });

    it('initializes and updates text', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useTts({ defaultText: 'Initial text', formatErrorMessage }));

        expect(result.current.text).toBe('Initial text');
        expect(result.current.ttsEngine).toBe('edge');

        act(() => {
            result.current.onTextChange('New text');
        });

        expect(result.current.text).toBe('New text');
    });

    it('switches TTS engine and clears stale output state', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useTts({ defaultText: 'Initial text', formatErrorMessage }));

        act(() => {
            result.current.onEngineChange('qwen_flash');
        });

        expect(result.current.ttsEngine).toBe('qwen_flash');
    });

    it('blocks pdf mode submit without prepared text', async () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useTts({ defaultText: 'Initial text', formatErrorMessage }));

        act(() => {
            result.current.onTtsModeChange('pdf');
            result.current.onPdfFileChange(new File(['pdf'], 'demo.pdf', { type: 'application/pdf' }));
        });

        await act(async () => {
            await result.current.onSubmit({ preventDefault() {} } as any);
        });

        expect(result.current.ttsError).toBe('请先选择 PDF 并准备可朗读文本。');
    });

    it('submits dialogue text to speech generation', async () => {
        vi.mocked(fetchSpeakAudio).mockResolvedValue({
            blob: new Blob(['audio'], { type: 'audio/mpeg' }),
            memorySaved: false
        });

        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useTts({ defaultText: 'Initial text', formatErrorMessage }));

        act(() => {
            result.current.onTtsModeChange('dialogue');
            result.current.onDialogueTextChange('A: 你好\\nB: 很高兴见到你');
        });

        await act(async () => {
            await result.current.onSubmit({ preventDefault() {} } as any);
        });

        expect(fetchSpeakAudio).toHaveBeenCalledWith(
            expect.objectContaining({
                text: 'A: 你好\\nB: 很高兴见到你',
                engine: 'edge'
            })
        );
    });
});
