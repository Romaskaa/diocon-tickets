import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText, CheckCircle2, Plus, ArrowRight,
  Building2, Loader2, FolderOpen, Package, Ticket, ChevronRight,
  Search, Sparkles, Sun, Moon, CloudSun,
  Flame, Timer, TrendingUp, TrendingDown, Activity, Zap,
  BarChart3, Users,
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { ticketsApi, counterpartiesApi, projectsApi, productsApi } from '../api/client';
import type { TicketListItem, Counterparty, Project } from '../types';
import GridBackground from '../components/ui/GridBackground';

/* 
   HELPERS
    */

const getGreeting = () => {
  const h = new Date().getHours();
  if (h < 6) return { text: 'Доброй ночи', icon: Moon };
  if (h < 12) return { text: 'Доброе утро', icon: Sun };
  if (h < 18) return { text: 'Добрый день', icon: CloudSun };
  return { text: 'Добрый вечер', icon: Moon };
};

/* 
   SPARKLINE — мини-график
    */

const Sparkline = ({ data, color = '#ef4444' }: { data: number[]; color?: string }) => {
  if (data.length < 2) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const w = 100, h = 32;
  const step = w / (data.length - 1);

  const points = data
    .map((v, i) => `${i * step},${h - ((v - min) / range) * h}`)
    .join(' ');

  const areaPoints = `0,${h} ${points} ${w},${h}`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-full overflow-visible" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill={`url(#grad-${color})`} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
};

/* 
   DONUT CHART — кольцевая диаграмма
    */

