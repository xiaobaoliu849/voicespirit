import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import VoiceCatalog from './VoiceCatalog';

describe('VoiceCatalog', () => {
    it('renders correctly', () => {
        render(
            <VoiceCatalog
                title="My Voices"
                voices={[
                    { voice: "TestVoice", type: "voice_design", target_model: "test_model" }
                ]}
                busy={false}
                listBusy={false}
                emptyText="No voices empty"
                onDeleteVoice={vi.fn()}
            />
        );
        expect(screen.getByText(/My Voices/)).toBeInTheDocument();
        expect(screen.getByText('TestVoice')).toBeInTheDocument();
    });
});
