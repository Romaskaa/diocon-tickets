import { useState } from 'react';
import { 
  Bell, 
  Settings,
  Trash2,
  Check,
  FileText,
  MessageSquare,
  UserPlus,
  AlertTriangle
} from 'lucide-react';

interface Notification {
  id: string;
  type: 'ticket' | 'comment' | 'assignment' | 'system';
  title: string;
  message: string;
  time: string;
  read: boolean;
}

export default function NotificationsPage() {
  const [activeTab, setActiveTab] = useState<'all' | 'settings'>('all');
  const [notifications, setNotifications] = useState<Notification[]>([
    {
      id: '1',
      type: 'ticket',
      title: 'Новая заявка',
      message: 'Создана заявка "Проблема с входом в систему"',
      time: '5 мин назад',
      read: false,
    },
    {
      id: '2',
      type: 'comment',
      title: 'Новый комментарий',
      message: 'Вам ответили в заявке #1234',
      time: '1 час назад',
      read: false,
    },
    {
      id: '3',
      type: 'assignment',
      title: 'Назначение',
      message: 'Вам назначена заявка #1235',
      time: '2 часа назад',
      read: true,
    },
  ]);

  const [settings, setSettings] = useState({
    emailNewTicket: true,
    emailAssignment: true,
    emailComment: true,
    emailResolved: false,
    pushEnabled: true,
    pushNewTicket: true,
    pushComment: true,
    soundEnabled: true,
  });

  const markAsRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const deleteNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'ticket': return FileText;
      case 'comment': return MessageSquare;
      case 'assignment': return UserPlus;
      default: return AlertTriangle;
    }
  };

  const getIconColor = (type: string) => {
    switch (type) {
      case 'ticket': return 'bg-blue-500/20 text-blue-400';
      case 'comment': return 'bg-green-500/20 text-green-400';
      case 'assignment': return 'bg-purple-500/20 text-purple-400';
      default: return 'bg-yellow-500/20 text-yellow-400';
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className=" ">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Уведомления</h1>
        <p className="text-white/50 mt-1">Управление уведомлениями и настройками</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('all')}
          className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
        >
          <Bell className="w-4 h-4 mr-2 inline" />
          Все
          {unreadCount > 0 && (
            <span className="ml-2 px-2 py-0.5 rounded-full bg-red-800 text-white text-xs">
              {unreadCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
        >
          <Settings className="w-4 h-4 mr-2 inline" />
          Настройки
        </button>
      </div>

      {/* All Tab */}
      {activeTab === 'all' && (
        <div className="glass-card-static">
          {notifications.length > 0 && (
            <div className="flex items-center justify-between p-4 border-b border-white/5">
              <span className="text-sm text-white/50">
                {unreadCount > 0 ? `${unreadCount} непрочитанных` : 'Все прочитано'}
              </span>
              {unreadCount > 0 && (
                <button onClick={markAllAsRead} className="text-sm text-red-400 hover:text-red-300">
                  Прочитать все
                </button>
              )}
            </div>
          )}

          {notifications.length === 0 ? (
            <div className="p-12 text-center">
              <Bell className="w-12 h-12 text-white/20 mx-auto mb-4" />
              <p className="text-white/50">Нет уведомлений</p>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {notifications.map((n) => {
                const Icon = getIcon(n.type);
                return (
                  <div
                    key={n.id}
                    className={`p-4 hover:bg-white/5 transition-colors ${!n.read ? 'bg-white/[0.02]' : ''}`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${getIconColor(n.type)}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className={`font-medium ${n.read ? 'text-white/70' : 'text-white'}`}>
                              {n.title}
                            </p>
                            <p className="text-sm text-white/50 mt-0.5">{n.message}</p>
                            <p className="text-xs text-white/30 mt-1">{n.time}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {!n.read && (
                              <button
                                onClick={() => markAsRead(n.id)}
                                className="p-2 rounded-lg hover:bg-white/5 text-white/40 hover:text-green-400"
                                title="Прочитано"
                              >
                                <Check className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => deleteNotification(n.id)}
                              className="p-2 rounded-lg hover:bg-white/5 text-white/40 hover:text-red-400"
                              title="Удалить"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <div className="space-y-6">
          {/* Email */}
          <div className="glass-card-static p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Email-уведомления</h3>
            <div className="space-y-4">
              {[
                { key: 'emailNewTicket', label: 'Новая заявка', desc: 'Уведомления о новых заявках' },
                { key: 'emailAssignment', label: 'Назначение', desc: 'Когда вам назначают заявку' },
                { key: 'emailComment', label: 'Комментарии', desc: 'Новые комментарии в заявках' },
                { key: 'emailResolved', label: 'Решение заявки', desc: 'Когда заявка решена' },
              ].map((item) => (
                <div key={item.key} className="flex items-center justify-between p-4 rounded-xl bg-white/5">
                  <div>
                    <p className="font-medium text-white">{item.label}</p>
                    <p className="text-sm text-white/50">{item.desc}</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings[item.key as keyof typeof settings] as boolean}
                      onChange={(e) => setSettings({ ...settings, [item.key]: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-white/10 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-800" />
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Push */}
          <div className="glass-card-static p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Push-уведомления</h3>
            <div className="space-y-4">
              {[
                { key: 'pushEnabled', label: 'Включить push', desc: 'Разрешить push-уведомления' },
                { key: 'pushNewTicket', label: 'Новые заявки', desc: 'Push о новых заявках' },
                { key: 'pushComment', label: 'Комментарии', desc: 'Push о комментариях' },
              ].map((item) => (
                <div key={item.key} className="flex items-center justify-between p-4 rounded-xl bg-white/5">
                  <div>
                    <p className="font-medium text-white">{item.label}</p>
                    <p className="text-sm text-white/50">{item.desc}</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings[item.key as keyof typeof settings] as boolean}
                      onChange={(e) => setSettings({ ...settings, [item.key]: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-white/10 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-800" />
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Sound */}
          <div className="glass-card-static p-6">
            <div className="flex items-center justify-between p-4 rounded-xl bg-white/5">
              <div>
                <p className="font-medium text-white">Звуковые уведомления</p>
                <p className="text-sm text-white/50">Воспроизводить звук при новых уведомлениях</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.soundEnabled}
                  onChange={(e) => setSettings({ ...settings, soundEnabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-white/10 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-800" />
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
