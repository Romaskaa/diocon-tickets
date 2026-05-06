import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText, Clock, AlertTriangle, CheckCircle2, Plus, ArrowRight,
  Building2, TrendingUp, Users, Loader2, FolderOpen, Package,
  Ticket, Hash, ChevronRight, Activity,
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { ticketsApi, counterpartiesApi, projectsApi, productsApi } from '../api/client';
import type { TicketListItem, Counterparty, Project } from '../types';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [tickets, setTickets]             = useState<TicketListItem[]>([]);
  const [counterparty, setCounterparty]   = useState<Counterparty | null>(null);
  const [projects, setProjects]           = useState<Project[]>([]);
  const [counterparties, setCounterparties] = useState<Counterparty[]>([]);
  const [productsCount, setProductsCount] = useState(0);
  const [loading, setLoading]             = useState(true);

  const isCustomer = user?.role === 'customer' || user?.role === 'customer_admin';
  const isSupport  = ['admin', 'support_manager', 'support_agent'].includes(user?.role ?? '');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [ticketsRes] = await Promise.all([
        ticketsApi.getMy(1, 100),
      ]);
      setTickets(ticketsRes.items);

      // Контрагент текущего клиента
      if (isCustomer && user?.counterparty_id) {
        counterpartiesApi.getById(user.counterparty_id)
          .then(cp => setCounterparty(cp))
          .catch(() => {});
      }

      // Проекты (мои или все)
      const projectsRes = isCustomer
        ? await projectsApi.getMyProjects('all', 1, 5).catch(() => ({ items: [] }))
        : await projectsApi.getAll(1, 5).catch(() => ({ items: [] }));
      setProjects(projectsRes.items ?? []);

      // Контрагенты (для support)
      if (isSupport) {
        counterpartiesApi.getAll(1, 5)
          .then(res => setCounterparties(res.items ?? []))
          .catch(() => {});
      }

      // Продукты — только количество
      productsApi.getProducts({ page: 1, size: 1 })
        .then(res => setProductsCount(res.total_items ?? 0))
        .catch(() => {});

    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  };

  // ── Статистика ────────────────────────────────────────────────────────

  const stats = {
    total:      tickets.length,
    new:        tickets.filter(t => t.status === 'Новый').length,
    inProgress: tickets.filter(t => t.status === 'В работе' || t.status === 'Открыт').length,
    critical:   tickets.filter(t => t.priority === 'Критический').length,
    resolved:   tickets.filter(t => t.status === 'Решён' || t.status === 'Закрыт').length,
    waiting:    tickets.filter(t => t.status === 'Ожидает ответа').length,
  };

  // ── Форматирование ────────────────────────────────────────────────────

  const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });

  const statusClr = (s: string) => ({
    'Новый':          'bg-blue-500/15 text-blue-400',
    'Открыт':         'bg-cyan-500/15 text-cyan-400',
    'В работе':       'bg-yellow-500/15 text-yellow-400',
    'Ожидает ответа': 'bg-orange-500/15 text-orange-400',
    'Решён':          'bg-emerald-500/15 text-emerald-400',
    'Закрыт':         'bg-neutral-500/15 text-neutral-400',
    'Переоткрыт':     'bg-red-500/15 text-red-400',
  }[s] ?? 'bg-white/5 text-white/50');

  const priorityClr = (p: string) => ({
    'Критический': 'bg-red-500/15 text-red-400',
    'Высокий':     'bg-orange-500/15 text-orange-400',
    'Средний':     'bg-yellow-500/15 text-yellow-400',
    'Низкий':      'bg-emerald-500/15 text-emerald-400',
  }[p] ?? 'bg-white/5 text-white/50');

  // ── Loading ───────────────────────────────────────────────────────────

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
    </div>
  );

  return (
    <div className="space-y-8">

      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-1.5">
            {user?.full_name || user?.username || 'Главная'}
          </h1>
          <p className="text-base text-white/50">
            {isCustomer ? 'Ваши заявки и проекты' : 'Обзор системы поддержки'}
          </p>
        </div>
        <button
          onClick={() => navigate('/tickets/new')}
          className="btn-primary py-4 px-8 text-[16px] font-semibold"
        >
          <Plus className="w-5 h-5" />
          Создать заявку
        </button>
      </div>

      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Всего заявок',  value: stats.total,      icon: FileText,     iconColor: 'text-white',    extra: null },
          { label: 'В работе',      value: stats.inProgress,  icon: Clock,        iconColor: 'text-blue-400',    extra: stats.new > 0 ? `+${stats.new} новых` : null },
          { label: 'Критических',   value: stats.critical,    icon: AlertTriangle,iconColor: 'text-red-400',  extra: stats.waiting > 0 ? `${stats.waiting} ждут ответа` : null },
          { label: 'Решено',        value: stats.resolved,    icon: CheckCircle2, iconColor: 'text-emerald-400', extra: stats.total > 0 ? `${Math.round((stats.resolved / stats.total) * 100)}%` : null },
        ].map(card => (
          <div key={card.label}
               className="glass-card rounded-2xl border border-white/[0.08] p-5 hover:border-white/[0.12] transition-colors">
            <div className="flex items-center justify-between mb-4">
              <div className="w-11 h-11 rounded-xl bg-white/[0.06] flex items-center justify-center">
                <card.icon className={`w-5 h-5 ${card.iconColor}`} />
              </div>
              {card.extra && (
                <span className="text-l text-white/30">{card.extra}</span>
              )}
            </div>
            <p className="text-3xl font-bold text-white mb-1">{card.value}</p>
            <p className="text-base text-white/40">{card.label}</p>
          </div>
        ))}
      </div>

      {/* ── Main Content ── */}
      <div className="grid lg:grid-cols-3 gap-6">

        {/* ── Левая колонка (2/3) ── */}
        <div className="lg:col-span-2 space-y-6">

          {/* Последние заявки */}
          <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
            <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between">
              <h2 className="text-xl font-bold text-white flex items-center gap-2.5">
                <Ticket className="w-5 h-5 text-white/40" />
                Последние заявки
              </h2>
              <Link to="/tickets"
                    className="text-red-400 hover:text-red-300 flex items-center gap-1.5 text-base font-medium transition-colors">
                Все заявки <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            {tickets.length === 0 ? (
              <div className="p-12 text-center">
                <FileText className="w-14 h-14 text-white/10 mx-auto mb-4" />
                <p className="text-white/50 text-base font-semibold mb-1">Нет заявок</p>
                <p className="text-white/30 text-l mb-5">Создайте первую заявку для начала работы</p>
                <button onClick={() => navigate('/tickets/new')}
                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-800 hover:bg-red-700
                                   text-white text-base font-medium transition-colors">
                  <Plus className="w-4 h-4" /> Создать заявку
                </button>
              </div>
            ) : (
              <div className="divide-y divide-white/[0.05]">
                {tickets.slice(0, 5).map(ticket => (
                  <Link key={ticket.id} to={`/tickets/${ticket.number}`}
                        className="flex items-start justify-between gap-4 px-6 py-4
                                   hover:bg-white/[0.03] transition-colors group">
                    <div className="flex-1 min-w-0">
                      <p className="text-base font-medium text-white mb-2 truncate
                                    group-hover:text-red-400 transition-colors">
                        {ticket.title}
                      </p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-red-400/70 font-mono text-sm">#{ticket.number}</span>
                        <span className={`px-2 py-0.5 rounded-md text-l font-medium ${statusClr(ticket.status)}`}>
                          {ticket.status}
                        </span>
                        <span className={`px-2 py-0.5 rounded-md text-l font-medium ${priorityClr(ticket.priority)}`}>
                          {ticket.priority}
                        </span>
                      </div>
                    </div>
                    <span className="text-l text-white/30 flex-shrink-0">{fmtDate(ticket.created_at)}</span>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Проекты */}
          <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
            <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between">
              <h2 className="text-xl font-bold text-white flex items-center gap-2.5">
                <FolderOpen className="w-5 h-5 text-white/40" />
                Проекты
                {projects.length > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-white/[0.08] text-l text-white/50">
                    {projects.length}
                  </span>
                )}
              </h2>
              <Link to="/projects"
                    className="text-red-400 hover:text-red-300 flex items-center gap-1.5 text-base font-medium transition-colors">
                Все проекты <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            {projects.length === 0 ? (
              <div className="p-10 text-center">
                <FolderOpen className="w-12 h-12 text-white/10 mx-auto mb-3" />
                <p className="text-white/40 text-base">Нет проектов</p>
              </div>
            ) : (
              <div className="divide-y divide-white/[0.05]">
                {projects.slice(0, 4).map(proj => (
                  <Link key={proj.id} to={`/projects/${proj.id}`}
                        className="flex items-center gap-4 px-6 py-4
                                   hover:bg-white/[0.03] transition-colors group">
                    <div className="w-10 h-10 rounded-xl bg-white/[0.06] flex items-center justify-center flex-shrink-0">
                      <FolderOpen className="w-5 h-5 text-white/30 group-hover:text-white/50 transition-colors" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-base font-medium text-white truncate group-hover:text-red-400 transition-colors">
                          {proj.name}
                        </span>
                        <span className={`text-l px-1.5 py-0.5 rounded font-medium ${
                          proj.status === 'active'
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : 'bg-white/[0.06] text-white/40'
                        }`}>
                          {proj.status === 'active' ? 'Активен' : 'Архив'}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-l text-white/30">
                        <span className="font-mono">{proj.key}</span>
                        <span>· {proj.memberships?.length ?? 0} участников</span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/15 group-hover:text-red-400
                                             group-hover:translate-x-0.5 transition-all flex-shrink-0" />
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Контрагенты (для support) */}
          {isSupport && counterparties.length > 0 && (
            <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between">
                <h2 className="text-xl font-bold text-white flex items-center gap-2.5">
                  <Building2 className="w-5 h-5 text-white/40" />
                  Контрагенты
                </h2>
                <Link to="/counterparties"
                      className="text-red-400 hover:text-red-300 flex items-center gap-1.5 text-base font-medium transition-colors">
                  Все <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
              <div className="divide-y divide-white/[0.05]">
                {counterparties.slice(0, 4).map(cp => (
                  <Link key={cp.id} to={`/counterparties/${cp.id}`}
                        className="flex items-center gap-4 px-6 py-4
                                   hover:bg-white/[0.03] transition-colors group">
                    <div className="w-10 h-10 rounded-xl bg-white/[0.06] flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-5 h-5 text-white/30" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-base font-medium text-white truncate group-hover:text-red-400 transition-colors">
                        {cp.name}
                      </p>
                      <p className="text-l text-white/30 truncate">
                        {cp.legal_name}
                        {cp.inn && <span className="ml-2 font-mono">· ИНН {cp.inn}</span>}
                      </p>
                    </div>
                    <span className={`text-l px-2 py-0.5 rounded-md font-medium flex-shrink-0 ${
                      cp.is_active
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : 'bg-white/[0.06] text-white/40'
                    }`}>
                      {cp.is_active ? 'Активен' : 'Неактивен'}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Правая колонка (1/3) ── */}
        <div className="space-y-5">

          {/* Карточка контрагента для клиента */}
          {isCustomer && counterparty && (
            <div className="glass-card rounded-2xl border border-white/[0.08] p-5">
              <div className="flex items-center gap-3.5 mb-5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-800 to-red-700
                                flex items-center justify-center shadow-md shadow-red-900/20">
                  <Building2 className="w-6 h-6 text-white" />
                </div>
                <div className="min-w-0">
                  <p className="text-base font-bold text-white truncate">{counterparty.name}</p>
                  <p className="text-l text-white/40">{counterparty.counterparty_type}</p>
                </div>
              </div>
              <div className="space-y-2.5 text-base">
                <div className="flex justify-between">
                  <span className="text-white/40">ИНН</span>
                  <span className="text-white/80 font-mono">{counterparty.inn}</span>
                </div>
                {(counterparty as any).contact_person && (
                  <div className="flex justify-between">
                    <span className="text-white/40">Контакт</span>
                    <span className="text-white/80">{(counterparty as any).contact_person.full_name}</span>
                  </div>
                )}
              </div>
              <Link to="/my-company"
                    className="mt-5 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl
                               bg-white/[0.06] hover:bg-white/[0.09] text-white/70 text-base font-medium transition-colors">
                Подробнее <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}

          {/* Быстрые действия */}
          <div className="glass-card rounded-2xl border border-white/[0.08] p-5">
            <p className="text-l uppercase tracking-widest text-white/30 mb-4">Быстрые действия</p>
            <div className="space-y-2.5">
              {[
                { label: 'Новая заявка',    desc: 'Создать обращение',    icon: Plus,       to: '/tickets/new', accent: true },
                { label: 'Мои заявки',       desc: 'Просмотреть все',      icon: FileText,   to: '/tickets' },
                { label: 'Проекты',          desc: 'Все проекты',          icon: FolderOpen,  to: '/projects' },
                ...(isSupport
                  ? [
                      { label: 'Контрагенты',    desc: 'Управление',           icon: Building2, to: '/counterparties' },
                      { label: 'Продукты',        desc: `${productsCount} в справочнике`, icon: Package,   to: '/products' },
                    ]
                  : []
                ),
              ].map(action => (
                <Link key={action.to} to={action.to}
                      className={`flex items-center gap-3.5 p-3.5 rounded-xl transition-colors ${
                        (action as any).accent
                          ? 'bg-red-800/15 hover:bg-red-800/25'
                          : 'bg-white/[0.03] hover:bg-white/[0.06]'
                      }`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    (action as any).accent ? 'bg-red-800/25' : 'bg-white/[0.06]'
                  }`}>
                    <action.icon className={`w-5 h-5 ${(action as any).accent ? 'text-red-400' : 'text-white/40'}`} />
                  </div>
                  <div>
                    <p className="text-base font-medium text-white">{action.label}</p>
                    <p className="text-l text-white/30">{action.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          

          {/* Сводка (для support) */}
          {isSupport && (
            <div className="glass-card rounded-2xl border border-white/[0.08] p-5">
              <p className="text-l uppercase tracking-widest text-white/30 mb-4">Сводка</p>
              <div className="divide-y divide-white/[0.06]">
                {[
                  { label: 'Контрагентов', value: counterparties.length, icon: Building2 },
                  { label: 'Проектов',     value: projects.length,       icon: FolderOpen },
                  { label: 'Продуктов',    value: productsCount,         icon: Package },
                ].map(row => (
                  <div key={row.label} className="flex items-center justify-between py-3">
                    <span className="flex items-center gap-2 text-base text-white/40">
                      <row.icon className="w-4 h-4" /> {row.label}
                    </span>
                    <span className="text-base font-bold text-white">{row.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}