import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, FolderOpen, Building2, Users, Calendar,
  User, Mail, Phone, Loader2, Archive, Plus, Ticket,
  Crown, Hash, Clock, UserPlus, ChevronRight,
  Search, X, Check, Settings, AlertTriangle,
} from 'lucide-react';
import { projectsApi, ticketsApi, counterpartiesApi, usersApi } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useToast } from '../components/ui/use-toast';
import type { Project, Counterparty, TicketListItem, SimpleUser, CounterpartyCustomer } from '../types';

type TabType = 'info' | 'members' | 'tickets';

// ─── Константы ────────────────────────────────────────────────────────────────

const PROJECT_ROLES = [
  { value: 'owner',          label: 'Владелец',              color: 'text-red-400',     bg: 'bg-red-500/15',     border: 'border-red-500/30' },
  { value: 'manager',        label: 'Менеджер',              color: 'text-blue-400',    bg: 'bg-blue-500/15',    border: 'border-blue-500/30' },
  { value: 'member',         label: 'Участник',              color: 'text-emerald-400', bg: 'bg-emerald-500/15', border: 'border-emerald-500/30' },
  { value: 'viewer',         label: 'Наблюдатель',           color: 'text-white/50',    bg: 'bg-white/[0.06]',   border: 'border-white/[0.1]' },
  { value: 'customer',       label: 'Клиент',                color: 'text-violet-400',  bg: 'bg-violet-500/15',  border: 'border-violet-500/30' },
  { value: 'customer_admin', label: 'Администратор клиента', color: 'text-cyan-400',    bg: 'bg-cyan-500/15',    border: 'border-cyan-500/30' },
] as const;

type RoleValue = typeof PROJECT_ROLES[number]['value'];

const getRoleMeta = (role: string) =>
  PROJECT_ROLES.find(r => r.value === role) ?? PROJECT_ROLES[2];

// ─── Вспомогательные компоненты ──────────────────────────────────────────────

function getInitials(name?: string | null): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map(w => w[0]).join('').toUpperCase();
}

