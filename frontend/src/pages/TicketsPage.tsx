// pages/TicketsPage.tsx
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus, Search, FileText, ChevronRight, ChevronLeft, Loader2,
  Clock, AlertTriangle, CheckCircle2, Calendar, XCircle, Hash,
  Building2, FolderOpen, User, X, SlidersHorizontal, ChevronDown, Check,
} from 'lucide-react';
import { ticketsApi, counterpartiesApi, projectsApi, usersApi } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import type {
  TicketListItem, TicketStatus, TicketPriority,
  Counterparty, Project, CounterpartyCustomer, SimpleUser,
} from '../types';

// ─── Константы ────────────────────────────────────────────────────────────────

const STATUSES: { value: TicketStatus; label: string; color: string }[] = [
  { value: 'Новый',           label: 'Новый',           color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  { value: 'На согласовании', label: 'На согласовании', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  { value: 'Открыт',         label: 'Открыт',          color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  { value: 'В работе',       label: 'В работе',        color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  { value: 'Ожидает ответа', label: 'Ожидает ответа',  color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  { value: 'Решён',          label: 'Решён',           color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  { value: 'Закрыт',         label: 'Закрыт',          color: 'bg-neutral-500/20 text-neutral-400 border-neutral-500/30' },
  { value: 'Переоткрыт',     label: 'Переоткрыт',      color: 'bg-red-500/20 text-red-400 border-red-500/30' },
];

const PRIORITIES: { value: TicketPriority; label: string; color: string }[] = [
  { value: 'Низкий',       label: 'Низкий',       color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  { value: 'Средний',      label: 'Средний',      color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  { value: 'Высокий',      label: 'Высокий',      color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  { value: 'Критический',  label: 'Критический',  color: 'bg-red-500/20 text-red-400 border-red-500/30' },
];

// ─── Кастомный Dropdown ──────────────────────────────────────────────────────

interface DropdownOption {
  value: string;
  label: string;
  sublabel?: string;
  color?: string;
  icon?: React.ReactNode;
}

interface FilterDropdownProps {
  label: string;
  icon?: React.ReactNode;
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  searchable?: boolean;
}

function FilterDropdown({
  label,
  icon,
  options,
  value,
  onChange,
  placeholder = 'Все',
  searchable = false,
}: FilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery('');
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
        (o.sublabel && o.sublabel.toLowerCase().includes(query.toLowerCase()))
      )
    : options;

  return (
    <div ref={ref} className="relative">
      <p className="text-xs uppercase tracking-wider text-white/30 mb-1.5 flex items-center gap-2">
        {icon}
        {label}
      </p>

      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`
          w-full flex items-center justify-between gap-2 px-3.5 py-3 rounded-xl border text-base transition-all
          ${open
            ? 'bg-white/[0.08] border-red-500/40 text-white'
            : value
              ? 'bg-white/[0.06] border-white/[0.12] text-white/90'
              : 'bg-white/[0.03] border-white/[0.08] text-white/50 hover:border-white/[0.15] hover:text-white/70'
          }
        `}
      >
        <span className="truncate">
          {selected ? (
            <span className="flex items-center gap-2">
              {selected.color && (
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${selected.color.split(' ')[0].replace('/20', '/60')}`} />
              )}
              {selected.label}
            </span>
          ) : placeholder}
        </span>

        <div className="flex items-center gap-1 flex-shrink-0">
          {value ? (
            <span
              role="button"
              tabIndex={0}
              onClick={e => { e.stopPropagation(); onChange(''); setOpen(false); }}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); onChange(''); setOpen(false); } }}
              className="p-0.5 rounded hover:bg-white/10 text-white/30 hover:text-white/60 transition-colors cursor-pointer"
            >
              <X size={13} />
            </span>
          ) : (
            <ChevronDown size={15} className={`text-white/25 transition-transform ${open ? 'rotate-180' : ''}`} />
          )}
        </div>
      </button>

      {open && (
        <div
          className="absolute top-full left-0 right-0 mt-1.5 z-[100] bg-[#1d1d1d] border border-white/[0.1] rounded-xl overflow-hidden"
          style={{ boxShadow: '0 16px 48px rgba(0,0,0,0.5)' }}
        >
          {searchable && (
            <div className="p-2 border-b border-white/[0.06]">
              <div className="relative">
                <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/25" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Поиск..."
                  className="w-full pl-8 pr-3 py-2 rounded-lg glass-card border border-white/[0.06]
                             text-sm text-white placeholder-white/25 focus:outline-none focus:border-white/[0.15]"
                />
              </div>
            </div>
          )}

          <div className="max-h-64 overflow-y-auto py-1">
            <button
              type="button"
              onClick={() => { onChange(''); setOpen(false); setQuery(''); }}
              className={`
                w-full flex items-center gap-3 px-4 py-2.5 text-left text-base transition-colors
                ${!value ? 'bg-red-500/10 text-white' : 'text-white/55 hover:bg-white/[0.04]'}
              `}
            >
              {!value ? <Check size={14} className="text-red-400 flex-shrink-0" /> : <span className="w-[14px]" />}
              <span>{placeholder}</span>
            </button>

            <div className="h-px bg-white/[0.06] mx-3 my-1" />

            {filtered.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-white/30">Ничего не найдено</div>
            ) : (
              filtered.map(option => {
                const isSelected = option.value === value;
                return (
                  <button
                    type="button"
                    key={option.value}
                    onClick={() => { onChange(option.value); setOpen(false); setQuery(''); }}
                    className={`
                      w-full flex items-center gap-3 px-4 py-2.5 text-left text-base transition-colors
                      ${isSelected ? 'bg-red-500/10 text-white' : 'text-white/65 hover:bg-white/[0.04]'}
                    `}
                  >
                    {isSelected
                      ? <Check size={14} className="text-red-400 flex-shrink-0" />
                      : <span className="w-[14px] flex-shrink-0" />
                    }

                    {option.color ? (
                      <span className={`px-2 py-0.5 rounded text-sm font-medium border ${option.color}`}>
                        {option.label}
                      </span>
                    ) : (
                      <div className="min-w-0">
                        <span className="block truncate">{option.label}</span>
                        {option.sublabel && (
                          <span className="block text-xs text-white/30 truncate">{option.sublabel}</span>
                        )}
                      </div>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Основной компонент ───────────────────────────────────────────────────────

export default function TicketsPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [tickets, setTickets]       = useState<TicketListItem[]>([]);
  const [loading, setLoading]       = useState(true);
  const [page, setPage]             = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Фильтры
  const [search, setSearch]                         = useState('');
  const [statusFilter, setStatusFilter]             = useState<TicketStatus | ''>('');
  const [priorityFilter, setPriorityFilter]         = useState<TicketPriority | ''>('');
  const [counterpartyFilter, setCounterpartyFilter] = useState('');
  const [projectFilter, setProjectFilter]           = useState('');
  const [reporterFilter, setReporterFilter]         = useState('');
  const [showFilters, setShowFilters]               = useState(false);

  // Данные для дропдаунов
  const [counterparties, setCounterparties] = useState<Counterparty[]>([]);
  const [projects, setProjects]             = useState<Project[]>([]);
  const [allUsers, setAllUsers]             = useState<SimpleUser[]>([]);
  const [companyUsers, setCompanyUsers]     = useState<CounterpartyCustomer[]>([]);

  // Роли
  const isCustomer      = user?.role === 'customer';
  const isCustomerAdmin = user?.role === 'customer_admin';
  const isSupport       = user?.role === 'support_agent' || user?.role === 'support_manager';
  const isAdmin         = user?.role === 'admin';

  // ── Загрузка фильтров ────────────────────────────────────────────────────

  useEffect(() => { loadFilters(); }, []);

  useEffect(() => {
    if (isAdmin || isSupport) loadAllUsers();
    else if (isCustomerAdmin && user?.counterparty_id) loadCompanyUsers();
  }, [isAdmin, isSupport, isCustomerAdmin, user?.counterparty_id]);

  const loadAllUsers = async () => {
    try { const r = await usersApi.getAllUsers(1, 100); setAllUsers(r.items); }
    catch (e) { console.error(e); }
  };

  const loadCompanyUsers = async () => {
    if (!user?.counterparty_id) return;
    try { const u = await ticketsApi.getCompanyUsers(user.counterparty_id); setCompanyUsers(u); }
    catch (e) { console.error(e); }
  };

  const loadFilters = async () => {
    try {
      if (isAdmin || isSupport) {
        const res = await counterpartiesApi.getAll(1, 100);
        setCounterparties(res.items);
      }
      if (isCustomer || isCustomerAdmin) {
        const res = await projectsApi.getMyProjects('all', 1, 100);
        setProjects(res.items);
      } else {
        const res = await projectsApi.getAll(1, 100);
        setProjects(res.items);
      }
    } catch (e) { console.error(e); }
  };

  // ── Загрузка тикетов ─────────────────────────────────────────────────────
  // Поиск убран из API — делается локально через useMemo

  useEffect(() => {
    setPage(1);
  }, [statusFilter, priorityFilter, counterpartyFilter, projectFilter, reporterFilter]);

  useEffect(() => {
    loadTickets();
  }, [page, statusFilter, priorityFilter, counterpartyFilter, projectFilter, reporterFilter]);

  const loadTickets = async () => {
    setLoading(true);
    try {
      const filters = {
        status:       statusFilter || undefined,
        priority:     priorityFilter || undefined,
        project_id:   projectFilter || undefined,
        reporter_id:  reporterFilter || undefined,
      };

      let response;

      if (isCustomer && user?.counterparty_id) {
        response = await ticketsApi.getAllWithFilters(page, 10, { ...filters, counterparty_id: user.counterparty_id });
      } else if (isCustomerAdmin && user?.counterparty_id) {
        response = await ticketsApi.getAllWithFilters(page, 10, { ...filters, counterparty_id: user.counterparty_id });
      } else if (isSupport || isAdmin) {
        response = await ticketsApi.getAllWithFilters(page, 10, { ...filters, counterparty_id: counterpartyFilter || undefined });
      } else {
        response = await ticketsApi.getAll(page, 10);
      }

      setTickets(response.items);
      setTotalPages(response.total_pages);
      setTotalItems(response.total_items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // ── Локальный поиск ───────────────────────────────────────────────────────

  const normalizedSearch = search.trim().toLowerCase();

  const filteredTickets = useMemo(() => {
    if (!normalizedSearch) return tickets;
    return tickets.filter(t =>
      (t.title || '').toLowerCase().includes(normalizedSearch) ||
      (t.number || '').toLowerCase().includes(normalizedSearch) ||
      (t.status || '').toLowerCase().includes(normalizedSearch) ||
      (t.priority || '').toLowerCase().includes(normalizedSearch)
    );
  }, [tickets, normalizedSearch]);

  // ── Reset, helpers ────────────────────────────────────────────────────────

  const resetFilters = () => {
    setStatusFilter('');
    setPriorityFilter('');
    setCounterpartyFilter('');
    setProjectFilter('');
    setReporterFilter('');
    setSearch('');
    setPage(1);
  };

  const hasActiveFilters = !!(statusFilter || priorityFilter || counterpartyFilter || projectFilter || reporterFilter || search);
  const activeFiltersCount = [statusFilter, priorityFilter, counterpartyFilter, projectFilter, reporterFilter].filter(Boolean).length;

  const getStatusColor  = (s: string) => STATUSES.find(x => x.value === s)?.color  || 'bg-neutral-500/20 text-neutral-400 border-neutral-500/30';
  const getPriorityColor = (p: string) => PRIORITIES.find(x => x.value === p)?.color || 'bg-neutral-500/20 text-neutral-400 border-neutral-500/30';

  const formatDate = (d: string) => {
    if (!d) return '—';
    const date = new Date(d);
    const now  = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 86400000);
    if (diff === 0) return `Сегодня, ${date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
    if (diff === 1) return `Вчера, ${date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
    if (diff < 7)  return `${diff} дн. назад`;
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const isClosed = (s: string) => s === 'Закрыт' || s === 'Решён';

  const getUserDisplayName = (uid: string) => {
    if (isAdmin || isSupport) { const u = allUsers.find(x => x.id === uid); return u?.full_name || u?.username || u?.email || uid; }
    if (isCustomerAdmin)      { const u = companyUsers.find(x => x.id === uid); return u?.full_name || u?.username || u?.email || uid; }
    return uid;
  };

  // ── Опции для дропдаунов ──────────────────────────────────────────────────

  const statusOptions: DropdownOption[]       = STATUSES.map(s => ({ value: s.value, label: s.label, color: s.color }));
  const priorityOptions: DropdownOption[]     = PRIORITIES.map(p => ({ value: p.value, label: p.label, color: p.color }));
  const counterpartyOptions: DropdownOption[] = counterparties.map(c => ({ value: c.id, label: c.name || c.legal_name, sublabel: c.inn ? `ИНН: ${c.inn}` : undefined }));
  const projectOptions: DropdownOption[]      = projects.map(p => ({ value: p.id, label: p.name }));
  const userOptions: DropdownOption[]         = (isAdmin || isSupport)
    ? allUsers.map(u => ({ value: u.id, label: u.full_name || u.username || u.email, sublabel: u.email && u.full_name ? u.email : undefined }))
    : companyUsers.map(u => ({ value: u.id, label: u.full_name || u.username || u.email, sublabel: u.email && (u.full_name || u.username) ? u.email : undefined }));

  // ── Рендер ────────────────────────────────────────────────────────────────

  if (loading && tickets.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            {isCustomer ? 'Мои заявки' : 'Заявки'}
          </h1>
          <p className="text-base text-white/60">
            Управление обращениями
            {totalItems > 0 && (
              <span className="ml-2 px-2 py-0.5 rounded-full bg-white/[0.08] text-white/50 text-sm">
                {totalItems}
              </span>
            )}
          </p>
        </div>
        <button
          onClick={() => navigate('/tickets/new')}
          className="btn-primary py-4 px-8 text-base font-semibold"
        >
          <Plus className="w-6 h-6" />
          Создать заявку
        </button>
      </div>

      {/* ── Поиск + кнопка фильтров ──────────────────────────────────────── */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30 pointer-events-none" />
          <input
            type="text"
            placeholder="Поиск по теме, номеру, статусу..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-12 pr-10 py-3 glass-card border border-white/[0.08]
                       rounded-xl text-white text-base placeholder-white/30
                       focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10
                       transition-all"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-md
                         text-white/30 hover:text-white/60 hover:bg-white/[0.06] transition-colors"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Кнопка фильтров */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`
            flex items-center gap-2 px-5 py-3 rounded-xl text-base font-medium
            transition-all duration-150
            ${showFilters || activeFiltersCount > 0
              ? 'bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/20'
              : 'bg-white/[0.04] text-white/60 border border-white/[0.08] hover:bg-white/[0.06] hover:text-white/80'
            }
          `}
        >
          <SlidersHorizontal size={16} />
          <span className="hidden sm:inline">Фильтры</span>
          {activeFiltersCount > 0 && (
            <span className="ml-0.5 w-5 h-5 rounded-full bg-red-600 text-white text-[11px] font-bold flex items-center justify-center">
              {activeFiltersCount}
            </span>
          )}
        </button>
      </div>

      {/* ── Активные теги поиска/фильтров ────────────────────────────────── */}
      {hasActiveFilters && !showFilters && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-white/30">Активно:</span>

          {search && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm
                             bg-white/[0.06] text-white/70 border border-white/[0.08]">
              <Search size={12} />
              «{search}»
              <X size={12} className="cursor-pointer text-white/30 hover:text-white/60" onClick={() => setSearch('')} />
            </span>
          )}

          {statusFilter && (
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium border ${getStatusColor(statusFilter)}`}>
              {statusFilter}
              <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setStatusFilter(''); setPage(1); }} />
            </span>
          )}

          {priorityFilter && (
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium border ${getPriorityColor(priorityFilter)}`}>
              {priorityFilter}
              <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setPriorityFilter(''); setPage(1); }} />
            </span>
          )}

          {counterpartyFilter && (isAdmin || isSupport) && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium bg-purple-500/15 text-purple-400 border border-purple-500/20">
              <Building2 size={10} />
              {counterparties.find(c => c.id === counterpartyFilter)?.name}
              <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setCounterpartyFilter(''); setPage(1); }} />
            </span>
          )}

          {projectFilter && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
              <FolderOpen size={10} />
              {projects.find(p => p.id === projectFilter)?.name}
              <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setProjectFilter(''); setPage(1); }} />
            </span>
          )}

          {reporterFilter && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium bg-cyan-500/15 text-cyan-400 border border-cyan-500/20">
              <User size={10} />
              {getUserDisplayName(reporterFilter)}
              <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setReporterFilter(''); setPage(1); }} />
            </span>
          )}

          <button
            onClick={resetFilters}
            className="text-sm text-white/35 hover:text-white/60 transition-colors ml-1"
          >
            Сбросить всё
          </button>
        </div>
      )}

      {/* ── Панель фильтров ──────────────────────────────────────────────── */}
      {showFilters && (
        <div className="bg-white/[0.03] border border-white/[0.08] rounded-2xl p-5 space-y-4
                        animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <SlidersHorizontal size={14} className="text-white/40" />
              Фильтры
            </h3>
            {hasActiveFilters && (
              <button
                onClick={resetFilters}
                className="text-sm text-red-400 hover:text-red-300 flex items-center gap-1 transition-colors"
              >
                <X size={12} /> Сбросить
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            <FilterDropdown
              label="Статус"
              options={statusOptions}
              value={statusFilter}
              onChange={v => { setStatusFilter(v as TicketStatus | ''); setPage(1); }}
              placeholder="Все статусы"
            />
            <FilterDropdown
              label="Приоритет"
              options={priorityOptions}
              value={priorityFilter}
              onChange={v => { setPriorityFilter(v as TicketPriority | ''); setPage(1); }}
              placeholder="Все приоритеты"
            />
            {(isAdmin || isSupport) && (
              <FilterDropdown
                label="Контрагент"
                icon={<Building2 size={14} />}
                options={counterpartyOptions}
                value={counterpartyFilter}
                onChange={v => { setCounterpartyFilter(v); setPage(1); }}
                placeholder="Все контрагенты"
                searchable
              />
            )}
            <FilterDropdown
              label="Проект"
              icon={<FolderOpen size={14} />}
              options={projectOptions}
              value={projectFilter}
              onChange={v => { setProjectFilter(v); setPage(1); }}
              placeholder="Все проекты"
              searchable
            />
            {(isAdmin || isSupport || isCustomerAdmin) && (
              <FilterDropdown
                label="Инициатор"
                icon={<User size={14} />}
                options={userOptions}
                value={reporterFilter}
                onChange={v => { setReporterFilter(v); setPage(1); }}
                placeholder="Все инициаторы"
                searchable
              />
            )}
          </div>

          {/* Активные фильтры-теги внутри панели */}
          {hasActiveFilters && (
            <div className="flex flex-wrap gap-1.5 pt-3 border-t border-white/[0.06]">
              {search && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm
                                 bg-white/[0.06] text-white/70 border border-white/[0.08]">
                  <Search size={10} /> «{search}»
                  <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => setSearch('')} />
                </span>
              )}
              {statusFilter && (
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium border ${getStatusColor(statusFilter)}`}>
                  {statusFilter}
                  <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setStatusFilter(''); setPage(1); }} />
                </span>
              )}
              {priorityFilter && (
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium border ${getPriorityColor(priorityFilter)}`}>
                  {priorityFilter}
                  <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setPriorityFilter(''); setPage(1); }} />
                </span>
              )}
              {counterpartyFilter && (isAdmin || isSupport) && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium bg-purple-500/15 text-purple-400 border border-purple-500/20">
                  <Building2 size={10} />
                  {counterparties.find(c => c.id === counterpartyFilter)?.name}
                  <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setCounterpartyFilter(''); setPage(1); }} />
                </span>
              )}
              {projectFilter && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                  <FolderOpen size={10} />
                  {projects.find(p => p.id === projectFilter)?.name}
                  <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setProjectFilter(''); setPage(1); }} />
                </span>
              )}
              {reporterFilter && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-sm font-medium bg-cyan-500/15 text-cyan-400 border border-cyan-500/20">
                  <User size={10} />
                  {getUserDisplayName(reporterFilter)}
                  <X size={10} className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => { setReporterFilter(''); setPage(1); }} />
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Статистика ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Всего',       value: totalItems,                                                                            icon: FileText,    color: 'text-white/60' },
          { label: 'Новых',       value: tickets.filter(t => t.status === 'Новый').length,                                      icon: Clock,       color: 'text-blue-400' },
          { label: 'В работе',    value: tickets.filter(t => t.status === 'В работе' || t.status === 'Открыт').length,          icon: CheckCircle2, color: 'text-purple-400' },
          { label: 'Критических', value: tickets.filter(t => t.priority === 'Критический').length,                              icon: AlertTriangle, color: 'text-red-400' },
        ].map(stat => (
          <div key={stat.label} className="glass-card rounded-2xl border border-white/[0.08] p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-white/[0.06] flex items-center justify-center flex-shrink-0">
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
            </div>
            <div>
              <p className="text-3xl font-bold text-white">{stat.value}</p>
              <p className="text-base text-white/60">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Список ───────────────────────────────────────────────────────── */}
      {filteredTickets.length === 0 ? (
        <div className="glass-card rounded-2xl border border-white/[0.08] p-16 text-center">
          <FileText className="w-20 h-20 text-white/20 mx-auto mb-6" />
          <h3 className="text-2xl font-bold text-white mb-3">Нет заявок</h3>
          <p className="text-base text-white/50 mb-8">
            {hasActiveFilters
              ? 'Попробуйте изменить параметры фильтрации'
              : search
                ? 'На текущей странице ничего не найдено'
                : 'Создайте первую заявку'}
          </p>
          {!hasActiveFilters && !search && (
            <button onClick={() => navigate('/tickets/new')} className="btn-primary py-4 px-8 text-base">
              <Plus className="w-6 h-6" /> Создать заявку
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {loading && (
              <div className="flex justify-center py-4">
                <Loader2 className="w-6 h-6 text-white/30 animate-spin" />
              </div>
            )}

            {filteredTickets.map(ticket => (
              <Link
                key={ticket.id}
                to={`/tickets/${ticket.number}`}
                className="glass-card p-6 block hover:bg-white/[0.08] hover:border-red-500/30 transition-all group"
              >
                <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Hash className="w-4 h-4 text-red-400" />
                      <span className="text-sm font-mono text-red-400 bg-red-500/10 px-2 py-0.5 rounded">
                        {ticket.number}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-3 group-hover:text-red-400 transition-colors line-clamp-2">
                      {ticket.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${getStatusColor(ticket.status)}`}>
                        {ticket.status}
                      </span>
                      <span className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${getPriorityColor(ticket.priority)}`}>
                        {ticket.priority}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <div className="flex items-center gap-3 text-base text-white/70">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-4 h-4 text-white/30" />
                        {formatDate(ticket.created_at)}
                      </div>
                      <ChevronRight className="w-4 h-4 text-white/30 group-hover:text-red-400 group-hover:translate-x-0.5 transition-all" />
                    </div>
                    {isClosed(ticket.status) && ticket.closed_at ? (
                      <div className="flex items-center gap-1.5 text-sm text-white/35">
                        <XCircle className="w-3.5 h-3.5" />
                        Закрыта {formatDate(ticket.closed_at)}
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-sm text-yellow-500/60">
                        <Clock className="w-3.5 h-3.5" />
                        Активна
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* ── Пагинация ──────────────────────────────────────────────── */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card border border-white/[0.08]
                           hover:bg-white/[0.07] disabled:opacity-40 disabled:cursor-not-allowed
                           text-white text-base transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Назад
              </button>

              <div className="flex items-center gap-1.5">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const pageNum = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
                  if (pageNum > totalPages) return null;
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className={`w-10 h-10 rounded-xl text-base font-medium transition-colors ${
                        pageNum === page
                          ? 'bg-red-700 text-white'
                          : 'glass-card text-white/60 border border-white/[0.08] hover:bg-white/[0.08]'
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
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card border border-white/[0.08]
                           hover:bg-white/[0.07] disabled:opacity-40 disabled:cursor-not-allowed
                           text-white text-base transition-colors"
              >
                Вперёд
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}