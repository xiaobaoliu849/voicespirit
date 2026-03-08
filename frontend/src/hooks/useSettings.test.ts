import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import useSettings from './useSettings';
import { createFormatErrorMessageStub } from '../test/factories';

vi.mock('../api', () => ({
    configureEverMemRuntime: vi.fn(),
    fetchApiRuntimeInfo: vi.fn().mockResolvedValue({}),
    fetchSettings: vi.fn().mockResolvedValue({ settings: { api_keys: {}, api_urls: {}, default_models: {} }, config_path: '', providers: [] }),
    updateSettings: vi.fn()
}));

describe('useSettings', () => {
    it('initializes correctly', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useSettings({ formatErrorMessage }));

        expect(result.current.settingsProvider).toBe('DashScope');
        expect(result.current.settingsBusy).toBe(true); // Initially fetching
    });
});
