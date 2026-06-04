import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Clock, User, FileText, History,
  Loader2, Download, Image, File, ChevronDown, ChevronUp,
  Calendar, UserPlus, UserCheck, CheckCircle2, X, Plus,
  Search, Settings, AlertCircle, RefreshCw, Tag, Edit,
  Paperclip as PaperclipIcon, MessageCircle, Building2, Phone, Mail,
  Archive,
} from 'lucide-react';
import { ticketsApi, usersApi } from '../api/client';
import { attachmentsApi } from '../api/attachments';
import { useAuthStore } from '../stores/authStore';
import { useToast } from '../components/ui/use-toast';
import type { Ticket, Comment, SimpleUser } from '../types';
import { CommentForm } from '../components/helpers/CommentForm';
import { CommentItem } from '../components/helpers/CommentItem';
import { HistoryEntry } from '../components/helpers/HistoryEntry';
import { ConfirmModal } from '../components/helpers/ConfirmModal';
import { counterpartiesApi } from '../api/client';
import { TicketDescriptionContent } from '../components/helpers/TicketDescriptionContent';
import {
  TicketEditor, serializeBlocks, deserializeToBlocks, type DescriptionBlock,
} from '../components/helpers/TicketEditor';

// ── Константы

const STATUS_TRANSITIONS: Record<string, string[]> = {
  'Новый': ['На согласовании', 'Открыт'],
  'На согласовании': ['Открыт', 'Отклонён'],
  'Открыт': ['В работе'],
  'В работе': ['Ожидает ответа', 'Решён'],
  'Ожидает ответа': ['В работе'],
  'Решён': ['Закрыт'],
  'Закрыт': ['Переоткрыт'],
  'Переоткрыт': ['Открыт'],
  'Отклонён': ['Закрыт'],
};

const STATUS_PERMISSIONS: Record<string, string[]> = {
  'Новый': ['support_agent', 'support_manager', 'admin'],
  'На согласовании': ['support_agent', 'support_manager', 'admin'],
  'Открыт': ['support_agent', 'support_manager', 'executor', 'admin'],
  'В работе': ['support_agent', 'support_manager', 'executor', 'admin'],
  'Ожидает ответа': ['support_agent', 'support_manager', 'executor', 'admin'],
  'Решён': ['support_agent', 'support_manager', 'executor', 'admin'],
  'Закрыт': ['support_agent', 'support_manager', 'admin'],
  'Переоткрыт': ['support_agent', 'support_manager', 'admin'],
};

const STATUS_DESCRIPTIONS: Record<string, string> = {
  'Новый': 'Тикет только создан, ожидает обработки',
  'На согласовании': 'Тикет создан, но ещё не согласован',
  'Открыт': 'Тикет согласован и готов к работе',
  'В работе': 'Над тикетом активно работают',
  'Ожидает ответа': 'Ждём ответа от клиента',
  'Решён': 'Работа выполнена, ждём подтверждения',
  'Закрыт': 'Тикет закрыт',
  'Переоткрыт': 'Тикет переоткрыт',
  'Отклонён': 'Тикет отклонён',
};

let ticketNumberToIdCache: Map<string, string> | null = null;
let cacheLoadingPromise: Promise<void> | null = null;
let userNamesCache: Map<string, string> | null = null;

interface NormalizedComments {
  byId: Map<string, Comment>;
  byParent: Map<string, string[]>;
  rootIds: string[];
}

// ── Компонент 

