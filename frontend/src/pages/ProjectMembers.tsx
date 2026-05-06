// components/ProjectMembers.tsx
import { useState, useEffect } from 'react';
import { Users, UserPlus, Loader2, X, Crown, Shield, User, Eye, Building2, Search } from 'lucide-react';
import { projectsApi, counterpartiesApi } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import type { Project, CounterpartyCustomer } from '../types';
import { useToast } from '../components/ui/use-toast';

interface ProjectMembersProps {
  project: Project;
  onUpdate: (project: Project) => void;
}

const ROLE_OPTIONS = [
  { value: 'owner', label: 'Владелец', icon: Crown, color: 'text-amber-400' },
  { value: 'manager', label: 'Управляющий', icon: Shield, color: 'text-blue-400' },
  { value: 'member', label: 'Участник', icon: User, color: 'text-green-400' },
  { value: 'viewer', label: 'Наблюдатель', icon: Eye, color: 'text-gray-400' },
  { value: 'customer', label: 'Клиент', icon: Building2, color: 'text-purple-400' },
  { value: 'customer_admin', label: 'Администратор клиента', icon: Building2, color: 'text-purple-400' },
];

const ROLE_LABELS: Record<string, string> = {
  owner: 'Владелец',
  manager: 'Управляющий',
  member: 'Участник',
  viewer: 'Наблюдатель',
  customer: 'Клиент',
  customer_admin: 'Админ клиента',
};

