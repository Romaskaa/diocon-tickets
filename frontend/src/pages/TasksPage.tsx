// pages/TasksPage.tsx
import { useState, useCallback, useEffect, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { createPortal } from 'react-dom';
import {
  Plus, Search, Filter, Calendar,
  Loader2, X, Check, Circle, Timer, Eye,
  ArrowUpRight, ChevronDown, Flag,
  AlertCircle, CheckCircle2, Ban, RotateCcw,
  RefreshCw, Archive, FolderOpen, Ticket, Zap,
  Star, User, ChevronRight, Layers, UserCheck,
  GitPullRequest, ThumbsUp, ThumbsDown, Pencil, Save,
} from 'lucide-react';
import { tasksApi, projectsApi, ticketsApi, usersApi } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useToast } from '../components/ui/use-toast';
import type {
  TaskKanbanItem, TaskKanbanColumn, TaskStatus, TaskPriority,
  TaskCreateInput, TaskUpdateInput, TaskKanbanContext,
  SimpleUser, CounterpartyCustomer, TicketListItem, Project,
} from '../types';
import { TASK_PRIORITY_LIST } from '../types';

/* 
   CONSTANTS
    */

const STATUS_LABELS: Record<TaskStatus, string> = {
  backlog: 'В резерве', todo: 'Готово к выполнению', in_progress: 'В работе',
  review: 'На проверке', blocked: 'Приостановлено', done: 'Выполнено', cancelled: 'Отменено',
};

const ALLOWED_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  backlog: ['todo', 'cancelled'], todo: ['in_progress', 'blocked', 'cancelled'],
  in_progress: ['blocked', 'review', 'done', 'cancelled'], blocked: ['in_progress', 'cancelled'],
  review: ['in_progress', 'done', 'cancelled'], done: [], cancelled: [],
};

const ALLOWED_EDIT_STATUSES: Set<TaskStatus> = new Set(['backlog', 'todo']);
const ALLOWED_ASSIGN_STATUSES: Set<TaskStatus> = new Set([
  'backlog', 'todo', 'in_progress', 'blocked', 'review',
]);

const COLUMN_ORDER: TaskStatus[] = [
  'backlog', 'todo', 'in_progress', 'blocked', 'review', 'done', 'cancelled',
];

const COL: Record<TaskStatus, {
  icon: React.ComponentType<{ className?: string }>;
  color: string; dot: string; bg: string;
  border: string; header: string; empty: string;
}> = {
  backlog: { icon: Circle, color: 'text-slate-400', dot: 'bg-slate-400', bg: 'bg-slate-500/[0.03]', border: 'border-slate-500/20', header: 'bg-slate-500/5', empty: 'Нет задач в резерве' },
  todo: { icon: AlertCircle, color: 'text-blue-400', dot: 'bg-blue-400', bg: 'bg-blue-500/[0.03]', border: 'border-blue-500/20', header: 'bg-blue-500/5', empty: 'Нет задач к выполнению' },
  in_progress: { icon: Timer, color: 'text-[var(--warning)]', dot: 'bg-yellow-400', bg: 'bg-yellow-500/[0.03]', border: 'border-yellow-500/20', header: 'bg-yellow-500/5', empty: 'Нет задач в работе' },
  blocked: { icon: Ban, color: 'text-[var(--accent)]', dot: 'bg-[var(--accent)]', bg: 'bg-[var(--accent)]/[0.03]', border: 'border-[var(--accent)]/20', header: 'bg-[var(--accent)]/5', empty: 'Нет приостановленных' },
  review: { icon: Eye, color: 'text-violet-400', dot: 'bg-violet-400', bg: 'bg-violet-500/[0.03]', border: 'border-violet-500/20', header: 'bg-violet-500/5', empty: 'Нет задач на проверке' },
  done: { icon: CheckCircle2, color: 'text-[var(--success)]', dot: 'bg-emerald-400', bg: 'bg-emerald-500/[0.03]', border: 'border-emerald-500/20', header: 'bg-emerald-500/5', empty: 'Нет выполненных задач' },
  cancelled: { icon: RotateCcw, color: 'text-[var(--text-primary)]/30', dot: 'bg-gray-600', bg: 'bg-[var(--hover-1)]/30', border: 'border-[var(--border-color)]', header: 'bg-[var(--hover-2)]/50', empty: 'Нет отменённых задач' },
};

const PRI: Record<TaskPriority, {
  color: string; bg: string; border: string; dot: string; icon: React.ReactNode;
}> = {
  'Низкий': { color: 'text-[var(--success)]', bg: 'bg-[var(--success)]/8', border: 'border-emerald-500/30', dot: 'bg-emerald-400', icon: <Flag className="w-3 h-3" /> },
  'Средний': { color: 'text-[var(--warning)]', bg: 'bg-yellow-500/15', border: 'border-yellow-500/30', dot: 'bg-yellow-400', icon: <Flag className="w-3 h-3" /> },
  'Высокий': { color: 'text-orange-400', bg: 'bg-orange-500/15', border: 'border-orange-500/30', dot: 'bg-orange-400', icon: <Flag className="w-3 h-3" /> },
  'Критический': { color: 'text-[var(--accent)]', bg: 'bg-[var(--accent-soft)]', border: 'border-[var(--accent)]/15', dot: 'bg-[var(--accent)]', icon: <Zap className="w-3 h-3" /> },
};

type ContextMode = 'my' | 'internal' | 'project' | 'assignee';

const CTX_TABS: { id: ContextMode; label: string; icon: React.ComponentType<{ className?: string }>; staffOnly?: boolean }[] = [
  { id: 'my', label: 'Мои', icon: User },
  { id: 'internal', label: 'Все', icon: Layers, staffOnly: true },
  { id: 'project', label: 'Проект', icon: FolderOpen },
  { id: 'assignee', label: 'Исполнитель', icon: UserCheck, staffOnly: true },
];

/* 
   HELPERS
    */

const initials = (n?: string | null) =>
  n ? n.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase() : '?';
const isOverdue = (d?: string | null) => (d ? new Date(d) < new Date() : false);
const fmtDue = (d: string) => {
  const diff = Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);
  if (diff < 0) return `${-diff}д. просрочено`;
  if (diff === 0) return 'Сегодня';
  if (diff === 1) return 'Завтра';
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
};
const apiErr = (err: any) =>
  err?.response?.data?.error?.public_message ?? err?.response?.data?.error?.message
  ?? err?.response?.data?.detail?.[0]?.msg ?? err.message ?? 'Неизвестная ошибка';

const INPUT_CLS =
  'w-full px-3.5 py-2.5 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl ' +
  'text-[var(--text-primary)] text-sm placeholder-[var(--text-primary)]/25 ' +
  'focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)] transition-all appearance-none';

/* 
   CUSTOM DROPDOWN — FIX: no nested <button>
    */

interface DropdownOption {
  value: string;
  label: string;
  sublabel?: string;
  icon?: React.ReactNode;
  dotColor?: string;
}

function useDropdownPosition(
  triggerRef: React.RefObject<HTMLDivElement | null>,
  open: boolean
) {
  const [style, setStyle] = useState<React.CSSProperties>({});

  useEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const openUp = spaceBelow < 300;

    setStyle({
      position: 'fixed',
      left: rect.left,
      width: rect.width,
      zIndex: 9999,
      ...(openUp
        ? { bottom: window.innerHeight - rect.top + 4 }
        : { top: rect.bottom + 4 }),
    });
  }, [open]);

  return style;
}

