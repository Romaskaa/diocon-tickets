import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, ImageOff } from 'lucide-react';
import { attachmentsApi } from '../../api/attachments';

// ─── Inline formatting 

function renderInlineFormatting(text: string): React.ReactNode[] {
  const result: React.ReactNode[] = [];
  // Порядок важен: сначала *** потом ** потом *
  const regex = /(\*\*\*(?!\s)([^*]+?)(?<!\s)\*\*\*|\*\*(?!\s)([^*]+?)(?<!\s)\*\*|\*(?!\s)([^*]+?)(?<!\s)\*)/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      result.push(<span key={key++}>{text.slice(lastIndex, match.index)}</span>);
    }

    const token = match[0];

    if (token.startsWith('***') && token.endsWith('***')) {
      result.push(
        <strong key={key++} className="font-bold italic text-[var(--text-primary)]">
          {token.slice(3, -3)}
        </strong>
      );
    } else if (token.startsWith('**') && token.endsWith('**')) {
      result.push(
        <strong key={key++} className="font-semibold text-[var(--text-primary)]">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('*') && token.endsWith('*')) {
      result.push(
        <em key={key++} className="italic text-[var(--text-primary)]">
          {token.slice(1, -1)}
        </em>
      );
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    result.push(<span key={key++}>{text.slice(lastIndex)}</span>);
  }

  return result;
}

// ─── Сегменты ────

type Segment =
  | { type: 'text'; value: string }
  | { type: 'image'; attachmentId: string }
  | { type: 'local-image'; localId: string };

// Новый markdown-формат: ![image](attachment:UUID) и ![image](local:blockId)
// Legacy формат: [[image:UUID]] и [[local-image:blockId]] (для обратной совместимости)
const LEGACY_IMAGE_RE = /\[\[(image|local-image):([^[\]]+)\]\]/g;

const MD_IMAGE_RE = /!\[image\]\((media):\/\/([^)]+)|!\[image\]\((attachment|local):([^)]+)\)/g;

function parseContent(text: string): Segment[] {
  const segments: Segment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  const mdRegex = new RegExp(MD_IMAGE_RE.source, 'g');

  while ((match = mdRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', value: text.slice(lastIndex, match.index) });
    }

    if (match[1] === 'media') {
      // ![image](media://UUID) — группы: [1]='media', [2]=UUID
      segments.push({ type: 'image', attachmentId: match[2] });
    } else if (match[3] === 'attachment') {
      // ![image](attachment:UUID) — группы: [3]='attachment', [4]=UUID
      segments.push({ type: 'image', attachmentId: match[4] });
    } else if (match[3] === 'local') {
      // ![image](local:blockId) — группы: [3]='local', [4]=blockId
      segments.push({ type: 'local-image', localId: match[4] });
    }

    lastIndex = mdRegex.lastIndex;
  }

  // Legacy формат [[image:UUID]]
  if (segments.length === 0 && lastIndex === 0) {
    const legacyRegex = new RegExp(LEGACY_IMAGE_RE.source, 'g');
    while ((match = legacyRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        segments.push({ type: 'text', value: text.slice(lastIndex, match.index) });
      }
      if (match[1] === 'image') {
        segments.push({ type: 'image', attachmentId: match[2] });
      } else {
        segments.push({ type: 'local-image', localId: match[2] });
      }
      lastIndex = legacyRegex.lastIndex;
    }
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', value: text.slice(lastIndex) });
  }

  return segments;
}

// ─── Remote Image 

function RemoteImage({ attachmentId }: { attachmentId: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;

    (async () => {
      try {
        const { download_url } = await attachmentsApi.getPresignedDownloadUrl(attachmentId);
        let finalUrl = download_url;
        if (finalUrl.includes('minio:9000') || finalUrl.includes('maildev:9000')) {
          finalUrl = finalUrl.replace(/http:\/\/(minio|maildev):9000/g, 'http://localhost:9900');
        }
        const res = await fetch(finalUrl);
        if (!res.ok) throw new Error('Failed');
        const blob = await res.blob();
        objectUrl = URL.createObjectURL(blob);
        if (active) { setSrc(objectUrl); setLoading(false); }
      } catch (err) {
        console.error('Remote image load failed:', attachmentId, err);
        if (active) { setFailed(true); setLoading(false); }
      }
    })();

    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [attachmentId]);

  if (loading) return (
    <div className="my-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.08]">
      <Loader2 className="w-4 h-4 animate-spin text-[var(--text-primary)]/30" />
      <span className="text-sm text-[var(--text-primary)]/40">Загрузка изображения...</span>
    </div>
  );

  if (failed || !src) return (
    <div className="my-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20">
      <ImageOff className="w-4 h-4 text-red-400" />
      <span className="text-sm text-red-400">Не удалось загрузить изображение</span>
    </div>
  );

  return <img src={src} alt="attachment"
    className="my-4 max-w-full max-h-[400px] rounded-2xl border border-white/[0.08] object-contain" />;
}

// ─── Основной компонент ──────────────────────────────────────────────────────

interface Props {
  text: string;
  className?: string;
  localImageBlocks?: Array<{ id: string; localPreview: string }>;
}

export function TicketDescriptionContent({ text, className, localImageBlocks }: Props) {
  const segments = useMemo(() => parseContent(text || ''), [text]);

  return (
    <div className={className}>
      {segments.map((seg, i) => {
        if (seg.type === 'text') {
          return seg.value
            ? <div key={i} className="whitespace-pre-wrap break-words">{renderInlineFormatting(seg.value)}</div>
            : null;
        }
        if (seg.type === 'image') return <RemoteImage key={i} attachmentId={seg.attachmentId} />;
        if (seg.type === 'local-image') {
          const lb = localImageBlocks?.find(b => b.id === seg.localId);
          return lb?.localPreview
            ? <img key={i} src={lb.localPreview} alt="preview"
              className="my-4 max-w-full max-h-[280px] rounded-2xl border border-white/[0.08] object-contain" />
            : null;
        }
        return null;
      })}
    </div>
  );
}