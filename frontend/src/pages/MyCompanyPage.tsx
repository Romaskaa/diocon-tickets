// pages/MyCompanyPage.tsx
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Building2, Phone, Mail, MapPin, Users,
  Calendar, User, MessageSquare, Loader2, AlertCircle,
  ExternalLink, Crown, GitBranch, Ticket, Clock,
  ChevronRight, Settings, Plus,
  Globe, X, CheckCircle2, UserPlus,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { counterpartiesApi, usersApi, ticketsApi } from '@/api/client';
import type { Counterparty, CounterpartyCustomer, TicketListItem } from '@/types';

type TabType = 'info' | 'contacts' | 'branches' | 'employees' | 'tickets';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getInitials(name?: string | null): string {
  if (!name) return '?';
  return name.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
}

function Avatar({ name, size = 'md' }: { name?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const cls = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-14 h-14 text-base' }[size];
  return (
    <div className={`${cls} rounded-full bg-gradient-to-br from-red-800 to-red-700
                    flex items-center justify-center font-bold text-white flex-shrink-0 select-none`}>
      {getInitials(name)}
    </div>
  );
}

const statusClr = (s: string) => ({
  'Новый':          'bg-blue-500/15 text-blue-400 border-blue-500/30',
  'На согласовании':'bg-purple-500/15 text-purple-400 border-purple-500/30',
  'Открыт':         'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  'В работе':       'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  'Ожидает ответа': 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  'Решён':          'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  'Закрыт':         'bg-neutral-500/15 text-neutral-400 border-neutral-500/30',
  'Переоткрыт':     'bg-red-500/15 text-red-400 border-red-500/30',
}[s] ?? 'bg-white/5 text-white/50 border-white/10');

const priorityClr = (p: string) => ({
  'Низкий':      'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  'Средний':     'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  'Высокий':     'bg-orange-500/15 text-orange-400 border-orange-500/30',
  'Критический': 'bg-red-500/15 text-red-400 border-red-500/30',
}[p] ?? 'bg-white/5 text-white/50 border-white/10');

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });

const fmtDateTime = (d: string) =>
  new Date(d).toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });

const getEmployeeRoleInfo = (role: string) => {
  const roles: Record<string, { label: string; icon: JSX.Element; color: string }> = {
    customer_admin: {
      label: 'Администратор',
      icon: <Crown className="w-3.5 h-3.5" />,
      color: 'bg-red-500/15 text-red-400 border-red-500/30',
    },
    customer: {
      label: 'Сотрудник',
      icon: <User className="w-3.5 h-3.5" />,
      color: 'bg-white/[0.06] text-white/60 border-white/[0.1]',
    },
  };
  return roles[role] || {
    label: 'Пользователь',
    icon: <User className="w-3.5 h-3.5" />,
    color: 'bg-white/[0.06] text-white/50 border-white/[0.1]',
  };
};

// ─── Основной компонент ───────────────────────────────────────────────────────