function CustomSelect({ value, onChange, options, placeholder, icon: LeadIcon, searchable = false, disabled = false }: {
  value: string;
  onChange: (v: string) => void;
  options: DropdownOption[];
  placeholder?: string;
  icon?: React.ComponentType<{ className?: string }>;
  searchable?: boolean;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const triggerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const dropdownStyle = useDropdownPosition(triggerRef, open);

  const selected = options.find(o => o.value === value);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (triggerRef.current?.contains(e.target as Node)) return;
      if (dropdownRef.current?.contains(e.target as Node)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  useEffect(() => {
    if (open && searchable) setTimeout(() => inputRef.current?.focus(), 50);
    if (!open) setSearch('');
  }, [open, searchable]);

  const filtered = search
    ? options.filter(o =>
      o.label.toLowerCase().includes(search.toLowerCase()) ||
      (o.sublabel || '').toLowerCase().includes(search.toLowerCase()))
    : options;

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    onChange('');
    setOpen(false);
  };

  const dropdown = open ? createPortal(
    <div ref={dropdownRef} style={dropdownStyle}
      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-[var(--shadow-lg)] overflow-hidden">
      {searchable && (
        <div className="p-2 border-b border-[var(--border-color)]">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-primary)]/25 pointer-events-none" />
            <input ref={inputRef} value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Поиск..."
              className="w-full pl-8 pr-3 py-2 bg-[var(--hover-1)] border border-[var(--border-color)] rounded-lg
                         text-sm text-[var(--text-primary)] placeholder-[var(--text-primary)]/25
                         focus:outline-none focus:border-[var(--accent)]/30 transition-all" />
          </div>
        </div>
      )}
      <div className="overflow-y-auto max-h-[220px] p-1 scrollbar-thin scrollbar-thumb-[var(--hover-3)] scrollbar-track-transparent">
        <div role="button" tabIndex={0}
          onClick={() => { onChange(''); setOpen(false); }}
          className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm cursor-pointer
                     ${!value ? 'bg-[var(--accent)]/8 text-[var(--text-primary)]' : 'text-[var(--text-primary)]/50 hover:bg-[var(--hover-2)]'}`}>
          <span className="text-[var(--text-primary)]/25">—</span>
          <span className="flex-1">Не выбрано</span>
          {!value && <Check className="w-3.5 h-3.5 text-[var(--accent)]" />}
        </div>

        {filtered.length === 0 && search && (
          <div className="px-3 py-4 text-center text-sm text-[var(--text-primary)]/30">Ничего не найдено</div>
        )}

        {filtered.map(opt => {
          const isSelected = opt.value === value;
          return (
            <div key={opt.value} role="button" tabIndex={0}
              onClick={() => { onChange(opt.value); setOpen(false); }}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm cursor-pointer
                         ${isSelected ? 'bg-[var(--accent)]/8 text-[var(--text-primary)]' : 'text-[var(--text-primary)]/70 hover:bg-[var(--hover-2)]'}`}>
              {opt.dotColor && <span className={`w-2 h-2 rounded-full flex-shrink-0 ${opt.dotColor}`} />}
              {opt.icon && <span className="flex-shrink-0">{opt.icon}</span>}
              <div className="flex-1 text-left min-w-0">
                <span className="block truncate">{opt.label}</span>
                {opt.sublabel && <span className="block text-xs text-[var(--text-primary)]/30 truncate">{opt.sublabel}</span>}
              </div>
              {isSelected && <Check className="w-3.5 h-3.5 text-[var(--accent)] flex-shrink-0" />}
            </div>
          );
        })}
      </div>
    </div>,
    document.body
  ) : null;

  return (
    <div ref={triggerRef} className="relative">
      <div
        role="button" tabIndex={disabled ? -1 : 0}
        onClick={() => !disabled && setOpen(v => !v)}
        onKeyDown={e => { if (!disabled && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setOpen(v => !v); } }}
        className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 bg-[var(--hover-2)] border rounded-xl
                   text-sm text-left transition-all select-none
                   ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-[var(--hover-3)]'}
                   ${open ? 'border-[var(--accent)]/30 ring-2 ring-[var(--accent-ring)]' : 'border-[var(--border-color)]'}`}>
        {LeadIcon && <LeadIcon className="w-4 h-4 text-[var(--text-primary)]/30 flex-shrink-0" />}
        <span className={`flex-1 truncate ${selected ? 'text-[var(--text-primary)]' : 'text-[var(--text-primary)]/25'}`}>
          {selected ? selected.label : (placeholder || '— Выберите —')}
        </span>
        {selected && value && (
          <span role="button" tabIndex={0} onClick={handleClear}
            className="p-0.5 rounded hover:bg-[var(--hover-2)] text-[var(--text-primary)]/25 hover:text-[var(--text-primary)]/60 flex-shrink-0 cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </span>
        )}
        <ChevronDown className={`w-4 h-4 text-[var(--text-primary)]/25 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </div>
      {dropdown}
    </div>
  );
}

/* 
   ASYNC SEARCH SELECT — для динамической загрузки с пагинацией
    */

function AsyncSelect({ value, onChange, loadOptions, renderSelected, placeholder, icon: LeadIcon, disabled = false }: {
  value: string;
  onChange: (v: string) => void;
  loadOptions: (search: string, page: number) => Promise<{ items: DropdownOption[]; hasNext: boolean }>;
  renderSelected?: (v: string) => string;
  placeholder?: string;
  icon?: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [options, setOptions] = useState<DropdownOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState('');
  const triggerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropdownStyle = useDropdownPosition(triggerRef, open);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (triggerRef.current?.contains(e.target as Node)) return;
      if (dropdownRef.current?.contains(e.target as Node)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const doLoad = useCallback(async (q: string, p: number, append = false) => {
    if (append) setLoadingMore(true); else setLoading(true);
    try {
      const res = await loadOptions(q, p);
      setOptions(prev => append ? [...prev, ...res.items] : res.items);
      setHasNext(res.hasNext);
      setPage(p);
    } catch { }
    finally { setLoading(false); setLoadingMore(false); }
  }, [loadOptions]);

  useEffect(() => {
    if (!open) return;
    doLoad('', 1);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  useEffect(() => {
    if (!open) { setSearch(''); return; }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doLoad(search, 1), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search]);

  // Resolve label
  useEffect(() => {
    if (!value) { setSelectedLabel(''); return; }
    if (renderSelected) { setSelectedLabel(renderSelected(value)); return; }
    const found = options.find(o => o.value === value);
    if (found) { setSelectedLabel(found.label); return; }
    loadOptions('', 1).then(res => {
      const f = res.items.find(o => o.value === value);
      setSelectedLabel(f ? f.label : value.slice(0, 8) + '...');
    }).catch(() => setSelectedLabel(value.slice(0, 8) + '...'));
  }, [value]);

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    onChange('');
    setSelectedLabel('');
    setOpen(false);
  };

  const dropdown = open ? createPortal(
    <div ref={dropdownRef} style={dropdownStyle}
      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-[var(--shadow-lg)] overflow-hidden">
      <div className="p-2 border-b border-[var(--border-color)]">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-primary)]/25 pointer-events-none" />
          <input ref={inputRef} value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Поиск..."
            className="w-full pl-8 pr-3 py-2 bg-[var(--hover-1)] border border-[var(--border-color)] rounded-lg
                       text-sm text-[var(--text-primary)] placeholder-[var(--text-primary)]/25
                       focus:outline-none focus:border-[var(--accent)]/30 transition-all" />
        </div>
      </div>
      <div className="overflow-y-auto max-h-[250px] p-1 scrollbar-thin scrollbar-thumb-[var(--hover-3)] scrollbar-track-transparent">
        <div role="button" tabIndex={0}
          onClick={() => { onChange(''); setOpen(false); }}
          className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm cursor-pointer
                     ${!value ? 'bg-[var(--accent)]/8 text-[var(--text-primary)]' : 'text-[var(--text-primary)]/50 hover:bg-[var(--hover-2)]'}`}>
          <span className="text-[var(--text-primary)]/25">—</span>
          <span className="flex-1">Не выбрано</span>
          {!value && <Check className="w-3.5 h-3.5 text-[var(--accent)]" />}
        </div>

        {loading && <div className="flex justify-center py-4"><Loader2 className="w-4 h-4 animate-spin text-[var(--text-primary)]/25" /></div>}

        {!loading && options.length === 0 && (
          <div className="px-3 py-4 text-center text-sm text-[var(--text-primary)]/30">
            {search ? 'Ничего не найдено' : 'Нет данных'}
          </div>
        )}

        {!loading && options.map(opt => {
          const isSelected = opt.value === value;
          return (
            <div key={opt.value} role="button" tabIndex={0}
              onClick={() => { onChange(opt.value); setSelectedLabel(opt.label); setOpen(false); }}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm cursor-pointer
                         ${isSelected ? 'bg-[var(--accent)]/8 text-[var(--text-primary)]' : 'text-[var(--text-primary)]/70 hover:bg-[var(--hover-2)]'}`}>
              {opt.dotColor && <span className={`w-2 h-2 rounded-full flex-shrink-0 ${opt.dotColor}`} />}
              {opt.icon && <span className="flex-shrink-0">{opt.icon}</span>}
              <div className="flex-1 text-left min-w-0">
                <span className="block truncate">{opt.label}</span>
                {opt.sublabel && <span className="block text-xs text-[var(--text-primary)]/30 truncate">{opt.sublabel}</span>}
              </div>
              {isSelected && <Check className="w-3.5 h-3.5 text-[var(--accent)] flex-shrink-0" />}
            </div>
          );
        })}

        {!loading && hasNext && (
          <div role="button" tabIndex={0}
            onClick={() => !loadingMore && doLoad(search, page + 1, true)}
            className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm
                       text-[var(--text-primary)]/30 hover:text-[var(--text-primary)]/50 hover:bg-[var(--hover-2)] cursor-pointer">
            {loadingMore ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ChevronDown className="w-3.5 h-3.5" />}
            Загрузить ещё
          </div>
        )}
      </div>
    </div>,
    document.body
  ) : null;

  return (
    <div ref={triggerRef} className="relative">
      <div
        role="button" tabIndex={disabled ? -1 : 0}
        onClick={() => !disabled && setOpen(v => !v)}
        onKeyDown={e => { if (!disabled && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setOpen(v => !v); } }}
        className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 bg-[var(--hover-2)] border rounded-xl
                   text-sm text-left transition-all select-none
                   ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-[var(--hover-3)]'}
                   ${open ? 'border-[var(--accent)]/30 ring-2 ring-[var(--accent-ring)]' : 'border-[var(--border-color)]'}`}>
        {LeadIcon && <LeadIcon className="w-4 h-4 text-[var(--text-primary)]/30 flex-shrink-0" />}
        <span className={`flex-1 truncate ${selectedLabel ? 'text-[var(--text-primary)]' : 'text-[var(--text-primary)]/25'}`}>
          {selectedLabel || (placeholder || '— Выберите —')}
        </span>
        {value && (
          <span role="button" tabIndex={0} onClick={handleClear}
            className="p-0.5 rounded hover:bg-[var(--hover-2)] text-[var(--text-primary)]/25 hover:text-[var(--text-primary)]/60 flex-shrink-0 cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </span>
        )}
        <ChevronDown className={`w-4 h-4 text-[var(--text-primary)]/25 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </div>
      {dropdown}
    </div>
  );
}

