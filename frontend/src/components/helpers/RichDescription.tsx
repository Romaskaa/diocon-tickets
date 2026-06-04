// components/helpers/RichDescription.tsx
import { useState, useEffect, useMemo } from 'react';
import { Loader2, ImageOff } from 'lucide-react';
import { attachmentsApi } from '../../api/attachments';

interface RichDescriptionProps {
  text: string;
  className?: string;
}

// ─── Оба формата ────
// Новый:   ![любой alt](attachment:UUID)
// Legacy:  [[image:UUID]]
const ATTACHMENT_REGEX =
  /!\[[^\]]*\]\(media:\/\/([a-f0-9-]{36})\)|!\[[^\]]*\]\(attachment:([a-f0-9-]{36})\)|\[\[image:([a-f0-9-]{36})\]\]/g;
  
interface Segment {
  type: 'text' | 'image';
  value: string; // текст или attachment ID
}

function parseDescription(text: string): Segment[] {
  const segments: Segment[] = [];
  let lastIndex = 0;

  const regex = new RegExp(ATTACHMENT_REGEX.source, 'g');
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', value: text.slice(lastIndex, match.index) });
    }
    // Берём ID из первой или второй группы (новый / legacy)
    const attachmentId = match[1] || match[2] || match[3];
    segments.push({ type: 'image', value: attachmentId });
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', value: text.slice(lastIndex) });
  }

  return segments;
}

/* ── Inline image ── */

function InlineImage({ attachmentId }: { attachmentId: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    (async () => {
      try {
        const { download_url } = await attachmentsApi.getPresignedDownloadUrl(attachmentId);
        const finalUrl = download_url.replace(
          /http:\/\/(minio|maildev):9000/g,
          'http://localhost:9900'
        );
        const response = await fetch(finalUrl);
        if (!response.ok) throw new Error('Failed to fetch');
        const blob = await response.blob();
        if (!cancelled) {
          objectUrl = URL.createObjectURL(blob);
          setUrl(objectUrl);
          setLoading(false);
        }
      } catch {
        if (!cancelled) { setError(true); setLoading(false); }
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [attachmentId]);

  if (loading) {
    return (
      <div className="inline-flex items-center gap-2 my-2 px-3 py-2
                      bg-white/[0.04] rounded-lg border border-white/[0.08]">
        <Loader2 size={16} className="animate-spin text-[var(--text-primary)]/30" />
        <span className="text-sm text-[var(--text-primary)]/40">Загрузка изображения...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="inline-flex items-center gap-2 my-2 px-3 py-2
                      bg-red-500/10 rounded-lg border border-red-500/20">
        <ImageOff size={16} className="text-red-400" />
        <span className="text-sm text-red-400">Не удалось загрузить изображение</span>
      </div>
    );
  }

  return (
    <img
      src={url!}
      alt="Вложение"
      className="max-w-full max-h-[400px] rounded-xl border border-white/[0.08]
                 my-3 object-contain cursor-pointer hover:opacity-90 transition-opacity"
      loading="lazy"
      onClick={() => url && window.open(url, '_blank')}
    />
  );
}

/* ── Main component ── */

export function RichDescription({ text, className = '' }: RichDescriptionProps) {
  const segments = useMemo(() => parseDescription(text), [text]);

  // Оптимизация: только текст — без лишних div
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