const DonutChart = ({
  segments,
  size = 160,
}: {
  segments: { value: number; color: string; label: string }[];
  size?: number;
}) => {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const radius = (size - 24) / 2;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="var(--border-color)" strokeWidth="12"
        />
        {segments.map((seg, i) => {
          const length = (seg.value / total) * circumference;
          const dasharray = `${length} ${circumference - length}`;
          const el = (
            <circle
              key={i}
              cx={size / 2} cy={size / 2} r={radius}
              fill="none" stroke={seg.color} strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={dasharray}
              strokeDashoffset={-offset}
              style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
          );
          offset += length;
          return el;
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-[var(--text-primary)] tabular-nums leading-none">{total}</span>
        <span className="text-[15px] text-[var(--text-primary)]/40 mt-1">всего</span>
      </div>
    </div>
  );
};

/* 
   BAR CHART — столбчатая диаграмма по дням
    */

const BarChart = ({ data }: { data: { label: string; value: number; isToday?: boolean }[] }) => {
  const max = Math.max(...data.map(d => d.value), 1);

  return (
    <div className="flex items-end justify-between gap-2 h-32">
      {data.map((d, i) => {
        const height = (d.value / max) * 100;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
            <div className="relative w-full flex items-end justify-center" style={{ height: '100%' }}>
              {d.value > 0 && (
                <span className="absolute -top-5 text-[13px] font-semibold text-[var(--text-primary)]/70 opacity-0
                                 group-hover:opacity-100 transition-opacity tabular-nums">
                  {d.value}
                </span>
              )}
              <div
                className={`w-full rounded-md transition-all duration-300 ${
                  d.isToday
                    ? 'bg-gradient-to-t from-red-600 to-red-500'
                    : 'bg-[var(--hover-1)] group-hover:bg-[var(--hover-1)]'
                }`}
                style={{ height: `${Math.max(height, 4)}%` }}
              />
            </div>
            <span className={`text-[13px] font-medium ${
              d.isToday ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]/40'
            }`}>
              {d.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};

/* 
   MAIN COMPONENT
    */

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [tickets, setTickets] = useState<TicketListItem[]>([]);
  const [counterparty, setCounterparty] = useState<Counterparty | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [counterparties, setCounterparties] = useState<Counterparty[]>([]);
  const [productsCount, setProductsCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const isCustomer = user?.role === 'customer' || user?.role === 'customer_admin';
  const isSupport = ['admin', 'support_manager', 'support_agent'].includes(user?.role ?? '');

  const greeting = useMemo(() => getGreeting(), []);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [ticketsRes] = await Promise.all([ticketsApi.getMy(1, 100)]);
      setTickets(ticketsRes.items);

      if (isCustomer && user?.counterparty_id) {
        counterpartiesApi.getById(user.counterparty_id)
          .then(cp => setCounterparty(cp)).catch(() => {});
      }

      const projectsRes = isCustomer
        ? await projectsApi.getMyProjects('all', 1, 5).catch(() => ({ items: [] }))
        : await projectsApi.getAll(1, 5).catch(() => ({ items: [] }));
      setProjects(projectsRes.items ?? []);

      if (isSupport) {
        counterpartiesApi.getAll(1, 5)
          .then(res => setCounterparties(res.items ?? [])).catch(() => {});
      }

      productsApi.getProducts({ page: 1, size: 1 })
        .then(res => setProductsCount(res.total_items ?? 0)).catch(() => {});
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  };

  /* ── СТАТИСТИКА ── */

  const stats = {
    total: tickets.length,
    new: tickets.filter(t => t.status === 'Новый').length,
    inProgress: tickets.filter(t => t.status === 'В работе' || t.status === 'Открыт').length,
    critical: tickets.filter(t => t.priority === 'Критический').length,
    resolved: tickets.filter(t => t.status === 'Решён' || t.status === 'Закрыт').length,
    waiting: tickets.filter(t => t.status === 'Ожидает ответа').length,
  };

  const resolvePct = stats.total > 0 ? Math.round((stats.resolved / stats.total) * 100) : 0;

  /* ── ДАННЫЕ ДЛЯ ГРАФИКОВ ── */

  // Заявки по дням за последние 7 дней
  const ticketsLast7Days = useMemo(() => {
    const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    const today = new Date();
    const todayDow = (today.getDay() + 6) % 7; // 0=Пн

    const counts = Array(7).fill(0);
    tickets.forEach(t => {
      const d = new Date(t.created_at);
      const diff = Math.floor((today.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
      if (diff >= 0 && diff < 7) {
        const dow = (d.getDay() + 6) % 7;
        counts[dow]++;
      }
    });

    return days.map((label, i) => ({
      label, value: counts[i], isToday: i === todayDow,
    }));
  }, [tickets]);

  // Спарклайны для статов (искусственная временная прогрессия)
  const buildSparkData = (final: number) => {
    if (final === 0) return [0, 0, 0, 0, 0, 0, 0];
    return Array.from({ length: 7 }, (_, i) => {
      const progress = (i + 1) / 7;
      const noise = Math.sin(i * 1.5) * (final * 0.15);
      return Math.max(0, Math.round(final * progress + noise));
    });
  };

  // Сегменты для donut
  const donutSegments = [
    { value: stats.new, color: '#3f56be', label: 'Новые' },
    { value: stats.inProgress, color: '#eab308', label: 'В работе' },
    { value: stats.waiting, color: '#f97316', label: 'Ожидают' },
    { value: stats.resolved, color: '#10b948', label: 'Решены' },
    { value: stats.critical, color: '#ef4444', label: 'Критичные' },
  ].filter(s => s.value > 0);

  /* ── ФОРМАТТЕРЫ ── */

  const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });

  const fmtTime = (d: string) =>
    new Date(d).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });

  const statusClr = (s: string) => {
    const map: Record<string, string> = {
      'Новый': 'status-new',
      'Открыт': 'status-open',
      'В работе': 'status-progress',
      'Ожидает ответа': 'status-waiting',
      'Решён': 'status-resolved',
      'Закрыт': 'status-closed',
      'Переоткрыт': 'status-reopened',
    };
    return map[s] || 'status-closed';
  };

  const priorityClr = (p: string) => {
    const map: Record<string, string> = {
      'Критический': 'priority-critical',
      'Высокий': 'priority-high',
      'Средний': 'priority-medium',
      'Низкий': 'priority-low',
    };
    return map[p] || 'priority-medium';
  };

  const priorityBar = (p: string) => {
    const map: Record<string, string> = {
      'Критический': 'status-bar-reopened',
      'Высокий': 'status-bar-waiting',
      'Средний': 'status-bar-progress',
      'Низкий': 'status-bar-resolved',
    };
    return map[p] || '';
  };

  /* ── LOADING ── */

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <Loader2 className="w-10 h-10 text-[var(--accent)] animate-spin" />
      <p className="text-[var(--text-primary)]/40 text-[15px]">Загружаем данные…</p>
    </div>
  );

  /*  */

  return (
    <div className="space-y-8 animate-in fade-in duration-500">

      {/* 
          HEADER с сеткой-фоном
           */}
      <div className="relative overflow-hidden rounded-3xl border border-[var(--border-color)]
                      p-8">
        <GridBackground variant="dots" />
        {/* Decorative blur */}

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 text-[var(--text-primary)]/50 text-[15px] font-medium
                            px-3 py-1.5 rounded-full bg-[var(--hover-1)] border border-[var(--border-color)]">
              <greeting.icon className="w-4 h-4" />
              {greeting.text}
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] tracking-tight">
              {user?.full_name || user?.username || 'Главная страница'}
            </h1>
            <p className="text-[15px] text-[var(--text-primary)]/40">
              {new Date().toLocaleDateString('ru-RU', {
                weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
              })}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-primary)]/30
                                 group-focus-within:text-[var(--accent)] transition-colors" />
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && searchQuery.trim()) {
                    navigate(`/tickets?search=${encodeURIComponent(searchQuery.trim())}`);
                  }
                }}
                placeholder="Поиск заявок…"
                className="pl-11 pr-4 py-3.5 w-72 rounded-2xl bg-[var(--hover-1)] border border-[var(--border-color)]
                           text-[var(--text-primary)] text-[15px] placeholder:text-[var(--text-muted)]
                           focus:outline-none focus:border-[var(--accent)] focus:bg-[var(--hover-1)]
                           transition-all"
              />
            </div>
            <button
              onClick={() => navigate('/tickets/new')}
              className="btn-primary py-3.5 px-6 text-[15px] font-semibold gap-2 group rounded-2xl"
            >
              <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
              Создать заявку
            </button>
          </div>
        </div>
      </div>

      {/* 
          STAT CARDS со спарклайнами
           */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Всего заявок', value: stats.total, icon: FileText,
            iconBg: 'bg-[var(--info)]/8', iconColor: 'text-[var(--info)]',
            color: '#8b5cf6', sub: `${stats.new} новых на этой неделе`,
            trend: stats.new > 0 ? { val: stats.new, up: true } : null,
          },
          {
            label: 'В работе', value: stats.inProgress, icon: Timer,
            iconBg: 'bg-[var(--info)]/8', iconColor: 'text-[var(--info)]',
            color: '#3b82f6', sub: 'активных задач',
            trend: stats.new > 0 ? { val: stats.new, up: true } : null,
          },
          {
            label: 'Критических', value: stats.critical, icon: Flame,
            iconBg: 'bg-[var(--accent-soft)]', iconColor: 'text-[var(--accent)]',
            color: '#ef4444', sub: stats.waiting > 0 ? `${stats.waiting} ждут ответа` : 'нет критичных',
            trend: stats.critical > 0 ? { val: stats.critical, up: false } : null,
          },
          {
            label: 'Решено', value: stats.resolved, icon: CheckCircle2,
            iconBg: 'bg-[var(--success)]/8', iconColor: 'text-[var(--success)]',
            color: '#10b926', sub: `${resolvePct}% выполнения`,
            trend: resolvePct > 50 ? { val: resolvePct, up: true } : null,
          },
        ].map((card, idx) => (
          <div
            key={card.label}
            className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)]
                       p-5 hover:border-[var(--border-hover)] transition-all duration-300
                        group"
            style={{ animationDelay: `${idx * 80}ms` }}
          >
            <GridBackground variant="grid" />

            <div className="relative z-10">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-11 h-11 rounded-xl ${card.iconBg} flex items-center justify-center
                                ring-1 ring-[var(--border-color)]`}>
                  <card.icon className={`w-5 h-5 ${card.iconColor}`} />
                </div>
                {card.trend && (
                  <span className={`flex items-center gap-1 text-[13px] font-semibold tabular-nums
                                    px-2 py-1 rounded-lg ${
                    card.trend.up
                      ? 'text-[var(--success)] bg-[var(--success)]/8'
                      : 'text-[var(--accent)] bg-[var(--accent-soft)]'
                  }`}>
                    {card.trend.up
                      ? <TrendingUp className="w-3 h-3" />
                      : <TrendingDown className="w-3 h-3" />}
                    {card.trend.val}
                  </span>
                )}
              </div>

              <p className="text-4xl font-bold text-[var(--text-primary)] mb-1 tabular-nums leading-none">
                {card.value}
              </p>
              <p className="text-[15px] text-[var(--text-primary)]/50 font-medium mb-1">{card.label}</p>
              <p className="text-[13px] text-[var(--text-primary)]/30 mb-3">{card.sub}</p>

              {/* Sparkline */}
              <div className="h-8 -mx-1">
                <Sparkline data={buildSparkData(card.value)} color={card.color} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 
          АНАЛИТИЧЕСКИЙ БЛОК — донат + бар-чарт
           */}
      <div className="grid lg:grid-cols-3 gap-6">

        {/* DONUT — распределение по статусам */}
        <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)] p-6">
          <GridBackground variant="dots" />
          <div className="relative z-10">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-[17px] font-bold text-[var(--text-primary)] mb-1">Структура заявок</h3>
                <p className="text-[15px] text-[var(--text-primary)]/40">по статусам</p>
              </div>
              <div className="w-9 h-9 rounded-lg bg-[var(--hover-1)] flex items-center justify-center">
                <Activity className="w-4 h-4 text-[var(--text-primary)]/40" />
              </div>
            </div>

            {donutSegments.length > 0 ? (
              <div className="flex items-center gap-6">
                <DonutChart segments={donutSegments} size={150} />
                <div className="flex-1 space-y-2.5">
                  {donutSegments.map(seg => {
                    const pct = Math.round((seg.value / stats.total) * 100);
                    return (
                      <div key={seg.label} className="flex items-center gap-3">
                        <div
                          className="w-3 h-3 rounded-sm flex-shrink-0"
                          style={{ backgroundColor: seg.color }}
                        />
                        <span className="text-[15px] text-[var(--00b10ftext-primary)]/70 flex-1 truncate">{seg.label}</span>
                        <span className="text-[15px] font-semibold text-[var(--text-primary)] tabular-nums">{seg.value}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="h-[150px] flex items-center justify-center text-[var(--text-primary)]/30 text-[15px]">
                Нет данных для отображения
              </div>
            )}
          </div>
        </div>

        {/* BAR CHART — активность за неделю */}
        <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)] p-6 lg:col-span-2">
          <GridBackground variant="grid" />
          <div className="relative z-10">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-[17px] font-bold text-[var(--text-primary)] mb-1">Активность за неделю</h3>
                <p className="text-[15px] text-[var(--text-primary)]/40">созданные заявки по дням</p>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--hover-1)]">
                <BarChart3 className="w-4 h-4 text-[var(--text-primary)]/40" />
                <span className="text-[15px] font-semibold text-[var(--text-primary)] tabular-nums">
                  {ticketsLast7Days.reduce((s, d) => s + d.value, 0)}
                </span>
                <span className="text-[13px] text-[var(--text-primary)]/40">за 7 дней</span>
              </div>
            </div>

            <BarChart data={ticketsLast7Days} />
          </div>
        </div>
      </div>

      {/* 
          ОСНОВНОЙ КОНТЕНТ
           */}
      <div className="grid lg:grid-cols-3 gap-6">

        {/* ── ЛЕВАЯ КОЛОНКА ── */}
        <div className="lg:col-span-2 space-y-6">

          {/* Последние заявки */}
          <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)]">
            <GridBackground variant="dots" />
            <div className="relative z-10">
              <div className="px-6 py-5 border-b border-[var(--border-color)] flex items-center justify-between">
                <h2 className="text-[17px] font-bold text-[var(--text-primary)] flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-[var(--accent-soft)] flex items-center justify-center
                                  ring-1 ring-[var(--accent)]/10">
                    <Ticket className="w-4 h-4 text-[var(--accent)]" />
                  </div>
                  Последние заявки
                  {tickets.length > 0 && (
                    <span className="ml-1 px-2.5 py-0.5 rounded-full bg-[var(--hover-1)] text-[13px] text-[var(--text-primary)]/50 tabular-nums">
                      {tickets.length}
                    </span>
                  )}
                </h2>
                <Link to="/tickets"
                  className="text-[var(--accent)] hover:text-[var(--accent)] flex items-center gap-1.5 text-[15px] font-medium
                             transition-colors group/link">
                  Все заявки
                  <ArrowRight className="w-4 h-4 group-hover/link:translate-x-0.5 transition-transform" />
                </Link>
              </div>

              {tickets.length === 0 ? (
                <div className="p-14 text-center">
                  <div className="w-20 h-20 rounded-2xl bg-[var(--hover-1)] flex items-center justify-center mx-auto mb-5">
                    <FileText className="w-10 h-10 text-[var(--text-primary)]/15" />
                  </div>
                  <p className="text-[var(--text-primary)]/70 text-[17px] font-semibold mb-2">Заявок пока нет</p>
                  <p className="text-[var(--text-primary)]/40 text-[15px] mb-6 max-w-xs mx-auto">
                    Создайте первую заявку, чтобы начать работу с системой поддержки
                  </p>
                  <button
                    onClick={() => navigate('/tickets/new')}
                    className="btn-primary inline-flex items-center gap-2 px-6 py-3 rounded-xl
                               text-white text-[15px] font-medium transition-all shadow-lg shadow-[var(--shadow-lg)]
                               hover:shadow-[var(--shadow-lg)] "
                  >
                    <Sparkles className="w-4 h-4" /> Создать первую заявку
                  </button>
                </div>
              ) : (
                <div className="divide-y divide-[var(--border-color)]">
                  {tickets.slice(0, 6).map(ticket => (
                    <Link
                      key={ticket.id}
                      to={`/tickets/${ticket.number}`}
                      className="flex items-center gap-4 px-6 py-4 hover:bg-[var(--hover-1)]
                                 transition-all duration-200 group relative"
                    >
                      {/* Цветная полоска приоритета слева */}
                      <div className={`absolute left-0 top-3 bottom-3 w-1 rounded-r-full ${priorityBar(ticket.priority)}
                                      opacity-60 group-hover:opacity-100 transition-opacity`} />

                      <div className="flex-1 min-w-0 pl-2">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[15px] font-medium text-[var(--text-primary)] truncate
                                          group-hover:text-[var(--accent)] transition-colors">
                            {ticket.title}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[var(--text-primary)]/50 font-mono text-[13px]">#{ticket.number}</span>
                          <span className={`px-2 py-0.5 rounded-md text-[13px] font-medium border ${statusClr(ticket.status)}`}>
                            {ticket.status}
                          </span>
                          <span className={`px-2 py-0.5 rounded-md text-[13px] font-medium border ${priorityClr(ticket.priority)}`}>
                            {ticket.priority}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 flex-shrink-0">
                        <div className="text-right">
                          <p className="text-[13px] text-[var(--text-primary)]/40">{fmtDate(ticket.created_at)}</p>
                          <p className="text-[13px] text-[var(--text-primary)]/25">{fmtTime(ticket.created_at)}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-[var(--text-primary)]/15 group-hover:text-[var(--accent)]
                                                group-hover:translate-x-0.5 transition-all" />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Проекты */}
          <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)]">
            <GridBackground variant="grid" />
            <div className="relative z-10">
              <div className="px-6 py-5 border-b border-[var(--border-color)] flex items-center justify-between">
                <h2 className="text-[17px] font-bold text-[var(--text-primary)] flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-[var(--status-open-bg)] flex items-center justify-center
                                  ring-1 ring-[var(--status-open-border)]">
                    <FolderOpen className="w-4 h-4 text-[var(--status-open-text)]" />
                  </div>
                  Проекты
                  {projects.length > 0 && (
                    <span className="ml-1 px-2.5 py-0.5 rounded-full bg-[var(--hover-1)] text-[13px] text-[var(--text-primary)]/50">
                      {projects.length}
                    </span>
                  )}
                </h2>
                <Link to="/projects"
                  className="text-[var(--accent)] hover:text-[var(--accent)] flex items-center gap-1.5 text-[15px] font-medium
                             transition-colors group/link">
                  Все проекты
                  <ArrowRight className="w-4 h-4 group-hover/link:translate-x-0.5 transition-transform" />
                </Link>
              </div>

              {projects.length === 0 ? (
                <div className="p-12 text-center">
                  <div className="w-16 h-16 rounded-2xl bg-[var(--hover-1)] flex items-center justify-center mx-auto mb-4">
                    <FolderOpen className="w-8 h-8 text-[var(--text-primary)]/15" />
                  </div>
                  <p className="text-[var(--text-primary)]/40 text-[15px]">Проектов пока нет</p>
                </div>
              ) : (
                <div className="grid sm:grid-cols-2 gap-px bg-[var(--hover-1)]">
                  {projects.slice(0, 4).map(proj => (
                    <Link
                      key={proj.id}
                      to={`/projects/${proj.id}`}
                      className=" p-5 hover:bg-[var(--hover-1)] transition-all group"
                    >
                      <div className="flex items-start gap-3.5">
                        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[var(--status-open-bg)] to-[var(--status-agreement-bg)]
                                        flex items-center justify-center flex-shrink-0
                                        ring-1 ring-[var(--status-open-border)]
                                        group-hover:ring-[var(--status-open-text)]/30 transition-all">
                          <FolderOpen className="w-5 h-5 text-[var(--status-open-text)]/70 group-hover:text-[var(--status-open-text)] transition-colors" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[15px] font-semibold text-[var(--text-primary)] truncate mb-1
                                       group-hover:text-[var(--accent)] transition-colors">
                            {proj.name}
                          </p>
                          <div className="flex items-center gap-2 mb-2">
                            <span className="font-mono text-[13px] text-[var(--text-primary)]/50">{proj.key}</span>
                            <span className={`text-[13px] px-1.5 py-0.5 rounded font-medium border ${
                              proj.status === 'active'
                                ? 'status-resolved'
                                : 'status-closed'
                            }`}>
                              {proj.status === 'active' ? 'Активен' : 'Архив'}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 text-[13px] text-[var(--text-primary)]/30">
                            <Users className="w-3.5 h-3.5" />
                            {proj.memberships?.length ?? 0} участников
                          </div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Контрагенты (support) */}
          {isSupport && counterparties.length > 0 && (
            <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)]">
              <GridBackground variant="dots" />
              <div className="relative z-10">
                <div className="px-6 py-5 border-b border-[var(--border-color)] flex items-center justify-between">
                  <h2 className="text-[17px] font-bold text-[var(--text-primary)] flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-[var(--status-waiting-bg)] flex items-center justify-center
                                    ring-1 ring-[var(--status-waiting-border)]">
                      <Building2 className="w-4 h-4 text-[var(--status-waiting-text)]" />
                    </div>
                    Контрагенты
                  </h2>
                  <Link to="/counterparties"
                    className="text-[var(--accent)] hover:text-[var(--accent)] flex items-center gap-1.5 text-[15px] font-medium
                               transition-colors group/link">
                    Все
                    <ArrowRight className="w-4 h-4 group-hover/link:translate-x-0.5 transition-transform" />
                  </Link>
                </div>
                <div className="divide-y divide-[var(--border-color)]">
                  {counterparties.slice(0, 4).map(cp => (
                    <Link
                      key={cp.id}
                      to={`/counterparties/${cp.id}`}
                      className="flex items-center gap-4 px-6 py-4 hover:bg-[var(--hover-1)] transition-all group"
                    >
                      <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[var(--status-waiting-bg)] to-[var(--status-progress-bg)]
                                      flex items-center justify-center flex-shrink-0
                                      ring-1 ring-[var(--status-waiting-border)]">
                        <Building2 className="w-5 h-5 text-[var(--status-waiting-text)]/70" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[15px] font-medium text-[var(--text-primary)] truncate
                                      group-hover:text-[var(--accent)] transition-colors">
                          {cp.name}
                        </p>
                        <p className="text-[13px] text-[var(--text-primary)]/50 truncate">
                          {cp.legal_name}
                          {cp.inn && <span className="ml-2 font-mono">ИНН {cp.inn}</span>}
                        </p>
                      </div>
                      <span className={`text-[13px] px-2.5 py-1 rounded-lg font-medium flex-shrink-0 border ${
                        cp.is_active
                          ? 'status-resolved'
                          : 'status-closed'
                      }`}>
                        {cp.is_active ? 'Активен' : 'Неактивен'}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── ПРАВАЯ КОЛОНКА ── */}
        <div className="space-y-5">

          {/* KPI / Производительность */}
          <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)] p-5">
            <GridBackground variant="dots" />
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <p className="text-[17px] font-bold text-[var(--text-primary)]">Производительность</p>
                  <p className="text-[13px] text-[var(--text-primary)]/40 mt-0.5">за всё время</p>
                </div>
                <div className="w-9 h-9 rounded-lg bg-[var(--status-resolved-bg)] flex items-center justify-center
                                ring-1 ring-[var(--status-resolved-border)]">
                  <Zap className="w-4 h-4 text-[var(--status-resolved-text)]" />
                </div>
              </div>

              {/* Прогресс-бар выполнения */}
              <div className="mb-5">
                <div className="flex items-baseline justify-between mb-2">
                  <span className="text-[15px] text-[var(--text-primary)]/50">Решено заявок</span>
                  <span className="text-2xl font-bold text-[var(--text-primary)] tabular-nums">
                    {resolvePct}<span className="text-[15px] text-[var(--text-primary)]/40">%</span>
                  </span>
                </div>
                <div className="h-2 bg-[var(--hover-1)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[var(--status-resolved-text)] to-[var(--priority-low-text)] rounded-full
                               transition-all duration-700 ease-out"
                    style={{ width: `${resolvePct}%` }}
                  />
                </div>
                <p className="text-[13px] text-[var(--text-primary)]/30 mt-2">
                  {stats.resolved} из {stats.total} заявок
                </p>
              </div>

              {/* Мини-метрики */}
              <div className="grid grid-cols-2 gap-3 pt-4 border-t border-[var(--border-color)]">
                <div>
                  <p className="text-[13px] text-[var(--text-primary)]/40 mb-1">Открытых</p>
                  <p className="text-xl font-bold text-[var(--text-primary)] tabular-nums">
                    {stats.total - stats.resolved}
                  </p>
                </div>
                <div>
                  <p className="text-[13px] text-[var(--text-primary)]/40 mb-1">В ожидании</p>
                  <p className="text-xl font-bold text-[var(--text-primary)] tabular-nums">{stats.waiting}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Карточка контрагента (клиент) */}
          {isCustomer && counterparty && (
            <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)]">
              <div className="h-24 bg-gradient-to-br from-[var(--accent)]/20 via-[var(--accent)]/10 to-transparent
                              relative overflow-hidden">
                <GridBackground variant="grid" />
                <div className="absolute bottom-0 left-5 translate-y-1/2 z-10">
                  <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)]
                                  flex items-center justify-center shadow-xl shadow-red-900/30
                                  ring-4 ring-[var(--bg-primary)]">
                    <Building2 className="w-7 h-7 text-white" />
                  </div>
                </div>
              </div>

              <div className="px-5 pt-10 pb-5">
                <p className="text-[17px] font-bold text-[var(--text-primary)]">{counterparty.name}</p>
                <p className="text-[13px] text-[var(--text-primary)]/40 mb-4">{counterparty.counterparty_type}</p>

                <div className="space-y-3 text-[15px]">
                  <div className="flex justify-between items-center">
                    <span className="text-[var(--text-primary)]/40">ИНН</span>
                    <span className="text-[var(--text-primary)]/80 font-mono text-[13px] bg-[var(--hover-1)] px-2 py-1 rounded-md">
                      {counterparty.inn}
                    </span>
                  </div>
                  {(counterparty as any).contact_person && (
                    <div className="flex justify-between items-center">
                      <span className="text-[var(--text-primary)]/40">Контакт</span>
                      <span className="text-[var(--text-primary)]/80 text-[15px]">
                        {(counterparty as any).contact_person.full_name}
                      </span>
                    </div>
                  )}
                </div>

                <Link to="/my-company"
                  className="mt-5 w-full flex items-center justify-center gap-2 py-3 rounded-xl
                             bg-[var(--hover-1)] hover:bg-[var(--hover-1)] text-[var(--text-primary)]/70 hover:text-[var(--text-primary)]
                             text-[15px] font-medium transition-all">
                  Подробнее <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}

          {/* Быстрые действия */}
          <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)] p-5">
            <GridBackground variant="dots" />
            <div className="relative z-10">
              <p className="text-[15px] uppercase tracking-[0.12em] text-[var(--text-primary)]/35 font-bold mb-4">
                Быстрые действия
              </p>
              <div className="space-y-2">
                {[
                  {
                    label: 'Новая заявка', desc: 'Создать обращение',
                    icon: Plus, to: '/tickets/new', accent: true,
                  },
                  { label: 'Мои заявки', desc: 'Просмотреть все', icon: FileText, to: '/tickets' },
                  { label: 'Проекты', desc: 'Все проекты', icon: FolderOpen, to: '/projects' },
                  ...(isSupport ? [
                    { label: 'Контрагенты', desc: 'Управление', icon: Building2, to: '/counterparties' },
                    { label: 'Продукты', desc: `${productsCount} в справочнике`, icon: Package, to: '/products' },
                  ] : []),
                ].map(action => (
                  <Link
                    key={action.to}
                    to={action.to}
                    className={`flex items-center gap-3.5 p-3 rounded-xl transition-all group/action ${
                      (action as any).accent
                        ? 'bg-[var(--accent-soft)]  '
                        : 'bg-[var(--hover-1)] hover:bg-[var(--hover-2)]'
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all
                                    group-hover/action:scale-105 ${
                      (action as any).accent
                        ? 'bg-[var(--accent-soft)] ring-1 ring-[var(--accent)]/20'
                        : 'bg-[var(--hover-2)] group-hover/action:bg-[var(--hover-3)]'
                    }`}>
                      <action.icon className={`w-5 h-5 ${
                        (action as any).accent ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]/50 group-hover/action:text-[var(--text-primary)]/80'
                      }`} />
                    </div>
                    <div className="flex-1">
                      <p className="text-[15px] font-medium text-[var(--text-primary)]">{action.label}</p>
                      <p className="text-[13px] text-[var(--text-primary)]/35">{action.desc}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-[var(--text-primary)]/15 group-hover/action:text-[var(--text-primary)]/40
                                            group-hover/action:translate-x-0.5 transition-all" />
                  </Link>
                ))}
              </div>
            </div>
          </div>

          {/* Сводка (support) */}
          {isSupport && (
            <div className="relative overflow-hidden glass-card rounded-2xl border border-[var(--border-color)] p-5">
              <GridBackground variant="grid" />
              <div className="relative z-10">
                <p className="text-[15px] uppercase tracking-[0.12em] text-[var(--text-primary)]/35 font-bold mb-4">
                  Сводка системы
                </p>
                <div className="space-y-1">
                  {[
                    { label: 'Контрагентов', value: counterparties.length, icon: Building2,
                      color: 'text-[var(--status-waiting-text)]', bg: 'bg-[var(--status-waiting-bg)]', ring: 'ring-[var(--status-waiting-border)]' },
                    { label: 'Проектов', value: projects.length, icon: FolderOpen,
                      color: 'text-[var(--status-open-text)]', bg: 'bg-[var(--status-open-bg)]', ring: 'ring-[var(--status-open-border)]' },
                    { label: 'Продуктов', value: productsCount, icon: Package,
                      color: 'text-[var(--status-agreement-text)]', bg: 'bg-[var(--status-agreement-bg)]', ring: 'ring-[var(--status-agreement-border)]' },
                  ].map(row => (
                    <div key={row.label}
                      className="flex items-center justify-between py-3 px-1 rounded-lg hover:bg-[var(--hover-1)] transition-colors">
                      <span className="flex items-center gap-3 text-[15px] text-[var(--text-primary)]/60">
                        <div className={`w-8 h-8 rounded-lg ${row.bg} flex items-center justify-center ring-1 ${row.ring}`}>
                          <row.icon className={`w-4 h-4 ${row.color}`} />
                        </div>
                        {row.label}
                      </span>
                      <span className="text-[17px] font-bold text-[var(--text-primary)] tabular-nums">{row.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          
        </div>
      </div>
    </div>
  );
}