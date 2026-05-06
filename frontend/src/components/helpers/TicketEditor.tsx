import { useCallback, useRef, useState, useEffect, useMemo } from 'react';
import { useEditor, EditorContent, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import ImageExtension from '@tiptap/extension-image';
import Placeholder from '@tiptap/extension-placeholder';
import { ImagePlus, Bold, Italic, Loader2, WandSparkles } from 'lucide-react';
import { proofreadingApi } from '../../api/client';
import { attachmentsApi } from '../../api/attachments';
import { SpellCheckDiff } from './SpellCheckDiff';

// ─── Типы ─────────────────────────────────────────────────────────────────────

export type DescriptionBlock =
  | { id: string; type: 'text'; value: string }
  | {
      id: string;
      type: 'image';
      localFile?: File;
      localPreview?: string;
      attachmentId?: string;
    };

// ─── Кастомный Image extension ────────────────────────────────────────────────
// Стандартный @tiptap/extension-image НЕ хранит data-attachment-id.
// Из-за этого при любом изменении в редакторе attachmentId терялся,
// и уже сохранённая картинка превращалась обратно в [[local-image:...]].

const TicketImage = ImageExtension.extend({
  addAttributes() {
    return {
      ...(this.parent?.() ?? {}),

      // Наш внутренний id блока (чтобы связать <img> с DescriptionBlock)
      blockId: {
        default: null,
        parseHTML: (el) =>
          el.getAttribute('data-block-id') || el.getAttribute('alt'),
        renderHTML: (attrs) =>
          attrs.blockId
            ? { 'data-block-id': attrs.blockId, alt: attrs.blockId }
            : {},
      },

      // ID вложения на сервере (главное что мы храним!)
      attachmentId: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-attachment-id'),
        renderHTML: (attrs) =>
          attrs.attachmentId
            ? { 'data-attachment-id': attrs.attachmentId }
            : {},
      },
    };
  },
});

// ─── Хелперы ──────────────────────────────────────────────────────────────────

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

export function serializeBlocks(blocks: DescriptionBlock[]): string {
  return blocks
    .map((b) => {
      if (b.type === 'text') return b.value.trim();
      if (b.type === 'image') {
        return b.attachmentId
          ? `[[image:${b.attachmentId}]]`
          : `[[local-image:${b.id}]]`;
      }
      return '';
    })
    .filter(Boolean)
    .join('\n\n');
}

export function deserializeToBlocks(text: string): DescriptionBlock[] {
  const RE = /\[\[(image|local-image):([^\]]+)\]\]/g;
  const blocks: DescriptionBlock[] = [];
  let last = 0;
  let m: RegExpExecArray | null;

  while ((m = RE.exec(text)) !== null) {
    const before = text.slice(last, m.index).trim();
    if (before) blocks.push({ id: makeId(), type: 'text', value: before });

    if (m[1] === 'image') {
      blocks.push({ id: makeId(), type: 'image', attachmentId: m[2] });
    }
    // local-image в сохранённых данных — это мусор от предыдущих багов.
    // Показываем как битый блок, но не теряем молча.
    if (m[1] === 'local-image') {
      blocks.push({ id: m[2], type: 'image' });
    }

    last = RE.lastIndex;
  }

  const rest = text.slice(last).trim();
  if (rest) blocks.push({ id: makeId(), type: 'text', value: rest });
  if (!blocks.length) blocks.push({ id: makeId(), type: 'text', value: '' });

  return blocks;
}

// ─── Toolbar ──────────────────────────────────────────────────────────────────