export default function TicketDetailPage() {
  const [imagePreviews, setImagePreviews] = useState<Record<string, string>>({});
  const [previewsLoaded, setPreviewsLoaded] = useState(false);
  const [previewFile, setPreviewFile] = useState<any>(null);

  const [normalizedComments, setNormalizedComments] = useState<NormalizedComments>({
    byId: new Map(), byParent: new Map(), rootIds: [],
  });
  const [loadingComments, setLoadingComments] = useState(false);
  const [commentsTotalItems, setCommentsTotalItems] = useState(0);
  const [hasMoreComments, setHasMoreComments] = useState(true);
  const [loadingMoreComments, setLoadingMoreComments] = useState(false);
  const [commentsPage, setCommentsPage] = useState(1);

  const { ticketNumber } = useParams<{ ticketNumber: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { toast } = useToast();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'chat' | 'details' | 'history' | 'manage'>('chat');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [expandedHistory, setExpandedHistory] = useState(false);

  const [showAssigneeModal, setShowAssigneeModal] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [updatingAssignee, setUpdatingAssignee] = useState(false);
  const [searchUser, setSearchUser] = useState('');

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [commentToDelete, setCommentToDelete] = useState<string | null>(null);

  const [archiving, setArchiving] = useState(false);
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false);

  const userRole = user?.role || '';
  const isStaff = ['admin', 'support_agent', 'support_manager'].includes(userRole);
  const canChangeStatus = userRole === 'admin' || STATUS_PERMISSIONS[ticket?.status || '']?.includes(userRole) || false;
  const canShowManage = isStaff;

  const canArchive = useCallback(() => {
    if (!ticket || !user) return false;
    if (ticket.is_archived) return false;
    const isCreatorOrReporter = user.user_id === ticket.created_by || user.user_id === ticket.reporter_id;
    const staff = userRole === 'admin' || userRole === 'support_manager';
    return isCreatorOrReporter || staff;
  }, [ticket, user, userRole]);

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [messageType, setMessageType] = useState<'public' | 'internal'>('public');

  const [supportUsers, setSupportUsers] = useState<SimpleUser[]>([]);
  const [loadingSupports, setLoadingSupports] = useState(false);

  const [commentSortOrder, setCommentSortOrder] = useState<'newest' | 'oldest'>('newest');
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');

  const canAssign = isStaff && ['Открыт', 'В работе', 'Ожидает ответа', 'Решён'].includes(ticket?.status || '');

  const [counterparty, setCounterparty] = useState<any | null>(null);

  // ── Имена акторов для истории и автора ──
  const [actorNames, setActorNames] = useState<Map<string, string>>(new Map());

  // ── Редактирование ──
  const [showEditModal, setShowEditModal] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescBlocks, setEditDescBlocks] = useState<DescriptionBlock[]>([]);
  const [editPriority, setEditPriority] = useState<string>('Средний');
  const [editTags, setEditTags] = useState<Array<{ name: string; color: string }>>([]);
  const [editNewTag, setEditNewTag] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // ── Computed ──

  const sortedRootComments = useMemo(() => {
    const roots = normalizedComments.rootIds
      .map(id => normalizedComments.byId.get(id))
      .filter(Boolean) as Comment[];
    return [...roots].sort((a, b) =>
      commentSortOrder === 'newest'
        ? new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        : new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
  }, [normalizedComments, commentSortOrder]);

  const sortedHistory = useMemo(() => {
    return [...(ticket?.history || [])].sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [ticket?.history]);

  const availableStatuses = STATUS_TRANSITIONS[ticket?.status || ''] || [];

  const canWriteInternal = isStaff;

  // Табы — условно включаем «Управление»
  const tabs = useMemo(() => {
    const t = [
      { id: 'details' as const, label: 'Детали', icon: FileText },
      { id: 'chat' as const, label: 'Обсуждение', icon: MessageCircle, count: commentsTotalItems },
      { id: 'history' as const, label: 'История', icon: History, count: ticket?.history?.length },
    ];
    if (canShowManage) {
      t.push({ id: 'manage' as const, label: 'Управление', icon: Settings, count: undefined });
    }
    return t;
  }, [commentsTotalItems, ticket?.history?.length, canShowManage]);

  // ── Loaders ──

  const loadSupportUsers = useCallback(async () => {
    setLoadingSupports(true);
    try {
      const r = await usersApi.getSupports(1, 100);
      setSupportUsers(r.items);
      if (!userNamesCache) userNamesCache = new Map();
      r.items.forEach((u: SimpleUser) => { userNamesCache!.set(u.id, u.full_name || u.username || u.email); });
    } catch { toast({ title: 'Ошибка', description: 'Не удалось загрузить исполнителей', variant: 'destructive' }); }
    finally { setLoadingSupports(false); }
  }, [toast]);

  useEffect(() => { if (canAssign) loadSupportUsers(); }, [canAssign, loadSupportUsers]);

  // Улучшенная функция получения имени исполнителя
  const getAssigneeName = useCallback(() => {
    if (!ticket?.assignee_id) return null;
    const fromSupport = supportUsers.find(u => u.id === ticket.assignee_id);
    if (fromSupport) return fromSupport.full_name || fromSupport.username || fromSupport.email;
    if (user?.user_id === ticket.assignee_id) return user.full_name || user.username || user.email;
    return ticket.assignee_id.slice(0, 8);
  }, [ticket?.assignee_id, supportUsers, user]);

  const filteredUsers = useMemo(() =>
    supportUsers.filter(u =>
      !searchUser ||
      u.full_name?.toLowerCase().includes(searchUser.toLowerCase()) ||
      u.username?.toLowerCase().includes(searchUser.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchUser.toLowerCase())
    ), [supportUsers, searchUser]);

  const formatRelativeTime = useCallback((d: string) => {
    const ms = Date.now() - new Date(d).getTime();
    const m = Math.floor(ms / 60000), h = Math.floor(ms / 3600000), dd = Math.floor(ms / 86400000);
    if (m < 1) return 'только что';
    if (m < 60) return `${m} мин. назад`;
    if (h < 24) return `${h} ч. назад`;
    if (dd === 1) return 'вчера';
    if (dd < 7) return `${dd} дн. назад`;
    return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  }, []);

  const getAvatarColor = useCallback((role: string) => {
    if (['admin', 'support_agent', 'support_manager'].includes(role)) return 'from-red-800 to-red-700';
    if (role === 'executor') return 'from-green-600 to-green-700';
    return 'from-gray-600 to-gray-700';
  }, []);

  const getAuthorName = useCallback((c: Comment) => {
    const map: Record<string, string> = {
      admin: 'Поддержка', support_agent: 'Агент поддержки', support_manager: 'Менеджер',
      customer_admin: 'Администратор контрагента', executor: 'Исполнитель',
    };
    return map[c.author_role] || 'Клиент';
  }, []);

  const initCache = useCallback(async () => {
    if (ticketNumberToIdCache) return;
    if (cacheLoadingPromise) return cacheLoadingPromise;
    cacheLoadingPromise = (async () => {
      ticketNumberToIdCache = new Map();
      let p = 1; let more = true;
      while (more) {
        try {
          const r = await ticketsApi.getAll(p, 100);
          r.items.forEach((i: any) => { if (i.number && i.id) ticketNumberToIdCache!.set(i.number, i.id); });
          more = r.items.length === 100; p++;
        } catch { more = false; }
      }
    })();
    return cacheLoadingPromise;
  }, []);
  
  const loadActorNames = useCallback(async (history: any[], counterpartyId?: string) => {
    const actorIds = [...new Set(history.map(e => e.actor_id).filter(Boolean))];
    if (ticket?.reporter_id) actorIds.push(ticket.reporter_id);
    if (ticket?.created_by) actorIds.push(ticket.created_by);
    if (ticket?.assignee_id) actorIds.push(ticket.assignee_id);
    if (!actorIds.length) return;

    const names = new Map<string, string>();
    if (user?.user_id) names.set(user.user_id, user.full_name || user.username || 'Вы');

    if (counterpartyId) {
      try {
        const r = await usersApi.getCustomers(counterpartyId, 1, 100);
        r.items.forEach((u: any) => names.set(u.id, u.full_name || u.username || u.email));
      } catch { }
    }

    const missing = actorIds.filter(id => !names.has(id));
    if (missing.length) {
      try {
        const r = await usersApi.getSupports(1, 100);
        r.items.forEach((u: any) => {
          if (missing.includes(u.id)) names.set(u.id, u.full_name || u.username || u.email);
        });
      } catch { }
    }
    setActorNames(names);
  }, [user, ticket?.reporter_id, ticket?.created_by, ticket?.assignee_id]);

  const loadComments = useCallback(async (tid: string, page = 1, append = false) => {
    append ? setLoadingMoreComments(true) : setLoadingComments(true);
    try {
      const r = await ticketsApi.getComments(tid, { include_internal: canWriteInternal, page, size: 15 });
      const byId = new Map<string, Comment>();
      const byParent = new Map<string, string[]>();
      const rootIds: string[] = [];
      r.items.forEach((c: Comment) => {
        byId.set(c.id, c);
        if (c.parent_comment_id) { byParent.set(c.parent_comment_id, [...(byParent.get(c.parent_comment_id) || []), c.id]); }
        else rootIds.push(c.id);
      });
      if (append) {
        setNormalizedComments(prev => {
          const nb = new Map(prev.byId); const np = new Map(prev.byParent); const nr = [...prev.rootIds];
          byId.forEach((c, id) => { if (!nb.has(id)) nb.set(id, c); });
          byParent.forEach((ch, pid) => { np.set(pid, [...(np.get(pid) || []), ...ch]); });
          rootIds.forEach(id => { if (!nr.includes(id)) nr.push(id); });
          return { byId: nb, byParent: np, rootIds: nr };
        });
      } else { setNormalizedComments({ byId, byParent, rootIds }); }
      setCommentsTotalItems(r.total_items); setCommentsPage(r.page); setHasMoreComments(r.page < r.total_pages);
    } catch { toast({ title: 'Ошибка', description: 'Не удалось загрузить комментарии', variant: 'destructive' }); }
    finally { setLoadingComments(false); setLoadingMoreComments(false); }
  }, [canWriteInternal, toast]);

  const loadMoreComments = useCallback(async () => {
    if (!ticket?.id || loadingMoreComments || !hasMoreComments) return;
    await loadComments(ticket.id, commentsPage + 1, true);
  }, [ticket?.id, commentsPage, hasMoreComments, loadingMoreComments, loadComments]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const t = e.target as HTMLDivElement;
    if (t.scrollTop + t.clientHeight >= t.scrollHeight - 100 && hasMoreComments && !loadingMoreComments) loadMoreComments();
  }, [hasMoreComments, loadingMoreComments, loadMoreComments]);

  const loadTicketByNumber = useCallback(async (number: string) => {
    setLoading(true);
    try {
      await initCache();
      const tid = ticketNumberToIdCache?.get(number);
      if (tid) {
        const data = await ticketsApi.getById(tid);
        setTicket(data);
        if (data.history?.length || data.reporter_id || data.created_by || data.assignee_id) {
          await loadActorNames(data.history || [], data.counterparty_id);
        }
        if (data.counterparty_id) { try { setCounterparty(await counterpartiesApi.getById(data.counterparty_id)); } catch { setCounterparty(null); } }
        else setCounterparty(null);
        await loadComments(tid, 1, false);
      } else {
        const sr = await ticketsApi.getAll(1, 100);
        const found = sr.items.find((t: any) => t.number === number);
        if (found) {
          const data = await ticketsApi.getById(found.id);
          setTicket(data); ticketNumberToIdCache?.set(number, found.id);
          await loadComments(found.id, 1, false);
        } else { toast({ title: 'Ошибка', description: 'Заявка не найдена', variant: 'destructive' }); navigate('/tickets'); }
      }
    } catch { toast({ title: 'Ошибка', description: 'Не удалось загрузить заявку', variant: 'destructive' }); navigate('/tickets'); }
    finally { setLoading(false); }
  }, [initCache, loadComments, loadActorNames, toast, navigate]);

  // ── Handlers ──

  const normalizeText = (t: string) => t.trim().replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n');

  const handleSendMessage = useCallback(async (files: any[]): Promise<string | null> => {
    const tm = message.trim();
    if ((!tm && !files.length) || !ticket?.id) return null;
    setSending(true);
    try {
      const nc = await ticketsApi.addComment(ticket.id, tm || '(вложения)', messageType);
      setNormalizedComments(prev => {
        const nb = new Map(prev.byId); nb.set(nc.id, nc);
        const nr = [...prev.rootIds]; if (!nc.parent_comment_id) nr.unshift(nc.id);
        return { ...prev, byId: nb, rootIds: nr };
      });
      setCommentsTotalItems(p => p + 1); setMessage(''); return nc.id;
    } catch { toast({ title: 'Ошибка', description: 'Не удалось отправить', variant: 'destructive' }); return null; }
    finally { setSending(false); }
  }, [message, ticket?.id, messageType, toast]);

  const handleEditComment = useCallback(async (cid: string, newText: string) => {
    if (!ticket?.id) return;
    setNormalizedComments(prev => {
      const nb = new Map(prev.byId); const ex = nb.get(cid);
      if (ex) nb.set(cid, { ...ex, text: newText, edited_at: new Date().toISOString() });
      return { ...prev, byId: nb };
    });
    try { await ticketsApi.editComment(ticket.id, cid, newText); }
    catch { toast({ title: 'Ошибка', variant: 'destructive' }); await loadComments(ticket.id, 1, false); }
  }, [ticket?.id, toast, loadComments]);

  const handleDeleteComment = useCallback(async (cid: string) => {
    if (!ticket?.id) return;
    const del = normalizedComments.byId.get(cid);
    if (del) {
      setNormalizedComments(prev => {
        const nb = new Map(prev.byId); nb.delete(cid);
        const nr = prev.rootIds.filter(id => id !== cid);
        if (del.parent_comment_id) {
          const np = new Map(prev.byParent);
          np.set(del.parent_comment_id, (np.get(del.parent_comment_id) || []).filter(id => id !== cid));
          return { ...prev, byId: nb, byParent: np, rootIds: nr };
        }
        return { ...prev, byId: nb, rootIds: nr };
      });
      setCommentsTotalItems(p => p - 1);
    }
    try { await ticketsApi.deleteComment(ticket.id, cid); }
    catch { toast({ title: 'Ошибка', variant: 'destructive' }); await loadComments(ticket.id, 1, false); }
  }, [ticket?.id, normalizedComments, toast, loadComments]);

  const handleSendReply = useCallback(async (pid: string, text: string): Promise<Comment | null> => {
    const n = normalizeText(text);
    if (!n || !ticket?.id) return null;
    try {
      const nr = await ticketsApi.replyToComment(ticket.id, pid, n, messageType);
      setNormalizedComments(prev => {
        const nb = new Map(prev.byId); nb.set(nr.id, nr);
        const np = new Map(prev.byParent); np.set(pid, [...(prev.byParent.get(pid) || []), nr.id]);
        return { ...prev, byId: nb, byParent: np };
      });
      setCommentsTotalItems(p => p + 1); setReplyText(''); setReplyingTo(null); return nr;
    } catch { toast({ title: 'Ошибка', variant: 'destructive' }); return null; }
  }, [ticket?.id, messageType, toast]);

  const handleReply = useCallback((cid: string) => { setReplyingTo(p => p === cid ? null : cid); setReplyText(''); }, []);
  const handleReactionUpdated = useCallback((cid: string, r: any) => {
    setNormalizedComments(prev => { const nb = new Map(prev.byId); const ex = nb.get(cid); if (ex) nb.set(cid, { ...ex, ...r }); return { ...prev, byId: nb }; });
  }, []);

  const handleDownload = useCallback(async (aid: string) => {
    setDownloadingId(aid);
    try { await attachmentsApi.downloadAttachment(aid); } catch { toast({ title: 'Ошибка', variant: 'destructive' }); }
    finally { setDownloadingId(null); }
  }, [toast]);

  const handleStatusChange = useCallback(async (s: string) => {
    if (!canChangeStatus || !ticket) return;
    setUpdatingStatus(true);
    try { 
      const updated = await ticketsApi.updateTicketStatus(ticket.id, s as any);
      setTicket(updated);
      toast({ title: 'Успешно', description: `Статус: ${s}` });
    } catch (e: any) { toast({ title: 'Ошибка', description: e.response?.status === 403 ? 'Нет прав' : 'Ошибка', variant: 'destructive' }); }
    finally { setUpdatingStatus(false); }
  }, [canChangeStatus, ticket, toast]);

  const handleAssign = useCallback(async (aid: string | null) => {
    if (!ticket) return;
    setUpdatingAssignee(true);
    try {
      const updated = await ticketsApi.assignTicket(ticket.id, aid || '');
      setTicket(updated);
      // Обновляем actorNames для нового исполнителя
      if (aid) {
        const found = supportUsers.find(u => u.id === aid);
        if (found) {
          setActorNames(prev => new Map(prev).set(aid, found.full_name || found.username || found.email));
        } else {
          await loadActorNames(updated.history || [], updated.counterparty_id);
        }
      }
      setShowAssigneeModal(false);
      setSearchUser('');
      toast({ title: 'Успешно', description: aid ? 'Исполнитель назначен' : 'Исполнитель снят' });
    } catch { toast({ title: 'Ошибка', variant: 'destructive' }); }
    finally { setUpdatingAssignee(false); }
  }, [ticket, supportUsers, loadActorNames, toast]);

  const handleArchive = useCallback(async () => {
    if (!ticket) return;
    setArchiving(true);
    try { setTicket(await ticketsApi.archiveTicket(ticket.id)); toast({ title: 'Архивировано' }); setShowArchiveConfirm(false); }
    catch (e: any) { toast({ title: 'Ошибка', description: e?.response?.status === 403 ? 'Нет прав' : 'Ошибка', variant: 'destructive' }); }
    finally { setArchiving(false); }
  }, [ticket, toast]);

  // ── Редактирование ──

  const openEditModal = useCallback(() => {
    if (!ticket) return;
    setEditTitle(ticket.title);
    setEditDescBlocks(deserializeToBlocks(ticket.description || ''));
    setEditPriority(ticket.priority);
    setEditTags(ticket.tags?.map(t => ({ name: t.name, color: t.color || '#64748b' })) || []);
    setShowEditModal(true);
  }, [ticket]);

  const handleSaveEdit = useCallback(async () => {
    if (!ticket) return;
    setSavingEdit(true);
    try {
      const imageBlocks = editDescBlocks.filter(
        (b): b is Extract<DescriptionBlock, { type: 'image' }> => b.type === 'image'
      );
      const newImageBlocks = imageBlocks.filter((b) => !b.attachmentId && b.localFile);
      const brokenBlocks = imageBlocks.filter((b) => !b.attachmentId && !b.localFile);
      if (brokenBlocks.length > 0) {
        toast({ title: 'Ошибка', description: `${brokenBlocks.length} изображение(й) потеряло связь с файлом.`, variant: 'destructive' });
        setSavingEdit(false);
        return;
      }
      const uploadMap: Record<string, string> = {};
      const failedUploads: string[] = [];
      for (const block of newImageBlocks) {
        try {
          const att = await attachmentsApi.uploadAttachment(block.localFile!, 'ticket', ticket.id);
          uploadMap[block.id] = att.id;
        } catch (e) { failedUploads.push(block.id); }
      }
      if (failedUploads.length > 0) {
        toast({ title: 'Ошибка загрузки', description: `Не удалось загрузить ${failedUploads.length} изображение(й).`, variant: 'destructive' });
        setSavingEdit(false);
        return;
      }
      let finalDesc = serializeBlocks(editDescBlocks);
      for (const [blockId, attachmentId] of Object.entries(uploadMap)) {
        finalDesc = finalDesc.replaceAll(`![image](local:${blockId})`, `![image](media://${attachmentId})`);
      }
      if (/!\[image\]\(local:[^)]+\)/.test(finalDesc)) {
        toast({ title: 'Ошибка', description: 'В описании остались незагруженные изображения.', variant: 'destructive' });
        setSavingEdit(false);
        return;
      }
      const updated = await ticketsApi.update(ticket.id, {
        title: editTitle.trim(),
        description: finalDesc,
        priority: editPriority as any,
        tags: editTags,
      });
      setTicket(updated);
      setShowEditModal(false);
      toast({ title: 'Сохранено' });
    } catch (e: any) {
      toast({ title: 'Ошибка', description: e?.message || 'Не удалось сохранить', variant: 'destructive' });
    } finally { setSavingEdit(false); }
  }, [ticket, editTitle, editDescBlocks, editPriority, editTags, toast]);

  // ── Effects ──

  useEffect(() => {
    if (activeTab !== 'details' || previewsLoaded || !ticket?.attachments) return;
    const ac = new AbortController();
    (async () => {
      const imgs = ticket.attachments.filter(f => f.mime_type.startsWith('image/'));
      const results: { fileId: string; url: string }[] = [];
      for (let i = 0; i < imgs.length; i += 3) {
        if (ac.signal.aborted) break;
        const batch = imgs.slice(i, i + 3);
        const br = await Promise.all(batch.map(async file => {
          try {
            const { download_url } = await attachmentsApi.getPresignedDownloadUrl(file.id);
            const url = download_url.replace(/http:\/\/(minio|maildev):9000/g, 'http://localhost:9900');
            const r = await fetch(url, { signal: ac.signal }); if (!r.ok) throw new Error();
            return { fileId: file.id, url: URL.createObjectURL(await r.blob()) };
          } catch { return null; }
        }));
        br.forEach(r => { if (r) results.push(r); });
      }
      setImagePreviews(p => { const n = { ...p }; results.forEach(({ fileId, url }) => { n[fileId] = url; }); return n; });
      setPreviewsLoaded(true);
    })();
    return () => { ac.abort(); };
  }, [activeTab, ticket?.attachments, previewsLoaded]);

  useEffect(() => { initCache(); }, [initCache]);
  useEffect(() => { if (ticketNumber) loadTicketByNumber(ticketNumber); }, [ticketNumber, loadTicketByNumber]);

  // ── Helpers ──

  const openPreview = useCallback((f: any) => setPreviewFile(f), []);
  const closePreview = useCallback(() => setPreviewFile(null), []);
  const formatFileSize = useCallback((b: number) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`, []);
  const getFileIcon = useCallback((m: string) => m.startsWith('image/') ? <Image className="w-6 h-6" /> : <File className="w-6 h-6" />, []);

  const getStatusColor = useCallback((s: string) => {
    const map: Record<string, string> = {
      'Новый': 'status-new', 'На согласовании': 'status-agreement', 'Открыт': 'status-open',
      'В работе': 'status-progress', 'Ожидает ответа': 'status-waiting', 'Решён': 'status-resolved',
      'Закрыт': 'status-closed', 'Переоткрыт': 'status-reopened', 'Отклонён': 'status-rejected',
    };
    return map[s] || 'status-closed';
  }, []);

  const getPriorityColor = useCallback((p: string) => {
    const map: Record<string, string> = {
      'Низкий': 'priority-low', 'Средний': 'priority-medium',
      'Высокий': 'priority-high', 'Критический': 'priority-critical',
    };
    return map[p] || 'priority-medium';
  }, []);

  const getTypeColor = useCallback((t: string) => {
    const map: Record<string, string> = {
      'Инцидент': 'type-incident', 'Запрос на услугу': 'type-service', 'Консультация': 'type-consultation',
      'Жалоба': 'type-complaint', 'Задача': 'type-task', 'Проблема': 'type-problem',
      'Запрос на изменение': 'type-change', 'Улучшение': 'type-improvement', 'Прочее': 'type-other',
    };
    return map[t] || 'type-other';
  }, []);

  const formatDate = useCallback((d: string) => {
    if (!d) return '—';
    const date = new Date(d);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const compareDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const diffDays = Math.floor((today.getTime() - compareDate.getTime()) / 86400000);
    if (diffDays === 0) return `Сегодня, ${date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
    if (diffDays === 1) return 'Вчера';
    if (diffDays < 7) return `${diffDays} дн. назад`;
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  }, []);

  // ── Render ──

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-12 h-12 text-[var(--accent)] animate-spin" /></div>;
  if (!ticket) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <p className="text-[var(--text-primary)]/50 text-base mb-4">Заявка не найдена</p>
        <Link to="/tickets" className="px-6 py-3 bg-[var(--hover-1)] hover:bg-[var(--hover-1)] rounded-xl text-[var(--text-primary)]">Вернуться</Link>
      </div>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">

      {/* ── Header ── */}
      <div className="flex items-start gap-5">
        <button onClick={() => navigate(-1)} className="p-3 rounded-xl hover:bg-[var(--hover-1)] text-[var(--text-primary)]/60 hover:text-[var(--text-primary)] transition-all mt-1">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <h1 className="text-2xl text-[var(--text-primary)] font-semibold">Заявка</h1>
            <span className="text-[var(--text-primary)]/50 font-mono text-base">#{ticket.number}</span>
            
            {ticket.is_archived && (
              <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-base font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
                <Archive className="w-4 h-4" /> Архив
              </span>
            )}
            {!ticket.is_archived && (user?.user_id === ticket.created_by || user?.user_id === ticket.reporter_id) && (
              <button onClick={openEditModal}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-base
                              bg-[var(--hover-2)] hover:bg-[var(--hover-3)] border border-[var(--border-color)]
                              text-[var(--text-primary)]/70 hover:text-[var(--text-primary)] transition-colors">
                <Edit className="w-4 h-4" /> Редактировать
              </button>
            )}
          </div>
          <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-4">{ticket.title}</h1>
          <div className="flex flex-wrap items-center gap-6 text-base text-[var(--text-primary)]/40">
            <div className="flex items-center gap-2"><Calendar className="w-5 h-5" />Создана: {formatDate(ticket.created_at)}</div>
            {ticket.closed_at && <div className="flex items-center gap-2"><Clock className="w-5 h-5" />Закрыта: {formatDate(ticket.closed_at)}</div>}
          </div>
        </div>
      </div>

      {/* ── Main grid ── */}
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">

          {/* Tabs */}
          <div className="flex gap-2 border-b border-[var(--border-color)] overflow-x-auto">
            {tabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-3 rounded-t-xl transition-all whitespace-nowrap ${activeTab === tab.id ? 'bg-[var(--accent)]/50 text-white border-b-2 border-[var(--accent)] shadow-[0_-4px_12px_var(--accent-glow)]' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--hover-1)]'
                  }`}>
                <tab.icon className="w-5 h-5" />
                <span className="text-base font-medium">{tab.label}</span>
                {tab.count !== undefined && tab.count > 0 && <span className="ml-1 px-2 py-0.5 rounded-full bg-[var(--hover-1)] text-base">{tab.count}</span>}
              </button>
            ))}
          </div>

          <div className="bg-[var(--hover-1)] backdrop-blur-sm rounded-xl border border-[var(--border-color)]">
            {/* ── Чат ── */}
            {activeTab === 'chat' && (
              <div className="flex flex-col">
                <div className="px-6 py-4 border-b border-[var(--border-color)] bg-[var(--hover-1)]">
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-3">
                      <MessageCircle className="w-5 h-5 text-[var(--text-primary)]/60" />
                      <span className="text-[var(--text-primary)] font-medium">
                        {commentsTotalItems} {commentsTotalItems === 1 ? 'комментарий' : commentsTotalItems < 5 ? 'комментария' : 'комментариев'}
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex gap-1 bg-[var(--hover-1)] rounded-lg p-0.5">
                        {(['newest', 'oldest'] as const).map(order => (
                          <button key={order} onClick={() => setCommentSortOrder(order)}
                            className={`px-3 py-1.5 text-base rounded-md transition-colors ${commentSortOrder === order ? 'bg-[var(--accent)]/50 text-white' : 'text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]/60'
                              }`}>
                            {order === 'newest' ? 'Сначала новые' : 'Сначала старые'}
                          </button>
                        ))}
                      </div>
                      {canWriteInternal && <span className="text-base text-[var(--text-primary)]/40">Внутренние видны только сотрудникам</span>}
                    </div>
                  </div>
                </div>

                <div className="p-5 border-b border-[var(--border-color)]">
                  <CommentForm message={message} setMessage={setMessage} onSend={handleSendMessage} sending={sending}
                    messageType={messageType} setMessageType={setMessageType} canWriteInternal={canWriteInternal}
                    onSuccess={() => { if (ticket?.id) loadComments(ticket.id, 1, false); }} />
                </div>

                <div ref={chatContainerRef} onScroll={handleScroll} className="flex-1 overflow-y-auto p-6 space-y-5 max-h-[500px]">
                  {loadingComments && sortedRootComments.length === 0 ? (
                    <div className="flex justify-center py-10"><Loader2 className="w-8 h-8 text-[var(--text-primary)]/30 animate-spin" /></div>
                  ) : sortedRootComments.length > 0 ? (
                    <>
                      {loadingMoreComments && <div className="flex justify-center py-2"><Loader2 className="w-6 h-6 text-[var(--text-primary)]/30 animate-spin" /></div>}
                      {sortedRootComments.map(comment => (
                        <CommentItem key={comment.id} comment={comment} isReplying={replyingTo === comment.id}
                          onReply={handleReply} onSendReply={handleSendReply} onEditComment={handleEditComment}
                          onDeleteComment={() => { setCommentToDelete(comment.id); setShowDeleteConfirm(true); }}
                          replyText={replyText} setReplyText={setReplyText} replyingTo={replyingTo} setReplyingTo={setReplyingTo}
                          getAuthorName={getAuthorName} formatRelativeTime={formatRelativeTime} getAvatarColor={getAvatarColor}
                          handleDownload={handleDownload} ticketId={ticket.id} currentUser={user} onReactionUpdated={handleReactionUpdated} />
                      ))}
                      {!hasMoreComments && <div className="text-center py-4 text-base text-[var(--text-primary)]/30">Все комментарии загружены</div>}
                    </>
                  ) : (
                    <div className="text-center py-16">
                      <MessageCircle className="w-16 h-16 mx-auto mb-4 text-[var(--text-primary)]/20" />
                      <p className="text-[var(--text-primary)]/50 text-lg">Нет комментариев</p>
                      <p className="text-base text-[var(--text-primary)]/30 mt-1">Будьте первым</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── Детали ── */}
            {activeTab === 'details' && (
              <div className="p-6 space-y-8">
                <div>
                  <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-3">
                    <FileText className="w-5 h-5 text-[var(--text-primary)]/60" /> Описание
                  </h3>
                  <div className="p-6">
                    <TicketDescriptionContent text={ticket.description || 'Описание отсутствует'} className="text-[var(--text-primary)] text-base leading-relaxed" />
                  </div>
                </div>

                {ticket.tags && ticket.tags.length > 0 && (
                  <div>
                    <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-3">
                      <Tag className="w-5 h-5 text-[var(--text-primary)]/60" /> Теги
                    </h3>
                    <div className="flex flex-wrap gap-3">
                      {ticket.tags.map(tag => (
                        <span key={tag.name} className="px-4 py-2 rounded-xl text-base font-medium"
                          style={{ backgroundColor: tag.color ? `${tag.color}20` : 'rgba(255,255,255,0.1)', color: tag.color || '#d1d5db' }}>
                          {tag.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-3">
                    <PaperclipIcon className="w-5 h-5 text-[var(--text-primary)]/60" /> Вложения ({ticket.attachments?.length || 0})
                  </h3>
                  {!ticket.attachments?.length ? (
                    <div className="text-center py-12 text-[var(--text-primary)]/40 bg-[var(--hover-1)] rounded-2xl">
                      <PaperclipIcon className="w-16 h-16 mx-auto mb-4 opacity-40" />
                      <p className="text-lg">Нет файлов</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {ticket.attachments.map(file => {
                        const isImage = file.mime_type.startsWith('image/');
                        return (
                          <div key={file.id} onClick={() => openPreview(file)}
                            className="bg-[var(--hover-1)] border border-[var(--border-color)] rounded-2xl overflow-hidden group hover:border-[var(--border-color)] transition-all cursor-pointer">
                            <div className="h-52 bg-zinc-950 flex items-center justify-center relative overflow-hidden">
                              {isImage && imagePreviews[file.id]
                                ? <img src={imagePreviews[file.id]} alt={file.original_filename} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                                : isImage ? <Loader2 className="w-8 h-8 text-[var(--text-primary)]/30 animate-spin" />
                                  : <div className="text-6xl text-[var(--text-primary)]/30">{getFileIcon(file.mime_type)}</div>
                              }
                              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                                <p className="text-white text-base line-clamp-2 font-medium">{file.original_filename}</p>
                              </div>
                            </div>
                            <div className="p-3 flex justify-between items-center">
                              <span className="text-base text-[var(--text-primary)]/40">{formatFileSize(file.size_bytes)}</span>
                              <button onClick={e => { e.stopPropagation(); handleDownload(file.id); }}
                                className="p-2 text-[var(--text-primary)]/60 hover:text-[var(--text-primary)] hover:bg-[var(--hover-1)] rounded-xl">
                                <Download className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── История ── */}
            {activeTab === 'history' && (
              <div className="p-6">
                <div className="space-y-5">
                  {sortedHistory.slice(0, expandedHistory ? undefined : 5).map((entry, i) => (
                    <HistoryEntry key={`${entry.created_at}-${i}`} entry={entry} formatDate={formatDate} actorNames={actorNames} />
                  ))}
                  {sortedHistory.length > 5 && (
                    <button onClick={() => setExpandedHistory(!expandedHistory)}
                      className="flex items-center gap-2 text-[var(--text-primary)]/50 hover:text-[var(--text-primary)]/80 text-base mt-4">
                      {expandedHistory ? <>Скрыть <ChevronUp className="w-4 h-4" /></> : <>Показать все ({sortedHistory.length}) <ChevronDown className="w-4 h-4" /></>}
                    </button>
                  )}
                  {sortedHistory.length === 0 && (
                    <div className="text-center py-16">
                      <History className="w-20 h-20 mx-auto mb-5 text-[var(--text-primary)]/20" />
                      <p className="text-[var(--text-primary)]/50 text-base">История пуста</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── Управление (только для staff) ── */}
            {activeTab === 'manage' && canShowManage && (
              <div className="p-6 space-y-8">
                {/* Статус */}
                <div className="bg-[var(--hover-1)] rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-semibold text-[var(--text-primary)] flex items-center gap-3">
                      <CheckCircle2 className="w-6 h-6 text-[var(--success)]" /> Текущий статус
                    </h3>
                    <span className={`px-4 py-1.5 rounded-xl text-base font-medium border ${getStatusColor(ticket.status)}`}>{ticket.status}</span>
                  </div>
                  <p className="text-[var(--text-primary)]/60 text-base">{STATUS_DESCRIPTIONS[ticket.status] || ''}</p>
                </div>

                {/* Смена статуса */}
                <div>
                  <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-5 flex items-center gap-3">
                    <RefreshCw className="w-5 h-5 text-[var(--info)]" /> Изменить статус
                  </h3>
                  {!canChangeStatus ? (
                    <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-5 flex items-center gap-4">
                      <AlertCircle className="w-6 h-6 text-[var(--warning)] flex-shrink-0" />
                      <p className="text-[var(--warning)]/80 text-base">У вас нет прав</p>
                    </div>
                  ) : availableStatuses.length === 0 ? (
                    <div className="bg-[var(--hover-1)] rounded-xl p-8 text-center"><p className="text-[var(--text-primary)]/50 text-lg">Нет доступных переходов</p></div>
                  ) : (
                    <div className="grid grid-cols-2 gap-4">
                      {availableStatuses.map(status => {
                        const statusBtnMap: Record<string, string> = {
                          'Новый': 'status-new', 'На согласовании': 'status-agreement', 'Открыт': 'status-open',
                          'В работе': 'status-progress', 'Ожидает ответа': 'status-waiting', 'Решён': 'status-resolved',
                          'Закрыт': 'status-closed', 'Переоткрыт': 'status-reopened', 'Отклонён': 'status-rejected',
                        };
                        const cls = statusBtnMap[status] || 'bg-[var(--hover-1)] text-[var(--text-primary)]';
                        return (
                          <button key={status} onClick={() => handleStatusChange(status)} disabled={updatingStatus}
                            className={`flex items-center justify-center gap-3 px-5 py-3 rounded-xl font-medium transition-all border ${cls} hover:opacity-90 disabled:opacity-50 text-base`}>
                            {updatingStatus ? <Loader2 className="w-5 h-5 animate-spin" /> : status}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Исполнитель - обновлённая версия */}
                {canAssign && (
                  <div>
                    <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-5 flex items-center gap-3">
                      <UserCheck className="w-5 h-5 text-[var(--info)]" /> Исполнитель
                    </h3>
                    <div className="bg-[var(--hover-1)] rounded-xl p-6">
                      {ticket.assignee_id ? (
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-red-700 to-red-800 flex items-center justify-center">
                              <User className="w-6 h-6 text-white" />
                            </div>
                            <div>
                              <p className="text-[var(--text-primary)] font-semibold text-base">{getAssigneeName() || 'Исполнитель'}</p>
                              <p className="text-[var(--text-primary)]/40 text-base">Текущий исполнитель</p>
                            </div>
                          </div>
                          <button
          onClick={() => { loadSupportUsers(); setShowAssigneeModal(true); }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                     bg-[var(--hover-2)] hover:bg-[var(--hover-3)] 
                     text-[var(--text-primary)]/70 hover:text-[var(--text-primary)]
                     border border-[var(--border-color)] hover:border-[var(--border-hover)]
                     transition-all duration-200"
        >
          Изменить
        </button>
                        </div>
                      ) : (
                        <div className="text-center py-5">
                          <p className="text-[var(--text-primary)]/50 text-lg mb-4">Не назначен</p>
                          <button onClick={() => { loadSupportUsers(); setShowAssigneeModal(true); }}
                            className="px-5 py-2.5 rounded-xl bg-[var(--accent)]/50 hover:bg-[var(--accent)] text-white text-base">
                            <UserPlus className="w-5 h-5 inline mr-2" />Назначить
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Архивирование */}
                <div className="border border-[var(--accent)]/30 rounded-xl overflow-hidden">
                  <div className="px-6 py-4 bg-red-950/20 border-b border-[var(--accent)]/30">
                    <h3 className="text-base font-semibold text-[var(--accent)]/80 uppercase tracking-wider">Архивирование</h3>
                  </div>
                  <div className="p-6">
                    {ticket.is_archived ? (
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2 mb-1"><Archive className="w-5 h-5 text-amber-400" /><span className="text-base font-semibold text-[var(--text-primary)]">В архиве</span></div>
                          <p className="text-base text-[var(--text-primary)]/40">Доступна только для чтения</p>
                        </div>
                        <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-base font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
                          <Archive className="w-4 h-4" /> Архив
                        </span>
                      </div>
                    ) : canArchive() ? (
                      <div className="flex items-center justify-between gap-6">
                        <div>
                          <div className="flex items-center gap-2 mb-1"><Archive className="w-5 h-5 text-[var(--text-primary)]/60" /><span className="text-base font-semibold text-[var(--text-primary)]">Архивировать</span></div>
                          <p className="text-base text-[var(--text-primary)]/40">Скроется из основного списка</p>
                        </div>
                        <button onClick={() => setShowArchiveConfirm(true)} disabled={archiving}
                          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 border border-amber-600/30 text-amber-400 text-base font-medium disabled:opacity-50 flex-shrink-0">
                          {archiving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Archive className="w-5 h-5" />}
                          Архивировать
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-4 text-[var(--text-primary)]/30">
                        <Archive className="w-5 h-5 flex-shrink-0" />
                        <p className="text-base">Нет прав для архивирования</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Правая колонка ── */}
        <div className="space-y-6 animate-in fade-in duration-500">
         {/* Исполнитель */}
<div className="bg-[var(--hover-1)] backdrop-blur-sm rounded-xl border border-[var(--border-color)] p-6">
  <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-5 flex items-center gap-3">
    <UserCheck className="w-5 h-5 text-[var(--text-primary)]/60" /> Исполнитель
  </h3>
  {ticket.assignee_id ? (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-red-700 to-red-800 flex items-center justify-center shadow-sm">
          <User className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className="font-semibold text-[var(--text-primary)] text-base">
            {getAssigneeName() || 'Исполнитель'}
          </p>
          <p className="text-sm text-[var(--text-primary)]/40">Текущий исполнитель</p>
        </div>
      </div>
      {canAssign && (
        <button
          onClick={() => { loadSupportUsers(); setShowAssigneeModal(true); }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                     bg-[var(--hover-2)] hover:bg-[var(--hover-3)] 
                     text-[var(--text-primary)]/70 hover:text-[var(--text-primary)]
                     border border-[var(--border-color)] hover:border-[var(--border-hover)]
                     transition-all duration-200"
        >
          Изменить
        </button>
      )}
    </div>
  ) : (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-[var(--hover-2)] border border-dashed border-[var(--border-color)] flex items-center justify-center">
          <User className="w-6 h-6 text-[var(--text-primary)]/30" />
        </div>
        <div>
          <p className="text-[var(--text-primary)]/40 text-base">Не назначен</p>
        </div>
      </div>
      {canAssign && (
        <button
          onClick={() => { loadSupportUsers(); setShowAssigneeModal(true); }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                     bg-[var(--accent)]/10 hover:bg-[var(--accent)]/20
                     text-[var(--accent)] hover:text-[var(--accent-light)]
                     border border-[var(--accent)]/20 hover:border-[var(--accent)]/40
                     transition-all duration-200"
        >
          <UserPlus className="w-4 h-4" />
          Назначить
        </button>
      )}
    </div>
  )}
</div>
         
          {/* Информация */}
          <div className="bg-[var(--hover-1)] backdrop-blur-sm rounded-xl border border-[var(--border-color)] p-6">
            <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-5 flex items-center gap-3">
              <FileText className="w-5 h-5 text-[var(--text-primary)]/60" /> Информация
            </h3>
            <div className="space-y-4">
              {[
                { label: 'Номер', value: <span className="font-mono">{ticket.number || '—'}</span> },
                { label: 'Тип', value: <span className={`px-3 py-1 rounded-lg text-base font-medium border ${getTypeColor(ticket.type)}`}>{ticket.type}</span> },
                { label: 'Статус', value: <span className={`px-3 py-1 rounded-lg text-base font-medium border ${getStatusColor(ticket.status)}`}>{ticket.status}</span> },
                { label: 'Приоритет', value: <span className={`px-3 py-1 rounded-lg text-base font-medium border ${getPriorityColor(ticket.priority)}`}>{ticket.priority}</span> },
              ].map(r => (
                <div key={r.label} className="flex justify-between items-center py-2 border-b border-[var(--border-color)]">
                  <span className="text-[var(--text-primary)]/50 text-base">{r.label}</span>{r.value}
                </div>
              ))}
              {ticket.is_archived && (
                <div className="flex justify-between items-center py-2 border-b border-[var(--border-color)]">
                  <span className="text-[var(--text-primary)]/50 text-base">Архив</span>
                  <span className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-base font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30"><Archive className="w-3.5 h-3.5" /> Да</span>
                </div>
              )}
              <div className="pt-3 space-y-3">
                {[{ label: 'Создана', value: formatDate(ticket.created_at) },
                ...(ticket.closed_at ? [{ label: 'Закрыта', value: formatDate(ticket.closed_at) }] : []),
                { label: 'Обновлена', value: formatDate(ticket.updated_at) },
                ].map(r => (
                  <div key={r.label}><span className="text-[var(--text-primary)]/50 text-base block mb-1">{r.label}</span><span className="text-[var(--text-primary)] text-base">{r.value}</span></div>
                ))}
              </div>
            </div>
          </div>

          {/* Контрагент */}
          <div className="bg-[var(--hover-1)] backdrop-blur-sm rounded-xl border border-[var(--border-color)] p-6">
            <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-5 flex items-center gap-3">
              <Building2 className="w-5 h-5 text-[var(--text-primary)]/60" /> Контрагент
            </h3>
            {counterparty ? (
              <div className="space-y-3">
                <p className="text-[var(--text-primary)] font-semibold text-lg">{counterparty.name}</p>
                <p className="text-[var(--text-primary)]/50 text-base">{counterparty.legal_name}</p>
                {counterparty.inn && <p className="text-[var(--text-primary)]/40 text-base">ИНН: {counterparty.inn}</p>}
                {counterparty.phone && <a href={`tel:${counterparty.phone}`} className="flex items-center gap-2 text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]/60 text-base"><Phone className="w-4 h-4" />{counterparty.phone}</a>}
                {counterparty.email && <a href={`mailto:${counterparty.email}`} className="flex items-center gap-2 text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]/60 text-base break-all"><Mail className="w-4 h-4" />{counterparty.email}</a>}
              </div>
            ) : <p className="text-[var(--text-primary)]/50 text-base">Не указан</p>}
          </div>

          

          {/* Автор */}
          <div className="bg-[var(--hover-1)] backdrop-blur-sm rounded-xl border border-[var(--border-color)] p-6">
            <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-5 flex items-center gap-3">
              <User className="w-5 h-5 text-[var(--text-primary)]/60" /> Автор
            </h3>
            {(() => {
              const reporter = ticket.reporter;
              const createdById = ticket.created_by;
              const reporterId = ticket.reporter_id;
              if (reporter?.full_name || reporter?.username || reporter?.email) {
                const name = reporter.full_name || reporter.username || 'Пользователь';
                const email = reporter.email;
                const roleLabel: Record<string, string> = {
                  customer: 'Клиент', customer_admin: 'Администратор клиента',
                  support_agent: 'Агент', support_manager: 'Менеджер', admin: 'Администратор',
                };
                return (
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-[var(--accent)] flex items-center justify-center">
                      <User className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-[var(--text-primary)] text-base">{name}</p>
                      {email && <p className="text-sm text-[var(--text-primary)]/40">{email}</p>}
                      {reporter.role && <p className="text-xs text-[var(--text-primary)]/25 mt-0.5">{roleLabel[reporter.role] || reporter.role}</p>}
                    </div>
                  </div>
                );
              }
              const fallbackId = reporterId || createdById;
              const fallbackName = fallbackId ? actorNames.get(fallbackId) : null;
              if (fallbackName) {
                return (
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-[var(--accent)] flex items-center justify-center">
                      <User className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-[var(--text-primary)] text-base">{fallbackName}</p>
                      <p className="text-xs text-[var(--text-primary)]/25 mt-0.5">Автор заявки</p>
                    </div>
                  </div>
                );
              }
              if (createdById === user?.user_id) {
                return (
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-[var(--accent)] flex items-center justify-center">
                      <User className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-[var(--text-primary)] text-base">{user?.full_name || user?.username || 'Вы'}</p>
                      {user?.email && <p className="text-sm text-[var(--text-primary)]/40">{user.email}</p>}
                    </div>
                  </div>
                );
              }
              return <p className="text-[var(--text-primary)]/30 text-base">Автор не указан</p>;
            })()}
          </div>
        </div>
      </div>

      {/* ── Превью файла ── */}
      {previewFile && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[var(--bg-primary)]/95 p-4" onClick={closePreview}>
          <div className="bg-zinc-900 rounded-3xl w-full max-w-5xl max-h-[95vh] flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center px-6 py-4 border-b border-[var(--border-color)]">
              <div className="text-lg font-medium text-white truncate pr-8">{previewFile.original_filename}</div>
              <button onClick={closePreview} className="text-white/50 hover:text-white/90 text-3xl">×</button>
            </div>
            <div className="flex-1 flex items-center justify-center bg-[var(--bg-primary)] p-6 overflow-auto">
              {previewFile.mime_type.startsWith('image/')
                ? <img src={imagePreviews[previewFile.id] || ''} alt="" className="max-h-[80vh] max-w-full object-contain rounded-2xl" />
                : <div className="text-center">
                  <File className="w-24 h-24 mx-auto mb-6 text-[var(--text-primary)]/30" />
                  <p className="text-2xl text-[var(--text-primary)] mb-3">Предпросмотр недоступен</p>
                  <button onClick={() => handleDownload(previewFile.id)} className="mt-6 px-10 py-3.5 bg-[var(--accent)]/50 hover:bg-[var(--accent)]/80 rounded-2xl text-white font-medium">Скачать</button>
                </div>
              }
            </div>
          </div>
        </div>
      )}

      {/* ── Модалка назначения исполнителя ── */}
      {showAssigneeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowAssigneeModal(false)} />
          <div className="relative w-full max-w-lg max-h-[80vh] flex flex-col bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden"
            style={{ boxShadow: 'var(--shadow-lg)' }}>

            <div className="flex items-center justify-between px-6 py-5 border-b border-[var(--border-color)] bg-[var(--hover-1)] flex-shrink-0">
              <div>
                <h2 className="text-lg font-bold text-[var(--text-primary)]">
                  {ticket.assignee_id ? 'Изменить исполнителя' : 'Назначить исполнителя'}
                </h2>
                <p className="text-sm text-[var(--text-primary)]/40 mt-0.5">#{ticket.number}</p>
              </div>
              <button onClick={() => setShowAssigneeModal(false)} disabled={updatingAssignee}
                className="p-2 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]"><X size={20} /></button>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto p-6">
              <div className="relative mb-4">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-primary)]/40" />
                <input
                  value={searchUser}
                  onChange={e => setSearchUser(e.target.value)}
                  placeholder="Поиск по имени, email..."
                  className="w-full pl-12 pr-4 py-3 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/30 text-base"
                />
              </div>

              {loadingSupports ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 text-[var(--text-primary)]/30 animate-spin" />
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="text-center py-8 text-[var(--text-primary)]/40">
                  <User className="w-12 h-12 mx-auto mb-3 opacity-40" />
                  <p>Нет сотрудников для назначения</p>
                </div>
              ) : (
                <div className="space-y-2">
                 
                  {filteredUsers.map(emp => (
                    <button
                      key={emp.id}
                      onClick={() => handleAssign(emp.id)}
                      className="w-full flex items-center gap-3 p-4 rounded-xl hover:bg-[var(--hover-1)] border border-[var(--border-color)] transition-colors text-left"
                    >
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-700 to-red-800 flex items-center justify-center flex-shrink-0">
                        <User className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[var(--text-primary)] font-medium text-base truncate">
                          {emp.full_name || emp.username}
                        </p>
                        <p className="text-[var(--text-primary)]/40 text-sm truncate">{emp.email}</p>
                      </div>
                      {ticket.assignee_id === emp.id && (
                        <UserCheck className="w-5 h-5 text-[var(--success)] flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[var(--border-color)] bg-[var(--hover-1)] flex-shrink-0">
              <button
                onClick={() => setShowAssigneeModal(false)}
                disabled={updatingAssignee}
                className="px-5 py-2.5 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-base"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Модалка редактирования ── */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => !savingEdit && setShowEditModal(false)} />
          <div className="relative w-full max-w-3xl max-h-[90vh] flex flex-col bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden"
            style={{ boxShadow: 'var(--shadow-lg)' }}>
            <div className="flex items-center justify-between px-6 py-5 border-b border-[var(--border-color)] bg-[var(--hover-1)] flex-shrink-0">
              <div>
                <h2 className="text-lg font-bold text-[var(--text-primary)]">Редактировать заявку</h2>
                <p className="text-sm text-[var(--text-primary)]/40 mt-0.5">#{ticket.number}</p>
              </div>
              <button onClick={() => setShowEditModal(false)} disabled={savingEdit}
                className="p-2 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]"><X size={20} /></button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-6">
              <div>
                <label className="block text-base font-medium text-[var(--text-primary)]/70 mb-2">Тема <span className="text-[var(--accent)]">*</span></label>
                <input type="text" value={editTitle} onChange={e => setEditTitle(e.target.value)}
                  className="w-full px-4 py-3 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] text-base focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)]" />
              </div>
              <div>
                <label className="block text-base font-medium text-[var(--text-primary)]/70 mb-2">Описание</label>
                <TicketEditor blocks={editDescBlocks} onChange={setEditDescBlocks} />
              </div>
              <div>
                <label className="block text-base font-medium text-[var(--text-primary)]/70 mb-3">Приоритет</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { value: 'Низкий', cls: 'priority-low' },
                    { value: 'Средний', cls: 'priority-medium' },
                    { value: 'Высокий', cls: 'priority-high' },
                    { value: 'Критический', cls: 'priority-critical' },
                  ].map(p => (
                    <button key={p.value} type="button" onClick={() => setEditPriority(p.value)}
                      className={`px-3 py-2.5 rounded-xl text-base font-medium border transition-all ${editPriority === p.value ? p.cls : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-muted)] hover:bg-[var(--hover-2)]'
                        }`}>{p.value}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-base font-medium text-[var(--text-primary)]/70 mb-3">Теги</label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {editTags.map(tag => (
                    <span key={tag.name} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-base font-medium"
                      style={{ backgroundColor: (tag.color || '#64748b') + '25', color: tag.color || '#94a3b8' }}>
                      {tag.name}
                      <button type="button" onClick={() => setEditTags(p => p.filter(t => t.name !== tag.name))} className="text-[var(--text-primary)]/30 hover:text-[var(--accent)]"><X size={13} /></button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input value={editNewTag} onChange={e => setEditNewTag(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') {
                        e.preventDefault(); const n = editNewTag.trim();
                        if (n && !editTags.some(t => t.name.toLowerCase() === n.toLowerCase())) { setEditTags(p => [...p, { name: n, color: '#64748b' }]); setEditNewTag(''); }
                      }
                    }}
                    placeholder="Новый тег (Enter)" className="flex-1 px-4 py-2.5 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] text-base placeholder-[var(--text-muted)] focus:outline-none" />
                  <button type="button" disabled={!editNewTag.trim()}
                    onClick={() => { const n = editNewTag.trim(); if (n && !editTags.some(t => t.name.toLowerCase() === n.toLowerCase())) { setEditTags(p => [...p, { name: n, color: '#64748b' }]); setEditNewTag(''); } }}
                    className="px-4 py-2.5 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/60 disabled:opacity-30"><Plus className="w-4 h-4" /></button>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[var(--border-color)] bg-[var(--hover-1)] flex-shrink-0">
              <button onClick={() => setShowEditModal(false)} disabled={savingEdit}
                className="px-5 py-2.5 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-base">Отмена</button>
              <button onClick={handleSaveEdit} disabled={savingEdit || !editTitle.trim()}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent)] text-white text-base font-medium disabled:opacity-40 shadow-[var(--shadow-md)]">
                {savingEdit && <Loader2 size={16} className="animate-spin" />}
                {savingEdit ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Подтверждение удаления комментария ── */}
      <ConfirmModal isOpen={showDeleteConfirm}
        onClose={() => { setShowDeleteConfirm(false); setCommentToDelete(null); }}
        onConfirm={() => { if (commentToDelete) handleDeleteComment(commentToDelete); setShowDeleteConfirm(false); setCommentToDelete(null); }}
        title="Удалить комментарий" message="Это действие нельзя отменить."
        confirmText="Удалить" cancelText="Отмена" type="danger" />

      {/* ── Подтверждение архивирования ── */}
      <ConfirmModal isOpen={showArchiveConfirm}
        onClose={() => setShowArchiveConfirm(false)}
        onConfirm={handleArchive}
        title="Архивировать заявку" message={`«${ticket.title}» будет перемещена в архив.`}
        confirmText={archiving ? 'Архивируем...' : 'Архивировать'} cancelText="Отмена" type="warning" />
    </div>
  );
}