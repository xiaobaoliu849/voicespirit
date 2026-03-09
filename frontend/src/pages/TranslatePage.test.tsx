import { fireEvent, render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TranslatePage from './TranslatePage';
import { createTranslateController } from '../test/factories';

describe('TranslatePage', () => {
    it('renders workstation layout', () => {
        render(
            <TranslatePage
                translate={createTranslateController()}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('原文输入区')).toBeInTheDocument();
        expect(screen.getByText('翻译结果')).toBeInTheDocument();
        expect(screen.getByText('开始翻译')).toBeInTheDocument();
    });

    it('shows translation result', () => {
        render(
            <TranslatePage
                translate={createTranslateController({ translateResult: 'Mock translation' })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('Mock translation')).toBeInTheDocument();
    });

    it('shows placeholder when no result', () => {
        render(
            <TranslatePage
                translate={createTranslateController({ translateResult: '' })}
                errorRuntimeContext={{}}
            />
        );
        expect(screen.getByText('译文会显示在这里')).toBeInTheDocument();
    });

    it('wires toolbar and pane actions to translate handlers', async () => {
        const translate = createTranslateController({
            translateInput: 'Hello world',
            translateResult: '你好，世界'
        });

        render(
            <TranslatePage
                translate={translate}
                errorRuntimeContext={{}}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: '交换语言方向' }));
        fireEvent.click(screen.getByRole('button', { name: '粘贴' }));
        fireEvent.click(screen.getByRole('button', { name: '复制原文' }));
        fireEvent.click(screen.getByRole('button', { name: '复制译文' }));
        fireEvent.click(screen.getByRole('button', { name: '清空' }));

        expect(translate.onSwapLanguages).toHaveBeenCalledTimes(1);
        expect(translate.onPasteInput).toHaveBeenCalledTimes(1);
        expect(translate.onCopySource).toHaveBeenCalledTimes(1);
        expect(translate.onCopyResult).toHaveBeenCalledTimes(1);
        expect(translate.onClearAll).toHaveBeenCalledTimes(1);
    });

    it('submits the translation form through the primary action', () => {
        const translate = createTranslateController();

        render(
            <TranslatePage
                translate={translate}
                errorRuntimeContext={{}}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: '开始翻译' }));

        expect(translate.onSubmit).toHaveBeenCalledTimes(1);
        expect(translate.onSubmit).toHaveBeenCalledWith(expect.any(Object));
    });
});