/* 
   ATOMS
    */

function Ava({ name, url, size = 'sm' }: { name?: string | null; url?: string | null; size?: 'xs' | 'sm' | 'md' }) {
  const c = { xs: 'w-6 h-6 text-[13px]', sm: 'w-7 h-7 text-[11px]', md: 'w-9 h-9 text-sm' }[size];
  if (url) return <img src={url} alt="" className={`${c} rounded-full object-cover flex-shrink-0`} />;
  return <div className={`${c} rounded-full bg-[var(--accent)] flex items-center justify-center font-bold text-white flex-shrink-0 select-none`}>{initials(name)}</div>;
}

function PBadge({ p }: { p: TaskPriority }) {
  const m = PRI[p];
  return <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium border ${m.bg} ${m.color} ${m.border}`}>{m.icon}{p}</span>;
}

function SPBadge({ v }: { v: number }) {
  return <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium border bg-[var(--hover-3)] text-[var(--text-primary)]/50 border-[var(--border-color)]"><Star className="w-2.5 h-2.5" />{v}</span>;
}

/* 
   TASK CARD
    */

function TaskCard({ task, userMap, onDragStart, onView }: {
  task: TaskKanbanItem; userMap: Map<string, SimpleUser | CounterpartyCustomer>;
  onDragStart: (id: string, from: TaskStatus) => void; onView: (t: TaskKanbanItem) => void;
}) {
  const od = isOverdue(task.due_date);
  const a = task.assignee_id ? userMap.get(task.assignee_id) : null;

  return (
    <div draggable
      onDragStart={(e) => { e.dataTransfer.effectAllowed = 'move'; onDragStart(task.id, task.status); }}
      onClick={() => onView(task)}
      className="group bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3
                 hover:border-[var(--accent)]/25 hover:shadow-[var(--shadow-md)]
                 cursor-grab active:cursor-grabbing transition-all duration-200
                 hover:-translate-y-0.5 active:scale-[0.98] active:opacity-70 select-none">
      <div className="flex items-start justify-between gap-1.5 mb-1.5">
        <div className="flex items-center gap-1 flex-wrap min-w-0">
          <PBadge p={task.priority} />
          {task.story_points != null && <SPBadge v={task.story_points} />}
        </div>
      </div>
      <span className="group-hover:text-[var(--accent)] text-[var(--text-primary)] font-mono text-[14px] bg-[var(--accent-soft)]
                       border border-[var(--accent)]/15 px-1.5 py-0.5 rounded-md">
        <span className='text-red-500'># </span>{task.number}
      </span>
      <p className="text-[15px] font-semibold text-[var(--text-primary)] leading-snug mt-1.5 mb-2.5 transition-colors line-clamp-2">{task.title}</p>
      <div className="flex items-center justify-between pt-2 border-t border-[var(--border-color)]">
        <div className="flex items-center gap-2 min-w-0">
          {task.due_date && (
            <span className={`flex items-center gap-1 text-[11px] font-medium whitespace-nowrap ${od ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]/30'}`}>
              <Calendar className="w-3 h-3" />{fmtDue(task.due_date)}
            </span>
          )}
          {task.ticket_id && <Ticket className="w-3 h-3 text-[var(--text-primary)]/20 flex-shrink-0" />}
        </div>
        {a ? <Ava name={a.full_name || a.username} url={a.avatar_url} size="xs" />
          : task.assignee_id ? <div className="w-6 h-6 rounded-full bg-[var(--hover-3)] border border-[var(--border-color)] flex items-center justify-center flex-shrink-0"><User className="w-3 h-3 text-[var(--text-primary)]/25" /></div>
            : null}
      </div>
    </div>
  );
}

/* 
   KANBAN COLUMN
    */

function KColumn({ column, userMap, isDragOver, loadingMore, onDragStart, onDragOver, onDrop, onAdd, onView, onMore }: {
  column: TaskKanbanColumn; userMap: Map<string, SimpleUser | CounterpartyCustomer>;
  isDragOver: boolean; loadingMore: boolean;
  onDragStart: (id: string, f: TaskStatus) => void; onDragOver: (e: React.DragEvent, s: TaskStatus) => void;
  onDrop: (e: React.DragEvent, s: TaskStatus) => void; onAdd: (s: TaskStatus) => void;
  onView: (t: TaskKanbanItem) => void; onMore: (s: TaskStatus) => void;
}) {
  const m = COL[column.status]; const Icon = m.icon;
  const label = column.label || STATUS_LABELS[column.status];

  return (
    <div className={`flex flex-col flex-shrink-0 min-h-[580px] min-w-[280px] w-[280px] rounded-2xl border-2
                  transition-all duration-200 ${isDragOver ? `${m.bg} border-dashed ${m.border}` : 'bg-[var(--hover-1)]/30 border-transparent'}`}
      style={{ maxHeight: 'calc(100vh - 250px)' }}
      onDragOver={e => onDragOver(e, column.status)} onDrop={e => onDrop(e, column.status)}>
      <div className={`flex items-center justify-between px-3 py-2.5 rounded-t-2xl flex-shrink-0 ${m.header}`}>
        <div className="flex items-center gap-1.5 min-w-0">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${m.dot}`} />
          <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${m.color}`} />
          <span className={`text-[15px] font-bold truncate ${m.color}`}>{label}</span>
          <span className="px-1.5 py-0.5 rounded-full bg-black/[0.08] text-[13px] font-bold tabular-nums flex-shrink-0 text-[var(--text-primary)]/40">{column.tasks.total_items}</span>
        </div>
        <button onClick={() => onAdd(column.status)} className="p-1 rounded-lg hover:bg-[var(--hover-2)] text-[var(--text-primary)]/25 hover:text-[var(--accent)] transition-colors flex-shrink-0"><Plus className="w-3.5 h-3.5" /></button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-1.5 space-y-1.5 scrollbar-thin scrollbar-thumb-[var(--hover-3)] scrollbar-track-transparent">
        {column.tasks.items.map(t => <TaskCard key={t.id} task={t} userMap={userMap} onDragStart={onDragStart} onView={onView} />)}
        {isDragOver && !column.tasks.items.length && <div className={`border-2 border-dashed ${m.border} rounded-xl h-20 flex items-center justify-center`}><span className="text-base text-[var(--text-primary)]/25">Перетащите сюда</span></div>}
        {!isDragOver && !column.tasks.items.length && <div className="py-8 text-center"><span className="text-base text-[var(--text-primary)]/15">{m.empty}</span></div>}
        {column.tasks.has_next && (
          <button onClick={() => onMore(column.status)} disabled={loadingMore}
            className="w-full flex items-center justify-center gap-1 py-2 rounded-xl text-[var(--text-primary)]/30 hover:text-[var(--text-primary)]/50 hover:bg-[var(--hover-2)] text-base transition-all disabled:opacity-40">
            {loadingMore ? <Loader2 className="w-3 h-3 animate-spin" /> : <ChevronDown className="w-3 h-3" />}
            Ещё ({column.tasks.total_items - column.tasks.items.length})
          </button>
        )}
      </div>
      <div className="px-2 pb-2 flex-shrink-0">
        <button onClick={() => onAdd(column.status)} className={`w-full flex items-center justify-center gap-1 py-1.5 rounded-xl border border-dashed text-base transition-all ${m.border} text-[var(--text-primary)]/20 hover:text-[var(--text-primary)]/40 hover:bg-[var(--hover-2)]`}><Plus className="w-3 h-3" /> Добавить</button>
      </div>
    </div>
  );
}

