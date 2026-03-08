import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TranslatePage from './TranslatePage';
import { createTranslateController } from '../test/factories';

describe('TranslatePage', () => {
    it('renders properly', () => {
        render(
            <TranslatePage
                translate={createTranslateController()}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('开始翻译')).toBeInTheDocument();
        expect(screen.getByText('Mock translation')).toBeInTheDocument();
    });
});
