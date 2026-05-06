// components/helpers/CommentItem.tsx
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  User, Reply, Paperclip, MoreVertical, Edit2, Trash2,
  ChevronDown, ChevronUp, Loader2, Smile, X, File, Image,
} from 'lucide-react';
import { ticketsApi } from '../../api/client';
import { attachmentsApi } from '../../api/attachments';
import { useToast } from '../ui/use-toast';

interface CommentItemProps {
  comment: any;
  isReplying: boolean;
  onReply: (id: string) => void;
  onSendReply: (id: string, text: string) => Promise<any>;
  onEditComment: (id: string, newText: string) => Promise<void>;
  onDeleteComment: (id: string) => void;
  replyText: string;
  setReplyText: (text: string) => void;
  replyingTo: string | null;
  setReplyingTo: (id: string | null) => void;
  getAuthorName: (comment: any) => string;
  formatRelativeTime: (date: string) => string;
  getAvatarColor: (role: string) => string;
  handleDownload: (id: string) => void;
  ticketId: string;
  currentUser: any;
  level?: number;
  onReplyAdded?: (parentId: string, newReply: any) => void;
  onReplyDeleted?: (replyId: string, parentId: string) => void;
  onReplyEdited?: (replyId: string, newText: string, parentId: string) => void;
  onReactionUpdated?: (commentId: string, reactions: any) => void;
}

const REACTIONS_CONFIG = [
  { type: 'like',        emoji: '/media/icons/like.svg',        label: 'Нравится',  isImage: true },
  { type: 'thanks',      emoji: '/media/icons/thanks.svg',      label: 'Спасибо',   isImage: true },
  { type: 'in_progress', emoji: '/media/icons/in_progress.svg', label: 'В работе',  isImage: true },
  { type: 'resolved',    emoji: '/media/icons/resolved.svg',    label: 'Решено',    isImage: true },
  { type: 'important',   emoji: '/media/icons/important.svg',   label: 'Важно',     isImage: true },
];

const getReactionChipClass = (isActive: boolean) =>
  [
    'inline-flex items-center gap-1.5 h-7 px-2.5 rounded-full border select-none',
    'backdrop-blur-sm transition-all duration-150 active:scale-[0.98]',
    'shadow-[inset_0_1px_0_rgba(255,255,255,0.03),0_1px_2px_rgba(0,0,0,0.18)]',
    isActive
      ? 'bg-blue-900/40 border-[#5b79ad]/35 text-white hover:bg-[#2b3950]'
      : 'bg-white/[0.04] border-white/[0.08] text-white/70 hover:bg-white/[0.065] hover:border-white/[0.12] hover:text-white/85 hover:-translate-y-[1px]',
  ].join(' ');

const getReactionPickerItemClass = (isActive: boolean) =>
  [
    'h-10 w-10 rounded-full flex items-center justify-center',
    'transition-all duration-150 active:scale-95',
    isActive
      ? 'bg-white/[0.10] scale-110 shadow-[0_4px_14px_rgba(0,0,0,.22)]'
      : 'hover:bg-white/[0.08] hover:scale-110',
  ].join(' ');

// ─── Компонент превью файла в ответе ─────────────────────────────────────────

interface ReplyFilePreviewProps {
  file: File;
  onRemove: () => void;
}

