import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import useChat from './useChat';
import { createFormatErrorMessageStub } from '../test/factories';

describe('useChat', () => {
    it('initializes correctly', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useChat({ formatErrorMessage }));

        expect(result.current.chatProvider).toBe('Google');
        expect(result.current.chatInput).toBe('');
        expect(result.current.chatMessages).toEqual([]);

        act(() => {
            result.current.onInputChange('Hello');
        });

        expect(result.current.chatInput).toBe('Hello');
    });
});
