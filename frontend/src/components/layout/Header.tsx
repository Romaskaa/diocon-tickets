import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, Bell, User, LogOut, Settings, ChevronDown } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';

interface HeaderProps {
  onMenuClick: () => void;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Закрытие дропдауна при клике вне области
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDropdown]);

  const getRoleLabel = (role: string) => {
    const labels: Record<string, string> = {
      customer: 'Клиент',
      customer_admin: 'Админ клиента',
      support_agent: 'Агент поддержки',
      support_manager: 'Менеджер',
      executor: 'Исполнитель',
      admin: 'Администратор'
    };
    return labels[role] || role;
  };

  return (
    <header className="sticky py-3 top-0 z-30 bg-[#1c1c1c] backdrop-blur-xl border-b border-white/10">
      <div className="flex items-center justify-between px-6">
        {/* Mobile Logo */}
        <div className="flex items-center gap-4 lg:hidden">
          <img 
            src="http://80.93.62.177:8000/media/images/Logo_bez_fona_bez_teksta.width-80.height-80.png"
            alt="ДИО-Консалт"
            className="w-10 h-10 object-contain"
          />
          <span className="font-bold text-white text-lg">ДИО-Консалт</span>
        </div>

        {/* Desktop Spacer */}
        <div className="hidden lg:block" />

        {/* Right Side */}
        <div className="flex items-center gap-4">
          {/* Notifications */}
          <Link 
            to="/notifications"
            className="relative p-2 rounded-xl hover:bg-white/5 transition-colors"
          >
            <Bell className="w-6 h-6 text-white/70 hover:text-white transition-colors" />
            <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-600 rounded-full" />
          </Link>

          {/* User Menu */}
          <div ref={dropdownRef} className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-colors"
            >
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-10 h-10 rounded-full object-cover ring-2 ring-white/20" />
              ) : (
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-700 to-red-900 flex items-center justify-center">
                  <User className="w-5 h-5 text-white" />
                </div>
              )}
              <div className="hidden md:block text-left">
                <p className="text-white font-medium text-base">{user?.full_name || user?.username}</p>
                <p className="text-sm text-white/50">{getRoleLabel(user?.role || '')}</p>
              </div>
              <ChevronDown className="w-5 h-5 text-white/50 hidden md:block" />
            </button>

            {showDropdown && (
              <div className="absolute right-0 top-full mt-2 w-72 glass-card p-2 z-50">
                <div className="px-4 py-3 border-b border-white/10">
                  <p className="font-semibold text-white text-base">{user?.full_name || user?.username}</p>
                  <p className="text-sm text-white/50">{user?.email}</p>
                </div>
                <div className="py-2">
                  <Link
                    to="/profile"
                    onClick={() => setShowDropdown(false)}
                    className="flex items-center gap-3 px-4 py-3 text-white/70 hover:text-white hover:bg-white/5 rounded-xl transition-colors text-base"
                  >
                    <User className="w-5 h-5" />
                    Профиль
                  </Link>
                  <Link
                    to="/notifications"
                    onClick={() => setShowDropdown(false)}
                    className="flex items-center gap-3 px-4 py-3 text-white/70 hover:text-white hover:bg-white/5 rounded-xl transition-colors text-base"
                  >
                    <Settings className="w-5 h-5" />
                    Настройки
                  </Link>
                </div>
                <div className="pt-2 border-t border-white/10">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-3 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded-xl transition-colors text-base"
                  >
                    <LogOut className="w-5 h-5" />
                    Выйти
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Mobile Menu */}
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-xl hover:bg-white/5 transition-colors"
          >
            <Menu className="w-6 h-6 text-white" />
          </button>
        </div>
      </div>
    </header>
  );
}