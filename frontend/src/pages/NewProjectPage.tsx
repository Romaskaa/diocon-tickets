// pages/NewProjectPage.tsx
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, Loader2, Building2, CheckCircle2, User, Search, Crown, 
  Sparkles, AlertCircle, CheckCircle, XCircle, ChevronDown
} from 'lucide-react';
import { projectsApi, counterpartiesApi, usersApi } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useToast } from '../components/ui/use-toast';
import type { Counterparty } from '../types';

interface SimpleUser {
  id: string;
  username: string;
  full_name: string | null;
  email: string;
  role: string;
}

interface KeySuggestionResponse {
  key: string;
}

interface KeyAvailabilityResponse {
  available: boolean;
  suggestions: string[];
}

export default function NewProjectPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { toast } = useToast();
  
  const [name, setName] = useState('');
  const [key, setKey] = useState('');
  const [description, setDescription] = useState('');
  const [counterpartyId, setCounterpartyId] = useState('');
  const [counterparties, setCounterparties] = useState<Counterparty[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  
  // AI состояния
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null);
  const [keyValidating, setKeyValidating] = useState(false);
  const [keyAvailability, setKeyAvailability] = useState<{
    available: boolean;
    suggestions: string[];
  } | null>(null);
  
  // Для выбора владельца проекта
  const [users, setUsers] = useState<SimpleUser[]>([]);
  const [selectedOwner, setSelectedOwner] = useState<SimpleUser | null>(null);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [showOwnerDropdown, setShowOwnerDropdown] = useState(false);
  
  const counterpartyDropdownRef = useRef<HTMLDivElement>(null);
  const ownerDropdownRef = useRef<HTMLDivElement>(null);

  const isSupport = user?.role === 'support_agent' || 
                    user?.role === 'support_manager' || 
                    user?.role === 'admin';

  // Валидация ключа
  const isValidKey = (key: string): boolean => {
    if (!key) return false;
    // Ключ должен быть 2-10 символов, начинаться с буквы, содержать только буквы, цифры или подчёркивания
    const keyRegex = /^[A-Za-zА-Яа-я][A-Za-zА-Яа-я0-9_]{1,9}$/;
    return keyRegex.test(key);
  };

  // Закрытие дропдаунов при клике вне
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (counterpartyDropdownRef.current && !counterpartyDropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
      if (ownerDropdownRef.current && !ownerDropdownRef.current.contains(event.target as Node)) {
        setShowOwnerDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!isSupport) {
      toast({ title: 'Доступ запрещён', description: 'Только поддержка может создавать проекты', variant: 'destructive' });
      navigate('/projects');
    }
  }, [isSupport]);

  useEffect(() => {
    loadCounterparties();
  }, []);

  // Загрузка пользователей при выборе организации
  useEffect(() => {
    if (counterpartyId) {
      loadUsers(counterpartyId);
    } else {
      setUsers([]);
      setSelectedOwner(null);
    }
  }, [counterpartyId]);

  // AI генерация ключа при изменении названия
  useEffect(() => {
    if (name && name.length > 2) {
      const timer = setTimeout(() => {
        generateKeySuggestion();
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [name]);

  // Проверка доступности ключа при его изменении (только если ключ валидный)
  useEffect(() => {
    if (key && isValidKey(key)) {
      const timer = setTimeout(() => {
        checkKeyAvailability();
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setKeyAvailability(null);
    }
  }, [key]);

  const loadCounterparties = async () => {
    setLoading(true);
    try {
      const response = await counterpartiesApi.getAll(1, 100);
      setCounterparties(response.items);
    } catch (error) {
      console.error('Failed to load counterparties:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async (counterpartyId: string) => {
    setLoadingUsers(true);
    try {
      const response = await usersApi.getCustomers(counterpartyId, 1, 100);
      const formattedUsers: SimpleUser[] = response.items.map(customer => ({
        id: customer.id,
        username: customer.username,
        full_name: customer.full_name,
        email: customer.email,
        role: customer.role,
      }));
      
      // СОЗДАЁМ СПИСОК ПОЛЬЗОВАТЕЛЕЙ, ВСЕГДА ВКЛЮЧАЯ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
      const currentUserObj: SimpleUser = {
        id: user?.user_id || '',
        username: user?.username || '',
        full_name: user?.full_name || null,
        email: user?.email || '',
        role: user?.role || 'admin',
      };
      
      // Всегда добавляем текущего пользователя в начало списка
      let allUsers: SimpleUser[] = [currentUserObj];
      
      // Добавляем остальных пользователей, исключая дубликат текущего
      const otherUsers = formattedUsers.filter(u => u.id !== user?.user_id);
      allUsers = [...allUsers, ...otherUsers];
      
      setUsers(allUsers);
      
      // ВСЕГДА ВЫБИРАЕМ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ ПО УМОЛЧАНИЮ
      setSelectedOwner(currentUserObj);
      
    } catch (error) {
      console.error('Failed to load users:', error);
      // При ошибке всё равно устанавливаем текущего пользователя
      if (user?.user_id) {
        const currentUserObj: SimpleUser = {
          id: user.user_id,
          username: user.username || '',
          full_name: user.full_name || null,
          email: user.email || '',
          role: user.role || 'admin',
        };
        setUsers([currentUserObj]);
        setSelectedOwner(currentUserObj);
      }
    } finally {
      setLoadingUsers(false);
    }
  };

  // AI: генерация ключа из названия
  const generateKeySuggestion = async () => {
    if (!name || name.length < 2) return;
    
    setAiLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/projects/key-suggestion?name=${encodeURIComponent(name)}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data: KeySuggestionResponse = await response.json();
      setAiSuggestion(data.key);
      setKey(data.key);
    } catch (error) {
      console.error('Failed to get key suggestion:', error);
    } finally {
      setAiLoading(false);
    }
  };

  // Проверка доступности ключа
  const checkKeyAvailability = async () => {
    if (!key || !isValidKey(key)) return;
    
    setKeyValidating(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/projects/keys/${encodeURIComponent(key)}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );
      
      if (response.status === 400) {
        setKeyAvailability(null);
        return;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data: KeyAvailabilityResponse = await response.json();
      setKeyAvailability(data);
      
      if (!data.available && data.suggestions && data.suggestions.length > 0 && !keyAvailability?.available) {
        toast({
          title: 'Ключ занят',
          description: `Предлагаем: ${data.suggestions.slice(0, 3).join(', ')}`,
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Failed to check key availability:', error);
      setKeyAvailability(null);
    } finally {
      setKeyValidating(false);
    }
  };

  // Применить предложение
  const applySuggestion = (suggestedKey: string) => {
    setKey(suggestedKey);
    setKeyAvailability(null);
  };

  const getCounterpartyDisplay = (cp: Counterparty) => {
    return cp.name || cp.legal_name || cp.inn || 'Без названия';
  };

  const getUserDisplayName = (u: SimpleUser) => {
    return u.full_name || u.username || u.email;
  };

  const filteredCounterparties = counterparties.filter(cp =>
    getCounterpartyDisplay(cp).toLowerCase().includes(search.toLowerCase()) ||
    cp.inn?.includes(search)
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !key || !counterpartyId) {
      toast({ title: 'Ошибка', description: 'Заполните все обязательные поля', variant: 'destructive' });
      return;
    }

    if (!isValidKey(key)) {
      toast({ title: 'Ошибка', description: 'Ключ должен быть 2-10 символов, начинаться с буквы, содержать только буквы, цифры или подчёркивания', variant: 'destructive' });
      return;
    }

    if (!selectedOwner) {
      toast({ title: 'Ошибка', description: 'Выберите владельца проекта', variant: 'destructive' });
      return;
    }

    if (keyAvailability && !keyAvailability.available) {
      toast({ title: 'Ошибка', description: 'Ключ уже занят, выберите другой', variant: 'destructive' });
      return;
    }

    setSubmitting(true);
    try {
      await projectsApi.create({
        name,
        key: key.toUpperCase(),
        description: description || undefined,
        counterparty_id: counterpartyId,
        owner_id: selectedOwner.id,
      });
      
      toast({ title: 'Успешно', description: 'Проект создан' });
      navigate('/projects');
    } catch (error: any) {
      console.error('Failed to create project:', error);
      if (error.response?.status === 409) {
        toast({ title: 'Ошибка', description: 'Проект с таким ключом уже существует', variant: 'destructive' });
      } else if (error.response?.status === 400) {
        toast({ title: 'Ошибка', description: error.response?.data?.detail?.[0]?.msg || 'Неверный формат ключа', variant: 'destructive' });
      } else {
        toast({ title: 'Ошибка', description: 'Не удалось создать проект', variant: 'destructive' });
      }
    } finally {
      setSubmitting(false);
    }
  };

  const getKeyInputBorderClass = () => {
    if (!key) return '';
    if (!isValidKey(key)) return 'border-red-500/50 focus:border-red-500';
    if (keyAvailability?.available) return 'border-green-500/50 focus:border-green-500';
    if (keyAvailability && !keyAvailability.available) return 'border-red-500/50 focus:border-red-500';
    return '';
  };

  const getKeyStatusIcon = () => {
    if (keyValidating) {
      return <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />;
    }
    if (!key) return null;
    if (!isValidKey(key)) {
      return <XCircle className="w-5 h-5 text-red-400" />;
    }
    if (keyAvailability?.available) {
      return <CheckCircle className="w-5 h-5 text-green-400" />;
    }
    if (keyAvailability && !keyAvailability.available) {
      return <XCircle className="w-5 h-5 text-red-400" />;
    }
    return null;
  };

  return (
    <div className="max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center gap-6 mb-8">
        <button
          onClick={() => navigate('/projects')}
          className="p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
        >
          <ArrowLeft className="w-6 h-6 text-white" />
        </button>
        <div>
          <h1 className="text-4xl font-bold text-white">Создание проекта</h1>
          <p className="text-white/60 mt-1">Новый проект для контрагента</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="glass-card p-8 space-y-8">

        {/* Организация */}
        <div>
          <label className="block text-lg font-semibold text-white mb-2">
            Контрагент <span className="text-red-400">*</span>
          </label>
          <div className="relative" ref={counterpartyDropdownRef}>
            <div className="relative">
              <Building2 className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/40" />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setShowDropdown(true);
                }}
                onFocus={() => setShowDropdown(true)}
                placeholder="Поиск контрагента..."
                className="input-field pl-12 py-4 text-lg w-full"
              />
            </div>
            
            {showDropdown && (
              <div className="absolute z-50 mt-2 w-full bg-[#1c1c1c] border border-white/20 rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                {loading ? (
                  <div className="p-8 text-center">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto text-white/50" />
                    <p className="text-white/50 mt-3">Загрузка контрагнета...</p>
                  </div>
                ) : filteredCounterparties.length === 0 ? (
                  <div className="p-8 text-center">
                    <Building2 className="w-12 h-12 mx-auto mb-3 text-white/20" />
                    <p className="text-white/50 text-lg">Ничего не найдено</p>
                  </div>
                ) : (
                  filteredCounterparties.map((cp) => (
                    <button
                      key={cp.id}
                      type="button"
                      onClick={() => {
                        setCounterpartyId(cp.id);
                        setSearch(getCounterpartyDisplay(cp));
                        setShowDropdown(false);
                      }}
                      className="w-full text-left p-5 hover:bg-white/10 transition-colors border-b border-white/10 last:border-0"
                    >
                      <div className="font-semibold text-white text-base">{getCounterpartyDisplay(cp)}</div>
                      {cp.legal_name && cp.legal_name !== cp.name && (
                        <div className="text-sm text-white/50 mt-1">{cp.legal_name}</div>
                      )}
                      {cp.inn && <div className="text-xs text-white/40 mt-1">ИНН: {cp.inn}</div>}
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
          {counterpartyId && (
            <div className="mt-4 p-4 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-400" />
              <span className="text-white">Контрагнет выбран</span>
            </div>
          )}
        </div>

        {/* Название проекта с AI помощником */}
        <div>
          <label className="block text-lg font-semibold text-white mb-2">
            Название проекта <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Корпоративный сайт компании"
              className="input-field py-4 text-lg w-full pr-12"
              required
            />
            {aiLoading && (
              <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
              </div>
            )}
            {!aiLoading && aiSuggestion && name && (
              <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                <Sparkles className="w-5 h-5 text-purple-400" />
              </div>
            )}
          </div>
          
          {/* AI подсказка */}
          {aiSuggestion && name && !aiLoading && (
            <div className="mt-3 p-4 rounded-xl bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-purple-400" />
                  <span className="text-white">Предложенный ключ:</span>
                  <span className="text-purple-400 font-mono font-bold text-lg">{aiSuggestion}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setKey(aiSuggestion)}
                  className="px-3 py-1 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 text-sm transition-colors"
                >
                  Использовать
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Ключ проекта с проверкой доступности */}
        <div>
          <label className="block text-lg font-semibold text-white mb-2">
            Ключ проекта <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            <input
              type="text"
              value={key}
              onChange={(e) => setKey(e.target.value.toUpperCase())}
              placeholder="Например: PROJ"
              className={`input-field py-4 text-lg w-full font-mono pr-12 ${getKeyInputBorderClass()}`}
              required
              maxLength={10}
            />
            <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
              {getKeyStatusIcon()}
            </div>
          </div>
          
          <p className="text-white/40 text-sm mt-1">
            Уникальный идентификатор проекта. 2-10 символов, начинается с буквы, только буквы, цифры или подчёркивания
          </p>
          
          {/* Ошибка валидации ключа */}
          {key && !isValidKey(key) && (
            <div className="mt-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
                <div>
                  <p className="text-red-400 font-medium">Неверный формат ключа</p>
                  <p className="text-white/70 text-sm">
                    Ключ должен быть 2-10 символов, начинаться с буквы и содержать только буквы, цифры или подчёркивания
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Статус доступности ключа */}
          {key && isValidKey(key) && keyAvailability && !keyAvailability.available && (
            <div className="mt-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
                <div className="flex-1">
                  <p className="text-red-400 font-medium">Ключ уже занят</p>
                  {keyAvailability.suggestions && keyAvailability.suggestions.length > 0 && (
                    <div className="mt-2">
                      <p className="text-white/70 text-sm mb-2">Предлагаем альтернативы:</p>
                      <div className="flex flex-wrap gap-2">
                        {keyAvailability.suggestions.slice(0, 5).map((suggestion) => (
                          <button
                            key={suggestion}
                            type="button"
                            onClick={() => applySuggestion(suggestion)}
                            className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm transition-colors font-mono"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {key && isValidKey(key) && keyAvailability?.available && (
            <div className="mt-3 p-3 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-green-400 text-sm">Ключ доступен</span>
            </div>
          )}
        </div>

        {/* Владелец проекта (Инициатор) */}
        {counterpartyId && (
          <div>
            <label className="block text-lg font-semibold text-white mb-2">
              <Crown className="inline w-5 h-5 mr-2 text-yellow-400" />
              Владелец проекта <span className="text-red-400">*</span>
            </label>
            
            {/* Отображение выбранного владельца */}
            {selectedOwner && (
              <div className="mb-3 p-4 rounded-xl bg-green-500/10 border border-green-500/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center">
                      {selectedOwner.id === user?.user_id ? (
                        <User className="w-5 h-5 text-white" />
                      ) : (
                        <Crown className="w-5 h-5 text-white" />
                      )}
                    </div>
                    <div>
                      <div className="text-white font-medium">
                        {getUserDisplayName(selectedOwner)}
                        {selectedOwner.id === user?.user_id && (
                          <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                            Вы (владелец по умолчанию)
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-white/50">{selectedOwner.email}</div>
                    </div>
                  </div>
                  
                  {/* Кнопка смены владельца */}
                  <button
                    type="button"
                    onClick={() => setShowOwnerDropdown(!showOwnerDropdown)}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm transition-colors flex items-center gap-1"
                  >
                    {showOwnerDropdown ? 'Скрыть' : 'Изменить'}
                    <ChevronDown className={`w-4 h-4 transition-transform ${showOwnerDropdown ? 'rotate-180' : ''}`} />
                  </button>
                </div>
              </div>
            )}
            
            {/* Выпадающий список для смены владельца */}
            {showOwnerDropdown && (
              <div className="relative" ref={ownerDropdownRef}>
                <div className="absolute z-50 mt-0 w-full bg-[#1c1c1c] border border-white/20 rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                  {loadingUsers ? (
                    <div className="p-8 text-center">
                      <Loader2 className="w-8 h-8 animate-spin mx-auto text-white/50" />
                      <p className="text-white/50 mt-3">Загрузка пользователей...</p>
                    </div>
                  ) : users.length === 0 ? (
                    <div className="p-8 text-center">
                      <User className="w-12 h-12 mx-auto mb-3 text-white/20" />
                      <p className="text-white/50 text-lg">Нет пользователей</p>
                      <p className="text-white/30 text-sm mt-1">Вы будете владельцем проекта</p>
                    </div>
                  ) : (
                    users.map((u) => {
                      const isCurrentUser = u.id === user?.user_id;
                      const isSelected = selectedOwner?.id === u.id;
                      
                      return (
                        <button
                          key={u.id}
                          type="button"
                          onClick={() => {
                            setSelectedOwner(u);
                            setShowOwnerDropdown(false);
                          }}
                          className={`w-full text-left p-4 hover:bg-white/10 transition-colors border-b border-white/10 last:border-0 ${
                            isSelected ? 'bg-green-500/10' : ''
                          } ${
                            isCurrentUser ? 'bg-gradient-to-r from-green-500/5 to-transparent' : ''
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                              isCurrentUser 
                                ? 'bg-gradient-to-br from-green-500 to-green-600'
                                : 'bg-gradient-to-br from-yellow-500 to-yellow-600'
                            }`}>
                              {isCurrentUser ? (
                                <User className="w-5 h-5 text-white" />
                              ) : (
                                <Crown className="w-5 h-5 text-white" />
                              )}
                            </div>
                            <div className="flex-1">
                              <div className="font-semibold text-white">
                                {getUserDisplayName(u)}
                                {isCurrentUser && (
                                  <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                                    Вы (по умолчанию)
                                  </span>
                                )}
                                {!isCurrentUser && u.role === 'customer_admin' && (
                                  <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">
                                    Админ
                                  </span>
                                )}
                              </div>
                              <div className="text-sm text-white/50">{u.email}</div>
                            </div>
                            {isSelected && (
                              <CheckCircle2 className="w-5 h-5 text-green-400" />
                            )}
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* Информация о владельце по умолчанию */}
            {selectedOwner && selectedOwner.id === user?.user_id && !showOwnerDropdown && (
              <div className="mt-2 text-xs text-green-400/60">
                Вы назначены владельцем проекта по умолчанию
              </div>
            )}
          </div>
        )}

        {/* Описание */}
        <div>
          <label className="block text-lg font-semibold text-white mb-2">
            Описание проекта
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Опишите цели и задачи проекта..."
            rows={5}
            className="input-field py-4 text-lg resize-none w-full"
          />
        </div>

        {/* Кнопки */}
        <div className="flex justify-end gap-4 pt-4 border-t border-white/10">
          <button
            type="button"
            onClick={() => navigate('/projects')}
            className="px-6 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-white font-medium transition-colors"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={submitting || !name || !key || !counterpartyId || !selectedOwner || !isValidKey(key) || (keyAvailability && !keyAvailability.available)}
            className="btn-primary px-8 py-3 text-lg font-semibold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle2 className="w-5 h-5" />}
            Создать проект
          </button>
        </div>
      </form>
    </div>

    
  );
}