import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell, Check, CheckCheck, FileText, MessageSquare, UserPlus,
  AlertTriangle, Loader2, ChevronLeft, ChevronRight, Filter,
  Ticket, RefreshCw, Eye, Clock, Sparkles, X,
} from 'lucide-react';
import { notificationsApi } from '../api/client';
import type { Notification } from '../api/client';

/* ═══════════════════════════════════════════════════════════════════════════
   HELPERS
   ═══════════════════════════════════════════════════════════════════════════ */

const NOTIFICATION_META: Record<string, {
  icon: React.ElementType;
  color: string;
  bg: string;
  label: string;
}> = {
  ticket_created: {
    icon: Ticket,
    color: 'text-blue-400',
    bg: 'bg-blue-500/15',
    label: 'Новая заявка',
  },
  ticket_assigned: {
    icon: UserPlus,
    color: 'text-purple-400',
    bg: 'bg-purple-500/15',
    label: 'Назначение',
  },
  ticket_status_changed: {
    icon: RefreshCw,
    color: 'text-amber-400',
    bg: 'bg-amber-500/15',
    label: 'Смена статуса',
  },
  ticket_commented: {
    icon: MessageSquare,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/15',
    label: 'Комментарий',
  },
  ticket_resolved: {
    icon: Check,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/15',
    label: 'Решена',
  },
  ticket_closed: {
    icon: Check,
    color: 'text-[var(--text-muted)]',
    bg: 'bg-[var(--hover-2)]',
    label: 'Закрыта',
  },
};

const DEFAULT_META = {
  icon: Bell,
  color: 'text-[var(--text-muted)]',
  bg: 'bg-[var(--hover-2)]',
  label: 'Уведомление',
};