function EditorToolbar({
  editor,
  onInsertImage,
  onSpellCheck,
  spellChecking,
  hasText,
}: {
  editor: Editor | null;
  onInsertImage: () => void;
  onSpellCheck: () => void;
  spellChecking: boolean;
  hasText: boolean;
}) {
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    if (!editor) return;
    const handler = () => forceUpdate((n) => n + 1);
    editor.on('selectionUpdate', handler);
    editor.on('transaction', handler);
    return () => {
      editor.off('selectionUpdate', handler);
      editor.off('transaction', handler);
    };
  }, [editor]);

  if (!editor) return null;

  const btnCls = (active: boolean) =>
    `px-2.5 py-1.5 rounded-lg border text-sm transition-all ${
      active
        ? 'bg-red-500/20 border-red-500/40 text-red-400 shadow-[0_0_8px_rgba(239,68,68,0.15)]'
        : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/[0.08] text-white/60 hover:text-white'
    }`;

  return (
    <div className="flex items-center gap-1.5 mb-2 px-1 flex-wrap">
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={btnCls(editor.isActive('bold'))}
        title="Жирный (Ctrl+B)"
      >
        <Bold size={15} />
      </button>
      <button
        type="button"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={btnCls(editor.isActive('italic'))}
        title="Курсив (Ctrl+I)"
      >
        <Italic size={15} />
      </button>

      <div className="w-px h-5 bg-white/[0.08] mx-1" />

      <button
        type="button"
        onClick={onInsertImage}
        className={btnCls(false)}
        title="Вставить изображение"
      >
        <ImagePlus size={15} />
      </button>

      <div className="w-px h-5 bg-white/[0.08] mx-1" />

      <button
        type="button"
        onClick={onSpellCheck}
        disabled={spellChecking || !hasText}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                   bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20
                   text-amber-400 hover:text-amber-300 font-medium
                   transition-all disabled:opacity-30 disabled:cursor-not-allowed"
      >
        {spellChecking ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <WandSparkles size={14} />
        )}
        {spellChecking ? 'Проверка...' : 'Проверить'}
      </button>
    </div>
  );
}

// ─── Основной компонент ───────────────────────────────────────────────────────

interface TicketEditorProps {
  blocks: DescriptionBlock[];
  onChange: (blocks: DescriptionBlock[]) => void;
}