/* 
   ASSIGN BEFORE PROGRESS MODAL
    */

function AssignBeforeProgressModal({ task, userMap, loading, onClose, onConfirm }: {
  task: TaskKanbanItem; userMap: Map<string, SimpleUser | CounterpartyCustomer>;
  loading: boolean; onClose: () => void; onConfirm: (id: string) => Promise<void>;
}) {
  const [aid, setAid] = useState('');
  const users = Array.from(userMap.values());
  const opts: DropdownOption[] = users.map(u => ({ value: u.id, label: u.full_name || u.username || u.email, sublabel: u.email }));

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !loading) onClose(); };
    document.addEventListener('keydown', h); document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', h); document.body.style.overflow = ''; };
  }, [onClose, loading]);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => !loading && onClose()} />
      <div className="relative w-full max-w-md bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden"
        style={{ boxShadow: 'var(--shadow-lg)' }} onClick={e => e.stopPropagation()}>
        <div className="px-6 py-5 border-b border-[var(--border-color)] bg-[var(--hover-1)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--warning)]/15 flex items-center justify-center"><UserCheck className="w-5 h-5 text-[var(--warning)]" /></div>
            <div><h2 className="text-base font-bold text-[var(--text-primary)]">Назначьте исполнителя</h2><p className="text-sm text-[var(--text-primary)]/40">Обязательно для «В работе»</p></div>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <div className="rounded-xl bg-[var(--hover-2)] border border-[var(--border-color)] p-4">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[var(--accent)] font-mono text-[13px] bg-[var(--accent-soft)] border border-[var(--accent)]/15 px-1.5 py-0.5 rounded-md">{task.number}</span>
              <PBadge p={task.priority} />
            </div>
            <p className="text-sm font-semibold text-[var(--text-primary)] leading-snug">{task.title}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-2">Исполнитель <span className="text-[var(--accent)]">*</span></label>
            <CustomSelect value={aid} onChange={setAid} options={opts} placeholder="Выберите" icon={UserCheck} searchable />
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[var(--border-color)] bg-[var(--hover-1)]">
          <button onClick={onClose} disabled={loading} className="px-4 py-2.5 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-sm disabled:opacity-50">Отмена</button>
          <button onClick={() => onConfirm(aid)} disabled={!aid || loading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-light)] text-white text-sm font-medium disabled:opacity-40 shadow-[var(--shadow-md)]">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserCheck className="w-4 h-4" />} Назначить
          </button>
        </div>
      </div>
    </div>
  );
}

/* 
   CREATE MODAL — с AsyncSelect для проекта, исполнителя, тикета
    */

function CreateModal({ initialStatus, context, userMap, onClose, onOk }: {
  initialStatus: TaskStatus; context: TaskKanbanContext;
  userMap: Map<string, SimpleUser | CounterpartyCustomer>;
  onClose: () => void; onOk: () => void;
}) {
  const { toast } = useToast();
  const { user } = useAuthStore();
  const staff = ['admin', 'support_manager', 'support_agent', 'executor'].includes(user?.role ?? '');

  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [pri, setPri] = useState<TaskPriority>('Средний');
  const [sp, setSp] = useState('');
  const [eh, setEh] = useState('');
  const [dd, setDd] = useState('');
  const [todo, setTodo] = useState(initialStatus === 'todo');
  const [aid, setAid] = useState('');
  const [tid, setTid] = useState('');
  const [pid, setPid] = useState(context.type === 'project' ? context.project_id : '');
  const [saving, setSaving] = useState(false);

  const ctid = context.type === 'ticket' ? context.ticket_id : undefined;
  useEffect(() => { if (ctid) setTid(ctid); }, [ctid]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !saving) onClose(); };
    document.addEventListener('keydown', h); document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', h); document.body.style.overflow = ''; };
  }, [onClose, saving]);

  // При смене проекта — сбросить тикет
  useEffect(() => { setTid(''); }, [pid]);

  // Async loaders
  const loadProjects = useCallback(async (search: string, page: number) => {
    const res = staff
      ? await projectsApi.getAll(page, 20, 'active')
      : await projectsApi.getMyProjects('all', page, 20);
    const filtered = search
      ? res.items.filter(p => p.name.toLowerCase().includes(search.toLowerCase()) || p.key.toLowerCase().includes(search.toLowerCase()))
      : res.items;
    return {
      items: filtered.map(p => ({ value: p.id, label: p.name, sublabel: p.key, icon: <FolderOpen className="w-4 h-4 text-amber-400" /> })),
      hasNext: res.items.length === 20,
    };
  }, [staff]);

  const loadUsers = useCallback(async (search: string, page: number) => {
    let items: (SimpleUser | CounterpartyCustomer)[] = [];
    try {
      if (staff) { items = (await usersApi.getAllUsers(page, 20)).items; }
      else { items = (await usersApi.getSupports(page, 20)).items; }
    } catch { }
    const filtered = search
      ? items.filter(u => (u.full_name || '').toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()))
      : items;
    return {
      items: filtered.map(u => ({ value: u.id, label: u.full_name || u.username || u.email, sublabel: u.email })),
      hasNext: items.length === 20,
    };
  }, [staff]);

  const loadTickets = useCallback(async (search: string, page: number) => {
    const res = await ticketsApi.getAllWithFilters(page, 20, { project_id: pid || undefined });
    const filtered = search
      ? res.items.filter(t => t.title.toLowerCase().includes(search.toLowerCase()) || String(t.number).includes(search))
      : res.items;
    return {
      items: filtered.map(t => ({ value: t.id, label: `#${t.number} — ${t.title}` })),
      hasNext: res.items.length === 20,
    };
  }, [pid]);

  const submit = async () => {
    if (!title.trim()) return;
    setSaving(true);
    try {
      const payload: TaskCreateInput = {
        title: title.trim(), description: desc.trim() || null, priority: pri,
        project_id: pid || null, ticket_id: tid || null,
        story_points: sp ? parseInt(sp) : null, estimated_hours: eh ? parseFloat(eh) : null,
        due_date: dd || null, mark_as_todo: todo, assignee_id: aid || null,
      };
      const t = await tasksApi.create(payload);
      toast({ title: 'Задача создана', description: `${t.number} — ${t.title}` });
      onOk();
    } catch (err: any) {
      toast({ title: 'Ошибка', description: apiErr(err), variant: 'destructive' });
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => !saving && onClose()} />
      <div className="relative w-full max-w-lg max-h-[90vh] flex flex-col bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden"
        style={{ boxShadow: 'var(--shadow-lg)' }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-color)] bg-[var(--hover-1)] flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)]/15 flex items-center justify-center"><Plus className="w-4 h-4 text-[var(--accent)]" /></div>
            <div><h2 className="text-sm font-bold text-[var(--text-primary)]">Новая задача</h2><p className="text-sm text-[var(--text-primary)]/40">«{STATUS_LABELS[initialStatus]}»</p></div>
          </div>
          <button onClick={() => !saving && onClose()} className="p-2 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-1.5">Название <span className="text-[var(--accent)]">*</span></label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Что нужно сделать?" autoFocus className={INPUT_CLS} />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-1.5">Описание</label>
            <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="Постановка задачи..." rows={3} className={`${INPUT_CLS} resize-none`} />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-1.5">Проект</label>
            <AsyncSelect value={pid} onChange={setPid} loadOptions={loadProjects} placeholder="Выберите проект" icon={FolderOpen} />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-2">Приоритет</label>
            <div className="flex flex-wrap gap-1.5">
              {TASK_PRIORITY_LIST.map(p => {
                const pm = PRI[p];
                return <button key={p} onClick={() => setPri(p)} className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium transition-all border ${pri === p ? `${pm.bg} ${pm.color} ${pm.border}` : 'bg-[var(--hover-1)] text-[var(--text-primary)]/50 border-[var(--border-color)] hover:bg-[var(--hover-2)]'}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${pm.dot}`} />{p}
                </button>;
              })}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-1.5">SP</label><input type="number" min={1} max={21} value={sp} onChange={e => setSp(e.target.value)} placeholder="—" className={INPUT_CLS} /></div>
            <div><label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-1.5">Оценка, ч.</label><input type="number" min={0} step={0.5} value={eh} onChange={e => setEh(e.target.value)} placeholder="—" className={INPUT_CLS} /></div>
          </div>
          <div><label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-1.5">Срок</label><input type="date" value={dd} onChange={e => setDd(e.target.value)} min={new Date().toISOString().split('T')[0]} className={INPUT_CLS} /></div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-1.5">Исполнитель</label>
            <AsyncSelect value={aid} onChange={setAid} loadOptions={loadUsers} placeholder="Не назначен" icon={UserCheck} />
          </div>
          {context.type !== 'ticket' && (
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)]/60 mb-1.5">Тикет</label>
              <AsyncSelect value={tid} onChange={setTid} loadOptions={loadTickets} placeholder="Без тикета" icon={Ticket} />
            </div>
          )}
          <button onClick={() => setTodo(v => !v)}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl border transition-all text-sm ${todo ? 'bg-blue-500/8 border-blue-500/25 text-blue-400' : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-primary)]/50 hover:bg-[var(--hover-2)]'}`}>
            <div className={`w-5 h-5 rounded-md border flex items-center justify-center flex-shrink-0 ${todo ? 'bg-blue-500 border-blue-600' : 'border-[var(--border-color)]'}`}>{todo && <Check className="w-3 h-3 text-white" />}</div>
            <span className="font-medium">Готова к выполнению</span>
          </button>
        </div>

        <div className="flex items-center justify-end gap-2.5 px-5 py-3.5 border-t border-[var(--border-color)] bg-[var(--hover-1)] flex-shrink-0">
          <button onClick={() => !saving && onClose()} disabled={saving} className="px-4 py-2 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-sm disabled:opacity-50">Отмена</button>
          <button onClick={submit} disabled={!title.trim() || saving}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-light)] text-white text-sm font-medium disabled:opacity-40 shadow-[var(--shadow-md)]">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Создать
          </button>
        </div>
      </div>
    </div>
  );
}

