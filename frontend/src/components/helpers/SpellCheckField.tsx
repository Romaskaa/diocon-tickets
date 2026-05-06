import { useState, useCallback } from 'react';
import { WandSparkles, Loader2 } from 'lucide-react';
import { proofreadingApi } from '../../api/client';
import { SpellCheckDiff } from './SpellCheckDiff';

interface Suggestion {
  category: string;
  original: string;
  suggestion: string;
  start: number;
  end: number;
  message: string;
}

interface SpellCheckResult {
  original_text: string;
  corrected_text: string;
  has_issues: boolean;
  suggestions: Suggestion[];
}

interface SpellCheckFieldProps {
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
  label?: string;
  disabled?: boolean;
}

const MEDIA_TOKEN_REGEX = /\[\[(local-image|image):([^\]]+)\]\]/g;

type MediaToken = {
  original: string;
  start: number;
  end: number;
  placeholder: string;
};

function makePlaceholder(length: number, index: number) {
  const base = `[ИЗОБРАЖЕНИЕ_${index}]`;
  if (base.length >= length) return base.slice(0, length);
  return base + '_'.repeat(length - base.length);
}

function maskMediaTokens(text: string) {
  const tokens: MediaToken[] = [];

  const maskedText = text.replace(MEDIA_TOKEN_REGEX, (match, _type, _id, offset) => {
    const placeholder = makePlaceholder(match.length, tokens.length);
    tokens.push({
      original: match,
      start: offset,
      end: offset + match.length,
      placeholder,
    });
    return placeholder;
  });

  return { maskedText, tokens };
}

function rangesOverlap(aStart: number, aEnd: number, bStart: number, bEnd: number) {
  return aStart < bEnd && aEnd > bStart;
}

function filterSuggestionsOutsideMedia(
  suggestions: Suggestion[],
  tokens: MediaToken[]
): Suggestion[] {
  return suggestions.filter((s) => {
    return !tokens.some((t) => rangesOverlap(s.start, s.end, t.start, t.end));
  });
}

function applySuggestionsToOriginalText(
  originalText: string,
  suggestions: Suggestion[]
): string {
  if (!suggestions.length) return originalText;

  const sorted = [...suggestions].sort((a, b) => a.start - b.start);
  let result = '';
  let cursor = 0;

  for (const s of sorted) {
    result += originalText.slice(cursor, s.start);
    result += s.suggestion;
    cursor = s.end;
  }

  result += originalText.slice(cursor);
  return result;
}

function replaceMediaTokensForDisplay(text: string): string {
  return text.replace(MEDIA_TOKEN_REGEX, '[изображение]');
}

export function SpellCheckField({
  value,
  onChange,
  children,
  label,
  disabled,
}: SpellCheckFieldProps) {
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<SpellCheckResult | null>(null);

  // Это значение пойдёт в onApply — уже с сохранёнными токенами
  const [safeCorrectedText, setSafeCorrectedText] = useState<string>('');

  const handleCheck = useCallback(async () => {
    if (!value.trim() || checking || disabled) return;

    setChecking(true);
    setResult(null);

    try {
      // 1. Маскируем токены
      const { maskedText, tokens } = maskMediaTokens(value);

      // 2. Отправляем только maskedText
      const res = await proofreadingApi.spellCheck(maskedText);

      // 3. Фильтруем предложения, которые касаются токенов
      const safeSuggestions = filterSuggestionsOutsideMedia(res.suggestions || [], tokens);

      // 4. Применяем только безопасные исправления к ОРИГИНАЛЬНОМУ тексту
      const correctedOriginal = applySuggestionsToOriginalText(value, safeSuggestions);

      // 5. Для UI заменяем токены на [изображение]
      const uiResult: SpellCheckResult = {
        ...res,
        has_issues: safeSuggestions.length > 0,
        suggestions: safeSuggestions.map((s) => ({
          ...s,
          original: replaceMediaTokensForDisplay(s.original),
          suggestion: replaceMediaTokensForDisplay(s.suggestion),
        })),
        original_text: replaceMediaTokensForDisplay(value),
        corrected_text: replaceMediaTokensForDisplay(correctedOriginal),
      };

      setSafeCorrectedText(correctedOriginal);
      setResult(uiResult);
    } catch (err) {
      console.error('SpellCheck error:', err);
    } finally {
      setChecking(false);
    }
  }, [value, checking, disabled]);

  const handleApply = useCallback(() => {
    onChange(safeCorrectedText || value);
    setResult(null);
  }, [onChange, safeCorrectedText, value]);

  const handleDismiss = useCallback(() => {
    setResult(null);
  }, []);

  return (
    <div className="space-y-2">
      {/* Label + кнопка */}
      <div className="flex items-center justify-between">
        {label && <span className="text-base font-medium text-white/80">{label}</span>}
        <button
          type="button"
          onClick={handleCheck}
          disabled={!value.trim() || checking || disabled}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                     bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20
                     text-amber-400 hover:text-amber-300 text-sm font-medium
                     transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          title="Проверить орфографию"
        >
          {checking
            ? <Loader2 size={14} className="animate-spin" />
            : <WandSparkles size={14} />}
          {checking ? 'Проверка...' : 'Проверить'}
        </button>
      </div>

      {/* Поле */}
      <div>
        {children}
      </div>

      {/* Результат ВСЕГДА снизу */}
      {result && (
        <div className="mt-2">
          <SpellCheckDiff
            result={result}
            onApply={handleApply}
            onDismiss={handleDismiss}
          />
        </div>
      )}
    </div>
  );
}