function ReplyFilePreview({ file, onRemove }: ReplyFilePreviewProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const isImage = file.type.startsWith('image/');

  useEffect(() => {
    if (!isImage) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file, isImage]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="relative group flex items-center gap-2 px-2.5 py-1.5 bg-white/[0.05] border border-white/[0.08] rounded-lg">
      {isImage && preview ? (
        <img src={preview} alt={file.name} className="w-8 h-8 rounded object-cover flex-shrink-0" />
      ) : (
        <div className="w-8 h-8 rounded bg-white/[0.06] flex items-center justify-center flex-shrink-0">
          <File size={14} className="text-white/40" />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-white/70 truncate max-w-[100px]">{file.name}</p>
        <p className="text-[10px] text-white/30">{formatSize(file.size)}</p>
      </div>
      <button
        onClick={onRemove}
        className="ml-1 p-0.5 rounded text-white/30 hover:text-red-400 hover:bg-white/[0.05] transition-colors flex-shrink-0"
      >
        <X size={12} />
      </button>
    </div>
  );
}

// ─── Основной компонент ───────────────────────────────────────────────────────

export const CommentItem = React.memo(({
  comment,
  isReplying,
  onReply,
  onSendReply,
  onEditComment,
  onDeleteComment,
  replyText,
  setReplyText,
  replyingTo,
  setReplyingTo,
  getAuthorName,
  formatRelativeTime,
  getAvatarColor,
  handleDownload,
  ticketId,
  currentUser,
  level = 0,
  onReplyAdded,
  onReplyDeleted,
  onReplyEdited,
  onReactionUpdated,
}: CommentItemProps) => {
  const [replies, setReplies]                 = useState<any[]>([]);
  const [loadingReplies, setLoadingReplies]   = useState(false);
  const [showReplies, setShowReplies]         = useState(false);
  const [isEditing, setIsEditing]             = useState(false);
  const [editText, setEditText]               = useState(comment.text);
  const [showActions, setShowActions]         = useState(false);
  const [localReplyCount, setLocalReplyCount] = useState(comment.reply_count || 0);
  const [reactionCounts, setReactionCounts]   = useState<Record<string, number>>(comment.reaction_counts || {});
  const [userReactions, setUserReactions]     = useState<string[]>(comment.user_reactions || []);
  const [loadingReaction, setLoadingReaction] = useState(false);
  const [contextMenu, setContextMenu]         = useState<{ x: number; y: number } | null>(null);
  const [showReactionPicker, setShowReactionPicker]         = useState(false);
  const [reactionPickerPosition, setReactionPickerPosition] = useState<{ x: number; y: number } | null>(null);
  const [isHovered, setIsHovered]             = useState(false);
  const [repliesDirty, setRepliesDirty]       = useState(false);

  // ── Файлы для ответа ──────────────────────────────────────────────────────
  const [replyFiles, setReplyFiles]           = useState<File[]>([]);
  const [uploadingReply, setUploadingReply]   = useState(false);
  const replyFileInputRef                     = useRef<HTMLInputElement>(null);

  const replyTextareaRef  = useRef<HTMLTextAreaElement>(null);
  const actionsRef        = useRef<HTMLDivElement>(null);
  const contextMenuRef    = useRef<HTMLDivElement>(null);
  const reactionPickerRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const isInternal    = comment.type === 'internal';
  const isCurrentUser = comment.author_id === currentUser?.user_id;
  const canEdit       = isCurrentUser || currentUser?.role === 'admin';

  // ── Закрытие по клику вне ─────────────────────────────────────────────────
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (actionsRef.current && !actionsRef.current.contains(event.target as Node))
        setShowActions(false);
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node))
        setContextMenu(null);
      if (reactionPickerRef.current && !reactionPickerRef.current.contains(event.target as Node)) {
        setShowReactionPicker(false);
        setReactionPickerPosition(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => { setEditText(comment.text); }, [comment.text]);
  useEffect(() => { setLocalReplyCount(comment.reply_count || 0); }, [comment.reply_count]);
  useEffect(() => {
    setReactionCounts(comment.reaction_counts || {});
    setUserReactions(comment.user_reactions || []);
  }, [comment.reaction_counts, comment.user_reactions]);

  // ── Очистка файлов при закрытии формы ответа ─────────────────────────────
  useEffect(() => {
    if (!isReplying) {
      setReplyFiles([]);
    }
  }, [isReplying]);

  // ── Загрузка ответов ──────────────────────────────────────────────────────
  const forceLoadReplies = useCallback(async () => {
    setLoadingReplies(true);
    try {
      const response = await ticketsApi.getCommentReplies(comment.id, {
        include_internal: currentUser?.role === 'admin' || currentUser?.role === 'support_agent',
        page: 1,
        size: 50,
      });
      setReplies(response.items);
      setRepliesDirty(false);
      setShowReplies(true);
    } catch {
      toast({ title: 'Ошибка', description: 'Не удалось загрузить ответы', variant: 'destructive' });
    } finally {
      setLoadingReplies(false);
    }
  }, [comment.id, currentUser?.role, toast]);

  const loadReplies = useCallback(async () => {
    if (showReplies && !repliesDirty) { setShowReplies(false); return; }
    if (replies.length > 0 && !repliesDirty) { setShowReplies(true); return; }
    await forceLoadReplies();
  }, [showReplies, replies.length, repliesDirty, forceLoadReplies]);

  // ── Реакции ───────────────────────────────────────────────────────────────
  const handleReaction = useCallback(async (reactionType: string) => {
    if (loadingReaction) return;
    setLoadingReaction(true);

    const hadReaction = userReactions.includes(reactionType);
    const newUserReactions = hadReaction
      ? userReactions.filter(r => r !== reactionType)
      : [...userReactions, reactionType];

    const newReactionCounts = { ...reactionCounts };
    if (hadReaction) {
      newReactionCounts[reactionType] = (newReactionCounts[reactionType] || 1) - 1;
      if (newReactionCounts[reactionType] <= 0) delete newReactionCounts[reactionType];
    } else {
      newReactionCounts[reactionType] = (newReactionCounts[reactionType] || 0) + 1;
    }

    setUserReactions(newUserReactions);
    setReactionCounts(newReactionCounts);
    setContextMenu(null);
    setShowReactionPicker(false);
    setReactionPickerPosition(null);

    try {
      await ticketsApi.toggleReaction(comment.id, reactionType);
    } catch {
      setUserReactions(userReactions);
      setReactionCounts(reactionCounts);
      toast({ title: 'Ошибка', description: 'Не удалось поставить реакцию', variant: 'destructive' });
    } finally {
      setLoadingReaction(false);
    }
  }, [comment.id, userReactions, reactionCounts, loadingReaction, toast]);

  // ── Контекстное меню ──────────────────────────────────────────────────────
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const menuWidth = 220, menuHeight = 220;
    let x = e.clientX + 8, y = e.clientY + 8;
    if (x + menuWidth > window.innerWidth) x = e.clientX - menuWidth - 8;
    if (y + menuHeight > window.innerHeight) y = e.clientY - menuHeight - 8;
    setContextMenu({ x, y });
  }, []);

  const openReactionPicker = useCallback((e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    if (showReactionPicker) { setShowReactionPicker(false); setReactionPickerPosition(null); return; }
    const rect = e.currentTarget.getBoundingClientRect();
    const pickerWidth = 260, pickerHeight = 60;
    let x = rect.left, y = rect.bottom + 8;
    if (x + pickerWidth > window.innerWidth - 8) x = window.innerWidth - pickerWidth - 8;
    if (x < 8) x = 8;
    if (y + pickerHeight > window.innerHeight - 8) y = rect.top - pickerHeight - 8;
    setReactionPickerPosition({ x, y });
    setShowReactionPicker(true);
  }, [showReactionPicker]);

  // ── Добавление ответа ─────────────────────────────────────────────────────
  const handleReplyAdded = useCallback(async (newReply: any) => {
    setLocalReplyCount(prev => prev + 1);
    setRepliesDirty(true);
    setLoadingReplies(true);
    try {
      const response = await ticketsApi.getCommentReplies(comment.id, {
        include_internal: currentUser?.role === 'admin' || currentUser?.role === 'support_agent',
        page: 1,
        size: 50,
      });
      setReplies(response.items);
      setRepliesDirty(false);
    } catch {
      setReplies(prev => {
        const exists = prev.some(r => r.id === newReply.id);
        return exists ? prev : [...prev, newReply];
      });
    } finally {
      setLoadingReplies(false);
    }
    setShowReplies(true);
    if (onReplyAdded) onReplyAdded(comment.id, newReply);
  }, [comment.id, currentUser?.role, onReplyAdded]);

  const handleNestedEdit = useCallback(async (replyId: string, newText: string) => {
    await onEditComment(replyId, newText);
    setReplies(prev => prev.map(r =>
      r.id === replyId ? { ...r, text: newText, edited_at: new Date().toISOString() } : r
    ));
  }, [onEditComment]);

  const handleNestedDelete = useCallback((replyId: string) => {
    onDeleteComment(replyId);
    setReplies(prev => prev.filter(r => r.id !== replyId));
    setLocalReplyCount(prev => Math.max(0, prev - 1));
    if (onReplyDeleted) onReplyDeleted(replyId, comment.id);
  }, [comment.id, onDeleteComment, onReplyDeleted]);

  // ── Высота textarea ───────────────────────────────────────────────────────
  const adjustReplyHeight = useCallback(() => {
    const ta = replyTextareaRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = `${Math.min(ta.scrollHeight, 150)}px`; }
  }, []);

  useEffect(() => { adjustReplyHeight(); }, [replyText, adjustReplyHeight]);

  // ── Выбор файлов для ответа ───────────────────────────────────────────────
  const handleReplyFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    if (!selected.length) return;

    const MAX_SIZE = 50 * 1024 * 1024; // 50 MB
    const oversized = selected.filter(f => f.size > MAX_SIZE);
    if (oversized.length) {
      toast({
        title: 'Файл слишком большой',
        description: `Максимальный размер файла — 50 MB. Превышен: ${oversized.map(f => f.name).join(', ')}`,
        variant: 'destructive',
      });
      return;
    }

    setReplyFiles(prev => {
      // Убираем дубли по имени+размеру
      const existing = new Set(prev.map(f => `${f.name}-${f.size}`));
      const unique = selected.filter(f => !existing.has(`${f.name}-${f.size}`));
      return [...prev, ...unique];
    });

    // Сбрасываем input, чтобы можно было выбрать тот же файл повторно
    e.target.value = '';
  };

  const removeReplyFile = (idx: number) => {
    setReplyFiles(prev => prev.filter((_, i) => i !== idx));
  };

  // ── Отправка ответа с файлами ─────────────────────────────────────────────
 const handleLocalSendReply = async (parentId: string, text: string) => {
  const hasText  = text.trim().length > 0;
  const hasFiles = replyFiles.length > 0;

  if (!hasText && !hasFiles) return null;

  setUploadingReply(true);
  try {
    // 1. Отправляем текстовый ответ
    const newReply = await onSendReply(parentId, hasText ? text : '(вложения)');
    if (!newReply) return null;

    // 2. Загружаем файлы если есть
    if (hasFiles && newReply.id) {
      const uploadPromises = replyFiles.map(file =>
        attachmentsApi.uploadAttachment(
          file,
          'comment',   // owner_type — тип владельца
          newReply.id  // owner_id — ID только что созданного ответа
        ).catch(err => {
          console.error(`Failed to upload ${file.name}:`, err);
          toast({
            title: 'Ошибка загрузки',
            description: `Не удалось загрузить файл «${file.name}»`,
            variant: 'destructive',
          });
          return null;
        })
      );
      await Promise.all(uploadPromises);
    }

    // 3. Обновляем UI
    handleReplyAdded(newReply);
    setReplyText('');
    setReplyFiles([]);
    setReplyingTo(null);

    return newReply;
  } catch (error) {
    console.error('Failed to send reply:', error);
    toast({
      title: 'Ошибка',
      description: 'Не удалось отправить ответ',
      variant: 'destructive',
    });
    return null;
  } finally {
    setUploadingReply(false);
  }
};

  // ── Редактирование ────────────────────────────────────────────────────────
  const handleEditKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) { e.preventDefault(); handleSaveEdit(); }
    if (e.key === 'Escape') { setIsEditing(false); setEditText(comment.text); }
  };

  const handleSaveEdit = async () => {
    if (!editText.trim() || editText.trim() === comment.text) { setIsEditing(false); return; }
    try {
      await onEditComment(comment.id, editText.trim());
      setIsEditing(false);
      toast({ title: 'Успешно', description: 'Комментарий изменён' });
    } catch {
      toast({ title: 'Ошибка', description: 'Не удалось сохранить изменения', variant: 'destructive' });
      setEditText(comment.text);
    }
  };

  const localHandleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      if (replyText.trim() || replyFiles.length > 0) {
        handleLocalSendReply(comment.id, replyText);
      }
    }
  };

  // ── Рендер контекстного меню ──────────────────────────────────────────────
  const renderContextMenu = () => {
    if (!contextMenu) return null;
    return createPortal(
      <div
        ref={contextMenuRef}
        className="fixed z-[9999] bg-[#1c1c1c]/95 backdrop-blur-xl rounded-2xl shadow-[0_18px_44px_rgba(0,0,0,.45)] border border-white/[0.08] overflow-hidden animate-in fade-in zoom-in-95 duration-100"
        style={{ top: contextMenu.y, left: contextMenu.x, minWidth: 220 }}
      >
        <div className="flex items-center gap-1 p-2.5 border-b border-white/[0.06]">
          {REACTIONS_CONFIG.map(r => (
            <button key={r.type} onClick={() => handleReaction(r.type)} className={getReactionPickerItemClass(userReactions.includes(r.type))} title={r.label}>
              {r.isImage ? <img src={r.emoji} alt={r.label} className="w-8 h-8" /> : <span className="text-l">{r.emoji}</span>}
            </button>
          ))}
        </div>
        <div className="py-1.5">
          <button onClick={() => { onReply(comment.id); setContextMenu(null); }} className="w-full text-left px-4 py-2.5 hover:bg-white/[0.06] flex items-center gap-3 text-l text-white/90 transition-colors">
            <Reply size={16} /> Ответить
          </button>
          {canEdit && (
            <>
              <button onClick={() => { setIsEditing(true); setContextMenu(null); }} className="w-full text-left px-4 py-2.5 hover:bg-white/[0.06] flex items-center gap-3 text-l text-white/90 transition-colors">
                <Edit2 size={16} /> Редактировать
              </button>
              <button onClick={() => { onDeleteComment(comment.id); setContextMenu(null); }} className="w-full text-left px-4 py-2.5 hover:bg-white/[0.06] flex items-center gap-3 text-l text-red-400 transition-colors">
                <Trash2 size={16} /> Удалить
              </button>
            </>
          )}
        </div>
      </div>,
      document.body
    );
  };

  const renderReactionPicker = () => {
    if (!showReactionPicker || !reactionPickerPosition) return null;
    return createPortal(
      <div
        ref={reactionPickerRef}
        className="fixed z-[9999] rounded-2xl border border-white/[0.08] bg-[#1c1c1c]/95 backdrop-blur-xl p-1.5 flex items-center gap-0.5 shadow-[0_12px_30px_rgba(0,0,0,.35)] animate-in fade-in zoom-in-95 duration-100"
        style={{ top: reactionPickerPosition.y, left: reactionPickerPosition.x }}
      >
        {REACTIONS_CONFIG.map(r => (
          <button key={r.type} onClick={() => { handleReaction(r.type); setShowReactionPicker(false); setReactionPickerPosition(null); }} className={getReactionPickerItemClass(userReactions.includes(r.type))} title={r.label}>
            {r.isImage ? <img src={r.emoji} alt={r.label} className="w-5 h-5" /> : <span className="text-l">{r.emoji}</span>}
          </button>
        ))}
      </div>,
      document.body
    );
  };

  // ── Рендер ───────────────────────────────────────────────────────────────
  return (
    <>
      <div
        className={`relative group transition-all duration-150 ${contextMenu !== null ? 'bg-white/[0.03] rounded-xl' : ''}`}
        style={{ marginLeft: level > 0 ? 24 : 0 }}
        onContextMenu={handleContextMenu}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {level > 0 && (
          <div className="absolute left-0 top-0 bottom-0 border-l border-white/10" style={{ left: '-12px' }} />
        )}

        <div className="flex gap-3">
          <div className="flex-shrink-0">
            <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${getAvatarColor(comment.author_role)} flex items-center justify-center shadow-sm`}>
              <User className="w-4 h-4 text-white" />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            {/* Шапка комментария */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-l font-medium text-white">{getAuthorName(comment)}</span>
              <span className="text-l text-white/40">{formatRelativeTime(comment.created_at)}</span>
              {comment.edited_at && <span className="text-l text-white/30">(изменён)</span>}
              {isInternal && (
                <span className="text-l px-2 py-0.5 rounded-full bg-yellow-500/15 text-yellow-300 border border-yellow-500/15">
                  Внутренний
                </span>
              )}
            </div>

            {/* Текст / редактирование */}
            {isEditing ? (
              <div className="mt-2">
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={handleEditKeyDown}
                  className="w-full px-3 py-2 bg-white/10 border border-white/15 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-red-500/40 text-l"
                  rows={3}
                  autoFocus
                />
                <div className="flex gap-2 mt-2">
                  <button onClick={handleSaveEdit} className="px-3 py-1.5 text-l bg-red-800 hover:bg-red-700 rounded-lg text-white transition-colors">
                    Сохранить
                  </button>
                  <button onClick={() => { setIsEditing(false); setEditText(comment.text); }} className="px-3 py-1.5 text-l bg-white/10 hover:bg-white/15 rounded-lg text-white transition-colors">
                    Отмена
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-white/90 text-l mt-1 whitespace-pre-wrap break-words leading-6">
                {comment.text}
              </p>
            )}

            {/* Реакции и действия */}
            <div className="flex items-center gap-1.5 mt-2 flex-wrap">
              {REACTIONS_CONFIG.map(reaction => {
                const count    = reactionCounts[reaction.type] || 0;
                const isActive = userReactions.includes(reaction.type);
                if (count === 0 && !isActive) return null;
                return (
                  <button key={reaction.type} onClick={() => handleReaction(reaction.type)} disabled={loadingReaction} className={getReactionChipClass(isActive)} title={reaction.label}>
                    {reaction.isImage
                      ? <img src={reaction.emoji} alt={reaction.label} className="w-7 h-7" />
                      : <span className="text-l">{reaction.emoji}</span>}
                    {count > 0 && (
                      <span className={`text-l font-semibold leading-none tabular-nums ${isActive ? 'text-white/90' : 'text-white/70'}`}>
                        {count}
                      </span>
                    )}
                  </button>
                );
              })}

              <button onClick={() => onReply(comment.id)} className="flex items-center gap-1 px-2 py-1 rounded-full text-l text-white/45 hover:text-white/70 hover:bg-white/[0.06] transition-colors">
                <Reply size={12} /><span>Ответить</span>
              </button>

              {localReplyCount > 0 && (
                <button onClick={() => loadReplies()} className="flex items-center gap-1 px-2 py-1 rounded-full text-l text-white/45 hover:text-white/70 hover:bg-white/[0.06] transition-colors">
                  {loadingReplies ? <Loader2 size={12} className="animate-spin" /> : showReplies ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  <span>{localReplyCount}</span>
                </button>
              )}

              {canEdit && isHovered && (
                <div className="relative" ref={actionsRef}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      const rect = e.currentTarget.getBoundingClientRect();
                      let x = rect.right + 8, y = rect.top;
                      if (x + 220 > window.innerWidth) x = rect.left - 220 - 8;
                      if (y + 220 > window.innerHeight) y = y - 220;
                      setContextMenu({ x, y });
                    }}
                    className="p-1 rounded-full text-white/40 hover:text-white/65 hover:bg-white/[0.06] transition-colors"
                  >
                    <MoreVertical size={16} />
                  </button>
                </div>
              )}
            </div>

            {/* ── Форма ответа с файлами ─────────────────────────────────── */}
            {isReplying && (
              <div className="mt-3 space-y-2">
                {/* Превью прикреплённых файлов */}
                {replyFiles.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {replyFiles.map((file, idx) => (
                      <ReplyFilePreview
                        key={`${file.name}-${file.size}-${idx}`}
                        file={file}
                        onRemove={() => removeReplyFile(idx)}
                      />
                    ))}
                  </div>
                )}

                <div className="flex gap-2 items-end">
                  {/* Скрытый input для файлов */}
                  <input
                    ref={replyFileInputRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={handleReplyFileSelect}
                    accept="*/*"
                  />

                  {/* Кнопка прикрепления */}
                  <button
                    type="button"
                    onClick={() => replyFileInputRef.current?.click()}
                    className="p-2 rounded-xl text-white/40 hover:text-white/70 hover:bg-white/[0.06] transition-colors flex-shrink-0 self-end mb-0.5"
                    title="Прикрепить файл"
                  >
                    <Paperclip size={16} />
                  </button>

                  {/* Textarea */}
                  <textarea
                    ref={replyTextareaRef}
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={localHandleKeyDown}
                    placeholder={`Ответить ${getAuthorName(comment)}...`}
                    className="flex-1 px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white placeholder-white/35 focus:outline-none focus:border-red-500/40 text-l resize-none overflow-hidden"
                    rows={1}
                    style={{ minHeight: '38px', maxHeight: '150px' }}
                    autoFocus
                  />

                  {/* Кнопки отправки/отмены */}
                  <div className="flex flex-col gap-1.5 flex-shrink-0">
                    <button
                      onClick={() => handleLocalSendReply(comment.id, replyText)}
                      disabled={(!replyText.trim() && replyFiles.length === 0) || uploadingReply}
                      className="px-3 py-2 bg-red-800 hover:bg-red-700 rounded-lg text-white text-l disabled:opacity-50 transition-colors flex items-center gap-1.5"
                    >
                      {uploadingReply
                        ? <><Loader2 size={12} className="animate-spin" /> Отправка...</>
                        : 'Ответить'
                      }
                    </button>
                    <button
                      onClick={() => { setReplyingTo(null); setReplyFiles([]); }}
                      className="px-3 py-2 bg-white/[0.04] hover:bg-white/[0.08] rounded-lg text-white/60 text-l transition-colors"
                    >
                      Отмена
                    </button>
                  </div>
                </div>

                {/* Подсказка */}
                <p className="text-[14px] text-white/25 pl-10">
                  Ctrl+Enter — отправить {replyFiles.length > 0 && `· ${replyFiles.length} файл(а) прикреплено`}
                </p>
              </div>
            )}

            {/* Вложения комментария */}
            {comment.attachments && comment.attachments.length > 0 && (
              <div className="flex gap-2 mt-3 flex-wrap">
                {comment.attachments.map((att: any) => (
                  <button
                    key={att.id}
                    onClick={() => handleDownload(att.id)}
                    className="text-l text-white/45 hover:text-white/70 flex items-center gap-1 transition-colors"
                  >
                    <span className="text-red-600"><Paperclip size={16} /></span>
                    {att.original_filename}
                  </button>
                ))}
              </div>
            )}

            {/* Вложенные ответы */}
            {showReplies && (
              <div className="mt-3 space-y-3">
                {loadingReplies ? (
                  <div className="flex justify-center py-2">
                    <Loader2 size={16} className="text-white/30 animate-spin" />
                  </div>
                ) : (
                  replies.map(reply => (
                    <CommentItem
                      key={reply.id}
                      comment={reply}
                      isReplying={replyingTo === reply.id}
                      onReply={onReply}
                      onSendReply={onSendReply}
                      onEditComment={handleNestedEdit}
                      onDeleteComment={handleNestedDelete}
                      replyText={replyText}
                      setReplyText={setReplyText}
                      replyingTo={replyingTo}
                      setReplyingTo={setReplyingTo}
                      getAuthorName={getAuthorName}
                      formatRelativeTime={formatRelativeTime}
                      getAvatarColor={getAvatarColor}
                      handleDownload={handleDownload}
                      ticketId={ticketId}
                      currentUser={currentUser}
                      level={level + 1}
                      onReplyAdded={onReplyAdded}
                      onReplyDeleted={onReplyDeleted}
                      onReplyEdited={onReplyEdited}
                      onReactionUpdated={onReactionUpdated}
                    />
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {renderContextMenu()}
      {renderReactionPicker()}
    </>
  );
});

CommentItem.displayName = 'CommentItem';