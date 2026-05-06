// components/helpers/RichDescription.tsx
import { useState, useEffect, useMemo } from 'react';
import { Loader2, ImageOff } from 'lucide-react';
import { attachmentsApi } from '../../api/attachments';

interface RichDescriptionProps {
  text: string;
  className?: string;
}

// Паттерн: ![image](attachment:UUID)
const ATTACHMENT_REGEX = /!\[image\]\(attachment:([a-f0-9-]{36})\)/g;

interface Segment {
  type: 'text' | 'image';
  value: string; // текст или attachment ID
}

function parseDescription(text: string): Segment[] {
  const segments: Segment[] = [];
  let lastIndex = 0;

  const regex = new RegExp(ATTACHMENT_REGEX.source, 'g');
  let match;

  while ((match = regex.exec(text)) !== null) {
    // Текст до маркера
    if (match.index > lastIndex) {
      segments.push({ type: 'text', value: text.slice(lastIndex, match.index) });
    }
    // Маркер картинки
    segments.push({ type: 'image', value: match[1] });
    lastIndex = regex.lastIndex;
  }

  // Остаток текста
  if (lastIndex < text.length) {
    segments.push({ type: 'text', value: text.slice(lastIndex) });
  }

  return segments;
}

function InlineImage({ attachmentId }: { attachmentId: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const { download_url } = await attachmentsApi.getPresignedDownloadUrl(attachmentId);
        let finalUrl = download_url;
        // Фикс для локальной разработки
        if (finalUrl.includes('minio:9000') || finalUrl.includes('maildev:9000')) {
          finalUrl = finalUrl.replace(/http:\/\/(minio|maildev):9000/g, 'http://localhost:9900');
        }

        const response = await fetch(finalUrl);
        if (!response.ok) throw new Error('Failed to fetch');
        const blob = await response.blob();
        if (!cancelled) {
          setUrl(URL.createObjectURL(blob));
          setLoading(false);
        }
      } catch {
        if (!cancelled) { setError(true); setLoading(false); }
      }
    })();

    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [attachmentId]);

  if (loading) return (
    <div className="inline-flex items-center gap-2 my-2 px-3 py-2 bg-white/[0.04] rounded-lg border border-white/[0.08]">
      <Loader2 size={16} className="animate-spin text-white/30" />
      <span className="text-sm text-white/40">Загрузка изображения...</span>
    </div>
  );

  if (error) return (
    <div className="inline-flex items-center gap-2 my-2 px-3 py-2 bg-red-500/10 rounded-lg border border-red-500/20">
      <ImageOff size={16} className="text-red-400" />
      <span className="text-sm text-red-400">Не удалось загрузить изображение</span>
    </div>
  );

  return (
    <img
      src={url!}
      alt="Вложение"
      className="max-w-full max-h-[400px] rounded-xl border border-white/[0.08] my-3 object-contain"
      loading="lazy"
    />
  );
}

export function RichDescription({ text, className = '' }: RichDescriptionProps) {
  const segments = useMemo(() => parseDescription(text), [text]);

  // Если нет маркеров — просто текст (оптимизация)
  if (segments.length === 1 && segments[0].type === 'text') {
    return (
      <p className={`whitespace-pre-wrap break-words ${className}`}>
        {segments[0].value}
      </p>
    );
  }

  return (
    <div className={className}>
      {segments.map((seg, i) => {
        if (seg.type === 'text') {
          return (
            <span key={i} className="whitespace-pre-wrap break-words">
              {seg.value}
            </span>
          );
        }
        return <InlineImage key={i} attachmentId={seg.value} />;
      })}
    </div>
  );
}