/* 
   DETAIL MODAL
    */

function DetailModal({ task, userMap, onClose, onRefresh, onNeedAssign }: {
  task: TaskKanbanItem; userMap: Map<string, SimpleUser | CounterpartyCustomer>;
  onClose: () => void; onRefresh: () => Promise<void>; onNeedAssign: (task: TaskKanbanItem) => void;
}) {
  const { toast } = useToast();
  const { user } = useAuthStore();
  const [showStatus, setShowStatus] = useState(false);
  const [busy, setBusy] = useState('');
  const canEdit = ALLOWED_EDIT_STATUSES.has(task.status);
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editPri, setEditPri] = useState<TaskPriority>(task.priority);
  const [editSp, setEditSp] = useState(task.story_points?.toString() ?? '');
  const [editDd, setEditDd] = useState(task.due_date ?? '');
  const [showAssign, setShowAssign] = useState(false);
  const [assignId, setAssignId] = useState(task.assignee_id ?? '');
  const [showReqReview, setShowReqReview] = useState(false);
  const [reviewerId, setReviewerId] = useState('');

  const assignee = task.assignee_id ? userMap.get(task.assignee_id) : null;
  const cm = COL[task.status]; const StatusIcon = cm.icon;
  const users = Array.from(userMap.values());
  const isStaff = ['admin', 'support_manager', 'support_agent', 'executor'].includes(user?.role ?? '');
  const canReview = task.status === 'review' && isStaff;
  const canReqReview = task.status === 'in_progress';
  const canAssign = ALLOWED_ASSIGN_STATUSES.has(task.status) && users.length > 0;
  const allowed = ALLOWED_TRANSITIONS[task.status];
  const isBroken = task.status === 'in_progress' && !task.assignee_id;
  const userOpts: DropdownOption[] = users.map(u => ({ value: u.id, label: u.full_name || u.username || u.email, sublabel: u.email }));

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', h); document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', h); document.body.style.overflow = ''; };
  }, [onClose]);

  const act = async (label: string, fn: () => Promise<any>, msg?: string) => {
    setBusy(label);
    try { await fn(); if (msg) toast({ title: msg }); await onRefresh(); onClose(); }
    catch (e: any) { toast({ title: 'Ошибка', description: apiErr(e), variant: 'destructive' }); }
    finally { setBusy(''); }
  };

  const saveEdit = () => act('edit', async () => {
    const p: TaskUpdateInput = {};
    if (editTitle.trim() !== task.title) p.title = editTitle.trim();
    if (editPri !== task.priority) p.priority = editPri;
    if (editSp !== (task.story_points?.toString() ?? '')) p.story_points = editSp ? parseInt(editSp) : null;
    if (editDd !== (task.due_date ?? '')) p.due_date = editDd || null;
    if (!Object.keys(p).length) return;
    await tasksApi.update(task.id, p);
  }, 'Задача обновлена');

  const handleStatusClick = (s: TaskStatus) => {
    if (s === 'in_progress' && !task.assignee_id) { setShowStatus(false); onNeedAssign(task); return; }
    setShowStatus(false);
    act('status', () => tasksApi.changeStatus(task.id, s), `→ ${STATUS_LABELS[s]}`);
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-xl max-h-[90vh] flex flex-col bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden"
        style={{ boxShadow: 'var(--shadow-lg)' }} onClick={e => e.stopPropagation()}>
        <div className="flex items-start justify-between px-5 py-4 border-b border-[var(--border-color)] bg-[var(--hover-1)] flex-shrink-0">
          <div className="flex-1 min-w-0 pr-3">
            <div className="flex items-center gap-1.5 mb-2 flex-wrap">
              <span className="text-[var(--accent)] font-mono text-base bg-[var(--accent-soft)] border border-[var(--accent)]/15 px-2 py-0.5 rounded-lg">{task.number}</span>
              <PBadge p={task.priority} />
              {task.story_points != null && <SPBadge v={task.story_points} />}
              {canEdit && <button onClick={() => setEditing(v => !v)} className={`p-1 rounded-lg transition-colors ml-auto ${editing ? 'bg-[var(--accent)]/15 text-[var(--accent)]' : 'hover:bg-[var(--hover-2)] text-[var(--text-primary)]/30'}`}><Pencil className="w-3.5 h-3.5" /></button>}
            </div>
            <h2 className="text-base font-bold text-[var(--text-primary)] leading-snug">{task.title}</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)] flex-shrink-0"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-3.5">
          {isBroken && <div className="px-4 py-3 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/20"><p className="text-sm text-[var(--accent)] font-medium">⚠ Статус «В работе», но исполнитель не назначен.</p></div>}

          {editing && canEdit && (
            <div className="p-4 rounded-xl bg-[var(--hover-2)] border border-[var(--accent)]/20 space-y-3">
              <p className="text-base uppercase tracking-widest text-[var(--accent)] font-bold flex items-center gap-1.5"><Pencil className="w-3 h-3" /> Редактирование</p>
              <div><label className="text-base text-[var(--text-primary)]/50 mb-1 block">Название</label><input value={editTitle} onChange={e => setEditTitle(e.target.value)} className={INPUT_CLS} /></div>
              <div>
                <label className="text-base text-[var(--text-primary)]/50 mb-1 block">Приоритет</label>
                <div className="flex flex-wrap gap-1.5">
                  {TASK_PRIORITY_LIST.map(p => { const pm = PRI[p]; return <button key={p} onClick={() => setEditPri(p)} className={`flex items-center gap-1 px-2 py-1 rounded-lg text-base font-medium border transition-all ${editPri === p ? `${pm.bg} ${pm.color} ${pm.border}` : 'bg-[var(--hover-1)] text-[var(--text-primary)]/50 border-[var(--border-color)]'}`}><span className={`w-1.5 h-1.5 rounded-full ${pm.dot}`} />{p}</button>; })}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-base text-[var(--text-primary)]/50 mb-1 block">SP</label><input type="number" min={1} max={21} value={editSp} onChange={e => setEditSp(e.target.value)} placeholder="—" className={INPUT_CLS} /></div>
                <div><label className="text-base text-[var(--text-primary)]/50 mb-1 block">Срок</label><input type="date" value={editDd} onChange={e => setEditDd(e.target.value)} className={INPUT_CLS} /></div>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button onClick={() => setEditing(false)} className="px-3 py-1.5 rounded-lg bg-[var(--hover-3)] text-[var(--text-primary)]/60 text-base">Отмена</button>
                <button onClick={saveEdit} disabled={busy === 'edit' || !editTitle.trim()} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent)] text-white text-base font-medium disabled:opacity-40">
                  {busy === 'edit' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />} Сохранить
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2.5">
            <div className="bg-[var(--hover-2)] rounded-xl border border-[var(--border-color)] p-3">
              <p className="text-[13px] uppercase tracking-widest text-[var(--text-primary)]/30 mb-1.5">Статус</p>
              <div className="relative">
                <button onClick={() => allowed.length > 0 && setShowStatus(v => !v)} disabled={busy !== '' || !allowed.length}
                  className={`flex items-center gap-1.5 text-sm font-semibold ${cm.color} disabled:opacity-40`}>
                  {busy === 'status' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <StatusIcon className="w-3.5 h-3.5" />}
                  {STATUS_LABELS[task.status]}
                  {allowed.length > 0 && <ChevronDown className="w-3 h-3 opacity-40" />}
                </button>
                {showStatus && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setShowStatus(false)} />
                    <div className="absolute left-0 top-full mt-1.5 z-20 w-56 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden shadow-[var(--shadow-lg)]">
                      <div className="p-1">
                        <p className="px-3 py-1.5 text-[13px] uppercase tracking-widest text-[var(--text-primary)]/25">Перевести в:</p>
                        {allowed.map(s => { const sm = COL[s]; const SI = sm.icon; const na = s === 'in_progress' && !task.assignee_id; return (
                          <button key={s} onClick={() => handleStatusClick(s)} className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)]">
                            <div className={`w-1.5 h-1.5 rounded-full ${sm.dot}`} /><SI className={`w-3.5 h-3.5 ${sm.color}`} /><span className="flex-1 text-left">{STATUS_LABELS[s]}</span>
                            {na && <span className="text-[13px] text-[var(--warning)] bg-[var(--warning)]/10 px-1.5 py-0.5 rounded">исполнитель</span>}
                          </button>
                        ); })}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
            <div className="bg-[var(--hover-2)] rounded-xl border border-[var(--border-color)] p-3">
              <p className="text-[13px] uppercase tracking-widest text-[var(--text-primary)]/30 mb-1.5">Срок</p>
              {task.due_date ? <span className={`flex items-center gap-1 text-sm font-semibold ${isOverdue(task.due_date) ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]/70'}`}><Calendar className="w-3.5 h-3.5" />{fmtDue(task.due_date)}</span> : <span className="text-sm text-[var(--text-primary)]/25">—</span>}
            </div>
            <div className="bg-[var(--hover-2)] rounded-xl border border-[var(--border-color)] p-3">
              <p className="text-[13px] uppercase tracking-widest text-[var(--text-primary)]/30 mb-1.5">Исполнитель</p>
              {assignee ? <div className="flex items-center gap-1.5"><Ava name={assignee.full_name || assignee.username} url={assignee.avatar_url} size="xs" /><span className="text-sm text-[var(--text-primary)]/70 font-medium truncate">{assignee.full_name || assignee.username}</span></div> : <span className="text-sm text-[var(--text-primary)]/25">—</span>}
            </div>
            <div className="bg-[var(--hover-2)] rounded-xl border border-[var(--border-color)] p-3">
              <p className="text-[13px] uppercase tracking-widest text-[var(--text-primary)]/30 mb-1.5">Создана</p>
              <span className="text-sm text-[var(--text-primary)]/70">{new Date(task.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
            </div>
          </div>

          {canAssign && (
  <div className="rounded-xl border border-[var(--border-color)] overflow-hidden">
    <button 
      onClick={() => setShowAssign(v => !v)} 
      className={`w-full flex items-center justify-between px-4 py-2.5 transition-all duration-200
                 ${showAssign 
                   ? 'bg-[var(--hover-2)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-3)]' 
                   : task.assignee_id 
                     ? 'bg-[var(--hover-2)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-3)]' 
                     : 'bg-[var(--hover-2)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-3)]'
                 }`}
    >
      <span className="flex items-center gap-2 text-sm font-medium">
        <UserCheck className="w-4 h-4" />
        {task.assignee_id ? 'Исполнитель назначен' : 'Назначить исполнителя'}
        {task.assignee_id && assignee && (
          <span className="ml-1.5 text-xs px-2 py-0.5 rounded-full bg-white/10">
            {assignee.full_name || assignee.username}
          </span>
        )}
      </span>
      <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${showAssign ? 'rotate-180' : ''}`} />
    </button>
    
    {showAssign && (
      <div className="px-4 py-3 bg-[var(--hover-1)] border-t border-[var(--border-color)] space-y-2.5">
        <CustomSelect 
          value={assignId} 
          onChange={setAssignId} 
          options={userOpts} 
          placeholder="Выберите исполнителя" 
          icon={UserCheck} 
          searchable 
        />
        <button 
          onClick={() => act('assign', () => tasksApi.assign(task.id, { assignee_id: assignId }), 'Назначен')}
          disabled={!assignId || busy === 'assign'} 
          className="w-full flex items-center justify-center gap-2 py-2 rounded-xl
                     bg-[var(--accent)] hover:bg-[var(--accent-light)] 
                     active:scale-[0.98] transition-all duration-200
                     text-white text-sm font-medium disabled:opacity-40 
                     disabled:cursor-not-allowed disabled:hover:bg-[var(--accent)]
                     shadow-[var(--shadow-sm)]"
        >
          {busy === 'assign' 
            ? <Loader2 className="w-4 h-4 animate-spin" /> 
            : <UserCheck className="w-4 h-4" />
          } 
          Назначить
        </button>
      </div>
    )}
  </div>
)}

          {canReqReview && users.length > 0 && (
            <div className="rounded-xl border border-violet-500/20 overflow-hidden">
              <button onClick={() => setShowReqReview(v => !v)} className="w-full flex items-center justify-between px-4 py-2.5 bg-violet-500/5 hover:bg-violet-500/8">
                <span className="flex items-center gap-2 text-sm font-medium text-violet-400"><GitPullRequest className="w-4 h-4" />Запросить ревью</span>
                <ChevronDown className={`w-4 h-4 text-violet-400/40 transition-transform ${showReqReview ? 'rotate-180' : ''}`} />
              </button>
              {showReqReview && (
                <div className="px-4 py-3 bg-[var(--hover-1)] border-t border-violet-500/20 space-y-2.5">
                  <CustomSelect value={reviewerId} onChange={setReviewerId} options={userOpts} placeholder="Ревьюер" searchable />
                  <button onClick={() => act('reqReview', () => tasksApi.requestReview(task.id, { reviewer_id: reviewerId }), 'Ревью запрошено')}
                    disabled={!reviewerId || busy === 'reqReview'} className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-violet-500/20 border border-violet-500/30 text-violet-400 text-sm font-medium disabled:opacity-40">
                    {busy === 'reqReview' ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitPullRequest className="w-4 h-4" />} Отправить
                  </button>
                </div>
              )}
            </div>
          )}

          {canReview && (
            <div className="p-4 rounded-xl bg-[var(--hover-2)] border border-[var(--border-color)]">
              <p className="text-sm font-medium text-[var(--text-primary)]/60 flex items-center gap-2 mb-3"><Eye className="w-4 h-4 text-violet-400" />Ревью</p>
              <div className="flex gap-2">
                <button onClick={() => act('review', () => tasksApi.review(task.id, { action: 'approve' }), 'Принято')} disabled={busy === 'review'}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-[var(--success)]/10 border border-emerald-500/30 text-[var(--success)] text-sm font-medium disabled:opacity-50">
                  {busy === 'review' ? <Loader2 className="w-4 h-4 animate-spin" /> : <ThumbsUp className="w-4 h-4" />} Принять
                </button>
                <button onClick={() => act('review', () => tasksApi.review(task.id, { action: 'reject' }), 'На доработку')} disabled={busy === 'review'}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/30 text-[var(--accent)] text-sm font-medium disabled:opacity-50">
                  {busy === 'review' ? <Loader2 className="w-4 h-4 animate-spin" /> : <ThumbsDown className="w-4 h-4" />} Вернуть
                </button>
              </div>
            </div>
          )}

          {task.ticket_id && (
  <div className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-[var(--hover-2)] border border-[var(--border-color)]">
    <Ticket className="w-4 h-4 text-[var(--text-primary)]/25 flex-shrink-0" />
    <span className="flex-1 text-base text-[var(--text-primary)]/40">
      Тикет
      {(task as any).number && (
        <span className="ml-1.5 text-[var(--accent)] font-mono text-sm">
          #{(task as any).number.slice(0, -4)}
        </span>
      )}
    </span>
    <Link
      to={`/tickets/${(task as any).number.slice(0, -4) || task.ticket_id}`}
      onClick={onClose}
      className="flex items-center gap-1 text-base text-[var(--accent)] hover:text-[var(--accent-light)]"
    >
      Открыть <ArrowUpRight className="w-3 h-3" />
    </Link>
  </div>
)}

          {task.project_id && <div className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-[var(--hover-2)] border border-[var(--border-color)]"><FolderOpen className="w-4 h-4 text-[var(--text-primary)]/25 flex-shrink-0" /><span className="flex-1 text-base text-[var(--text-primary)]/40">Проект</span><Link to={`/projects/${task.project_id}`} onClick={onClose} className="flex items-center gap-1 text-base text-[var(--accent)]">Открыть <ArrowUpRight className="w-3 h-3" /></Link></div>}
        </div>

        <div className="flex items-center justify-between gap-3 px-5 py-3.5 border-t border-[var(--border-color)] bg-[var(--hover-1)] flex-shrink-0">
          <button onClick={() => act('archive', () => tasksApi.archive(task.id), 'Архивировано')} disabled={busy === 'archive'}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[var(--accent)]/10 hover:bg-[var(--accent)]/20 border border-[var(--accent)]/20 text-[var(--accent)] text-sm font-medium disabled:opacity-50">
            {busy === 'archive' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Archive className="w-4 h-4" />} Архив
          </button>
          <button onClick={onClose} className="px-4 py-2 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-sm">Закрыть</button>
        </div>
      </div>
    </div>
  );
}

/* 
   MAIN PAGE
    */

export default function TasksPage() {
  const [sp] = useSearchParams();
  const { user } = useAuthStore();
  const { toast } = useToast();

  const up = sp.get('project_id');
  const ua = sp.get('assignee_id');

  const [mode, setMode] = useState<ContextMode>(up ? 'project' : ua ? 'assignee' : 'my');
  const [selPid, setSelPid] = useState(up ?? '');
  const [selAid, setSelAid] = useState(ua ?? '');
  const [projects, setProjects] = useState<Project[]>([]);
  const [lpj, setLpj] = useState(false);
  const [umap, setUmap] = useState<Map<string, SimpleUser | CounterpartyCustomer>>(new Map());
  const [cols, setCols] = useState<TaskKanbanColumn[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [moreCol, setMoreCol] = useState<TaskStatus | null>(null);
  const [drag, setDrag] = useState<{ id: string; from: TaskStatus } | null>(null);
  const [dragOver, setDragOver] = useState<TaskStatus | null>(null);
  const [q, setQ] = useState('');
  const [fp, setFp] = useState<TaskPriority[]>([]);
  const [fo, setFo] = useState(false);
  const [sf, setSf] = useState(false);
  const [view, setView] = useState<TaskKanbanItem | null>(null);
  const [create, setCreate] = useState<TaskStatus | null>(null);
  const [assignBeforeTask, setAssignBeforeTask] = useState<TaskKanbanItem | null>(null);
  const [assignBeforeLoading, setAssignBeforeLoading] = useState(false);

  const staff = ['admin', 'support_manager', 'support_agent', 'executor'].includes(user?.role ?? '');

  // Refs for stable fetchBoard
  const fpRef = useRef(fp);
  const foRef = useRef(fo);
  fpRef.current = fp;
  foRef.current = fo;

  const ctx = useCallback((): TaskKanbanContext => {
    if (mode === 'project' && selPid) return { type: 'project', project_id: selPid };
    if (mode === 'assignee' && selAid) return { type: 'assignee', assignee_id: selAid };
    if (mode === 'internal') return { type: 'internal' };
    return { type: 'my' };
  }, [mode, selPid, selAid]);

  const loadU = useCallback(async () => {
    const m = new Map<string, SimpleUser | CounterpartyCustomer>();
    try {
      if (staff) { (await usersApi.getAllUsers(1, 100)).items.forEach(u => m.set(u.id, u)); }
      else { (await usersApi.getSupports(1, 100)).items.forEach(u => m.set(u.id, u)); }
      if (user?.counterparty_id) { (await usersApi.getCustomers(user.counterparty_id, 1, 100)).items.forEach(u => m.set(u.id, u)); }
    } catch { }
    setUmap(m);
  }, [staff, user]);

  const loadP = useCallback(async () => {
    setLpj(true);
    try { setProjects((staff ? await projectsApi.getAll(1, 100, 'active') : await projectsApi.getMyProjects('all', 1, 100)).items); }
    catch { setProjects([]); } finally { setLpj(false); }
  }, [staff]);

  const fetchBoard = useCallback(async (silent = false) => {
    if (!silent) setLoading(true); else setRefreshing(true);
    try {
      const d = await tasksApi.getKanban(ctx(), {
        size: 20, priorities: fpRef.current.length ? fpRef.current : undefined, overdue_only: foRef.current || undefined,
      });
      setCols(COLUMN_ORDER.map(s => d.columns.find(c => c.status === s)).filter((c): c is TaskKanbanColumn => !!c));
      setTotal(d.total_tasks);
    } catch (e: any) { toast({ title: 'Ошибка', description: apiErr(e), variant: 'destructive' }); }
    finally { setLoading(false); setRefreshing(false); }
  }, [ctx, toast]);

  useEffect(() => { loadU(); }, [loadU]);
  useEffect(() => { loadP(); }, [loadP]);
  useEffect(() => { fetchBoard(); }, [fetchBoard]);
  // Re-fetch when filters change
  useEffect(() => { fetchBoard(true); }, [fp, fo]);

  const more = useCallback(async (st: TaskStatus) => {
    const c = cols.find(x => x.status === st);
    if (!c?.tasks.has_next) return;
    setMoreCol(st);
    try {
      const d = await tasksApi.getKanban(ctx(), { page: c.tasks.page + 1, size: c.tasks.size, priorities: fpRef.current.length ? fpRef.current : undefined });
      const nc = d.columns.find(x => x.status === st);
      if (!nc) return;
      setCols(p => p.map(x => x.status === st ? { ...x, tasks: { ...nc.tasks, items: [...x.tasks.items, ...nc.tasks.items] } } : x));
    } catch (e: any) { toast({ title: 'Ошибка', description: apiErr(e), variant: 'destructive' }); }
    finally { setMoreCol(null); }
  }, [cols, ctx, toast]);

  const handleAssignAndProgress = useCallback(async (assigneeId: string) => {
    if (!assignBeforeTask) return;
    setAssignBeforeLoading(true);
    try {
      await tasksApi.assign(assignBeforeTask.id, { assignee_id: assigneeId });
      await tasksApi.changeStatus(assignBeforeTask.id, 'in_progress');
      toast({ title: 'Задача переведена в работу' }); setAssignBeforeTask(null); await fetchBoard(true);
    } catch (e: any) { toast({ title: 'Ошибка', description: apiErr(e), variant: 'destructive' }); }
    finally { setAssignBeforeLoading(false); }
  }, [assignBeforeTask, fetchBoard, toast]);

  const onDragStart = useCallback((id: string, from: TaskStatus) => { setDrag({ id, from }); }, []);
  const onDragOver = useCallback((e: React.DragEvent, st: TaskStatus) => {
    e.preventDefault();
    if (drag && !ALLOWED_TRANSITIONS[drag.from].includes(st)) return;
    e.dataTransfer.dropEffect = 'move'; setDragOver(st);
  }, [drag]);
  const onDrop = useCallback(async (e: React.DragEvent, to: TaskStatus) => {
    e.preventDefault(); setDragOver(null);
    if (!drag || drag.from === to) { setDrag(null); return; }
    const srcCol = cols.find(c => c.status === drag.from);
    const dt = srcCol?.tasks.items.find(t => t.id === drag.id);
    if (!dt) { setDrag(null); return; }
    if (!ALLOWED_TRANSITIONS[drag.from].includes(to)) {
      toast({ title: 'Переход недоступен', description: `${STATUS_LABELS[drag.from]} → ${STATUS_LABELS[to]}`, variant: 'destructive' });
      setDrag(null); return;
    }
    if (to === 'in_progress' && !dt.assignee_id) { setDrag(null); setAssignBeforeTask(dt); return; }
    const { id, from } = drag; setDrag(null);
    let mv: TaskKanbanItem | undefined;
    setCols(prev => {
      const next = prev.map(c => {
        if (c.status === from) { const items = c.tasks.items.filter(t => { if (t.id === id) { mv = t; return false; } return true; }); return { ...c, tasks: { ...c.tasks, items, total_items: c.tasks.total_items - 1 } }; }
        return c;
      });
      if (!mv) return prev;
      const updated = { ...mv, status: to };
      return next.map(c => c.status === to ? { ...c, tasks: { ...c.tasks, items: [updated, ...c.tasks.items], total_items: c.tasks.total_items + 1 } } : c);
    });
    try { await tasksApi.changeStatus(id, to); } catch (e: any) { toast({ title: 'Ошибка', description: apiErr(e), variant: 'destructive' }); fetchBoard(true); }
  }, [drag, cols, fetchBoard, toast]);

  const disp = cols.map(c => {
    if (!q) return c;
    const s = q.toLowerCase();
    return { ...c, tasks: { ...c.tasks, items: c.tasks.items.filter(t => t.title.toLowerCase().includes(s) || t.number.toLowerCase().includes(s)) } };
  });

  const hf = fp.length > 0 || fo;
  const done = cols.find(c => c.status === 'done')?.tasks.total_items ?? 0;
  const tabs = CTX_TABS.filter(t => !t.staffOnly || staff);

  // Async loaders for tab selects
  const loadProjectsAsync = useCallback(async (search: string, page: number) => {
    const res = staff ? await projectsApi.getAll(page, 20, 'active') : await projectsApi.getMyProjects('all', page, 20);
    const items = search ? res.items.filter(p => p.name.toLowerCase().includes(search.toLowerCase()) || p.key.toLowerCase().includes(search.toLowerCase())) : res.items;
    return { items: items.map(p => ({ value: p.id, label: p.name, sublabel: p.key, icon: <FolderOpen className="w-4 h-4 text-amber-400" /> })), hasNext: res.items.length === 20 };
  }, [staff]);

  const loadAssigneesAsync = useCallback(async (search: string, page: number) => {
    let items: (SimpleUser | CounterpartyCustomer)[] = [];
    try { if (staff) items = (await usersApi.getAllUsers(page, 20)).items; else items = (await usersApi.getSupports(page, 20)).items; } catch { }
    const filtered = search ? items.filter(u => (u.full_name || '').toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase())) : items;
    return { items: filtered.map(u => ({ value: u.id, label: u.full_name || u.username || u.email, sublabel: u.email })), hasNext: items.length === 20 };
  }, [staff]);

  return (
    <div className="space-y-4 animate-in fade-in duration-500" onDragEnd={() => { setDrag(null); setDragOver(null); }}>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-4xl font-bold text-[var(--text-primary)]">Задачи сотрудников</h1>
            {!loading && <span className="px-2 py-0.5 rounded-lg bg-[var(--hover-3)] text-base font-medium text-[var(--text-primary)]/50 tabular-nums">{total}</span>}
            {refreshing && <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--text-primary)]/30" />}
          </div>
          {!loading && <p className="text-base text-[var(--text-primary)]/35 mt-0.5">{total - done} активных · {done} завершено{hf && <span className="text-[var(--accent)] ml-1.5">· фильтры</span>}</p>}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-primary)]/25 pointer-events-none" />
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Поиск..."
              className="w-44 pl-8 pr-7 py-2 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] text-sm placeholder-[var(--text-primary)]/25 focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)] transition-all" />
            {q && <button onClick={() => setQ('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 hover:text-[var(--text-primary)]"><X className="w-3.5 h-3.5" /></button>}
          </div>
          <div className="relative">
            <button onClick={() => setSf(v => !v)} className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-sm font-medium transition-all ${hf ? 'bg-[var(--accent)]/10 border-[var(--accent)]/30 text-[var(--accent)]' : 'bg-[var(--hover-2)] border-[var(--border-color)] text-[var(--text-primary)]/50'}`}>
              <Filter className="w-3.5 h-3.5" />Фильтры{hf && <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />}
            </button>
            {sf && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setSf(false)} />
                <div className="absolute right-0 top-full mt-1.5 z-20 w-56 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-[var(--shadow-lg)]">
                  <div className="p-2.5 space-y-2.5">
                    <div>
                      <p className="px-1 pb-1 text-[13px] uppercase tracking-widest text-[var(--text-primary)]/25">Приоритет</p>
                      <div className="flex flex-wrap gap-1 px-0.5">
                        {TASK_PRIORITY_LIST.map(p => { const pm = PRI[p]; return <button key={p} onClick={() => setFp(v => v.includes(p) ? v.filter(x => x !== p) : [...v, p])}
                          className={`flex items-center gap-1 px-2 py-1 rounded-lg text-base font-medium border transition-all ${fp.includes(p) ? `${pm.bg} ${pm.color} ${pm.border}` : 'bg-[var(--hover-1)] text-[var(--text-primary)]/40 border-[var(--border-color)]'}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${pm.dot}`} />{p}
                        </button>; })}
                      </div>
                    </div>
                    <div className="border-t border-[var(--border-color)] pt-2 px-0.5">
                      <button onClick={() => setFo(v => !v)} className={`w-full flex items-center gap-2 py-1.5 px-1 rounded-lg text-sm transition-colors ${fo ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]/50'}`}>
                        <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0 ${fo ? 'bg-[var(--accent)] border-[var(--accent)]' : 'border-[var(--border-color)]'}`}>{fo && <Check className="w-2 h-2 text-white" />}</div>Просроченные
                      </button>
                    </div>
                    {hf && <div className="border-t border-[var(--border-color)] pt-1.5"><button onClick={() => { setFp([]); setFo(false); }} className="w-full text-center text-base text-[var(--accent)] py-1">Сбросить</button></div>}
                  </div>
                </div>
              </>
            )}
          </div>
          <button onClick={() => fetchBoard(true)} disabled={refreshing || loading}
            className="p-2 rounded-xl bg-[var(--hover-2)] border border-[var(--border-color)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)] hover:bg-[var(--hover-3)] transition-all disabled:opacity-40">
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button onClick={() => setCreate('backlog')} className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-light)] text-white text-sm font-medium transition-colors shadow-[var(--shadow-md)]">
            <Plus className="w-4 h-4" /> Задача
          </button>
        </div>
      </div>

      {/* Context tabs with AsyncSelect */}
      <div className="flex items-center gap-2.5 flex-wrap">
        <div className="flex items-center gap-0.5 p-0.5 bg-[var(--hover-2)] rounded-xl border border-[var(--border-color)]">
          {tabs.map(t => {
            const TI = t.icon;
            return <button key={t.id} onClick={() => setMode(t.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-base font-medium transition-all whitespace-nowrap ${mode === t.id ? 'bg-[var(--accent)]/15 text-[var(--text-primary)]' : 'text-[var(--text-primary)]/70 hover:text-[var(--text-primary)]/70 hover:bg-[var(--hover-3)]'}`}>
              <TI className="w-3.5 h-3.5" />{t.label}
            </button>;
          })}
        </div>
        {mode === 'project' && (
          <div className="flex items-center gap-1.5">
            <ChevronRight className="w-4 h-4 text-[var(--text-primary)]/15" />
            <div className="min-w-[200px]">
              <AsyncSelect value={selPid} onChange={setSelPid} loadOptions={loadProjectsAsync}
                placeholder="Выберите проект" icon={FolderOpen} />
            </div>
          </div>
        )}
        {mode === 'assignee' && (
          <div className="flex items-center gap-1.5">
            <ChevronRight className="w-4 h-4 text-[var(--text-primary)]/15" />
            <div className="min-w-[200px]">
              <AsyncSelect value={selAid} onChange={setSelAid} loadOptions={loadAssigneesAsync}
                placeholder="Выберите исполнителя" icon={UserCheck} />
            </div>
          </div>
        )}
      </div>

      {/* Board */}
      {loading ? (
        <div className="flex items-center justify-center py-20"><div className="text-center"><Loader2 className="w-8 h-8 text-[var(--accent)] animate-spin mx-auto mb-3" /><p className="text-[var(--text-primary)]/30 text-sm">Загрузка...</p></div></div>
      ) : !cols.length ? (
        <div className="flex items-center justify-center py-20"><div className="text-center max-w-xs">
          <FolderOpen className="w-12 h-12 text-[var(--text-primary)]/10 mx-auto mb-3" />
          <p className="text-sm font-semibold text-[var(--text-primary)]/60 mb-1">Нет данных</p>
          <p className="text-base text-[var(--text-primary)]/30 mb-4">{mode === 'project' && !selPid ? 'Выберите проект' : mode === 'assignee' && !selAid ? 'Выберите исполнителя' : 'Задачи не найдены'}</p>
          <button onClick={() => fetchBoard()} className="px-4 py-2 rounded-xl bg-[var(--accent)] text-white text-sm font-medium">Обновить</button>
        </div></div>
      ) : (
        <div className="max-w-full overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-[var(--hover-3)] scrollbar-track-transparent" style={{ minHeight: 'calc(100vh - 280px)' }}>
          <div className="flex gap-3 inline-flex">
            {disp.map(c => <KColumn key={c.status} column={c} userMap={umap} isDragOver={dragOver === c.status} loadingMore={moreCol === c.status}
              onDragStart={onDragStart} onDragOver={onDragOver} onDrop={onDrop} onAdd={setCreate} onView={setView} onMore={more} />)}
          </div>
        </div>
      )}

      {/* Modals */}
      {view && <DetailModal task={view} userMap={umap} onClose={() => setView(null)} onRefresh={() => fetchBoard(true)} onNeedAssign={t => { setView(null); setAssignBeforeTask(t); }} />}
      {create != null && <CreateModal initialStatus={create} context={ctx()} userMap={umap} onClose={() => setCreate(null)} onOk={() => { setCreate(null); fetchBoard(true); }} />}
      {assignBeforeTask && <AssignBeforeProgressModal task={assignBeforeTask} userMap={umap} loading={assignBeforeLoading}
        onClose={() => { if (!assignBeforeLoading) setAssignBeforeTask(null); }} onConfirm={handleAssignAndProgress} />}
    </div>
  );
}