function Avatar({ name, size = 'md' }: { name?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const cls = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base' }[size];
  return (
    <div className={`${cls} rounded-full bg-gradient-to-br from-red-800 to-red-700
                    flex items-center justify-center font-bold text-white flex-shrink-0 select-none`}>
      {getInitials(name)}
    </div>
  );
}

// ─── Модалка архивирования ───────────────────────────────────────────────────

function ArchiveModal({
  projectName,
  loading,
  onConfirm,
  onClose,
}: {
  projectName: string;
  loading: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !loading) onClose(); };
    document.addEventListener('keydown', h);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', h);
      document.body.style.overflow = '';
    };
  }, [onClose, loading]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => !loading && onClose()} />
      <div
        className="relative w-full max-w-md bg-[#1a1a1a] border border-white/[0.1] rounded-2xl overflow-hidden"
        style={{ boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 24px 80px rgba(0,0,0,0.7)' }}
      >
        {/* Icon */}
        <div className="pt-8 flex justify-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20
                          flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-amber-400" />
          </div>
        </div>

        {/* Text */}
        <div className="px-7 pt-5 pb-2 text-center">
          <h2 className="text-xl font-bold text-white mb-3">Архивировать проект?</h2>
          <p className="text-base text-white/60 leading-relaxed">
            Проект <span className="text-white font-semibold">«{projectName}»</span> будет архивирован.
            В нём нельзя будет создавать новые заявки.
          </p>
          <p className="text-sm text-white/30 mt-2">
            Существующие заявки и данные сохранятся.
          </p>
        </div>

        {/* Buttons */}
        <div className="flex gap-3 p-6">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.09]
                       text-white/70 text-base font-medium transition-colors disabled:opacity-50"
          >
            Отмена
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                       bg-amber-600/20 hover:bg-amber-600/30 border border-amber-600/30
                       text-amber-400 text-base font-medium transition-all
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Archive className="w-4 h-4" />}
            {loading ? 'Архивируем...' : 'Архивировать'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Основной компонент ───────────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { toast } = useToast();

  const [project, setProject]             = useState<Project | null>(null);
  const [counterparty, setCounterparty]   = useState<Counterparty | null>(null);
  const [loading, setLoading]             = useState(true);
  const [activeTab, setActiveTab]         = useState<TabType>('info');

  // Участники — обогащённые данными из getCustomers
  const [members, setMembers]             = useState<Array<{ user_id: string; project_role: string; user: CounterpartyCustomer | SimpleUser | null }>>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  // Тикеты
  const [projectTickets, setProjectTickets] = useState<TicketListItem[]>([]);
  const [loadingTickets, setLoadingTickets] = useState(false);

  // Архивирование
  const [showArchiveModal, setShowArchiveModal] = useState(false);
  const [archiving, setArchiving]           = useState(false);

  // Модал добавления участников
  const [showAddModal, setShowAddModal]     = useState(false);
  const [availableUsers, setAvailableUsers] = useState<Array<CounterpartyCustomer | SimpleUser>>([]);
  const [loadingAvailable, setLoadingAvailable] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<Map<string, CounterpartyCustomer | SimpleUser>>(new Map());
  const [selectedRole, setSelectedRole]     = useState<RoleValue>('member');
  const [searchUser, setSearchUser]         = useState('');
  const [addingMembers, setAddingMembers]   = useState(false);

  const userRole = user?.role ?? '';
  const isSupportOrHigher = ['admin', 'support_manager', 'support_agent'].includes(userRole);
  const canEdit = isSupportOrHigher || project?.owner_id === user?.user_id;
  const isActive = project?.status === 'active';

  // ── Загрузка участников ───────────────────────────────────────────────────


const enrichMembers = useCallback(async (
  memberships: Array<{ user_id: string; project_role: string }>,
  counterpartyId: string | null | undefined,
) => {
  setLoadingMembers(true);
  try {
    const userMap = new Map<string, CounterpartyCustomer | SimpleUser>();

    // Шаг 1: загружаем клиентов контрагента (доступно всем)
    if (counterpartyId) {
      try {
        const res = await counterpartiesApi.getCustomers(counterpartyId, 1, 15);
        (res.items ?? []).forEach((u: CounterpartyCustomer) => userMap.set(u.id, u));
      } catch (err) {
        console.error('getCustomers failed:', err);
      }
    }

    // Шаг 2: для customer НЕ вызываем getAllUsers (нет прав)
    const isCustomer = user?.role === 'customer' || user?.role === 'customer_admin';
    
    if (!isCustomer) {
      const missingIds = memberships
        .map(m => m.user_id)
        .filter(uid => !userMap.has(uid) && uid !== user?.user_id);

      if (missingIds.length > 0) {
        try {
          const res = await usersApi.getAllUsers(1, 15);
          (res.items ?? []).forEach((u: SimpleUser) => {
            if (missingIds.includes(u.id)) userMap.set(u.id, u);
          });
        } catch (err) {
          console.error('getAllUsers failed:', err);
        }
      }
    }

    // Шаг 3: текущий пользователь
    if (user?.user_id && !userMap.has(user.user_id)) {
      userMap.set(user.user_id, {
        id: user.user_id,
        email: user.email ?? '',
        username: user.username ?? '',
        full_name: user.full_name ?? '',
        role: user.role ?? '',
      } as any);
    }

    const enriched = memberships.map(m => ({
      user_id: m.user_id,
      project_role: m.project_role,
      user: userMap.get(m.user_id) ?? null,
    }));

    setMembers(enriched);
  } finally {
    setLoadingMembers(false);
  }
}, [user]);

  // ── Загрузка проекта ─────────────────────────────────────────────────────

  const loadProject = useCallback(async () => {
    setLoading(true);
    try {
      const data = await projectsApi.getById(id!);
      setProject(data);

      // Параллельно: контрагент + участники
      await Promise.all([
        data.counterparty_id
          ? counterpartiesApi.getById(data.counterparty_id)
              .then(cp => setCounterparty(cp))
              .catch(() => {})
          : Promise.resolve(),
        enrichMembers(data.memberships ?? [], data.counterparty_id),
      ]);
    } catch {
      toast({ title: 'Ошибка', description: 'Не удалось загрузить проект', variant: 'destructive' });
      navigate('/projects');
    } finally {
      setLoading(false);
    }
  }, [id, enrichMembers, toast, navigate]);

  // ── Загрузка тикетов ─────────────────────────────────────────────────────

  const loadTickets = useCallback(async () => {
    if (!project?.id) return;
    setLoadingTickets(true);
    try {
      const res = await ticketsApi.getAllWithFilters(1, 100, { project_id: project.id });
      setProjectTickets(res.items);
    } catch {
      setProjectTickets([]);
    } finally {
      setLoadingTickets(false);
    }
  }, [project?.id]);

  // ── Загрузка доступных для добавления пользователей ─────────────────────
  //
  // Источник: getCustomers контрагента (только клиенты контрагента могут быть
  // добавлены как customer/customer_admin через этот UI)

const loadAvailableUsers = useCallback(async () => {
  setLoadingAvailable(true);
  try {
    const existingIds = new Set(members.map(m => m.user_id));
    const allAvailable: Array<CounterpartyCustomer | SimpleUser> = [];
    const seenIds = new Set<string>();

    // 1. Клиенты контрагента
    if (project?.counterparty_id) {
      try {
        const res = await counterpartiesApi.getCustomers(project.counterparty_id, 1, 15);
        (res.items ?? []).forEach((u: CounterpartyCustomer) => {
          if (!existingIds.has(u.id) && !seenIds.has(u.id)) {
            allAvailable.push(u);
            seenIds.add(u.id);
          }
        });
      } catch (err) {
        console.error('Failed to load counterparty customers:', err);
      }
    }

    // 2. Сотрудники поддержки
    try {
      const res = await usersApi.getSupports(1, 15);
      (res.items ?? []).forEach((u: SimpleUser) => {
        if (!existingIds.has(u.id) && !seenIds.has(u.id)) {
          allAvailable.push(u);
          seenIds.add(u.id);
        }
      });
    } catch (err) {
      console.error('Failed to load support users:', err);
    }

    setAvailableUsers(allAvailable);
  } catch {
    toast({
      title: 'Ошибка',
      description: 'Не удалось загрузить пользователей',
      variant: 'destructive',
    });
  } finally {
    setLoadingAvailable(false);
  }
}, [project?.counterparty_id, members, toast]);

  useEffect(() => { if (id) loadProject(); }, [id, loadProject]);
  useEffect(() => { if (activeTab === 'tickets') loadTickets(); }, [activeTab, loadTickets]);
  useEffect(() => { if (showAddModal) loadAvailableUsers(); }, [showAddModal, loadAvailableUsers]);

  // ── Действия ─────────────────────────────────────────────────────────────

  const handleArchive = async () => {
    setArchiving(true);
    try {
      await projectsApi.archive(id!);
      toast({ title: 'Успешно', description: 'Проект архивирован' });
      setShowArchiveModal(false);
      await loadProject();
    } catch {
      toast({ title: 'Ошибка', description: 'Не удалось архивировать проект', variant: 'destructive' });
    } finally {
      setArchiving(false);
    }
  };

  const handleAddMembers = async () => {
    if (!selectedUsers.size) return;
    setAddingMembers(true);
    try {
      const payload = Array.from(selectedUsers.values()).map(u => ({
        user_id: u.id,
        project_role: selectedRole,
      }));
      await projectsApi.addMembers(id!, payload);
      toast({ title: 'Успешно', description: `Добавлено ${payload.length} участников` });
      setShowAddModal(false);
      setSelectedUsers(new Map());
      setSearchUser('');
      setSelectedRole('member');
      await loadProject();
    } catch {
      toast({ title: 'Ошибка', description: 'Не удалось добавить участников', variant: 'destructive' });
    } finally {
      setAddingMembers(false);
    }
  };

 const toggleUser = (u: CounterpartyCustomer | SimpleUser) => {
  setSelectedUsers(prev => {
    const m = new Map(prev);
    m.has(u.id) ? m.delete(u.id) : m.set(u.id, u as any);
    return m;
  });
};

  // ── Вспомогательные ───────────────────────────────────────────────────────

  // Получить имя и email участника
// Получить имя и email участника
const resolveDisplay = (member: typeof members[0]) => {
  const u = member.user;
  const isMe = member.user_id === user?.user_id;

  // Если пользователь не найден в данных (нет доступа к API поддержки)
  if (!u) {
    // Для customer и customer_admin показываем "Агент поддержки"
    if (user?.role === 'customer' || user?.role === 'customer_admin') {
      return {
        name: 'Агент поддержки',
        email: undefined,
        isMe: false,
      };
    }
    // Fallback — показываем ID
    return {
      name: `ID: ${member.user_id.slice(0, 8)}`,
      email: undefined,
      isMe: false,
    };
  }

  if (u) {
    return {
      name: u.full_name || (u as any).username || u.email || `ID: ${member.user_id.slice(0, 8)}`,
      email: u.email,
      isMe,
    };
  }

  // Fallback — показываем текущего пользователя
  if (isMe) {
    return {
      name: user?.full_name || user?.username || 'Вы',
      email: user?.email,
      isMe: true,
    };
  }

  return { name: `ID: ${member.user_id.slice(0, 8)}`, email: undefined, isMe: false };
};

  // Владелец и создатель
  const ownerMember = members.find(m => m.project_role === 'owner') ?? members.find(m => m.user_id === project?.owner_id);
  const ownerDisplay = ownerMember ? resolveDisplay(ownerMember) : null;

  const creatorMember = members.find(m => m.user_id === project?.created_by);
  const creatorDisplay = creatorMember
    ? resolveDisplay(creatorMember)
    : project?.created_by === user?.user_id
      ? { name: user?.full_name || user?.username || 'Вы', email: user?.email, isMe: true }
      : null;

  // Фильтр для модала
const filteredAvailable = availableUsers.filter(u => {
  if (!searchUser) return true;
  const q = searchUser.toLowerCase();
  const name = u.full_name || (u as any).username || '';
  return (
    name.toLowerCase().includes(q) ||
    u.email?.toLowerCase().includes(q)
  );
});

  // Форматирование
  const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
  const fmtDateTime = (d: string) =>
    new Date(d).toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });

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

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
    </div>
  );

  if (!project) return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-16 text-center">
      <FolderOpen className="w-20 h-20 text-white/15 mx-auto mb-5" />
      <h2 className="text-2xl font-bold text-white mb-3">Проект не найден</h2>
      <p className="text-base text-white/50 mb-6">Возможно, он был удалён или у вас нет доступа</p>
      <Link to="/projects"
            className="inline-flex px-6 py-2.5 rounded-xl bg-red-800 hover:bg-red-700
                       text-white text-base font-medium transition-colors">
        Вернуться к проектам
      </Link>
    </div>
  );

  return (
    <div className="space-y-8">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          <button onClick={() => navigate('/projects')}
                  className="p-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06]
                             text-white/60 hover:text-white transition-all mt-1">
            <ArrowLeft className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-800 to-red-700
                            flex items-center justify-center shadow-lg shadow-red-900/30 flex-shrink-0">
              <FolderOpen className="w-8 h-8 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap mb-2">
                <h1 className="text-3xl font-bold text-white">{project.name}</h1>
                <span className={`px-3 py-1 rounded-lg text-base font-medium border ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    : 'bg-white/[0.06] text-white/40 border-white/[0.1]'
                }`}>
                  {isActive ? 'Активен' : 'Архивирован'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Hash className="w-4 h-4 text-white/30" />
                <span className="text-white/50 font-mono text-base">{project.key}</span>
              </div>
            </div>
          </div>
        </div>

        {canEdit && isActive && (
          <div className="flex gap-2.5 flex-shrink-0">
            <button onClick={() => setShowArchiveModal(true)}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                               bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20
                               text-amber-400 text-base font-medium transition-all">
              <Archive className="w-4 h-4" />
              Архивировать
            </button>
            <Link to={`/tickets/new?project_id=${project.id}`}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                             bg-red-800 hover:bg-red-700 text-white text-base font-medium
                             transition-colors shadow-lg shadow-red-900/30">
              <Plus className="w-4 h-4" />
              Создать заявку
            </Link>
          </div>
        )}
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────────────── */}
      <div className="flex gap-1.5 border-b border-white/[0.08]">
        {([
          { id: 'info'    as TabType, label: 'Информация', icon: FolderOpen },
          { id: 'members' as TabType, label: 'Участники',  icon: Users,  count: members.length },
          { id: 'tickets' as TabType, label: 'Заявки',     icon: Ticket, count: projectTickets.length },
        ]).map(tab => (
          <button key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-5 py-3 rounded-t-xl transition-all whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'bg-red-800/50 text-white border-b-2 border-red-500'
                      : 'text-white/50 hover:text-white/70 hover:bg-white/[0.04]'
                  }`}>
            <tab.icon className="w-4 h-4" />
            <span className="text-base font-medium">{tab.label}</span>
            {'count' in tab && (tab.count ?? 0) > 0 && (
              <span className="ml-0.5 px-2 py-0.5 rounded-full bg-white/[0.1] text-sm">{tab.count}</span>
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
              {project.description && (
                <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-6">
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-3">Описание</p>
                  <p className="text-white text-base leading-relaxed whitespace-pre-wrap">
                    {project.description}
                  </p>
                </div>
              )}

              <div className="grid md:grid-cols-2 gap-4">
                {/* Контрагент */}
                <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2">
                    <Building2 className="w-3.5 h-3.5" /> Контрагент
                  </p>
                  {counterparty ? (
                    <>
                      <p className="text-white font-semibold text-base">{counterparty.name}</p>
                      {counterparty.legal_name && <p className="text-white/50 text-sm mt-1">{counterparty.legal_name}</p>}
                      {counterparty.inn && <p className="text-white/30 text-sm mt-1.5 font-mono">ИНН {counterparty.inn}</p>}
                    </>
                  ) : (
                    <p className="text-white/30 text-base">Не указан</p>
                  )}
                </div>

                {/* Владелец */}
                <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2">
                    <Crown className="w-3.5 h-3.5" /> Владелец
                  </p>
                  {ownerDisplay ? (
                    <div className="flex items-center gap-3">
                      <Avatar name={ownerDisplay.name} />
                      <div className="min-w-0">
                        <p className="text-white font-semibold text-base truncate">{ownerDisplay.name}</p>
                        {ownerDisplay.email && (
                          <a href={`mailto:${ownerDisplay.email}`}
                             className="text-white/40 text-sm hover:text-white/60 transition-colors truncate block">
                            {ownerDisplay.email}
                          </a>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-white/30 text-base">Не указан</p>
                  )}
                </div>

                {/* Создан */}
                <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5" /> Дата создания
                  </p>
                  <p className="text-white text-base font-medium">{fmtDateTime(project.created_at)}</p>
                </div>

                {/* Создатель */}
                <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2">
                    <User className="w-3.5 h-3.5" /> Создатель
                  </p>
                  {creatorDisplay ? (
                    <div className="flex items-center gap-3">
                      <Avatar name={creatorDisplay.name} />
                      <div className="min-w-0">
                        <p className="text-white font-semibold text-base truncate">{creatorDisplay.name}</p>
                        {creatorDisplay.email && (
                          <a href={`mailto:${creatorDisplay.email}`}
                             className="text-white/40 text-sm hover:text-white/60 transition-colors truncate block">
                            {creatorDisplay.email}
                          </a>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-white/30 text-base">Не удалось определить</p>
                  )}
                </div>
              </div>

              {/* Статистика */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { icon: Users,  value: members.length,       label: 'Участников' },
                  { icon: Ticket, value: projectTickets.length, label: 'Заявок' },
                  { icon: Clock,  value: projectTickets.filter(t => t.status !== 'Закрыт' && t.status !== 'Решён').length, label: 'Активных' },
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

          {/* ═══ Members ═══ */}
          {activeTab === 'members' && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.01]">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <Users className="w-5 h-5 text-white/40" />
                  Участники
                  {members.length > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-white/[0.08] text-sm text-white/50">
                      {members.length}
                    </span>
                  )}
                </h2>
                {canEdit && (
                  <button onClick={() => setShowAddModal(true)}
                          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-red-800 hover:bg-red-700
                                     text-white text-base font-medium transition-colors shadow-md shadow-red-900/30">
                    <UserPlus className="w-4 h-4" />
                    Добавить
                  </button>
                )}
              </div>

              <div className="p-6">
                {loadingMembers ? (
                  <div className="flex justify-center py-16">
                    <Loader2 className="w-8 h-8 animate-spin text-white/20" />
                  </div>
                ) : members.length === 0 ? (
                  <div className="text-center py-20">
                    <Users className="w-16 h-16 text-white/10 mx-auto mb-4" />
                    <p className="text-white/50 text-base font-semibold mb-1">Нет участников</p>
                    <p className="text-white/30 text-sm">Добавьте первых участников в проект</p>
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {members.map(member => {
                      const { name, email, isMe } = resolveDisplay(member);
                      const role = getRoleMeta(member.project_role);
                      return (
                        <div key={member.user_id}
                             className={`flex items-center gap-4 py-4 px-2 rounded-xl ${
                               isMe ? 'bg-red-500/[0.04]' : ''
                             }`}>
                          <Avatar name={name} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-white font-semibold text-base truncate">{name}</span>
                              {isMe && (
                                <span className="text-xs px-2 py-0.5 rounded-full bg-white/[0.08] text-white/50">
                                  Вы
                                </span>
                              )}
                            </div>
                            {email ? (
                              <a href={`mailto:${email}`}
                                 className="text-white/40 text-sm hover:text-white/60 transition-colors truncate block">
                                {email}
                              </a>
                            ) : (
                              <span className="text-white/20 text-sm">email не указан</span>
                            )}
                          </div>
                          <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                                           border flex-shrink-0 ${role.bg} ${role.color} ${role.border}`}>
                            {member.project_role === 'owner' && <Crown className="w-3 h-3" />}
                            {role.label}
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
          {activeTab === 'tickets' && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.01]">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <Ticket className="w-5 h-5 text-white/40" />
                  Заявки
                </h2>
                <Link to={`/tickets/new?project_id=${project.id}`}
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
                ) : projectTickets.length === 0 ? (
                  <div className="text-center py-20">
                    <Ticket className="w-16 h-16 text-white/10 mx-auto mb-4" />
                    <p className="text-white/50 text-base font-semibold mb-1">Нет заявок</p>
                    <p className="text-white/30 text-sm mb-5">В этом проекте пока нет заявок</p>
                    <Link to={`/tickets/new?project_id=${project.id}`}
                          className="text-red-400 hover:text-red-300 transition-colors text-base">
                      Создать первую заявку →
                    </Link>
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {projectTickets.map(ticket => (
                      <Link key={ticket.id} to={`/tickets/${ticket.number}`}
                            className="flex items-start justify-between gap-4 py-4 px-2
                                       hover:bg-white/[0.03] rounded-xl transition-colors group">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <span className="text-red-400 font-mono text-sm bg-red-500/10
                                             border border-red-500/20 px-2 py-0.5 rounded-lg">
                              #{ticket.number}
                            </span>
                            <span className={`px-2.5 py-0.5 rounded-lg text-sm font-medium border ${statusClr(ticket.status)}`}>
                              {ticket.status}
                            </span>
                            <span className={`px-2.5 py-0.5 rounded-lg text-sm font-medium border ${priorityClr(ticket.priority)}`}>
                              {ticket.priority}
                            </span>
                          </div>
                          <p className="text-white font-medium text-base group-hover:text-red-400 transition-colors truncate">
                            {ticket.title}
                          </p>
                          <p className="text-white/30 text-sm mt-1">{fmtDate(ticket.created_at)}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-red-400
                                                 group-hover:translate-x-0.5 transition-all flex-shrink-0 mt-1" />
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Sidebar ───────────────────────────────────────────────────── */}
        <div className="space-y-5">
          <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
            <p className="text-xs uppercase tracking-widest text-white/30 mb-5 flex items-center gap-2">
              <Settings className="w-3.5 h-3.5" /> Информация
            </p>
            <div className="divide-y divide-white/[0.06]">
              {[
                { label: 'Ключ',       value: <span className="font-mono text-white/80">{project.key}</span> },
                { label: 'Статус',     value: (
                  <span className={`text-sm px-2.5 py-1 rounded-lg font-medium border ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      : 'bg-white/[0.06] text-white/40 border-white/[0.1]'
                  }`}>
                    {isActive ? 'Активен' : 'Архивирован'}
                  </span>
                )},
                { label: 'Участников', value: <span className="text-white font-bold">{members.length}</span> },
                { label: 'Заявок',     value: <span className="text-white font-bold">{projectTickets.length}</span> },
                { label: 'Создан',     value: <span className="text-white/70 text-sm">{fmtDate(project.created_at)}</span> },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between py-3">
                  <span className="text-white/40 text-base">{row.label}</span>
                  {row.value}
                </div>
              ))}
            </div>
          </div>

          {counterparty && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
              <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2">
                <Building2 className="w-3.5 h-3.5" /> Контрагент
              </p>
              <p className="text-white font-semibold text-base">{counterparty.name}</p>
              {counterparty.legal_name && <p className="text-white/50 text-sm mt-1">{counterparty.legal_name}</p>}
              {counterparty.inn && <p className="text-white/30 text-sm mt-1.5 font-mono">ИНН {counterparty.inn}</p>}
              <div className="mt-4 space-y-2">
                {counterparty.phone && (
                  <a href={`tel:${counterparty.phone}`}
                     className="flex items-center gap-2 text-white/40 hover:text-white/60 transition-colors text-base">
                    <Phone className="w-4 h-4" /> {counterparty.phone}
                  </a>
                )}
                {counterparty.email && (
                  <a href={`mailto:${counterparty.email}`}
                     className="flex items-center gap-2 text-white/40 hover:text-white/60 transition-colors text-base break-all">
                    <Mail className="w-4 h-4" /> {counterparty.email}
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Модал архивирования ──────────────────────────────────────────── */}
      {showArchiveModal && (
        <ArchiveModal
          projectName={project.name}
          loading={archiving}
          onConfirm={handleArchive}
          onClose={() => setShowArchiveModal(false)}
        />
      )}

      {/* ── Модал добавления участников ──────────────────────────────────── */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
             onClick={() => setShowAddModal(false)}>
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div
            className="relative w-full max-w-xl max-h-[85vh] flex flex-col
                       bg-[#1a1a1a] border border-white/[0.1] rounded-2xl overflow-hidden"
            style={{ boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 24px 80px rgba(0,0,0,0.7)' }}
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5
                            border-b border-white/[0.08] bg-white/[0.02] flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-red-800/20 flex items-center justify-center">
                  <UserPlus className="w-4 h-4 text-red-400" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white">Добавить участников</h2>
                  <p className="text-sm text-white/40 mt-0.5">
                    Пользователи из контрагента «{counterparty?.name ?? '...'}»
                  </p>
                </div>
              </div>
              <button onClick={() => setShowAddModal(false)}
                      className="p-2 rounded-xl hover:bg-white/[0.06] text-white/40 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-5">
              {/* Роль */}
              <div>
                <label className="block text-base text-white/60 mb-3">Роль в проекте</label>
                <div className="flex flex-wrap gap-2">
                  {PROJECT_ROLES.map(role => (
                    <button key={role.value}
                            onClick={() => setSelectedRole(role.value)}
                            className={`px-3.5 py-2 rounded-xl text-base font-medium transition-all border ${
                              selectedRole === role.value
                                ? `${role.bg} ${role.color} ${role.border}`
                                : 'bg-white/[0.03] text-white/50 border-white/[0.06] hover:bg-white/[0.06]'
                            }`}>
                      {role.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Поиск */}
              <div>
                <label className="block text-base text-white/60 mb-2">
                  Сотрудники контрагента
                  {selectedUsers.size > 0 && (
                    <span className="ml-2 text-sm text-red-400">· {selectedUsers.size} выбрано</span>
                  )}
                </label>
                <div className="relative mb-3">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                  <input value={searchUser}
                         onChange={e => setSearchUser(e.target.value)}
                         placeholder="Поиск по имени или email..."
                         className="w-full pl-10 pr-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl
                                    text-white text-base placeholder-white/25
                                    focus:outline-none focus:border-red-500/40 focus:ring-2
                                    focus:ring-red-500/10 transition-all" />
                </div>

                {/* Список */}
                <div className="max-h-72 overflow-y-auto rounded-xl border border-white/[0.08]
                                bg-[#161616] divide-y divide-white/[0.04]">
                  {loadingAvailable ? (
                    <div className="flex justify-center py-10">
                      <Loader2 className="w-6 h-6 animate-spin text-white/20" />
                    </div>
                  ) : filteredAvailable.length === 0 ? (
                    <div className="text-center py-10">
                      <Users className="w-10 h-10 mx-auto mb-3 text-white/10" />
                      <p className="text-white/40 text-base">
                        {searchUser ? 'Ничего не найдено' : 'Все сотрудники уже добавлены в проект'}
                      </p>
                    </div>
                  ) : (
                    filteredAvailable.map(u => {
                    const isSel = selectedUsers.has(u.id);
                    const displayName = u.full_name || (u as any).username || u.email;
                    // Определяем тип: если есть counterparty_id — клиент, иначе — сотрудник
                    const isSupport = !(u as any).counterparty_id;

                    return (
                      <button key={u.id}
                              onClick={() => toggleUser(u)}
                              className={`w-full flex items-center gap-3 px-4 py-3.5 text-left transition-colors ${
                                isSel ? 'bg-red-500/[0.08]' : 'hover:bg-white/[0.03]'
                              }`}>
                        <Avatar name={displayName} size="sm" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-white font-medium text-base truncate">{displayName}</p>
                            {isSupport && (
                              <span className="text-[11px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400
                                              border border-red-500/20 flex-shrink-0">
                                Поддержка
                              </span>
                            )}
                          </div>
                          <p className="text-white/40 text-sm truncate">{u.email}</p>
                        </div>
                        <div className={`w-5 h-5 rounded-md border flex-shrink-0 flex items-center
                                        justify-center transition-all ${
                          isSel ? 'bg-red-600 border-red-600' : 'border-white/[0.15]'
                        }`}>
                          {isSel && <Check className="w-3 h-3 text-white" />}
                        </div>
                      </button>
                    );
                  })

                  )}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4
                            border-t border-white/[0.08] bg-white/[0.01] flex-shrink-0">
              <button onClick={() => setShowAddModal(false)}
                      className="px-5 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.08]
                                 text-white/70 text-base transition-colors">
                Отмена
              </button>
              <button onClick={handleAddMembers}
                      disabled={!selectedUsers.size || addingMembers}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-800 hover:bg-red-700
                                 text-white text-base font-medium transition-colors
                                 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-red-900/30">
                {addingMembers
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <UserPlus className="w-4 h-4" />}
                Добавить{selectedUsers.size > 0 ? ` (${selectedUsers.size})` : ''}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}