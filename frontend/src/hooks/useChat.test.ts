import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import useChat from './useChat';
import { createFormatErrorMessageStub } from '../test/factories';

describe('useChat', () => {
    it('initializes correctly', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() =>
            useChat({
                formatErrorMessage,
                providerOptions: ['DashScope', 'Google'],
                preferredProvider: 'DashScope',
                providerModelCatalog: {
                    DashScope: {
                        defaultModel: 'qwen-plus',
                        availableModels: ['qwen-plus', 'qwen-max']
                    },
                    Google: {
                        defaultModel: 'gemini-2.5-flash',
                        availableModels: ['gemini-2.5-flash']
                    }
                }
            })
        );

        expect(result.current.chatProvider).toBe('DashScope');
        expect(result.current.chatProviderOptions).toEqual(['DashScope', 'Google']);
        expect(result.current.chatModel).toBe('qwen-plus');
        expect(result.current.chatModelOptions).toEqual(['qwen-plus', 'qwen-max']);
        expect(result.current.chatInput).toBe('');
        expect(result.current.chatMessages).toEqual([]);

        act(() => {
            result.current.onInputChange('Hello');
        });

        expect(result.current.chatInput).toBe('Hello');
    });

    it('switches model defaults when provider changes', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() =>
            useChat({
                formatErrorMessage,
                providerOptions: ['DashScope', 'Google'],
                preferredProvider: 'DashScope',
                providerModelCatalog: {
                    DashScope: {
                        defaultModel: 'qwen-plus',
                        availableModels: ['qwen-plus', 'qwen-max']
                    },
                    Google: {
                        defaultModel: 'gemini-2.5-flash',
                        availableModels: ['gemini-2.5-flash', 'gemini-2.5-pro']
                    }
                }
            })
        );

        act(() => {
            result.current.onProviderChange('Google');
        });

        expect(result.current.chatProvider).toBe('Google');
        expect(result.current.chatModel).toBe('gemini-2.5-flash');
        expect(result.current.chatModelOptions).toEqual(['gemini-2.5-flash', 'gemini-2.5-pro']);
    });
});
