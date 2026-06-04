// pages/TicketsPage.tsx
import { useState, useEffect, useRef, useCallback } from 'react';
import type { ElementType, ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus, Search, FileText, ChevronRight, ChevronLeft, Loader2,
  Clock, AlertTriangle, CheckCircle2, Calendar, XCircle,
  Building2, User, X, SlidersHorizontal, ChevronDown, Check,
  Sparkles, Flame, MessageSquare, HelpCircle, Edit3, FolderOpen,
  UserCheck,
} from 'lucide-react';
import { ticketsApi } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import type { TicketListItem, TicketStatus, TicketPriority } from '../types';

const STATUSES: { value: TicketStatus; label: string; color: string }[] = [
  { value: 'Новый', label: 'Новый', color: 'status-new' },
  { value: 'На согласовании', label: 'На согласовании', color: 'status-agreement' },
  { value: 'Открыт', label: 'Открыт', color: 'status-open' },
  { value: 'В работе', label: 'В работе', color: 'status-progress' },
  { value: 'Ожидает ответа', label: 'Ожидает ответа', color: 'status-waiting' },
  { value: 'Решён', label: 'Решён', color: 'status-resolved' },
  { value: 'Закрыт', label: 'Закрыт', color: 'status-closed' },
  { value: 'Переоткрыт', label: 'Переоткрыт', color: 'status-reopened' },
];

const PRIORITIES: { value: TicketPriority; label: string; color: string }[] = [
  { value: 'Низкий', label: 'Низкий', color: 'priority-low' },
  { value: 'Средний', label: 'Средний', color: 'priority-medium' },
  { value: 'Высокий', label: 'Высокий', color: 'priority-high' },
  { value: 'Критический', label: 'Критический', color: 'priority-critical' },
];

const TICKET_TYPES: { value: string; label: string; icon: ReactNode; color: string }[] = [
  { value: 'Инцидент', label: 'Инцидент', icon: null, color: 'type-incident' },
  { value: 'Запрос на услугу', label: 'Запрос на услугу', icon: null, color: 'type-service' },
  { value: 'Консультация', label: 'Консультация', icon: null, color: 'type-consultation' },
  { value: 'Жалоба', label: 'Жалоба', icon: null, color: 'type-complaint' },
  { value: 'Задача', label: 'Задача', icon: null, color: 'type-task' },
  { value: 'Проблема', label: 'Проблема', icon: null, color: 'type-problem' },
  { value: 'Запрос на изменение', label: 'Запрос на изменение', icon: null, color: 'type-change' },
  { value: 'Улучшение', label: 'Улучшение', icon: null, color: 'type-improvement' },
  { value: 'Прочее', label: 'Прочее', icon: null, color: 'type-other' },
];

const STATUS_ICON: Record<string, ReactNode> = {
  'Новый': null,
  'На согласовании': null,
  'Открыт': null,
  'В работе': null,
  'Ожидает ответа': null,
  'Решён': null,
  'Закрыт': null,
  'Переоткрыт': null,
};


function toShortName(fullName: string | null | undefined): string {
  if (!fullName) return '—';
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 1) return parts[0];
  const [last, first, middle] = parts;
  const initials = [first, middle]
    .filter(Boolean)
    .map(p => `${p[0].toUpperCase()}.`)
    .join('');
  return initials ? `${last} ${initials}` : last;
}

interface DropdownOption {
  value: string;
  label: string;
  sublabel?: string;
  color?: string;
}

interface FilterDropdownProps {
  label: string;
  icon?: ReactNode;
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  searchable?: boolean;
}

