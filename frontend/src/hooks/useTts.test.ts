import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import useTts from './useTts';
import { createFormatErrorMessageStub } from '../test/factories';

vi.mock('../api', () => ({
    fetchVoices: vi.fn().mockResolvedValue({ voices: [] })
}));

describe('useTts', () => {
    it('initializes and updates text', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useTts({ defaultText: 'Initial text', formatErrorMessage }));

        expect(result.current.text).toBe('Initial text');

        act(() => {
            result.current.onTextChange('New text');
        });

        expect(result.current.text).toBe('New text');
    });
});
