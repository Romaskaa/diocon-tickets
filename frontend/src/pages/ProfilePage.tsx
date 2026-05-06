import { useState, useRef } from 'react';
import { 
  User, 
  Shield,
  Bell,
  Camera,
  Loader2,
  Building2,
  Check
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { authApi, counterpartiesApi } from '../api/client';
import { useToast } from '../components/ui/use-toast';
import type { Counterparty } from '../types';
import { useEffect } from 'react';

export default function ProfilePage() {
  const { user, setUser } = useAuthStore();
  const { toast } = useToast();
  
  const [activeTab, setActiveTab] = useState<'profile' | 'company' | 'security' | 'notifications'>('profile');
  const [uploading, setUploading] = useState(false);
  const [myCompany, setMyCompany] = useState<Counterparty | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isCustomer = user?.role === 'customer' || user?.role === 'customer_admin';

  useEffect(() => {
    if (isCustomer && user?.counterparty_id) {
      loadMyCompany();
    }
  }, [user]);

  const loadMyCompany = async () => {
    if (!user?.counterparty_id) return;
    try {
      const company = await counterpartiesApi.getById(user.counterparty_id);
      setMyCompany(company);
    } catch (error) {
      console.error('Failed to load company:', error);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast({ title: 'Ошибка', description: 'Выберите изображение', variant: 'destructive' });
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast({ title: 'Ошибка', description: 'Максимальный размер 5MB', variant: 'destructive' });
      return;
    }

    setUploading(true);
    try {
      const updatedProfile = await authApi.uploadAvatar(file);
      if (user) {
        setUser({
          ...user,
          avatar_url: updatedProfile.avatar_url,
          full_name: updatedProfile.full_name || user.full_name,
        });
      }
      toast({ title: 'Успешно', description: 'Аватар обновлён' });
    } catch (error) {
      toast({ title: 'Ошибка', description: 'Не удалось загрузить аватар', variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const getRoleLabel = (role: string) => {
    const labels: Record<string, string> = {
      customer: 'Клиент',
      customer_admin: 'Администратор клиента',
      support_agent: 'Агент поддержки',
      support_manager: 'Менеджер поддержки',
      executor: 'Исполнитель',
      admin: 'Администратор системы',
    };
    return labels[role] || role;
  };

  const tabs = [
    { id: 'profile' as const, label: 'Профиль', icon: User },
    ...(isCustomer ? [{ id: 'company' as const, label: 'Моя компания', icon: Building2 }] : []),
    { id: 'security' as const, label: 'Безопасность', icon: Shield },
    { id: 'notifications' as const, label: 'Уведомления', icon: Bell },
  ];

  return (
    <div className=" space-y-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Профиль</h1>
        <p className="text-white/50 mt-1">Управление аккаунтом и настройками</p>
      </div>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <div className="glass-card-static p-6">
            {/* Avatar */}
            <div className="text-center mb-6">
              <div className="relative inline-block">
                <div className="w-24 h-24 rounded-2xl overflow-hidden bg-gradient-to-br from-red-800 to-red-900 mx-auto">
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <User className="w-10 h-10 text-white" />
                    </div>
                  )}
                </div>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="absolute -bottom-2 -right-2 w-10 h-10 rounded-xl bg-red-800 hover:bg-red-700 flex items-center justify-center transition-colors"
                >
                  {uploading ? (
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                  ) : (
                    <Camera className="w-5 h-5 text-white" />
                  )}
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarUpload}
                  className="hidden"
                />
              </div>
              <h2 className="font-semibold text-white mt-4">
                {user?.full_name || user?.username || 'Пользователь'}
              </h2>
              <p className="text-sm text-white/50">{user?.email}</p>
              <span className="inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium bg-red-800/20 text-red-400 border border-red-800/30">
                {getRoleLabel(user?.role || '')}
              </span>
            </div>

            {/* Navigation */}
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                    activeTab === tab.id
                      ? 'bg-red-800/20 text-red-400'
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <tab.icon className="w-5 h-5" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="glass-card-static p-6">
              <h3 className="text-lg font-semibold text-white mb-6">Личная информация</h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Имя пользователя</label>
                  <input
                    type="text"
                    value={user?.username || ''}
                    disabled
                    className="input-field opacity-60"
                  />
                </div>
                <div>
                  <label className="label">Полное имя</label>
                  <input
                    type="text"
                    value={user?.full_name || ''}
                    disabled
                    className="input-field opacity-60"
                  />
                </div>
                <div>
                  <label className="label">Email</label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="input-field opacity-60"
                  />
                </div>
                <div>
                  <label className="label">Роль</label>
                  <input
                    type="text"
                    value={getRoleLabel(user?.role || '')}
                    disabled
                    className="input-field opacity-60"
                  />
                </div>
              </div>

              <p className="text-white/40 text-sm mt-6">
                Для изменения данных профиля обратитесь к администратору системы.
              </p>
            </div>
          )}

          {/* Company Tab */}
          {activeTab === 'company' && myCompany && (
            <div className="glass-card-static p-6">
              <h3 className="text-lg font-semibold text-white mb-6">Информация о компании</h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Название</label>
                  <input type="text" value={myCompany.name} disabled className="input-field opacity-60" />
                </div>
                <div>
                  <label className="label">Юридическое название</label>
                  <input type="text" value={myCompany.legal_name} disabled className="input-field opacity-60" />
                </div>
                <div>
                  <label className="label">Тип</label>
                  <input type="text" value={myCompany.counterparty_type} disabled className="input-field opacity-60" />
                </div>
                <div>
                  <label className="label">ИНН</label>
                  <input type="text" value={myCompany.inn} disabled className="input-field opacity-60" />
                </div>
                {myCompany.kpp && (
                  <div>
                    <label className="label">КПП</label>
                    <input type="text" value={myCompany.kpp} disabled className="input-field opacity-60" />
                  </div>
                )}
                {myCompany.okpo && (
                  <div>
                    <label className="label">ОКПО</label>
                    <input type="text" value={myCompany.okpo} disabled className="input-field opacity-60" />
                  </div>
                )}
                {myCompany.phone && (
                  <div>
                    <label className="label">Телефон</label>
                    <input type="text" value={myCompany.phone} disabled className="input-field opacity-60" />
                  </div>
                )}
                {myCompany.email && (
                  <div>
                    <label className="label">Email</label>
                    <input type="text" value={myCompany.email} disabled className="input-field opacity-60" />
                  </div>
                )}
              </div>

              {myCompany.address && (
                <div className="mt-6">
                  <label className="label">Адрес</label>
                  <input type="text" value={myCompany.address} disabled className="input-field opacity-60" />
                </div>
              )}
            </div>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className="glass-card-static p-6">
              <h3 className="text-lg font-semibold text-white mb-6">Безопасность</h3>
              
              <div className="space-y-6">
                <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
                        <Check className="w-5 h-5 text-green-400" />
                      </div>
                      <div>
                        <p className="font-medium text-white">Пароль</p>
                        <p className="text-sm text-white/50">Установлен</p>
                      </div>
                    </div>
                    <button className="btn-secondary text-sm">Изменить</button>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-yellow-400" />
                      </div>
                      <div>
                        <p className="font-medium text-white">Двухфакторная аутентификация</p>
                        <p className="text-sm text-white/50">Не настроена</p>
                      </div>
                    </div>
                    <button className="btn-secondary text-sm">Настроить</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="glass-card-static p-6">
              <h3 className="text-lg font-semibold text-white mb-6">Настройки уведомлений</h3>
              
              <div className="space-y-4">
                {[
                  { label: 'Новая заявка', desc: 'Уведомления о новых заявках' },
                  { label: 'Назначение заявки', desc: 'Когда вам назначают заявку' },
                  { label: 'Новый комментарий', desc: 'Комментарии в ваших заявках' },
                  { label: 'Решение заявки', desc: 'Когда заявка решена' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
                    <div>
                      <p className="font-medium text-white">{item.label}</p>
                      <p className="text-sm text-white/50">{item.desc}</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked className="sr-only peer" />
                      <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-800"></div>
                    </label>
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