export default function MyCompanyPage() {
  const { user } = useAuthStore();

  const [company, setCompany] = useState<Counterparty | null>(null);
  const [branches, setBranches] = useState<Counterparty[]>([]);
  const [employees, setEmployees] = useState<CounterpartyCustomer[]>([]);
  const [tickets, setTickets] = useState<TicketListItem[]>([]);
  const [ticketsPage, setTicketsPage] = useState(1);
  const [ticketsTotalPages, setTicketsTotalPages] = useState(1);
  const [ticketsTotalItems, setTicketsTotalItems] = useState(0);

  const [loading, setLoading] = useState(true);
  const [loadingEmployees, setLoadingEmployees] = useState(false);
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('info');
  
  const canViewEmployees = user?.role === 'customer_admin' || user?.role === 'admin';
  const canViewTickets = user?.role === 'customer_admin' || user?.role === 'customer' || user?.role === 'admin';

  // ── Загрузка компании ─────────────────────────────────────────────────────

  useEffect(() => {
    const load = async () => {
      if (!user?.counterparty_id) {
        setError('Вы не привязаны к компании');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const companyData = await counterpartiesApi.getById(user.counterparty_id);
        setCompany(companyData);

        try {
          const all = await counterpartiesApi.getAll(1, 100);
          setBranches(all.items.filter(cp => cp.parent_id === companyData.id));
        } catch {
          setBranches([]);
        }

        setError(null);
      } catch {
        setError('Не удалось загрузить данные компании');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [user?.counterparty_id]);

  // ── Загрузка сотрудников ──────────────────────────────────────────────────

  useEffect(() => {
    if (!canViewEmployees || !company?.id) return;
    if (activeTab !== 'employees' && employees.length > 0) return;

    const load = async () => {
      setLoadingEmployees(true);
      try {
        const res = await usersApi.getCustomers(company.id, 1, 100);
        setEmployees(res.items);
      } catch {
        setEmployees([]);
      } finally {
        setLoadingEmployees(false);
      }
    };

    load();
  }, [canViewEmployees, company?.id, activeTab]);

  // ── Загрузка заявок ───────────────────────────────────────────────────────

  const TICKETS_PER_PAGE = 10;

const loadTickets = useCallback(async (page = 1) => {
  if (!company?.id) return;
  setLoadingTickets(true);
  try {
    const res = await ticketsApi.getAllWithFilters(page, TICKETS_PER_PAGE, {
      counterparty_id: company.id,
    });
    setTickets(res.items);
    setTicketsPage(res.page);
    setTicketsTotalPages(res.total_pages);
    setTicketsTotalItems(res.total_items);
  } catch {
    setTickets([]);
    setTicketsTotalItems(0);
    setTicketsTotalPages(1);
  } finally {
    setLoadingTickets(false);
  }
}, [company?.id]);

// Загружаем общее количество заявок сразу при загрузке компании (для статистики)
useEffect(() => {
  if (company?.id) loadTickets(1);
}, [company?.id, loadTickets]);

// При переключении страницы
useEffect(() => {
  if (activeTab === 'tickets') loadTickets(ticketsPage);
}, [ticketsPage]);

  // ── Tabs ──────────────────────────────────────────────────────────────────

  const hasBranches = branches.length > 0;

  const tabs: { id: TabType; label: string; icon: typeof Building2; count?: number }[] = [
    { id: 'info', label: 'Информация', icon: Building2 },
    { id: 'contacts', label: 'Контактное лицо', icon: User },
  ];

  if (hasBranches) {
    tabs.push({ id: 'branches', label: 'Подразделения', icon: GitBranch, count: branches.length });
  }

  if (canViewEmployees) {
    tabs.push({ id: 'employees', label: 'Сотрудники', icon: Users, count: employees.length });
  }

  if (canViewTickets) {
    tabs.push({ id: 'tickets', label: 'Заявки', icon: Ticket, count: ticketsTotalItems });
  }

  // ── Stats ─────────────────────────────────────────────────────────────────

  const activeTickets = tickets.filter(t => t.status !== 'Закрыт' && t.status !== 'Решён').length;

  // ── Loading / Error ───────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center max-w-md">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">Компания не найдена</h2>
          <p className="text-base text-white/50">{error || 'Вы не привязаны ни к одной компании'}</p>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-8">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-800 to-red-700
                          flex items-center justify-center shadow-lg shadow-red-900/30 flex-shrink-0">
            {company.avatar_url ? (
              <img src={company.avatar_url} alt={company.name}
                   className="w-16 h-16 rounded-2xl object-cover" />
            ) : (
              <Building2 className="w-8 h-8 text-white" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-3 flex-wrap mb-2">
              <h1 className="text-3xl font-bold text-white">{company.name}</h1>
              <span className={`px-3 py-1 rounded-lg text-base font-medium border ${
                company.is_active
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-white/[0.06] text-white/40 border-white/[0.1]'
              }`}>
                {company.is_active ? 'Активен' : 'Неактивен'}
              </span>
              {hasBranches && (
                <span className="px-3 py-1 rounded-lg text-base font-medium
                                 bg-amber-500/15 text-amber-400 border border-amber-500/30">
                  Головная компания
                </span>
              )}
            </div>
            <p className="text-white/50 text-base">{company.legal_name}</p>
          </div>
        </div>

        <Link to="/tickets/new"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                         bg-red-800 hover:bg-red-700 text-white text-base font-medium
                         transition-colors shadow-lg shadow-red-900/30 flex-shrink-0">
          <Plus className="w-4 h-4" />
          Создать заявку
        </Link>
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────────────── */}
      <div className="flex gap-1.5 border-b border-white/[0.08] overflow-x-auto">
        {tabs.map(tab => (
          <button key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-5 py-3 rounded-t-xl transition-all whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'bg-red-800/50 text-white border-b-2 border-red-500'
                      : 'text-white/50 hover:text-white/70 hover:bg-white/[0.04]'
                  }`}>
            <tab.icon className="w-4 h-4" />
            <span className="text-base font-medium">{tab.label}</span>
            {(tab.count ?? 0) > 0 && (
              <span className="ml-0.5 px-2 py-0.5 rounded-full bg-white/[0.1] text-sm">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Content ──────────────────────────────────────────────────────── */}
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">

          {/* ═══ Info ═══ */}
          {activeTab === 'info' && (
            <div className="space-y-6">
              <div className="grid md:grid-cols-2 gap-4">
                {[
                  { label: 'ИНН', value: company.inn },
                  { label: 'КПП', value: company.kpp },
                  { label: 'ОКПО', value: company.okpo },
                  { label: 'Тип', value: company.counterparty_type },
                ].map(field => (
                  <div key={field.label}
                       className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                    <p className="text-xs uppercase tracking-widest text-white/30 mb-2">{field.label}</p>
                    <p className="text-base font-semibold text-white">{field.value || '—'}</p>
                  </div>
                ))}
              </div>

              {company.address && (
                <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-2 flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5" /> Адрес
                  </p>
                  <p className="text-base text-white">{company.address}</p>
                </div>
              )}

              <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                <p className="text-xs uppercase tracking-widest text-white/30 mb-2 flex items-center gap-2">
                  <Calendar className="w-3.5 h-3.5" /> Дата регистрации
                </p>
                <p className="text-base text-white font-medium">{fmtDateTime(company.created_at)}</p>
              </div>

              {/* Статистика */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { icon: GitBranch, value: branches.length, label: 'Подразделений' },
                  { icon: Ticket, value: ticketsTotalItems, label: 'Заявок' },
                  { icon: Clock,     value: activeTickets,   label: 'Активных' },
                ].map(s => (
                  <div key={s.label}
                       className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5 text-center">
                    <s.icon className="w-5 h-5 text-white/30 mx-auto mb-3" />
                    <p className="text-3xl font-bold text-white mb-1">{s.value}</p>
                    <p className="text-sm text-white/40">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ═══ Contacts ═══ */}
          {activeTab === 'contacts' && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-6">
              <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2.5">
                <User className="w-5 h-5 text-white/40" />
                Контактное лицо
              </h3>

              {company.contact_person ? (
                <div>
                  <div className="flex items-center gap-4 mb-6">
                    <Avatar name={company.contact_person.full_name} size="lg" />
                    <div>
                      <p className="text-lg font-bold text-white">{company.contact_person.full_name}</p>
                      <p className="text-base text-white/40">Контактное лицо</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {company.contact_person.phone && (
                      <a href={`tel:${company.contact_person.phone}`}
                         className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03]
                                    hover:bg-white/[0.06] transition-colors">
                        <Phone className="w-5 h-5 text-emerald-400" />
                        <span className="text-base text-white">{company.contact_person.phone}</span>
                      </a>
                    )}
                    {company.contact_person.email && (
                      <a href={`mailto:${company.contact_person.email}`}
                         className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03]
                                    hover:bg-white/[0.06] transition-colors">
                        <Mail className="w-5 h-5 text-red-400" />
                        <span className="text-base text-white">{company.contact_person.email}</span>
                      </a>
                    )}
                    {company.contact_person.messengers?.telegram && (
                      <a href={`https://t.me/${company.contact_person.messengers.telegram}`}
                         target="_blank" rel="noopener noreferrer"
                         className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03]
                                    hover:bg-white/[0.06] transition-colors">
                        <MessageSquare className="w-5 h-5 text-sky-400" />
                        <span className="text-base text-white flex-1">
                          @{company.contact_person.messengers.telegram}
                        </span>
                        <ExternalLink className="w-4 h-4 text-white/20" />
                      </a>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-16">
                  <User className="w-16 h-16 text-white/10 mx-auto mb-4" />
                  <p className="text-white/50 text-base font-semibold mb-1">Не указано</p>
                  <p className="text-white/30 text-sm">Контактное лицо не задано</p>
                </div>
              )}
            </div>
          )}

          {/* ═══ Branches ═══ */}
          {activeTab === 'branches' && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.01]">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <GitBranch className="w-5 h-5 text-amber-400" />
                  Подразделения
                  <span className="px-2 py-0.5 rounded-full bg-white/[0.08] text-sm text-white/50">
                    {branches.length}
                  </span>
                </h2>
              </div>

              <div className="p-6">
                {branches.length === 0 ? (
                  <div className="text-center py-16">
                    <GitBranch className="w-16 h-16 text-white/10 mx-auto mb-4" />
                    <p className="text-white/50 text-base">Нет подразделений</p>
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {branches.map(branch => (
                      <div key={branch.id} className="flex items-center gap-4 py-4 px-2">
                        <div className="w-10 h-10 rounded-xl bg-amber-600/15 flex items-center justify-center flex-shrink-0">
                          <Building2 className="w-5 h-5 text-amber-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-white font-semibold text-base truncate">{branch.name}</p>
                          <p className="text-white/40 text-sm truncate">{branch.legal_name}</p>
                        </div>
                        <div className="text-right text-sm text-white/30 flex-shrink-0">
                          {branch.inn && <p>ИНН {branch.inn}</p>}
                          {branch.kpp && <p>КПП {branch.kpp}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ═══ Employees ═══ */}
          {activeTab === 'employees' && canViewEmployees && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.01]">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <Users className="w-5 h-5 text-white/40" />
                  Сотрудники
                  {employees.length > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-white/[0.08] text-sm text-white/50">
                      {employees.length}
                    </span>
                  )}
                </h2>
              </div>

              <div className="p-6">
                {loadingEmployees ? (
                  <div className="flex justify-center py-16">
                    <Loader2 className="w-8 h-8 animate-spin text-white/20" />
                  </div>
                ) : employees.length === 0 ? (
                  <div className="text-center py-16">
                    <Users className="w-16 h-16 text-white/10 mx-auto mb-4" />
                    <p className="text-white/50 text-base font-semibold mb-1">Пока нет сотрудников</p>
                    <p className="text-white/30 text-sm">
                      Вы можете пригласить коллег через раздел «Приглашения»
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {employees.map(emp => {
                      const roleInfo = getEmployeeRoleInfo(emp.role);
                      const isMe = emp.id === user?.user_id;

                      return (
                        <div key={emp.id}
                             className={`flex items-center gap-4 py-4 px-2 rounded-xl ${
                               isMe ? 'bg-red-500/[0.04]' : ''
                             }`}>
                          <Avatar name={emp.full_name || emp.username} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-white font-semibold text-base truncate">
                                {emp.full_name || emp.username}
                              </span>
                              {isMe && (
                                <span className="text-xs px-2 py-0.5 rounded-full bg-white/[0.08] text-white/50">
                                  Вы
                                </span>
                              )}
                            </div>
                            <p className="text-white/40 text-sm truncate">{emp.email}</p>
                          </div>
                          <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                                           font-medium border flex-shrink-0 ${roleInfo.color}`}>
                            {roleInfo.icon}
                            {roleInfo.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ═══ Tickets ═══ */}
          {activeTab === 'tickets' && canViewTickets && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.01]">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <Ticket className="w-5 h-5 text-white/40" />
                  Заявки
                  {tickets.length > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-white/[0.08] text-sm text-white/50">
                      {tickets.length}
                    </span>
                  )}
                </h2>
                <Link to="/tickets/new"
                      className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-red-800 hover:bg-red-700
                                 text-white text-base font-medium transition-colors shadow-md shadow-red-900/30">
                  <Plus className="w-4 h-4" />
                  Создать
                </Link>
              </div>

              <div className="p-6">
                {loadingTickets ? (
                  <div className="flex justify-center py-16">
                    <Loader2 className="w-8 h-8 animate-spin text-white/20" />
                  </div>
                ) : tickets.length === 0 ? (
                  <div className="text-center py-20">
                    <Ticket className="w-16 h-16 text-white/10 mx-auto mb-4" />
                    <p className="text-white/50 text-base font-semibold mb-1">Нет заявок</p>
                    <p className="text-white/30 text-sm mb-5">
                      У вашей компании пока нет заявок
                    </p>
                    <Link to="/tickets/new"
                          className="text-red-400 hover:text-red-300 transition-colors text-base">
                      Создать первую заявку →
                    </Link>
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {tickets.map(ticket => (
                      <Link key={ticket.id} to={`/tickets/${ticket.number}`}
                            className="flex items-start justify-between gap-4 py-4 px-2
                                       hover:bg-white/[0.03] rounded-xl transition-colors group">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <span className="text-red-400 font-mono text-sm bg-red-500/10
                                             border border-red-500/20 px-2 py-0.5 rounded-lg">
                              #{ticket.number}
                            </span>
                            <span className={`px-2.5 py-0.5 rounded-lg text-sm font-medium border
                                             ${statusClr(ticket.status)}`}>
                              {ticket.status}
                            </span>
                            <span className={`px-2.5 py-0.5 rounded-lg text-sm font-medium border
                                             ${priorityClr(ticket.priority)}`}>
                              {ticket.priority}
                            </span>
                          </div>
                          <p className="text-white font-medium text-base group-hover:text-red-400
                                        transition-colors truncate">
                            {ticket.title}
                          </p>
                          <p className="text-white/30 text-sm mt-1">{fmtDate(ticket.created_at)}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-red-400
                                                 group-hover:translate-x-0.5 transition-all
                                                 flex-shrink-0 mt-1" />
                      </Link>
                    ))}
                                   </div>
                )}

                {/* Пагинация */}
                {ticketsTotalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 pt-6 border-t border-white/[0.06]">
                    <button
                      onClick={() => setTicketsPage(p => Math.max(1, p - 1))}
                      disabled={ticketsPage === 1}
                      className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                                 bg-white/[0.04] border border-white/[0.08]
                                 hover:bg-white/[0.07] disabled:opacity-40 disabled:cursor-not-allowed
                                 text-white text-base transition-colors"
                    >
                      <ChevronRight className="w-4 h-4 rotate-180" />
                      Назад
                    </button>

                    <div className="flex items-center gap-1.5">
                      {Array.from({ length: Math.min(5, ticketsTotalPages) }, (_, i) => {
                        const pageNum = Math.max(1, Math.min(ticketsPage - 2, ticketsTotalPages - 4)) + i;
                        if (pageNum > ticketsTotalPages) return null;
                        return (
                          <button
                            key={pageNum}
                            onClick={() => setTicketsPage(pageNum)}
                            className={`w-10 h-10 rounded-xl text-base font-medium transition-colors ${
                              pageNum === ticketsPage
                                ? 'bg-red-700 text-white'
                                : 'bg-white/[0.04] text-white/60 border border-white/[0.08] hover:bg-white/[0.08]'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                    </div>

                    <button
                      onClick={() => setTicketsPage(p => Math.min(ticketsTotalPages, p + 1))}
                      disabled={ticketsPage === ticketsTotalPages}
                      className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                                 bg-white/[0.04] border border-white/[0.08]
                                 hover:bg-white/[0.07] disabled:opacity-40 disabled:cursor-not-allowed
                                 text-white text-base transition-colors"
                    >
                      Вперёд
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Sidebar ───────────────────────────────────────────────────── */}
        <div className="space-y-5">
          {/* Информация */}
          <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
            <p className="text-xs uppercase tracking-widest text-white/30 mb-5 flex items-center gap-2">
              <Settings className="w-3.5 h-3.5" /> Информация
            </p>
            <div className="divide-y divide-white/[0.06]">
              {[
                { label: 'Тип',           value: <span className="text-white/80">{company.counterparty_type}</span> },
                { label: 'Статус',        value: (
                  <span className={`text-sm px-2.5 py-1 rounded-lg font-medium border ${
                    company.is_active
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      : 'bg-white/[0.06] text-white/40 border-white/[0.1]'
                  }`}>
                    {company.is_active ? 'Активен' : 'Неактивен'}
                  </span>
                )},
                { label: 'Подразделений', value: <span className="text-white font-bold">{branches.length}</span> },
                { label: 'Заявок', value: <span className="text-white font-bold">{ticketsTotalItems}</span> },
                { label: 'Активных',      value: <span className="text-white font-bold">{activeTickets}</span> },
                { label: 'Зарегистрирован', value: <span className="text-white/70 text-sm">{fmtDate(company.created_at)}</span> },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between py-3">
                  <span className="text-white/40 text-base">{row.label}</span>
                  {row.value}
                </div>
              ))}
            </div>
          </div>

          {/* Контакты */}
          <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
            <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2">
              <Phone className="w-3.5 h-3.5" /> Контакты
            </p>
            <div className="space-y-3">
              {company.phone ? (
                <a href={`tel:${company.phone}`}
                   className="flex items-center gap-2 text-white/50 hover:text-white/70 transition-colors text-base">
                  <Phone className="w-4 h-4" /> {company.phone}
                </a>
              ) : (
                <p className="text-white/20 text-base">Телефон не указан</p>
              )}
              {company.email ? (
                <a href={`mailto:${company.email}`}
                   className="flex items-center gap-2 text-white/50 hover:text-white/70 transition-colors text-base break-all">
                  <Mail className="w-4 h-4" /> {company.email}
                </a>
              ) : (
                <p className="text-white/20 text-base">Email не указан</p>
              )}
            </div>
          </div>

          {company.inn && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
              <p className="text-xs uppercase tracking-widest text-white/30 mb-4">Реквизиты</p>
              <div className="space-y-2 text-sm">
                <p className="text-white/40">ИНН <span className="text-white font-mono">{company.inn}</span></p>
                {company.kpp && <p className="text-white/40">КПП <span className="text-white font-mono">{company.kpp}</span></p>}
                {company.okpo && <p className="text-white/40">ОКПО <span className="text-white font-mono">{company.okpo}</span></p>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}