export function TicketEditor({ blocks, onChange }: TicketEditorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [spellChecking, setSpellChecking] = useState(false);
  const [spellResult, setSpellResult] = useState<any>(null);

  // ────────────────────────────────────────────────────────────────────────────
  // КЛЮЧЕВОЙ ФИКС: imageFiles храним в ref, а не в state.
  // useState — асинхронный, и при быстрой вставке картинки
  // syncBlocksFromEditor мог не видеть File, потому что setState
  // ещё не применился. useRef обновляется мгновенно.
  // ────────────────────────────────────────────────────────────────────────────
  const imageFilesRef = useRef<Map<string, File>>(new Map());

  const insertImageRef = useRef<(file: File) => void>(() => {});

  // ── Загрузка blob URL для картинок с attachmentId ──────────────────────────
  const [resolvedUrls, setResolvedUrls] = useState<Map<string, string>>(
    new Map()
  );
  const [urlsReady, setUrlsReady] = useState(false);

  useEffect(() => {
    const attachmentBlocks = blocks.filter(
      (b) =>
        b.type === 'image' &&
        (b as any).attachmentId &&
        !(b as any).localPreview
    ) as any[];

    if (!attachmentBlocks.length) {
      setUrlsReady(true);
      return;
    }

    let cancelled = false;
    const createdUrls: string[] = [];

    (async () => {
      const map = new Map<string, string>();

      await Promise.all(
        attachmentBlocks.map(async (block) => {
          try {
            const { download_url } =
              await attachmentsApi.getPresignedDownloadUrl(
                block.attachmentId
              );
            let url = download_url;
            if (
              url.includes('minio:9000') ||
              url.includes('maildev:9000')
            ) {
              url = url.replace(
                /http:\/\/(minio|maildev):9000/g,
                'http://localhost:9900'
              );
            }
            const res = await fetch(url);
            if (!res.ok) throw new Error();
            const blob = await res.blob();
            const objectUrl = URL.createObjectURL(blob);
            createdUrls.push(objectUrl);
            map.set(block.id, objectUrl);
          } catch (err) {
            console.error(
              'Failed to resolve image URL for block:',
              block.id,
              err
            );
          }
        })
      );

      if (!cancelled) {
        setResolvedUrls(map);
        setUrlsReady(true);
      }
    })();

    return () => {
      cancelled = true;
      createdUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── HTML для инициализации ────────────────────────────────────────────────

  function markdownToHtml(text: string): string {
    return text
      .replace(/\*\*\*([^*\n]+)\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }

  const initialHtml = useMemo(() => {
    return blocks
      .map((b) => {
        if (b.type === 'text') {
          return `<p>${markdownToHtml(b.value)}</p>`;
        }
        if (b.type === 'image') {
          if ((b as any).localPreview) {
            return `<img src="${(b as any).localPreview}" alt="${b.id}" data-block-id="${b.id}" />`;
          }
          if ((b as any).attachmentId) {
            const resolvedUrl = resolvedUrls.get(b.id);
            if (resolvedUrl) {
              return `<img src="${resolvedUrl}" alt="${b.id}" data-block-id="${b.id}" data-attachment-id="${(b as any).attachmentId}" />`;
            }
            return `<p style="color:rgba(255,255,255,0.3);font-size:14px">[Изображение загружается...]</p>`;
          }
          // Битый блок (local-image из БД без файла)
          return `<p style="color:rgba(255,200,100,0.5);font-size:14px">[⚠ Изображение не было сохранено корректно]</p>`;
        }
        return '';
      })
      .join('');
  }, [blocks, resolvedUrls]);

  // ── Ref на editor ─────────────────────────────────────────────────────────
  const editorRef = useRef<Editor | null>(null);

  // ── Синхронизация editor → blocks ─────────────────────────────────────────

  const syncBlocksFromEditor = useCallback(
    (ed: Editor) => {
      const html = ed.getHTML();
      const newBlocks: DescriptionBlock[] = [];
      const div = document.createElement('div');
      div.innerHTML = html;

      const htmlToMarkdown = (el: Element): string => {
        let result = '';
        el.childNodes.forEach((node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            result += node.textContent || '';
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            const child = node as Element;
            const tag = child.tagName.toLowerCase();
            const inner = htmlToMarkdown(child);

            if (tag === 'strong' || tag === 'b') {
              if (child.querySelector('em, i')) {
                result += `***${inner.replace(/\*/g, '')}***`;
              } else {
                result += `**${inner}**`;
              }
            } else if (tag === 'em' || tag === 'i') {
              result += `*${inner}*`;
            } else if (tag === 'br') {
              result += '\n';
            } else {
              result += inner;
            }
          }
        });
        return result;
      };

      div.childNodes.forEach((node) => {
        if (node.nodeName === 'IMG') {
          const img = node as HTMLImageElement;
          const src = img.src || '';
          const blockId =
            img.getAttribute('data-block-id') ||
            img.getAttribute('alt') ||
            makeId();
          const attachmentId = img.getAttribute('data-attachment-id');

          if (attachmentId) {
            // Уже сохранённая на сервере картинка — сохраняем attachmentId
            newBlocks.push({
              id: blockId,
              type: 'image',
              attachmentId,
              localPreview: src,
            });
          } else if (src.startsWith('blob:') || src.startsWith('data:')) {
            // Новая локальная картинка
            newBlocks.push({
              id: blockId,
              type: 'image',
              localFile: imageFilesRef.current.get(blockId),
              localPreview: src,
            });
          }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          const el = node as Element;
          if (el.classList?.contains('img-placeholder')) return;

          const tag = el.tagName?.toLowerCase();
          let text = '';
          if (tag === 'p' || tag === 'div') {
            text = htmlToMarkdown(el);
          } else {
            text = node.textContent || '';
          }

          if (text.trim()) {
            newBlocks.push({ id: makeId(), type: 'text', value: text });
          }
        }
      });

      if (!newBlocks.length)
        newBlocks.push({ id: makeId(), type: 'text', value: '' });
      onChange(newBlocks);
    },
    [onChange]
  );

  // ── Создание редактора ─────────────────────────────────────────────────────

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        blockquote: false,
        bulletList: false,
        orderedList: false,
        listItem: false,
        horizontalRule: false,
      }),
      TicketImage.configure({ inline: false, allowBase64: true }),
      Placeholder.configure({
        placeholder: 'Напишите подробное описание проблемы...',
      }),
    ],
    content: initialHtml,
    editorProps: {
      attributes: {
        class:
          'min-h-[200px] p-5 focus:outline-none text-white text-base leading-relaxed prose prose-invert max-w-none',
      },
      handleDrop: (_view, event) => {
        const files = Array.from(event.dataTransfer?.files || []).filter((f) =>
          f.type.startsWith('image/')
        );
        if (files.length) {
          event.preventDefault();
          files.forEach((f) => insertImageRef.current(f));
          return true;
        }
        return false;
      },
      handlePaste: (_view, event) => {
        const files = Array.from(event.clipboardData?.files || []).filter(
          (f) => f.type.startsWith('image/')
        );
        if (files.length) {
          event.preventDefault();
          files.forEach((f) => insertImageRef.current(f));
          return true;
        }
        return false;
      },
    },
    onUpdate: ({ editor: ed }) => {
      syncBlocksFromEditor(ed);
    },
  });

  useEffect(() => {
    editorRef.current = editor;
  }, [editor]);

  // ── Обновляем контент когда blob URLs готовы ──────────────────────────────

  useEffect(() => {
    if (!editor || !urlsReady || resolvedUrls.size === 0) return;
    const timer = setTimeout(() => {
      editor.commands.setContent(initialHtml);
    }, 50);
    return () => clearTimeout(timer);
  }, [urlsReady, resolvedUrls]); // eslint-disable-line

  // ── Вставка картинки ───────────────────────────────────────────────────────

  const insertImageFile = useCallback(
    (file: File) => {
      if (!editor) return;
      const id = makeId();
      const url = URL.createObjectURL(file);

      // Сохраняем в ref (мгновенно, без ожидания рендера)
      imageFilesRef.current.set(id, file);

      editor
        .chain()
        .focus()
        .setImage({
          src: url,
          alt: id,
          // Кастомные атрибуты нашего TicketImage
          blockId: id,
        } as any)
        .run();
    },
    [editor]
  );

  useEffect(() => {
    insertImageRef.current = insertImageFile;
  }, [insertImageFile]);

  // ── SpellCheck ─────────────────────────────────────────────────────────────

  const handleSpellCheck = useCallback(async () => {
    if (!editor) return;
    const text = editor.getText();
    if (!text.trim()) return;
    setSpellChecking(true);
    setSpellResult(null);
    try {
      setSpellResult(await proofreadingApi.spellCheck(text));
    } catch (e) {
      console.error('SpellCheck:', e);
    } finally {
      setSpellChecking(false);
    }
  }, [editor]);

  const handleApplySpellCheck = useCallback(
    (corrected: string) => {
      if (!editor) return;
      const currentText = editor.getText();
      let html = editor.getHTML();
      const oldWords = currentText.split(/(\s+)/);
      const newWords = corrected.split(/(\s+)/);
      if (oldWords.length === newWords.length) {
        for (let i = 0; i < oldWords.length; i++) {
          if (oldWords[i] !== newWords[i] && oldWords[i].trim()) {
            html = html.replace(oldWords[i], newWords[i]);
          }
        }
        editor.commands.setContent(html);
      }
      setSpellResult(null);
    },
    [editor]
  );

  // ── Рендер ─────────────────────────────────────────────────────────────────

  if (!urlsReady) {
    return (
      <div className="min-h-[200px] rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center">
        <div className="flex items-center gap-3 text-white/40">
          <Loader2 size={20} className="animate-spin" />
          <span className="text-base">Загрузка изображений...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => {
          Array.from(e.target.files || []).forEach((f) => insertImageFile(f));
          e.target.value = '';
        }}
      />

      <EditorToolbar
        editor={editor}
        onInsertImage={() => fileInputRef.current?.click()}
        onSpellCheck={handleSpellCheck}
        spellChecking={spellChecking}
        hasText={!!editor?.getText().trim()}
      />

      <div
        className="rounded-2xl bg-white/[0.03] border border-white/[0.08]
                    focus-within:border-white/[0.15] transition-colors overflow-hidden"
      >
        <EditorContent editor={editor} />
      </div>

      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        className="mt-3 flex items-center gap-2 px-4 py-2 rounded-xl text-sm
                   bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08]
                   text-white/50 hover:text-white/80 transition-all"
      >
        <ImagePlus size={16} /> Добавить изображение
      </button>

      {spellResult && (
        <div className="mt-3">
          <SpellCheckDiff
            result={spellResult}
            onApply={handleApplySpellCheck}
            onDismiss={() => setSpellResult(null)}
          />
        </div>
      )}
    </div>
  );
}