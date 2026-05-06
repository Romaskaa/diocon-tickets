// components/helpers/SpellCheckDiff.tsx
import React, { useEffect, useMemo, useState } from 'react';
import { Check, X, WandSparkles, ChevronDown, ChevronUp } from 'lucide-react';

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

interface SpellCheckDiffProps {
  result: SpellCheckResult;
  onApply: (correctedText: string) => void;
  onDismiss: () => void;
}

const CATEGORY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  TYPOS: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'Ошибка' },
  CASING: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'Ошибка' },
  GRAMMAR: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'Ошибка' },
  PUNCTUATION: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'Ошибка' },
  STYLE: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'Ошибка' },
};

const getStyle = (category: string) =>
  CATEGORY_STYLES[category] || {
    bg: 'bg-white/10',
    text: 'text-white/60',
    label: 'Ошибка',
  };

export const SpellCheckDiff: React.FC<SpellCheckDiffProps> = ({
  result,
  onApply,
  onDismiss,
}) => {
    const correctedSegments = useMemo(() => {
    if (!result.suggestions.length) {
      return [{ type: 'text' as const, value: result.corrected_text }];
    }

    // Сортируем предложения по позиции в тексте
    const sorted = [...result.suggestions].sort((a, b) => a.start - b.start);
    const parts: Array<{
      type: 'text' | 'fix';
      value: string;
      suggestion?: Suggestion;
    }> = [];

    let cursor = 0;

    for (const s of sorted) {
      // Добавляем обычный текст до начала ошибки
      if (s.start > cursor) {
        parts.push({
          type: 'text',
          value: result.original_text.slice(cursor, s.start),
        });
      }

      // ПРОВЕРКА: Если оригинальное слово было токеном изображения, 
      // или если исправление содержит токен — мы НЕ считаем это ошибкой.
      const isMediaToken = s.original.includes('[[') || s.suggestion.includes('[[');

      if (isMediaToken) {
        // Рендерим как обычный текст, чтобы не было красных подчеркиваний в истории
        parts.push({
          type: 'text',
          value: s.suggestion,
        });
      } else {
        // Рендерим как исправление (fix)
        parts.push({
          type: 'fix',
          value: s.suggestion,
          suggestion: s,
        });
      }

      cursor = s.end;
    }

    // Добавляем остаток текста после последней ошибки
    if (cursor < result.original_text.length) {
      parts.push({
        type: 'text',
        value: result.original_text.slice(cursor),
      });
    }

    return parts;
  }, [result]);


  const isLongText =
    result.corrected_text.length > 260 ||
    result.corrected_text.split('\n').length > 4;

  const hasManySuggestions = result.suggestions.length > 4;

  const [showFullText, setShowFullText] = useState(false);
  const [showChanges, setShowChanges] = useState(!(isLongText || hasManySuggestions));

  useEffect(() => {
    setShowFullText(false);
    setShowChanges(!(isLongText || hasManySuggestions));
  }, [result, isLongText, hasManySuggestions]);

  if (!result.has_issues) {
    return (
      <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-green-500/10 border border-green-500/20 animate-in fade-in slide-in-from-top-2 duration-200">
        <div className="flex items-center justify-center w-6 h-6 rounded-full bg-green-500/20">
          <Check size={14} className="text-green-400" />
        </div>
        <span className="text-sm text-green-300">Ошибок не найдено </span>
        <button
          onClick={onDismiss}
          className="ml-auto p-1 rounded-full text-white/40 hover:text-white/70 hover:bg-white/10 transition-colors"
        >
          <X size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] animate-in fade-in slide-in-from-top-2 duration-200">
      {/* Заголовок */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.06] bg-white/[0.02]">
        <WandSparkles size={14} className="text-amber-400" />
        <span className="text-sm text-white/80 font-medium">
          Найдено {result.suggestions.length}{' '}
          {result.suggestions.length === 1
            ? 'исправление'
            : result.suggestions.length < 5
              ? 'исправления'
              : 'исправлений'}
        </span>
        <button
          onClick={onDismiss}
          className="ml-auto p-1 rounded-full text-white/40 hover:text-white/70 hover:bg-white/10 transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      {/* Только исправленный текст */}
      <div className="px-3 py-2.5">
        <div className="mb-2 text-sm text-white/45">
          Исправленный текст
        </div>

        <div className="rounded-lg   px-3 py-2.5">
          <div
            className={`relative ${
              !showFullText && isLongText ? 'max-h-[160px] overflow-hidden' : ''
            }`}
          >
            <p className="text-[16px] leading-relaxed text-white/90 whitespace-pre-wrap break-words">
              {correctedSegments.map((seg, i) => {
                if (seg.type === 'text') {
                  return <span key={i}>{seg.value}</span>;
                }

                return (
                  <span
                    key={i}
                    className="mx-[1px] inline-flex items-center px-1.5 py-0.5 rounded-md bg-green-500/15 border border-green-500/20"
                  >
                    <span className="text-[16px] font-medium text-green-400">
                      {seg.value}
                    </span>
                  </span>
                );
              })}
            </p>

            {!showFullText && isLongText && (
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[#162018] to-transparent" />
            )}
          </div>

          {isLongText && (
            <button
              onClick={() => setShowFullText(prev => !prev)}
              className="mt-2 text-sm text-green-400 hover:text-green-300 transition-colors"
            >
              {showFullText ? 'Свернуть текст' : 'Показать весь текст'}
            </button>
          )}
        </div>
      </div>

      {/* Что исправлено */}
      <div className="border-t border-white/[0.06] px-3 py-2.5">
        <button
          type="button"
          onClick={() => setShowChanges(prev => !prev)}
          className="w-full flex items-center justify-between gap-2 text-left"
        >
          <div className="text-sm text-white/45">
            Что исправлено
          </div>

          <div className="flex items-center gap-2 text-white/40 px-2 hover:bg-white/10 rounded-xl">
            {!showChanges && (
              <span className="text-xs">
                {result.suggestions.length}
              </span>
            )}
            {showChanges ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </button>

        {/* Сводка, если блок свернут */}
        {!showChanges && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {result.suggestions.slice(0, 3).map((s, i) => {
              const style = getStyle(s.category);

              return (
                <div
                  key={i}
                  className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg ${style.bg} border border-current/5`}
                >
                  <span className="text-sm text-white/50 line-through">
                    {s.original}
                  </span>
                  <span className="text-sm text-white/30">→</span>
                  <span className={`text-sm font-medium ${style.text}`}>
                    {s.suggestion}
                  </span>
                </div>
              );
            })}

            {result.suggestions.length > 3 && (
              <div className="inline-flex items-center px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] text-sm text-white/45">
                + ещё {result.suggestions.length - 3}
              </div>
            )}
          </div>
        )}

        {/* Полный список */}
        {showChanges && (
          <div className={`mt-2 space-y-2 ${result.suggestions.length > 6 ? 'max-h-[260px] overflow-y-auto pr-1' : ''}`}>
            {result.suggestions.map((s, i) => {
              const style = getStyle(s.category);

              return (
                <div
                  key={i}
                  className="rounded-lg  px-3 py-2"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md ${style.bg} border border-current/10`}
                    >
                      <span className={`text-sm font-medium ${style.text}`}>
                        {style.label}
                      </span>
                    </span>

                    <span className="text-[16px] text-white/50 line-through break-all">
                      {s.original}
                    </span>

                    <span className="text-[16px] text-white/30">→</span>

                    <span className={`text-[16px] font-medium ${style.text} break-all`}>
                      {s.suggestion}
                    </span>
                  </div>

                  <div className="mt-1 text-sm text-white/55">
                    {s.message}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Кнопки */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-t border-white/[0.06] bg-white/[0.02]">
        <button
          onClick={() => onApply(result.corrected_text)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-600/40 hover:bg-green-600/60 text-white text-sm font-medium transition-colors"
        >
          <Check size={14} />
          Применить все
        </button>
        <button
          onClick={onDismiss}
          className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.08] text-white/60 text-sm transition-colors"
        >
          Оставить как есть
        </button>
      </div>
    </div>
  );
};