import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import useSettings from './useSettings';
import { createFormatErrorMessageStub } from '../test/factories';

vi.mock('../api', () => ({
    configureEverMemRuntime: vi.fn(),
    getEverMemRuntimeConfig: vi.fn().mockReturnValue({
        enabled: false,
        api_url: "",
        api_key: "",
        scope_id: "",
        temporary_session: false,
        remember_chat: true,
        remember_voice_chat: true,
        remember_recordings: false,
        remember_podcast: true,
        remember_tts: true,
        store_transcript_fulltext: false
    }),
    fetchApiRuntimeInfo: vi.fn().mockResolvedValue({}),
    fetchSettings: vi.fn().mockResolvedValue({
        settings: {
            api_keys: { dashscope_api_key: 'sk-test' },
            api_urls: { DashScope: 'https://dashscope.example.com' },
            default_models: {
                DashScope: {
                    default: 'qwen-plus',
                    available: ['qwen-plus', 'qwen-max']
                }
            },
            general_settings: {},
            memory_settings: {
                enabled: true,
                api_url: 'https://evermem.example.com',
                api_key: 'evermem-key',
                scope_id: 'workspace-main',
                temporary_session: false,
                remember_chat: true,
                remember_voice_chat: true,
                remember_recordings: false,
                remember_podcast: true,
                remember_tts: true,
                store_transcript_fulltext: false
            },
            output_directory: "",
            tts_settings: {},
            qwen_tts_settings: {},
            transcription_settings: {
                upload_mode: 's3',
                public_base_url: '',
                s3_bucket: 'voicespirit-assets',
                s3_region: 'us-east-1',
                s3_endpoint_url: '',
                s3_access_key_id: '',
                s3_secret_access_key: '',
                s3_key_prefix: 'transcription'
            },
            minimax: {},
            ui_settings: {},
            shortcuts: {}
        },
        config_path: '',
        providers: ['DashScope']
    }),
    updateSettings: vi.fn()
}));

describe('useSettings', () => {
    it('initializes correctly', () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useSettings({ formatErrorMessage }));

        expect(result.current.settingsProvider).toBe('DashScope');
        expect(result.current.settingsBusy).toBe(true); // Initially fetching
    });

    it('builds grouped section metadata after settings load', async () => {
        const formatErrorMessage = createFormatErrorMessageStub();
        const { result } = renderHook(() => useSettings({ formatErrorMessage }));

        await waitFor(() => {
            expect(result.current.settingsBusy).toBe(false);
        });

        expect(result.current.providerSection.apiKeyConfigured).toBe(true);
        expect(result.current.providerSection.availableModelCount).toBe(2);
        expect(result.current.memorySection.configured).toBe(true);
        expect(result.current.memorySection.scenes.find((item) => item.id === 'transcription')?.enabled).toBe(false);
        expect(result.current.transcriptionSection.uploadMode).toBe('s3');
        expect(result.current.transcriptionSection.s3Configured).toBe(false);
        expect(result.current.transcriptionSection.s3MissingFields).toEqual([
            's3_access_key_id',
            's3_secret_access_key'
        ]);
    });
});
