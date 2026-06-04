import { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Ticket,
  CheckSquare,
  Building2,
  UserPlus,
  Bell,
  User,
  X,
  Building,
  FolderOpen,
  Package,
  ChevronLeft,
} from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { useUnreadNotifications } from '../../hooks/useUnreadNotifications';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

const ROLE_LABEL: Record<string, string> = {
  admin: 'Администратор',
  support_manager: 'Менеджер поддержки',
  support_agent: 'Агент поддержки',
  executor: 'Исполнитель',
  customer_admin: 'Админ клиента',
  customer: 'Клиент',
};

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { count: unreadNotifications } = useUnreadNotifications();

  const isCustomer = user?.role === 'customer' || user?.role === 'customer_admin';
  const canInvite = ['support_agent', 'support_manager', 'executor', 'admin'].includes(user?.role || '');

  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem('sidebarCollapsed') === 'true';
  });

  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', isCollapsed.toString());
  }, [isCollapsed]);

  const mainNavItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Главная' },
    { to: '/tickets', icon: Ticket, label: 'Заявки' },
    ...(isCustomer
      ? [{ to: '/my-company', icon: Building, label: 'Моя компания' }]
      : [{ to: '/counterparties', icon: Building2, label: 'Контрагенты' }]
    ),
    { to: '/projects', icon: FolderOpen, label: 'Проекты' },
    ...(canInvite ? [{ to: '/products', icon: Package, label: 'Продукты' }] : []),
    ...(canInvite ? [{ to: '/tasks', icon: CheckSquare, label: 'Задачи сотрудников' }] : []),
    ...(canInvite ? [{ to: '/invitations', icon: UserPlus, label: 'Приглашения' }] : []),
  ];

  const accountItems = [
    { to: '/notifications', icon: Bell, label: 'Уведомления', badge: unreadNotifications },
    { to: '/profile', icon: User, label: 'Профиль' },
  ];

  // ─── Nav item ───
  const NavItem = ({ to, icon: Icon, label, badge }: {
    to: string; icon: any; label: string; badge?: number;
  }) => (
    <NavLink
      to={to}
      onClick={onClose}
      title={isCollapsed ? label : undefined}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-xl text-l font-medium
         transition-all duration-200 ${isCollapsed ? 'justify-center px-2 py-4.5 mx-auto w-11 h-11' : 'px-4 py-3.5'}
         ${isActive
          ? 'bg-[var(--hover-1)] '
          : 'text-[var(--text-secondary)] hover:bg-[var(--hover-1)] hover:text-[var(--text-primary)]'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {/* Активный индикатор слева */}
          {isActive && !isCollapsed && (
            <span
              className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full
                         bg-gradient-to-b from-[var(--accent-light)] to-[var(--accent)]"
              style={{ boxShadow: '0 0 8px var(--accent-glow)' }}
            />
          )}

          {/* Иконка с бейджем */}
          <div className="relative flex-shrink-0">
            <Icon
              className={`w-6 h-6 transition-transform group-hover:scale-110
                         ${isActive ? 'text-[var(--accent-light)]' : ''}`}
            />
            {/* Бейдж на иконке (для свёрнутого режима) */}
            {badge != null && badge > 0 && isCollapsed && (
              <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1
                               flex items-center justify-center rounded-full
                               bg-[var(--accent)] text-white text-[10px] font-bold
                               ring-2 ring-[var(--bg-primary)] animate-pulse">
                {badge > 99 ? '99+' : badge}
              </span>
            )}
          </div>

          {!isCollapsed && (
            <>
              <span className="truncate flex-1">{label}</span>

              {/* Бейдж рядом с текстом (для развёрнутого режима) */}
              {badge != null && badge > 0 && (
                <span className="ml-auto px-2 py-0.5 min-w-[22px] text-center
                                 rounded-full bg-[var(--accent)] text-white
                                 text-xs font-bold animate-pulse">
                  {badge > 99 ? '99+' : badge}
                </span>
              )}
            </>
          )}

          {/* Tooltip для свёрнутого режима */}
          {isCollapsed && (
            <span className="pointer-events-none absolute left-full ml-3 px-2.5 py-1.5 rounded-lg
                             bg-[var(--bg-card)] border border-[var(--border-color)]
                             text-xs font-medium text-[var(--text-primary)] whitespace-nowrap
                             opacity-0 group-hover:opacity-100 transition-opacity duration-150
                             shadow-lg z-50 flex items-center gap-2">
              {label}
              {badge != null && badge > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-[var(--accent)] text-white text-[10px] font-bold">
                  {badge}
                </span>
              )}
            </span>
          )}
        </>
      )}
    </NavLink>
  );

  // ─── Section label ───
  const SectionLabel = ({ children }: { children: React.ReactNode }) => (
    !isCollapsed ? (
      <p className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">
        {children}
      </p>
    ) : (
      <div className="mx-auto w-8 h-px bg-[var(--border-color)] my-2" />
    )
  );

  const SidebarContent = ({ isMobile = false }: { isMobile?: boolean }) => (
    <div className="sidebar-bg flex flex-col h-full relative">
      {/* Header */}
      <div className={`flex items-center border-b border-[var(--border-color)]
                      ${isCollapsed && !isMobile ? 'p-4 justify-center' : 'p-4 justify-between gap-2'}`}>
        <NavLink
          to="/dashboard"
          onClick={onClose}
          className={`flex items-center gap-3 min-w-0 group
                     ${isCollapsed && !isMobile ? '' : 'flex-1'}`}
        >
          <div className="relative flex-shrink-0">
            <div className="absolute inset-0 bg-[var(--accent)]/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
            <img
              src="http://80.93.62.177:8000/media/images/Logo_bez_fona_bez_teksta.width-80.height-80.png"
              alt="ДИО-Консалт"
              className="relative w-12 h-12 object-contain"
            />
          </div>
          {(!isCollapsed || isMobile) && (
            <div className="min-w-0">
              <h1 className="text-[var(--text-primary)] text-2xl">ДИО Деск</h1>
            </div>
          )}
        </NavLink>

        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--hover-1)] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className={`flex-1 overflow-y-auto overflow-x-hidden py-4
                      ${isCollapsed && !isMobile ? 'px-2' : 'px-3'}`}>
        <SectionLabel>Меню</SectionLabel>
        <div className="space-y-1 mb-6">
          {mainNavItems.map(item => (
            <NavItem key={item.to} {...item} />
          ))}
        </div>

        <SectionLabel>Аккаунт</SectionLabel>
        <div className="space-y-1">
          {accountItems.map(item => (
            <NavItem key={item.to} {...item} />
          ))}
        </div>
      </nav>
    </div>
  );

  return (
    <>
      {/* Desktop */}
      <aside
        className={`hidden lg:flex z-40 flex-col h-screen sticky top-0 border-r border-[var(--border-color)]
                   transition-all duration-300 sidebar-bg relative
                   ${isCollapsed ? 'w-20' : 'w-72'}`}
      >
        <SidebarContent />

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? 'Развернуть' : 'Свернуть'}
          className="absolute top-7 -right-3 w-6 h-6 rounded-full
                     bg-[var(--bg-card)] border border-[var(--border-color)]
                     flex items-center justify-center
                     text-[var(--text-muted)] hover:text-[var(--accent-light)]
                     hover:border-[var(--accent)]/40 hover:scale-110
                     shadow-md transition-all duration-200"
        >
          <ChevronLeft
            className={`w-3.5 h-3.5 transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`}
          />
        </button>
      </aside>

      {/* Mobile */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 lg:hidden"
            onClick={onClose}
          />
          <aside className="fixed right-0 top-0 h-full w-80 sidebar-bg border-l border-[var(--border-color)] z-50 lg:hidden overflow-y-auto">
            <SidebarContent isMobile />
          </aside>
        </>
      )}
    </>
  );
}