function FilterDropdown({
  label, icon, options, value, onChange, placeholder = 'Все', searchable = false,
}: FilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false); setQuery('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    if (open && searchable) setTimeout(() => inputRef.current?.focus(), 50);
    if (!open) setQuery('');
  }, [open, searchable]);

  const selected = options.find(o => o.value === value);
  const filtered = query
    ? options.filter(o =>
      o.label.toLowerCase().includes(query.toLowerCase()) ||
      o.sublabel?.toLowerCase().includes(query.toLowerCase()))
    : options;

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(!open)}
        className={`w-full flex items-center justify-between gap-2 px-3.5 py-2.5 rounded-xl border text-base
          transition-all whitespace-nowrap cursor-pointer
          ${open
            ? 'bg-[var(--hover-2)] border-red-500/40 text-[var(--text-primary)]'
            : value
              ? 'bg-[var(--hover-2)] border-[var(--border-color)] text-[var(--text-primary)]/90'
              : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-primary)]/50 hover:text-[var(--text-primary)]/70'
          }`}>
        <span className="flex items-center gap-2 truncate">
          {icon && <span className={value ? 'text-red-400' : 'text-[var(--text-primary)]/40'}>{icon}</span>}
          {selected ? (
            <span className="flex items-center gap-2 truncate">
              {selected.color && (
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: `var(--${selected.color}-text)` }} />
              )}
              <span className="truncate">{selected.label}</span>
            </span>
          ) : <span className="truncate">{label}</span>}
        </span>
        {value ? (
          <span role="button" tabIndex={0}
            onClick={e => { e.stopPropagation(); onChange(''); setOpen(false); }}
            onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); onChange(''); setOpen(false); } }}
            className="ml-1 p-0.5 rounded-md hover:bg-[var(--hover-1)] text-[var(--text-primary)]/30
                       hover:text-[var(--text-primary)]/60 cursor-pointer transition-colors">
            <X size={18} />
          </span>
        ) : (
          <ChevronDown size={18}
            className={`text-[var(--text-primary)]/30 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        )}
      </button>

      {open && (
        <div className="absolute z-[100] min-w-[220px] w-max top-full mt-2 left-0
                        bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden"
          style={{ boxShadow: 'var(--shadow-lg)' }}>
          {searchable && (
            <div className="p-2 border-b border-[var(--border-color)]">
              <div className="relative">
                <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)} placeholder="Поиск..."
                  className="w-full pl-7 pr-3 py-1.5 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-color)]
                             text-base text-[var(--text-primary)] placeholder-[var(--text-muted)]
                             focus:outline-none focus:border-[var(--border-hover)]" />
              </div>
            </div>
          )}
          <div className="py-1.5 max-h-[300px] overflow-y-auto">
            <button type="button" onClick={() => { onChange(''); setOpen(false); setQuery(''); }}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left text-base transition-colors
                ${!value ? 'bg-red-500/10 text-[var(--text-primary)]' : 'text-[var(--text-primary)]/60 hover:bg-[var(--hover-1)]'}`}>
              {!value ? <Check size={18} className="text-red-400 flex-shrink-0" /> : <span className="w-4 flex-shrink-0" />}
              <span>{placeholder}</span>
            </button>
            <div className="h-px bg-[var(--hover-2)] mx-3 my-1" />
            {filtered.length === 0 ? (
              <div className="px-4 py-6 text-center text-base text-[var(--text-muted)]">Ничего не найдено</div>
            ) : filtered.map(option => {
              const isSelected = option.value === value;
              return (
                <button type="button" key={option.value}
                  onClick={() => { onChange(option.value); setOpen(false); setQuery(''); }}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left text-base transition-colors
                    ${isSelected ? 'bg-red-500/10 text-[var(--text-primary)]' : 'text-[var(--text-primary)]/70 hover:bg-[var(--hover-1)]'}`}>
                  {isSelected ? <Check size={18} className="text-red-400 flex-shrink-0" /> : <span className="w-4 flex-shrink-0" />}
                  {option.color ? (
                    <span className={`px-2.5 py-1 rounded-lg text-base font-medium border ${option.color}`}>{option.label}</span>
                  ) : (
                    <div className="min-w-0">
                      <span className="block truncate">{option.label}</span>
                      {option.sublabel && <span className="block text-base text-[var(--text-muted)] truncate">{option.sublabel}</span>}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}


function StatCard({ label, value, icon: Icon, color, bg }: {
  label: string; value: number; icon: ElementType; color: string; bg: string;
}) {
  return (
    <div className=" rounded-xl border border-[var(--border-color)] p-4 flex items-center gap-3
                    hover:border-[var(--border-hover)] hover:-translate-y-0.5 transition-all duration-200">
      <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center flex-shrink-0`}>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <div>
        <p className="text-2xl font-bold text-[var(--text-primary)] leading-none mb-0.5">{value}</p>
        <p className="text-base text-[var(--text-secondary)]">{label}</p>
      </div>
    </div>
  );
}


function FilterTag({ label, icon, colorClass, onRemove }: {
  label: string; icon?: ReactNode; colorClass?: string; onRemove: () => void;
}) {
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-base border transition-all hover:opacity-80
      ${colorClass || 'bg-[var(--hover-2)] text-[var(--text-primary)]/80 border-[var(--border-color)]'}`}>
      {icon}
      <span className="truncate max-w-[180px]">{label}</span>
      <X size={12} className="cursor-pointer opacity-50 hover:opacity-100 transition-opacity flex-shrink-0"
        onClick={e => { e.preventDefault(); e.stopPropagation(); onRemove(); }} />
    </span>
  );
}


function TicketRow({ ticket, formatDate, getStatusColor, getPriorityColor, getTypeColor }: {
  ticket: TicketListItem;
  formatDate: (d: string) => string;
  getStatusColor: (s: string) => string;
  getPriorityColor: (p: string) => string;
  getTypeColor: (t: string) => string;
}) {
  return (
    <Link
      to={`/tickets/${ticket.number}`}
      className="grid items-start px-4 py-3.5 rounded-xl
                 hover:bg-[var(--hover-1)] active:bg-[var(--hover-2)]
                 transition-colors duration-100 group"
      style={{ gridTemplateColumns: 'minmax(0,2fr) minmax(0,1fr) minmax(0,1fr) 110px 120px 110px 20px' }}
    >
      {/* ── Название + номер ── */}
      <div className="min-w-0 pr-3">
        <span className="text-[17px] font-semibold text-[var(--text-primary)] block leading-snug
                         group-hover:text-[var(--accent-light)] transition-colors line-clamp-1">
          {ticket.title}
        </span>
        <span className="text-[15px] font-mono text-[var(--text-primary)]/65 mt-0.5 block">
          {ticket.number}
        </span>
      </div>

      {/* ── Контрагент ── */}
      <div className="min-w-0 pr-2 self-center">
        {ticket.counterparty_name ? (
          <span className="flex items-center gap-1 text-[16px] text-[var(--text-primary)]/60 truncate">
            <Building2 size={18} className="shrink-0 text-[var(--text-primary)]/30" />
            <span className="truncate">{ticket.counterparty_name}</span>
          </span>
        ) : (
          <span className="text-[16px] text-[var(--text-primary)]/20">—</span>
        )}
        {ticket.project_key && (
          <span className="flex items-center gap-1 text-[16px] text-[var(--text-primary)]/35 mt-0.5 truncate">
            <FolderOpen size={18} className="shrink-0" />
            <span className="font-mono truncate">{ticket.project_key}</span>
          </span>
        )}
      </div>

      {/* ── Исполнитель ── */}
      <div className="min-w-0 pr-2 self-center">
        {ticket.assignee_full_name ? (
          <span className="flex items-center gap-1 text-[16px] text-[var(--text-primary)]/60 truncate">
            <UserCheck size={18} className="shrink-0 text-[var(--text-primary)]/30" />
            <span className="truncate">{toShortName(ticket.assignee_full_name)}</span>
          </span>
        ) : (
          <span className="text-[16px] text-[var(--text-primary)]/20">—</span>
        )}
        {ticket.reporter_full_name && (
          <span className="flex items-center gap-1 text-[16px] text-[var(--text-primary)]/35 mt-0.5 truncate">
            <User size={18} className="shrink-0" />
            <span className="truncate">{toShortName(ticket.reporter_full_name)}</span>
          </span>
        )}
      </div>

      {/* ── Статус ── */}
      <div className="self-center">
        <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[16px] font-semibold
                         border whitespace-nowrap ${getStatusColor(ticket.status)}`}>
          {ticket.status}
        </span>
      </div>

      {/* ── Приоритет ── */}
      <div className="self-center">
        <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[16px] font-semibold
                         border whitespace-nowrap ${getPriorityColor(ticket.priority)}`}>
          {ticket.priority}
        </span>
      </div>

      {/* ── Дата ── */}
      <div className="self-center text-right">
        <span className="text-[15px] text-[var(--text-primary)]/45 whitespace-nowrap">
          {formatDate(ticket.created_at)}
        </span>
      </div>

      {/* ── Стрелка ── */}
      <div className="self-center flex justify-end">
        <ChevronRight size={18}
          className="text-[var(--text-primary)]/20 group-hover:text-[var(--accent-light)]
                     group-hover:translate-x-0.5 transition-all shrink-0" />
      </div>
    </Link>
  );
}


function TableHeader() {
  const cols: { label: string; align?: string }[] = [
    { label: 'Заявка' },
    { label: 'Контрагент / Проект' },
    { label: 'Исполнитель / Автор' },
    { label: 'Статус' },
    { label: 'Приоритет' },
    { label: 'Дата', align: 'text-right' },
    { label: '' },
  ];

  return (
    <div
      className="hidden lg:grid px-4 py-2 text-[13px] uppercase tracking-widest
                 font-semibold text-[var(--text-primary)]/25
                 border-b border-[var(--border-color)]"
      style={{ gridTemplateColumns: 'minmax(0,2fr) minmax(0,1fr) minmax(0,1fr) 110px 120px 110px 20px' }}
    >
      {cols.map((c, i) => (
        <div key={i} className={c.align || ''}>
          {c.label}
        </div>
      ))}
    </div>
  );
}


function EmptyState({ hasFilters, hasSearch, onCreateClick }: {
  hasFilters: boolean; hasSearch: boolean; onCreateClick: () => void;
}) {
  return (
    <div className=" rounded-2xl border border-[var(--border-color)] p-16 text-center">
      <div className="w-20 h-20 rounded-2xl bg-[var(--hover-1)] flex items-center justify-center mx-auto mb-6">
        <FileText className="w-10 h-10 text-[var(--text-primary)]/20" />
      </div>
      <h3 className="text-2xl font-bold text-[var(--text-primary)] mb-3">Нет заявок</h3>
      <p className="text-base text-[var(--text-secondary)] mb-8 max-w-md mx-auto">
        {hasSearch
          ? 'По вашему запросу ничего не найдено'
          : hasFilters
            ? 'Попробуйте изменить параметры фильтрации'
            : 'Создайте первую заявку, чтобы начать работу'}
      </p>
      {!hasFilters && !hasSearch && (
        <button onClick={onCreateClick} className="btn-primary py-4 px-8 text-base">
          <Plus size={18} /> Создать заявку
        </button>
      )}
    </div>
  );
}


export default function TicketsPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [tickets, setTickets] = useState<TicketListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<TicketStatus | ''>('');
  const [priorityFilter, setPriorityFilter] = useState<TicketPriority | ''>('');
  const [typeFilter, setTypeFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  /* ── Debounce ─ */
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 500);
    return () => clearTimeout(t);
  }, [search]);

  /* ── Сброс страницы при смене фильтров ──────────────────────────── */
  useEffect(() => { setPage(1); }, [statusFilter, priorityFilter, typeFilter, debouncedSearch]);

  /* ── Загрузка  */
  const loadTickets = useCallback(async () => {
    setLoading(true);
    try {
      const response = await ticketsApi.getAll(page, 20, {
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        ticket_type: typeFilter || undefined,
        query: debouncedSearch || undefined,
      });
      setTickets(response.items);
      setTotalPages(response.total_pages);
      setTotalItems(response.total_items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setInitialLoad(false);
    }
  }, [page, statusFilter, priorityFilter, typeFilter, debouncedSearch]);

  useEffect(() => { loadTickets(); }, [loadTickets]);

  /* ── Helpers ── */
  const resetFilters = () => {
    setStatusFilter('');
    setPriorityFilter('');
    setTypeFilter('');
    setSearch('');
    setPage(1);
  };

  const hasFilters = !!(statusFilter || priorityFilter || typeFilter);
  const hasActiveFilters = !!(hasFilters || debouncedSearch);
  const activeFiltersCount = [statusFilter, priorityFilter, typeFilter].filter(Boolean).length;

  const getStatusColor = (s: string) => STATUSES.find(x => x.value === s)?.color || 'status-closed';
  const getPriorityColor = (p: string) => PRIORITIES.find(x => x.value === p)?.color || 'priority-medium';
  const getTypeColor = (t: string) => TICKET_TYPES.find(x => x.value === t)?.color || 'type-other';

  const formatDate = (d: string) => {
    if (!d) return '—';
    const date = new Date(d);
    const now = new Date();

    // Обнуляем время для корректного сравнения дат
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const compareDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const diffDays = Math.floor((today.getTime() - compareDate.getTime()) / 86400000);

    if (diffDays === 0) {
      // Сегодня — показываем "Сегодня, HH:MM"
      return `Сегодня, ${date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
    }
    if (diffDays === 1) return 'Вчера';
    if (diffDays < 7) return `${diffDays} дн. назад`;

    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  };

  /* ── Options ── */
  const statusOptions: DropdownOption[] = STATUSES.map(s => ({ value: s.value, label: s.label, color: s.color }));
  const priorityOptions: DropdownOption[] = PRIORITIES.map(p => ({ value: p.value, label: p.label, color: p.color }));
  const typeOptions: DropdownOption[] = TICKET_TYPES.map(t => ({ value: t.value, label: t.label }));

  /* ── Initial loader ───────── */
  if (initialLoad) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
      </div>
    );
  }

  /* ── Render ─── */
  return (
    <div className="space-y-6 animate-in fade-in duration-500">

      {/* ── Header ──────────── */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)] mb-1.5">
            {user?.role === 'customer' ? 'Мои заявки' : 'Заявки'}
          </h1>
          <p className="text-base text-[var(--text-primary)]/50">
            Управление обращениями
            {totalItems > 0 && (
              <span className="ml-2 px-2 py-0.5 rounded-full bg-[var(--hover-1)] text-[var(--text-secondary)] text-base">
                {totalItems}
              </span>
            )}
          </p>
        </div>
        <button onClick={() => navigate('/tickets/new')} className="btn-primary py-4 px-8 text-base font-semibold">
          <Plus size={18} /> Создать заявку
        </button>
      </div>

      {/* ── Stats ───────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Всего" value={totalItems}
          icon={FileText} color="text-[var(--text-secondary)]" bg="bg-[var(--hover-1)]" />
        <StatCard label="Новых" value={tickets.filter(t => t.status === 'Новый').length}
          icon={Clock} color="text-[var(--status-new-text)]" bg="bg-[var(--status-new-bg)]" />
        <StatCard label="В работе" value={tickets.filter(t => t.status === 'В работе' || t.status === 'Открыт').length}
          icon={CheckCircle2} color="text-[var(--status-progress-text)]" bg="bg-[var(--status-progress-bg)]" />
        <StatCard label="Критических" value={tickets.filter(t => t.priority === 'Критический').length}
          icon={AlertTriangle} color="text-[var(--priority-critical-text)]" bg="bg-[var(--priority-critical-bg)]" />
      </div>

      {/* ── Search + Filter toggle ──────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="relative flex-1 min-w-[220px]">
          <Search size={18}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/30 pointer-events-none" />
          <input
            type="text"
            placeholder="Поиск по теме, номеру..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-10 py-3 glass-card border border-[var(--border-color)]
                       rounded-xl text-[var(--text-primary)] text-base placeholder-[var(--text-muted)]
                       focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10 transition-all"
          />
          {search && !loading && (
            <button type="button" onClick={() => setSearch('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-md
                         text-[var(--text-primary)]/30 hover:text-[var(--text-primary)]/60
                         hover:bg-[var(--hover-2)] transition-colors">
              <X size={18} />
            </button>
          )}
          {loading && search !== debouncedSearch && (
            <Loader2 size={18}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-red-500/50 animate-spin" />
          )}
        </div>

        <button onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl border text-base
            transition-all whitespace-nowrap cursor-pointer
            ${showFilters || activeFiltersCount > 0
              ? 'bg-red-500/10 border-red-500/40 text-[var(--text-primary)]'
              : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-primary)]/50 hover:text-[var(--text-primary)]/70'
            }`}>
          <SlidersHorizontal size={18}
            className={showFilters || activeFiltersCount > 0 ? 'text-red-400' : 'text-[var(--text-primary)]/40'} />
          <span>Фильтры</span>
          {activeFiltersCount > 0 ? (
            <span className="w-5 h-5 rounded-full bg-red-600 text-white text-[15px] font-bold
                             flex items-center justify-center">
              {activeFiltersCount}
            </span>
          ) : (
            <ChevronDown size={18}
              className={`text-[var(--text-primary)]/30 transition-transform duration-200 ${showFilters ? 'rotate-180' : ''}`} />
          )}
        </button>
      </div>

      {/* ── Filters panel ───── */}
      {showFilters && (
        <div className=" rounded-xl border border-[var(--border-color)] p-3.5 space-y-3
                        animate-in fade-in slide-in-from-top-1 duration-200">
          <div className="flex items-center justify-between">
            <span className="text-base font-semibold text-[var(--text-primary)]/30 uppercase tracking-widest">
              Фильтрация
            </span>
            {hasActiveFilters && (
              <button onClick={resetFilters}
                className="text-base text-red-400 hover:text-red-300 flex items-center gap-1 transition-colors">
                <X size={18} /> Сбросить
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <FilterDropdown label="Статус" options={statusOptions} value={statusFilter}
              onChange={v => setStatusFilter(v as TicketStatus | '')} placeholder="Все статусы" />
            <FilterDropdown label="Приоритет" options={priorityOptions} value={priorityFilter}
              onChange={v => setPriorityFilter(v as TicketPriority | '')} placeholder="Все приоритеты" />
            <FilterDropdown label="Тип заявки" options={typeOptions} value={typeFilter}
              onChange={v => setTypeFilter(v)} placeholder="Все типы" />
          </div>
        </div>
      )}

      {/* ── Active filter tags  */}
      {hasActiveFilters && (
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className="text-base text-[var(--text-primary)]/40 flex items-center gap-1.5">
            <SlidersHorizontal size={18} /> Фильтры:
          </span>
          {debouncedSearch && (
            <FilterTag label={`«${debouncedSearch}»`} icon={<Search size={12} />} onRemove={() => setSearch('')} />
          )}
          {statusFilter && (
            <FilterTag label={statusFilter} colorClass={`${getStatusColor(statusFilter)} border`}
              onRemove={() => setStatusFilter('')} />
          )}
          {priorityFilter && (
            <FilterTag label={priorityFilter} colorClass={`${getPriorityColor(priorityFilter)} border`}
              onRemove={() => setPriorityFilter('')} />
          )}
          {typeFilter && (
            <FilterTag label={typeFilter} colorClass={`${getTypeColor(typeFilter)} border`}
              onRemove={() => setTypeFilter('')} />
          )}
          <button onClick={resetFilters}
            className="text-base text-red-400/60 hover:text-red-400 transition-colors ml-1">
            Сбросить
          </button>
        </div>
      )}

      {/* ── Loading indicator ─ */}
      {loading && !initialLoad && (
        <div className="flex justify-center py-2">
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--hover-1)] border border-[var(--border-color)]">
            <Loader2 size={18} className="text-red-500 animate-spin" />
            <span className="text-base text-[var(--text-muted)]">Загрузка...</span>
          </div>
        </div>
      )}

      {/* ── Content ─────────── */}
      {tickets.length === 0 && !loading ? (
        <EmptyState hasFilters={hasFilters} hasSearch={!!debouncedSearch}
          onCreateClick={() => navigate('/tickets/new')} />
      ) : tickets.length > 0 ? (
        <>
          {/* ── Desktop: заголовок + строки ─────────────────────────── */}
          <div className="hidden lg:block  rounded-xl border border-[var(--border-color)] overflow-hidden">
            <TableHeader />
            <div className="divide-y divide-[var(--border-color)]/40 px-1 py-1">
              {tickets.map(ticket => (
                <TicketRow
                  key={ticket.id}
                  ticket={ticket}
                  formatDate={formatDate}
                  getStatusColor={getStatusColor}
                  getPriorityColor={getPriorityColor}
                  getTypeColor={getTypeColor}
                />
              ))}
            </div>
          </div>

          {/* ── Mobile cards ── */}
          <div className="lg:hidden space-y-2">
            {tickets.map(ticket => {
              const closed = ticket.status === 'Закрыт' || ticket.status === 'Решён';
              const typeInfo = TICKET_TYPES.find(t => t.value === ticket.type);

              return (
                <Link key={ticket.id} to={`/tickets/${ticket.number}`}
                  className="glass-card rounded-xl border border-[var(--border-color)] p-4 block
                             hover:bg-[var(--hover-1)] hover:border-[var(--border-hover)] transition-all group">

                  {/* Верх */}
                  <div className="flex items-center justify-between gap-3 mb-2.5">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="text-base font-mono text-[var(--accent-light)] bg-[var(--accent-soft)]/50
                                       px-1.5 py-0.5 rounded-md border border-[var(--accent)]/10 whitespace-nowrap">
                        {ticket.number}
                      </span>
                      {!closed ? (
                        <span className="flex items-center gap-1 text-[10px] text-green-400 font-medium">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> Активна
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
                          <XCircle size={18} /> Закрыта
                        </span>
                      )}
                    </div>
                    <ChevronRight size={18}
                      className="text-[var(--text-muted)] group-hover:text-[var(--accent-light)]
                                 group-hover:translate-x-0.5 transition-all shrink-0" />
                  </div>

                  {/* Заголовок */}
                  <h3 className="text-[18px] font-semibold text-[var(--text-primary)] mb-3 leading-snug
                                 group-hover:text-[var(--accent-light)] transition-colors line-clamp-2">
                    {ticket.title}
                  </h3>

                  {/* Бейджи */}
                  <div className="flex flex-wrap items-center gap-1.5 mb-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[15px] font-medium border ${getTypeColor(ticket.type)}`}>
                      {typeInfo?.icon} {ticket.type}
                    </span>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[15px] font-medium border ${getStatusColor(ticket.status)}`}>
                      {STATUS_ICON[ticket.status]} {ticket.status}
                    </span>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[15px] font-medium border ${getPriorityColor(ticket.priority)}`}>
                      {ticket.priority === 'Критический' && <Flame size={18} />} {ticket.priority}
                    </span>
                  </div>

                  {/* Мета */}
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-base text-[var(--text-muted)]
                                  border-t border-[var(--border-color)] pt-2.5">
                    <span className="flex items-center gap-1">
                      <Calendar size={18} />{formatDate(ticket.created_at)}
                    </span>
                    {ticket.counterparty_name && (
                      <span className="flex items-center gap-1 truncate max-w-[150px]">
                        <Building2 size={18} />{ticket.counterparty_name}
                      </span>
                    )}
                    {ticket.project_key && (
                      <span className="flex items-center gap-1 font-mono">
                        <FolderOpen size={18} />{ticket.project_key}
                      </span>
                    )}
                    {ticket.assignee_full_name && (
                      <span className="flex items-center gap-1 truncate max-w-[130px]">
                        <UserCheck size={18} />{toShortName(ticket.assignee_full_name)}
                      </span>
                    )}
                    {ticket.reporter_full_name && (
                      <span className="flex items-center gap-1 truncate max-w-[130px]">
                        <User size={18} />{toShortName(ticket.reporter_full_name)}
                      </span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>

          {/* ── Pagination ──── */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4 border-t border-[var(--border-color)]">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card border border-[var(--border-color)]
                           hover:bg-[var(--hover-2)] disabled:opacity-40 disabled:cursor-not-allowed
                           text-[var(--text-primary)] text-base transition-colors">
                <ChevronLeft className="w-4 h-4" /> Назад
              </button>

              <div className="flex items-center gap-1.5">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const pageNum = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
                  if (pageNum > totalPages) return null;
                  return (
                    <button key={pageNum} onClick={() => setPage(pageNum)}
                      className={`w-10 h-10 rounded-xl text-base font-medium transition-colors
                        ${pageNum === page
                          ? 'bg-red-700 text-white'
                          : 'glass-card text-[var(--text-primary)]/60 border border-[var(--border-color)] hover:bg-[var(--hover-2)]'
                        }`}>
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card border border-[var(--border-color)]
                           hover:bg-[var(--hover-2)] disabled:opacity-40 disabled:cursor-not-allowed
                           text-[var(--text-primary)] text-base transition-colors">
                Вперёд <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}