function getMeta(type: string) {
  return NOTIFICATION_META[type] || DEFAULT_META;
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return 'только что';
  if (diffMin < 60) return `${diffMin} мин. назад`;
  if (diffHours < 24) return `${diffHours} ч. назад`;
  if (diffDays === 1) return 'вчера';
  if (diffDays < 7) return `${diffDays} дн. назад`;

  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   NOTIFICATION ITEM
   ═══════════════════════════════════════════════════════════════════════════ */

function NotificationItem({
  notification,
  onMarkRead,
  onClick,
}: {
  notification: Notification;
  onMarkRead: (id: string) => void;
  onClick: (n: Notification) => void;
}) {
  const meta = getMeta(notification.type);
  const Icon = meta.icon;
  const isUnread = !notification.read;

  return (
    <div
      className={`flex items-start gap-4 px-5 py-4 transition-colors cursor-pointer group
        ${isUnread
          ? 'bg-[var(--accent-soft)]/30 hover:bg-[var(--accent-soft)]/50'
          : 'hover:bg-[var(--hover-1)]'
        }`}
      onClick={() => onClick(notification)}
    >
      {/* Индикатор непрочитанного */}
      <div className="flex-shrink-0 pt-1.5">
        {isUnread ? (
          <div className="w-2.5 h-2.5 rounded-full bg-[var(--accent)] animate-pulse" />
        ) : (
          <div className="w-2.5 h-2.5 rounded-full bg-transparent" />
        )}
      </div>

      {/* Иконка типа */}
      <div className={`w-11 h-11 rounded-xl ${meta.bg} flex items-center justify-center flex-shrink-0`}>
        <Icon className={`w-5 h-5 ${meta.color}`} />
      </div>

      {/* Контент */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className={`text-base font-semibold leading-snug
              ${isUnread ? 'text-[var(--text-primary)]' : 'text-[var(--text-primary)]/70'}`}>
              {notification.title}
            </p>
            <p className={`text-base mt-1 leading-relaxed
              ${isUnread ? 'text-[var(--text-primary)]/70' : 'text-[var(--text-primary)]/45'}`}>
              {notification.message}
            </p>
            <div className="flex items-center gap-3 mt-2">
              <span className="flex items-center gap-1.5 text-sm text-[var(--text-muted)]">
                <Clock size={13} />
                {formatTime(notification.created_at)}
              </span>
              <span className={`text-sm px-2 py-0.5 rounded-lg ${meta.bg} ${meta.color} font-medium`}>
                {meta.label}
              </span>
            </div>
          </div>

          {/* Кнопка «прочитано» */}
          {isUnread && (
            <button
              onClick={e => {
                e.stopPropagation();
                onMarkRead(notification.id);
              }}
              className="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--accent)]
                         hover:bg-[var(--hover-2)] transition-colors flex-shrink-0
                         opacity-0 group-hover:opacity-100"
              title="Прочитано"
            >
              <Eye size={18} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

export default function NotificationsPage() {
  const navigate = useNavigate();

  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);

  /* ── Load ───────────────────────────────────────────────────────────── */

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const [response, count] = await Promise.all([
        notificationsApi.getAll(page, 20, unreadOnly),
        notificationsApi.getUnreadCount(),
      ]);
      setNotifications(response.items);
      setTotalPages(response.total_pages);
      setTotalItems(response.total_items);
      setUnreadCount(count);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
      setInitialLoad(false);
    }
  }, [page, unreadOnly]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    setPage(1);
  }, [unreadOnly]);

  /* ── Actions ────────────────────────────────────────────────────────── */

  const handleMarkRead = async (id: string) => {
    // Оптимистичное обновление
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
    setUnreadCount(prev => Math.max(0, prev - 1));

    try {
      await notificationsApi.markAsRead(id);
    } catch {
      // Откатываем при ошибке
      loadNotifications();
    }
  };

  const handleMarkAllRead = async () => {
    const unreadIds = notifications.filter(n => !n.read).map(n => n.id);
    if (!unreadIds.length) return;

    setMarkingAll(true);

    // Оптимистичное обновление
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    setUnreadCount(0);

    try {
      await Promise.all(unreadIds.map(id => notificationsApi.markAsRead(id)));
    } catch {
      loadNotifications();
    } finally {
      setMarkingAll(false);
    }
  };

  const handleNotificationClick = (n: Notification) => {
    // Помечаем как прочитанное
    if (!n.read) {
      handleMarkRead(n.id);
    }

    // Переход по типу уведомления
    const ticketNumber = n.data?.ticket_number;
    if (ticketNumber) {
      navigate(`/tickets/${ticketNumber}`);
      return;
    }

    const ticketId = n.data?.ticket_id;
    if (ticketId) {
      navigate(`/tickets/${ticketId}`);
    }
  };

  /* ── Render ─────────────────────────────────────────────────────────── */

  if (initialLoad) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-[var(--accent)] animate-spin" />
      </div>
    );
  }

  const currentPageUnread = notifications.filter(n => !n.read).length;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)] mb-1.5 flex items-center gap-3">
            Уведомления
            {unreadCount > 0 && (
              <span className="px-3 py-1 rounded-full bg-[var(--accent)] text-white text-base font-bold">
                {unreadCount}
              </span>
            )}
          </h1>
          <p className="text-base text-[var(--text-primary)]/50">
            {unreadCount > 0
              ? `У вас ${unreadCount} непрочитанных уведомлений`
              : 'Все уведомления прочитаны'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Фильтр */}
          <button
            onClick={() => setUnreadOnly(!unreadOnly)}
            className={`flex items-center gap-2 px-4 py-3 rounded-xl border text-base transition-all cursor-pointer
              ${unreadOnly
                ? 'bg-[var(--accent-soft)] border-[var(--accent)]/20 text-[var(--text-primary)]'
                : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
          >
            <Filter size={16} className={unreadOnly ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'} />
            {unreadOnly ? 'Только непрочитанные' : 'Все уведомления'}
            {unreadOnly && (
              <span onClick={e => { e.stopPropagation(); setUnreadOnly(false); }}
                className="p-0.5 rounded hover:bg-[var(--hover-1)] text-[var(--text-muted)] cursor-pointer">
                <X size={14} />
              </span>
            )}
          </button>

          {/* Кнопка «Прочитать все» */}
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              disabled={markingAll}
              className="flex items-center gap-2 px-4 py-3 rounded-xl
                         bg-[var(--accent)] hover:bg-[var(--accent-hover)]
                         text-white text-base font-medium transition-colors
                         disabled:opacity-50"
            >
              {markingAll
                ? <Loader2 size={16} className="animate-spin" />
                : <CheckCheck size={16} />}
              Прочитать все
            </button>
          )}
        </div>
      </div>

      {/* ── Stats ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          {
            label: 'Всего',
            value: totalItems,
            icon: Bell,
            color: 'text-[var(--text-secondary)]',
            bg: 'bg-[var(--hover-1)]',
          },
          {
            label: 'Непрочитанных',
            value: unreadCount,
            icon: Sparkles,
            color: 'text-[var(--accent)]',
            bg: 'bg-[var(--accent-soft)]',
          },
          {
            label: 'На странице',
            value: notifications.length,
            icon: FileText,
            color: 'text-[var(--info)]',
            bg: 'bg-blue-500/10',
          },
          {
            label: 'Прочитанных',
            value: totalItems - unreadCount,
            icon: Check,
            color: 'text-[var(--success)]',
            bg: 'bg-emerald-500/10',
          },
        ].map(stat => (
          <div key={stat.label}
            className="glass-card rounded-xl border border-[var(--border-color)] p-4 flex items-center gap-3
                       hover:border-[var(--border-hover)] transition-all">
            <div className={`w-10 h-10 rounded-xl ${stat.bg} flex items-center justify-center flex-shrink-0`}>
              <stat.icon className={`w-5 h-5 ${stat.color}`} />
            </div>
            <div>
              <p className="text-2xl font-bold text-[var(--text-primary)] leading-none mb-0.5">
                {stat.value}
              </p>
              <p className="text-base text-[var(--text-secondary)]">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Loading ────────────────────────────────────────────────── */}
      {loading && !initialLoad && (
        <div className="flex justify-center py-2">
          <div className="flex items-center gap-2 px-4 py-2 rounded-full
                          bg-[var(--hover-1)] border border-[var(--border-color)]">
            <Loader2 size={14} className="text-[var(--accent)] animate-spin" />
            <span className="text-base text-[var(--text-muted)]">Загрузка...</span>
          </div>
        </div>
      )}

      {/* ── Content ────────────────────────────────────────────────── */}
      {notifications.length === 0 && !loading ? (
        <div className="glass-card rounded-2xl border border-[var(--border-color)] p-16 text-center">
          <div className="w-20 h-20 rounded-2xl bg-[var(--hover-1)] flex items-center justify-center mx-auto mb-6">
            <Bell className="w-10 h-10 text-[var(--text-primary)]/20" />
          </div>
          <h3 className="text-2xl font-bold text-[var(--text-primary)] mb-3">
            {unreadOnly ? 'Нет непрочитанных' : 'Нет уведомлений'}
          </h3>
          <p className="text-base text-[var(--text-secondary)] max-w-md mx-auto">
            {unreadOnly
              ? 'Все уведомления прочитаны. Снимите фильтр, чтобы увидеть все.'
              : 'Уведомления будут появляться здесь, когда произойдут события в ваших заявках.'}
          </p>
          {unreadOnly && (
            <button onClick={() => setUnreadOnly(false)}
              className="mt-6 px-6 py-3 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)]
                         text-[var(--text-primary)] text-base font-medium transition-colors">
              Показать все
            </button>
          )}
        </div>
      ) : (
        <div className="glass-card rounded-2xl border border-[var(--border-color)] overflow-hidden">

          {/* Шапка списка */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border-color)]
                          bg-[var(--hover-1)]/50">
            <span className="text-base text-[var(--text-muted)]">
              {unreadOnly
                ? `${totalItems} непрочитанных`
                : `${totalItems} уведомлений`}
              {currentPageUnread > 0 && !unreadOnly && (
                <span className="ml-2 text-[var(--accent)]">
                  · {currentPageUnread} новых на странице
                </span>
              )}
            </span>
          </div>

          {/* Список */}
          <div className="divide-y divide-[var(--border-color)]/50">
            {notifications.map(n => (
              <NotificationItem
                key={n.id}
                notification={n}
                onMarkRead={handleMarkRead}
                onClick={handleNotificationClick}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Pagination ─────────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4 border-t border-[var(--border-color)]">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card border border-[var(--border-color)]
                       hover:bg-[var(--hover-2)] disabled:opacity-40 disabled:cursor-not-allowed
                       text-[var(--text-primary)] text-base transition-colors"
          >
            <ChevronLeft className="w-4 h-4" /> Назад
          </button>

          <div className="flex items-center gap-1.5">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
              if (pageNum > totalPages) return null;
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`w-10 h-10 rounded-xl text-base font-medium transition-all
                    ${pageNum === page
                      ? 'bg-[var(--accent)] text-white'
                      : 'glass-card text-[var(--text-secondary)] border border-[var(--border-color)] hover:bg-[var(--hover-2)]'
                    }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card border border-[var(--border-color)]
                       hover:bg-[var(--hover-2)] disabled:opacity-40 disabled:cursor-not-allowed
                       text-[var(--text-primary)] text-base transition-colors"
          >
            Вперёд <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}