export default function ProjectMembers({ project, onUpdate }: ProjectMembersProps) {
  const { user } = useAuthStore();
  const { toast } = useToast();
  const [isAdding, setIsAdding] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [employees, setEmployees] = useState<CounterpartyCustomer[]>([]);
  const [filteredEmployees, setFilteredEmployees] = useState<CounterpartyCustomer[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<string>('member');
  const [loading, setLoading] = useState(false);
  const [loadingEmployees, setLoadingEmployees] = useState(false);

  // Загружаем сотрудников компании при открытии формы
  useEffect(() => {
    if (isAdding && project.counterparty_id) {
      loadEmployees();
    }
  }, [isAdding, project.counterparty_id]);

  // Фильтрация сотрудников по поиску
  useEffect(() => {
    if (searchQuery.trim()) {
      const filtered = employees.filter(emp =>
        emp.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (emp.full_name && emp.full_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        emp.username.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredEmployees(filtered);
    } else {
      setFilteredEmployees(employees);
    }
  }, [searchQuery, employees]);

  const loadEmployees = async () => {
    if (!project.counterparty_id) return;
    
    setLoadingEmployees(true);
    try {
      // Получаем всех сотрудников контрагента
      const response = await counterpartiesApi.getCustomers(project.counterparty_id, 1, 100);
      // Исключаем уже добавленных участников
      const existingUserIds = new Set(project.memberships?.map(m => m.user_id) || []);
      const availableEmployees = response.items.filter(emp => !existingUserIds.has(emp.id));
      setEmployees(availableEmployees);
      setFilteredEmployees(availableEmployees);
    } catch (error) {
      console.error('Failed to load employees:', error);
      toast({ title: 'Ошибка', description: 'Не удалось загрузить список сотрудников', variant: 'destructive' });
    } finally {
      setLoadingEmployees(false);
    }
  };

  const getRoleIcon = (role: string) => {
    const option = ROLE_OPTIONS.find(r => r.value === role);
    if (option) {
      const Icon = option.icon;
      return <Icon className={`w-4 h-4 ${option.color}`} />;
    }
    return <User className="w-4 h-4 text-gray-400" />;
  };

  const handleAddMember = async () => {
    if (!selectedUserId) return;

    setLoading(true);
    try {
      const updatedProject = await projectsApi.addMember(project.id, {
        user_id: selectedUserId,
        project_role: selectedRole as any,
      });
      
      onUpdate(updatedProject);
      toast({ title: 'Участник добавлен', description: 'Пользователь успешно добавлен в проект' });
      
      // Сброс формы
      setSelectedUserId(null);
      setSearchQuery('');
      setSelectedRole('member');
      setIsAdding(false);
    } catch (error) {
      console.error('Failed to add member:', error);
      toast({ title: 'Ошибка', description: 'Не удалось добавить участника', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'owner': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'manager': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'member': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'viewer': return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
      case 'customer': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'customer_admin': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const isCurrentUser = (userId: string) => {
    return user?.user_id === userId;
  };

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-white/60" />
          <h3 className="text-[16px] font-semibold text-white">Участники проекта</h3>
          <span className="px-2 py-0.5 rounded-full bg-white/10 text-white/50 text-sm">
            {project.memberships?.length || 0}
          </span>
        </div>
        
        <button
          onClick={() => setIsAdding(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 transition-colors text-white text-sm"
        >
          <UserPlus className="w-4 h-4" />
          Добавить участника
        </button>
      </div>

      {/* Форма добавления */}
      {isAdding && (
        <div className="bg-white/5 rounded-xl p-5 border border-white/10">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-white font-medium">Добавить участника</h4>
            <button
              onClick={() => {
                setIsAdding(false);
                setSelectedUserId(null);
                setSearchQuery('');
              }}
              className="p-1 rounded-lg hover:bg-white/10 text-white/50"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {!selectedUserId ? (
            <div className="space-y-4">
              {/* Поиск сотрудников */}
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/40" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Поиск по имени или email..."
                  className="input-field pl-11 py-3 w-full"
                />
              </div>

              {/* Список сотрудников */}
              {loadingEmployees ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-white/30" />
                </div>
              ) : filteredEmployees.length === 0 ? (
                <div className="text-center py-8 text-white/40">
                  <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>{searchQuery ? 'Сотрудники не найдены' : 'Нет доступных сотрудников для добавления'}</p>
                  {!searchQuery && (
                    <p className="text-sm mt-1">Все сотрудники уже добавлены в проект</p>
                  )}
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {filteredEmployees.map((employee) => (
                    <button
                      key={employee.id}
                      onClick={() => setSelectedUserId(employee.id)}
                      className="w-full flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors text-left"
                    >
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-neutral-700 to-neutral-800 flex items-center justify-center">
                        <User className="w-5 h-5 text-neutral-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-white font-medium truncate">
                          {employee.full_name || employee.username}
                        </p>
                        <p className="text-white/40 text-sm truncate">{employee.email}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Выбранный сотрудник */}
              {(() => {
                const selectedEmp = employees.find(e => e.id === selectedUserId);
                return (
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-purple-700 flex items-center justify-center">
                      <User className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="text-white font-medium">{selectedEmp?.full_name || selectedEmp?.username}</p>
                      <p className="text-white/50 text-sm">{selectedEmp?.email}</p>
                    </div>
                    <button
                      onClick={() => setSelectedUserId(null)}
                      className="p-1 rounded-lg hover:bg-white/10 text-white/50"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                );
              })()}

              {/* Выбор роли */}
              <div>
                <label className="block text-white/60 text-sm mb-2">Роль в проекте</label>
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="select-field w-full"
                >
                  {ROLE_OPTIONS.map(role => (
                    <option key={role.value} value={role.value}>{role.label}</option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setSelectedUserId(null)}
                  className="flex-1 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors text-white"
                >
                  Назад
                </button>
                <button
                  onClick={handleAddMember}
                  disabled={loading}
                  className="flex-1 btn-primary"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Добавить'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Список участников */}
      <div className="space-y-2">
        {project.memberships?.length === 0 ? (
          <div className="text-center py-8 text-white/40">
            <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Нет участников</p>
            <p className="text-sm">Добавьте первого участника в проект</p>
          </div>
        ) : (
          project.memberships?.map((membership) => {
            const isOwner = membership.project_role === 'owner';
            return (
              <div
                key={membership.user_id}
                className={`flex items-center justify-between p-4 rounded-xl transition-colors ${
                  isCurrentUser(membership.user_id) 
                    ? 'bg-gradient-to-r from-red-500/10 to-red-600/5 border border-red-500/30' 
                    : 'bg-white/5 hover:bg-white/10'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-neutral-700 to-neutral-800 flex items-center justify-center">
                    <User className="w-5 h-5 text-neutral-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-white font-medium">
                        {membership.user_id === project.owner_id ? 'Владелец' : 'Участник'}
                      </p>
                      {isCurrentUser(membership.user_id) && (
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-400">
                          Вы
                        </span>
                      )}
                    </div>
                    <p className="text-white/40 text-sm">ID: {membership.user_id.slice(0, 8)}...</p>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium ${getRoleBadgeColor(membership.project_role)}`}>
                    {getRoleIcon(membership.project_role)}
                    <span>{ROLE_LABELS[membership.project_role] || membership.project_role}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}