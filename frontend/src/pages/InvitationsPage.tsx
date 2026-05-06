import { useState, useEffect, useRef } from 'react';
import {
  Mail, Send, History, Loader2, AlertCircle, CheckCircle2, Clock,
  XCircle, Trash2, ChevronLeft, ChevronRight, HelpCircle, Building2,
  Users, Shield, UserPlus, Search, X, Check, ChevronDown, RefreshCcw,
  User, Briefcase, HeadphonesIcon, Settings,
} from 'lucide-react';
import { invitationsApi, counterpartiesApi } from '../api/client';
import type { Counterparty, Invitation, UserRole } from '../types';

// ─── Роли ─────────────────────────────────────────────────────────────────────

interface RoleOption {
  value: UserRole;
  label: string;
  desc: string;
  icon: React.ReactNode;
  color: string;
  borderColor: string;
  group: 'client' | 'staff';
}

const ROLES: RoleOption[] = [
  {
    value: 'customer',
    label: 'Клиент',
    desc: 'Создаёт и отслеживает заявки',
    icon: <User className="w-5 h-5" />,
    color: 'text-blue-400',
    borderColor: 'border-blue-500/40',
    group: 'client',
  },
  {
    value: 'customer_admin',
    label: 'Админ клиента',
    desc: 'Управляет заявками и сотрудниками контрагента',
    icon: <Briefcase className="w-5 h-5" />,
    color: 'text-cyan-400',
    borderColor: 'border-cyan-500/40',
    group: 'client',
  },
  {
    value: 'support_agent',
    label: 'Агент поддержки',
    desc: 'Обрабатывает входящие заявки',
    icon: <HeadphonesIcon className="w-5 h-5" />,
    color: 'text-purple-400',
    borderColor: 'border-purple-500/40',
    group: 'staff',
  },
  {
    value: 'support_manager',
    label: 'Менеджер',
    desc: 'Управляет командой и распределяет задачи',
    icon: <Settings className="w-5 h-5" />,
    color: 'text-orange-400',
    borderColor: 'border-orange-500/40',
    group: 'staff',
  },
];

const getRoleMeta = (v: string) => ROLES.find(r => r.value === v);

// ─── Кастомный dropdown для контрагентов ──────────────────────────────────────

