import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TtsPage from './TtsPage';
import { createTtsController } from '../test/factories';

describe('TtsPage', () => {
    it('renders correctly', () => {
        render(
            <TtsPage
                tts={createTtsController()}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('生成语音')).toBeInTheDocument();
        expect(screen.getByText('Sample test text')).toBeInTheDocument();
    });
});