function CounterpartyDropdown({
  value,
  onChange,
  counterparties,
}: {
  value: string;
  onChange: (v: string) => void;
  counterparties: Counterparty[];
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [dropDirection, setDropDirection] = useState<'down' | 'up'>('down');
  const ref = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
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

  // Проверка позиции при открытии
  useEffect(() => {
    if (open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      const dropdownHeight = 320; // примерная высота дропдауна
      
      // Если снизу меньше места, чем нужно, и сверху больше — показываем вверх
      if (spaceBelow < dropdownHeight && spaceAbove > dropdownHeight) {
        setDropDirection('up');
      } else {
        setDropDirection('down');
      }
      
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const selected = counterparties.find(c => c.id === value);

  const filtered = query
    ? counterparties.filter(c =>
        c.name.toLowerCase().includes(query.toLowerCase()) ||
        (c.inn && c.inn.includes(query)) ||
        (c.legal_name && c.legal_name.toLowerCase().includes(query.toLowerCase()))
      )
    : counterparties;

  return (
    <div ref={ref} className="relative">
      <button
        ref={buttonRef}
        onClick={() => { setOpen(!open); setQuery(''); }}
        className={`
          w-full flex items-center gap-3 px-4 py-4 rounded-xl text-left text-base
          transition-all duration-150 border
          ${open
            ? 'bg-white/[0.06] border-red-500/40 ring-2 ring-red-500/10'
            : value
              ? 'bg-white/[0.05] border-white/[0.12] hover:border-white/[0.2]'
              : 'bg-white/[0.03] border-white/[0.08] hover:bg-white/[0.05]'
          }
        `}
      >
        <Building2 className="w-5 h-5 text-white/40 flex-shrink-0" />
        {selected ? (
          <div className="flex-1 min-w-0">
            <span className="text-white truncate block">{selected.name}</span>
            <span className="text-l text-white/30">ИНН: {selected.inn}</span>
          </div>
        ) : (
          <span className="text-white/40 flex-1">Выберите контрагента...</span>
        )}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {value && (
            <button
              onClick={(e) => { e.stopPropagation(); onChange(''); setOpen(false); }}
              className="p-1 rounded hover:bg-white/10 text-white/25 hover:text-white/50"
            >
              <X size={14} />
            </button>
          )}
          <ChevronDown size={16} className={`text-white/25 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {open && (
        <div 
          className={`
            absolute z-50 bg-[#1a1a1a] border border-white/[0.1] rounded-xl 
            shadow-[0_16px_48px_rgba(0,0,0,.5)] overflow-hidden
            min-w-[280px] w-auto max-w-[calc(100vw-32px)]
            ${dropDirection === 'up' ? 'bottom-full mb-2' : 'top-full mt-2'}
          `}
          style={{
            left: 0,
            right: 0,
            maxWidth: 'calc(100vw - 32px)',
          }}
        >
          {/* Поиск */}
          <div className="p-2.5 border-b border-white/[0.06]">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/25" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Поиск по названию или ИНН..."
                className="w-full pl-9 pr-3 py-2.5 bg-white/[0.04] border border-white/[0.06] rounded-lg text-l text-white placeholder-white/25 focus:outline-none focus:border-white/[0.15]"
              />
            </div>
          </div>

          <div className="max-h-64 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <div className="px-4 py-6 text-center text-l text-white/25">
                {query ? 'Ничего не найдено' : 'Нет контрагентов'}
              </div>
            ) : (
              filtered.map(cp => {
                const isSelected = cp.id === value;
                return (
                  <button
                    key={cp.id}
                    onClick={() => { onChange(cp.id); setOpen(false); setQuery(''); }}
                    className={`
                      w-full flex items-center gap-3 px-4 py-3 text-left text-l transition-colors
                      ${isSelected ? 'bg-white/[0.06] text-white' : 'text-white/70 hover:bg-white/[0.04]'}
                    `}
                  >
                    {isSelected
                      ? <Check size={14} className="text-red-400 flex-shrink-0" />
                      : <span className="w-[14px] flex-shrink-0" />
                    }
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{cp.name}</p>
                      <p className="text-l text-white/30 truncate">
                        {cp.legal_name} · ИНН: {cp.inn}
                      </p>
                    </div>
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

// ─── Статус приглашения ───────────────────────────────────────────────────────

function getInvitationStatus(inv: Invitation) {
  if (inv.is_used) return { label: 'Принято', cls: 'bg-green-500/15 text-green-400 border border-green-500/20', Icon: CheckCircle2 };
  if (new Date(inv.expires_at) < new Date()) return { label: 'Истекло', cls: 'bg-red-500/15 text-red-400 border border-red-500/20', Icon: XCircle };
  return { label: 'Ожидает', cls: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20', Icon: Clock };
}

// ─── Основной компонент ───────────────────────────────────────────────────────

export default function InvitationsPage() {
  const [activeTab, setActiveTab] = useState<'send' | 'history'>('send');

  // Форма
  const [email, setEmail]               = useState('');
  const [role, setRole]                 = useState<UserRole | ''>('');
  const [counterpartyId, setCounterpartyId] = useState('');
  const [counterparties, setCounterparties] = useState<Counterparty[]>([]);
  const [sending, setSending]           = useState(false);
  const [success, setSuccess]           = useState(false);
  const [error, setError]               = useState('');

  // История
  const [invitations, setInvitations]   = useState<Invitation[]>([]);
  const [loading, setLoading]           = useState(false);
  const [page, setPage]                 = useState(1);
  const [totalPages, setTotalPages]     = useState(1);
  const [totalItems, setTotalItems]     = useState(0);
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'used' | 'expired'>('all');

  const [revokeTarget, setRevokeTarget] = useState<Invitation | null>(null);
  const [revoking, setRevoking] = useState(false);

  const selectedRole = ROLES.find(r => r.value === role);
  const needsCounterparty = selectedRole?.group === 'client';
  const clientRoles = ROLES.filter(r => r.group === 'client');
  const staffRoles  = ROLES.filter(r => r.group === 'staff');

  useEffect(() => { loadCounterparties(); }, []);

  useEffect(() => {
    if (activeTab === 'history') loadInvitations();
  }, [activeTab, page]);

  const loadCounterparties = async () => {
    try {
      const res = await counterpartiesApi.getAll(1, 100);
      setCounterparties(res.items);
    } catch (e) { console.error(e); }
  };

  const loadInvitations = async () => {
    setLoading(true);
    try {
      const res = await invitationsApi.getAll(page, 15);
      setInvitations(res.items);
      setTotalPages(res.total_pages);
      setTotalItems(res.total_items);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleSend = async () => {
    if (!email || !role) return;
    if (needsCounterparty && !counterpartyId) return;

    setSending(true);
    setError('');
    setSuccess(false);

    try {
      await invitationsApi.send({
        email,
        assigned_role: role as UserRole,
        counterparty_id: needsCounterparty ? counterpartyId : undefined,
      });
      setSuccess(true);
      setEmail('');
      setRole('');
      setCounterpartyId('');
      setTimeout(() => setSuccess(false), 4000);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка отправки приглашения');
    } finally {
      setSending(false);
    }
  };

const handleRevoke = async () => {
  if (!revokeTarget) return;
  setRevoking(true);
  try {
    await invitationsApi.delete(revokeTarget.id);
    setRevokeTarget(null);
    loadInvitations();
  } catch (e) {
    console.error(e);
  } finally {
    setRevoking(false);
  }
};

  // Фильтрация истории на клиенте
  const filteredInvitations = invitations.filter(inv => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'used') return inv.is_used;
    if (statusFilter === 'expired') return !inv.is_used && new Date(inv.expires_at) < new Date();
    if (statusFilter === 'pending') return !inv.is_used && new Date(inv.expires_at) >= new Date();
    return true;
  });

  const isFormValid = email && role && (!needsCounterparty || counterpartyId);

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });

  const formatDateTime = (d: string) =>
    new Date(d).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

  // Статистика
  const stats = {
    total: invitations.length,
    pending: invitations.filter(i => !i.is_used && new Date(i.expires_at) >= new Date()).length,
    used: invitations.filter(i => i.is_used).length,
    expired: invitations.filter(i => !i.is_used && new Date(i.expires_at) < new Date()).length,
  };

  return (
    <div className="space-y-8">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">Приглашения</h1>
          <p className="text-base text-white/50">Пригласите новых пользователей в систему</p>
        </div>
        <div className="flex items-center gap-2">
          {activeTab === 'history' && (
            <button
              onClick={loadInvitations}
              className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-white/40 hover:text-white/60 transition-colors"
              title="Обновить"
            >
              <RefreshCcw className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* ── Tabs ──────────────────────────────────────────────────────────── */}
      <div className="flex gap-2 border-b border-white/10">
        {[
          { id: 'send' as const,    label: 'Отправить',  icon: Send },
          { id: 'history' as const, label: 'История',    icon: History, count: totalItems },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-6 py-3.5 rounded-t-xl text-base font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-red-800/50 text-white border-b-2 border-red-500'
                : 'text-white/50 hover:text-white/70 hover:bg-white/5'
            }`}
          >
            <tab.icon className="w-5 h-5" />
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span className="ml-1 text-l px-2 py-0.5 rounded-full bg-white/15">{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Content ───────────────────────────────────────────────────────── */}
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">

          {/* ═══ Вкладка «Отправить» ═══ */}
          {activeTab === 'send' && (
            <div className="glass-card bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 overflow-hidden">
              <div className="p-6 border-b border-white/10 flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-red-800/25 flex items-center justify-center">
                  <UserPlus className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Новое приглашение</h2>
                  <p className="text-l text-white/50">Заполните данные для отправки</p>
                </div>
              </div>

              <div className="p-6 space-y-7">
                {/* Уведомления */}
                {success && (
                  <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
                    <p className="text-l text-green-400">Приглашение успешно отправлено!</p>
                  </div>
                )}
                {error && (
                  <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                    <p className="text-l text-red-400">{error}</p>
                  </div>
                )}

                {/* Email */}
                <div>
                  <label className="block text-l font-medium text-white/70 mb-2">
                    Email адрес <span className="text-red-400">*</span>
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder="user@company.ru"
                      className="w-full pl-12 pr-4 py-4 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white placeholder-white/25 focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10 text-base transition-all"
                    />
                  </div>
                </div>

                {/* Роль — разделена на группы */}
                <div>
                  <label className="block text-l font-medium text-white/70 mb-3">
                    Роль пользователя <span className="text-red-400">*</span>
                  </label>

                  {/* Клиентские роли */}
                  <div className="mb-3">
                    <p className="text-l uppercase tracking-widest text-white/25 mb-2 flex items-center gap-2">
                      <Building2 className="w-3.5 h-3.5" />
                      Клиент (привязка к контрагенту)
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      {clientRoles.map(r => {
                        const isSelected = role === r.value;
                        return (
                          <button
                            key={r.value}
                            onClick={() => {
                              setRole(r.value);
                              if (r.group !== 'client') setCounterpartyId('');
                            }}
                            className={`
                              p-4 rounded-xl border-2 text-left transition-all
                              ${isSelected
                                ? `bg-white/[0.06] ${r.borderColor}`
                                : 'bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04] hover:border-white/[0.1]'
                              }
                            `}
                          >
                            <div className="flex items-center gap-2.5 mb-1.5">
                              <span className={isSelected ? r.color : 'text-white/40'}>{r.icon}</span>
                              <span className={`text-l font-semibold ${isSelected ? 'text-white' : 'text-white/70'}`}>
                                {r.label}
                              </span>
                            </div>
                            <p className="text-l text-white/40 leading-relaxed">{r.desc}</p>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Сотрудники */}
                  <div>
                    <p className="text-l uppercase tracking-widest text-white/25 mb-2 flex items-center gap-2">
                      <Shield className="w-3.5 h-3.5" />
                      Сотрудник (внутренний доступ)
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      {staffRoles.map(r => {
                        const isSelected = role === r.value;
                        return (
                          <button
                            key={r.value}
                            onClick={() => {
                              setRole(r.value);
                              setCounterpartyId('');
                            }}
                            className={`
                              p-4 rounded-xl border-2 text-left transition-all
                              ${isSelected
                                ? `bg-white/[0.06] ${r.borderColor}`
                                : 'bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04] hover:border-white/[0.1]'
                              }
                            `}
                          >
                            <div className="flex items-center gap-2.5 mb-1.5">
                              <span className={isSelected ? r.color : 'text-white/40'}>{r.icon}</span>
                              <span className={`text-l font-semibold ${isSelected ? 'text-white' : 'text-white/70'}`}>
                                {r.label}
                              </span>
                            </div>
                            <p className="text-l text-white/40 leading-relaxed">{r.desc}</p>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Контрагент (если клиентская роль) */}
                {needsCounterparty && (
                  <div>
                    <label className="block text-l font-medium text-white/70 mb-2">
                      Контрагент <span className="text-red-400">*</span>
                    </label>
                    <CounterpartyDropdown
                      value={counterpartyId}
                      onChange={setCounterpartyId}
                      counterparties={counterparties}
                    />
                    {counterparties.length === 0 && (
                      <p className="mt-2 text-l text-yellow-400/70 flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5" />
                        Нет контрагентов. Сначала создайте контрагента.
                      </p>
                    )}
                  </div>
                )}

                {/* Превью: что будет отправлено */}
                {isFormValid && (
                  <div className="p-4 bg-white/[0.03] border border-white/[0.06] rounded-xl">
                    <p className="text-l text-white/30 mb-2">Будет отправлено:</p>
                    <div className="flex flex-wrap items-center gap-2 text-l">
                      <span className="px-2.5 py-1 rounded-lg bg-white/5 text-white/70">{email}</span>
                      <span className="text-white/20">→</span>
                      <span className={`px-2.5 py-1 rounded-lg bg-white/5 font-medium ${selectedRole?.color || 'text-white/70'}`}>
                        {selectedRole?.label}
                      </span>
                      {needsCounterparty && counterpartyId && (
                        <>
                          <span className="text-white/20">@</span>
                          <span className="px-2.5 py-1 rounded-lg bg-white/5 text-white/70">
                            {counterparties.find(c => c.id === counterpartyId)?.name}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Кнопка */}
                <button
                  onClick={handleSend}
                  disabled={sending || !isFormValid}
                  className="w-full flex items-center justify-center gap-3 py-4 rounded-xl bg-red-800 hover:bg-red-700 text-white text-base font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {sending ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      Отправить приглашение
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* ═══ Вкладка «История» ═══ */}
          {activeTab === 'history' && (
            <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 overflow-hidden">

              {/* Шапка + фильтры */}
              <div className="p-6 border-b border-white/10">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <h2 className="text-xl font-bold text-white">История приглашений</h2>
                  <div className="flex gap-1.5 bg-white/5 rounded-lg p-0.5">
                    {[
                      { id: 'all' as const,     label: 'Все' },
                      { id: 'pending' as const,  label: 'Ожидает' },
                      { id: 'used' as const,     label: 'Принято' },
                      { id: 'expired' as const,  label: 'Истекло' },
                    ].map(f => (
                      <button
                        key={f.id}
                        onClick={() => setStatusFilter(f.id)}
                        className={`px-3 py-1.5 rounded-md text-l font-medium transition-colors ${
                          statusFilter === f.id
                            ? 'bg-red-800/60 text-white'
                            : 'text-white/40 hover:text-white/60'
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Список */}
              {loading ? (
                <div className="py-16 text-center">
                  <Loader2 className="w-8 h-8 text-red-500 animate-spin mx-auto" />
                </div>
              ) : filteredInvitations.length === 0 ? (
                <div className="py-16 text-center">
                  <Mail className="w-16 h-16 text-white/10 mx-auto mb-4" />
                  <p className="text-base text-white/40">
                    {statusFilter !== 'all' ? 'Нет приглашений с таким статусом' : 'Нет приглашений'}
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-white/[0.04]">
                  {filteredInvitations.map(inv => {
                    const status = getInvitationStatus(inv);
                    const roleMeta = getRoleMeta(inv.assigned_role);
                    const canRevoke = !inv.is_used && new Date(inv.expires_at) >= new Date();

                    return (
                      <div
                        key={inv.id}
                        className="px-6 py-5 hover:bg-white/[0.02] transition-colors"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                          {/* Инфо */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <p className="text-base font-medium text-white truncate">{inv.email}</p>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                              {/* Роль */}
                              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-l font-medium bg-white/5 ${roleMeta?.color || 'text-white/50'}`}>
                                {roleMeta?.icon || <User className="w-3.5 h-3.5" />}
                                {roleMeta?.label || inv.assigned_role}
                              </span>
                              {/* Статус */}
                              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-l font-medium ${status.cls}`}>
                                <status.Icon className="w-3.5 h-3.5" />
                                {status.label}
                              </span>
                              {/* Контрагент */}
                              {inv.counterparty_id && (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-l bg-white/5 text-white/40">
                                  <Building2 className="w-3 h-3" />
                                  {counterparties.find(c => c.id === inv.counterparty_id)?.name || '...'}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Даты + действия */}
                          <div className="flex items-center gap-3 flex-shrink-0">
                            <div className="text-right">
                              <p className="text-l text-white/40">{formatDateTime(inv.created_at)}</p>
                              <p className="text-[14px] text-white/20 mt-0.5">
                                до {formatDate(inv.expires_at)}
                              </p>
                            </div>
                            {canRevoke && (
                                <button
                                  onClick={() => setRevokeTarget(inv)}
                                  className="p-2.5 rounded-xl bg-red-900/30 hover:bg-red-900/50 text-white/40 hover:text-red-400 transition-colors"
                                  title="Отозвать"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Пагинация */}
              {totalPages > 1 && (
                <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between">
                  <span className="text-l text-white/30">
                    Страница {page} из {totalPages}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-2 rounded-lg hover:bg-white/10 text-white/40 disabled:opacity-20 transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="p-2 rounded-lg hover:bg-white/10 text-white/40 disabled:opacity-20 transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Sidebar ─────────────────────────────────────────────────────── */}
        <div className="space-y-6">

          {/* Статистика (видна на вкладке истории) */}
          {activeTab === 'history' && invitations.length > 0 && (
            <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-5">
              <h3 className="text-l font-semibold text-white mb-4 flex items-center gap-2">
                <Users className="w-4 h-4 text-white/50" />
                Статистика
              </h3>
              <div className="space-y-3">
                {[
                  { label: 'Всего', value: stats.total,   color: 'text-white',       dot: 'bg-white/30' },
                  { label: 'Ожидает', value: stats.pending, color: 'text-yellow-400', dot: 'bg-yellow-400' },
                  { label: 'Принято', value: stats.used,    color: 'text-green-400',  dot: 'bg-green-400' },
                  { label: 'Истекло', value: stats.expired, color: 'text-red-400',    dot: 'bg-red-400' },
                ].map(s => (
                  <div key={s.label} className="flex items-center justify-between py-1.5">
                    <span className="flex items-center gap-2 text-l text-white/50">
                      <span className={`w-2 h-2 rounded-full ${s.dot}`} />
                      {s.label}
                    </span>
                    <span className={`text-lg font-bold ${s.color}`}>{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Как это работает */}
          <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-5">
            <div className="flex items-center gap-2.5 mb-5">
              <HelpCircle className="w-5 h-5 text-blue-400" />
              <h3 className="text-l font-bold text-white">Как это работает?</h3>
            </div>
            <div className="space-y-5">
              {[
                { n: '1', title: 'Отправьте приглашение',   desc: 'Укажите email, роль и контрагента' },
                { n: '2', title: 'Пользователь получит письмо', desc: 'Со ссылкой для регистрации' },
                { n: '3', title: 'Регистрация',             desc: 'Создаёт аккаунт и получает доступ' },
              ].map(step => (
                <div key={step.n} className="flex gap-3.5">
                  <div className="w-8 h-8 rounded-full bg-red-800/25 flex items-center justify-center text-l font-bold text-red-400 flex-shrink-0">
                    {step.n}
                  </div>
                  <div>
                    <p className="text-l font-medium text-white">{step.title}</p>
                    <p className="text-l text-white/40">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* О ролях */}
          <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-5">
            <div className="flex items-center gap-2.5 mb-5">
              <Shield className="w-5 h-5 text-purple-400" />
              <h3 className="text-l font-bold text-white">О ролях</h3>
            </div>
            <div className="space-y-4">
              {ROLES.map(r => (
                <div key={r.value} className="flex items-start gap-3">
                  <span className={`mt-0.5 ${r.color}`}>{r.icon}</span>
                  <div>
                    <p className={`text-l font-medium ${r.color}`}>{r.label}</p>
                    <p className="text-l text-white/40">{r.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Важно */}
          <div className="bg-yellow-500/5 rounded-xl border border-yellow-500/15 p-5">
            <div className="flex items-center gap-2.5 mb-3">
              <AlertCircle className="w-5 h-5 text-yellow-400" />
              <h3 className="text-l font-bold text-white">Важно</h3>
            </div>
            <p className="text-l text-white/50 leading-relaxed">
              Приглашение действительно <span className="text-white font-medium">7 дней</span>.
              После истечения срока необходимо отправить новое.
            </p>
          </div>
        </div>
      </div>
            {/* ── Модалка подтверждения отзыва ──────────────────────────────── */}
      {revokeTarget && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => !revoking && setRevokeTarget(null)}
          />
          <div
            className="relative w-full max-w-md bg-[#1a1a1a] border border-white/[0.1] rounded-2xl overflow-hidden"
            style={{ boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 24px 80px rgba(0,0,0,0.7)' }}
          >
            {/* Иконка */}
            <div className="pt-8 flex justify-center">
              <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20
                              flex items-center justify-center">
                <Trash2 className="w-8 h-8 text-red-400" />
              </div>
            </div>

            {/* Текст */}
            <div className="px-7 pt-5 pb-2 text-center">
              <h2 className="text-xl font-bold text-white mb-3">Отозвать приглашение?</h2>
              <p className="text-base text-white/60 leading-relaxed">
                Приглашение для{' '}
                <span className="text-white font-semibold">{revokeTarget.email}</span>{' '}
                будет отменено. Пользователь больше не сможет зарегистрироваться по этой ссылке.
              </p>

              {/* Детали приглашения */}
              <div className="mt-4 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <div className="flex flex-wrap items-center justify-center gap-2 text-sm">
                  {(() => {
                    const roleMeta = getRoleMeta(revokeTarget.assigned_role);
                    return (
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 font-medium ${roleMeta?.color || 'text-white/50'}`}>
                        {roleMeta?.icon || <User className="w-3.5 h-3.5" />}
                        {roleMeta?.label || revokeTarget.assigned_role}
                      </span>
                    );
                  })()}
                  {revokeTarget.counterparty_id && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 text-white/40">
                      <Building2 className="w-3 h-3" />
                      {counterparties.find(c => c.id === revokeTarget.counterparty_id)?.name || '...'}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Кнопки */}
            <div className="flex gap-3 p-6">
              <button
                onClick={() => setRevokeTarget(null)}
                disabled={revoking}
                className="flex-1 px-4 py-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.09]
                           text-white/70 text-base font-medium transition-colors disabled:opacity-50"
              >
                Отмена
              </button>
              <button
                onClick={handleRevoke}
                disabled={revoking}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                           bg-red-600/20 hover:bg-red-600/30 border border-red-600/30
                           text-red-400 text-base font-medium transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {revoking
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Trash2 className="w-4 h-4" />}
                {revoking ? 'Отзываем...' : 'Отозвать'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}