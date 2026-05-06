import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  ArrowLeft, ArrowRight, Sparkles, Loader2, FileText, 
  Tag, Upload, X, CheckCircle2, File, Building2, Zap, Plus, Search, Users, FolderOpen, User 
} from 'lucide-react';
import { 
  SignalLow, SignalMedium, SignalHigh, Flame 
} from 'lucide-react';

import { useAuthStore } from '../stores/authStore';
import { ticketsApi, counterpartiesApi, projectsApi, usersApi } from '../api/client';
import { attachmentsApi, type Attachment } from '../api/attachments';
import type { Counterparty, TicketTag, TicketPriority, Project, User as UserType } from '../types';

const PRIORITIES = [
  { 
    value: 'Низкий', 
    label: 'Низкий', 
    color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', 
    icon: <SignalLow className="w-10 h-10" />, 
    desc: 'Можно выполнить в плановом порядке' 
  },
  { 
    value: 'Средний', 
    label: 'Средний', 
    color: 'bg-amber-500/20 text-amber-400 border-amber-500/40', 
    icon: <SignalMedium className="w-10 h-10" />, 
    desc: 'Стандартный приоритет' 
  },
  { 
    value: 'Высокий', 
    label: 'Высокий', 
    color: 'bg-orange-500/20 text-orange-400 border-orange-500/40', 
    icon: <SignalHigh className="w-10 h-10" />, 
    desc: 'Требует внимания в ближайшее время' 
  },
  { 
    value: 'Критический', 
    label: 'Критический', 
    color: 'bg-red-500/20 text-red-400 border-red-500/40', 
    icon: <Flame className="w-10 h-10" />, 
    desc: 'Нужно решать немедленно!' 
  },
];

const PRESET_TAGS = [
  { name: 'Инцидент',     color: '#ef4444' },
  { name: 'Консультация', color: '#3b82f6' },
  { name: 'Доработка',    color: '#8b5cf6' },
  { name: 'Ошибка',       color: '#f97316' },
  { name: 'Интеграция',   color: '#06b6d4' },
  { name: 'Обучение',     color: '#10b981' },
  { name: 'Срочное',      color: '#dc2626' },
];

interface LocalFile {
  id: string;
  file: File;
  preview?: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  attachmentId?: string;
}

interface SimpleUser {
  id: string;
  username: string;
  full_name: string | null;
  email: string;
  role?: string;
}

// Роли, которые могут выбирать контрагента
const CAN_SELECT_COUNTERPARTY_ROLES = ['admin', 'support_agent', 'support_manager', 'executor'];

// Тип выбора: 'project' или 'counterparty'
type SelectionType = 'project' | 'counterparty' | null;

export default function NewTicketPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuthStore();
  const pageRef = useRef<HTMLDivElement>(null);

  const [step, setStep] = useState(1);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<TicketPriority>('Средний');
  const [tags, setTags] = useState<TicketTag[]>([]);
  const [aiSuggestedTags, setAiSuggestedTags] = useState<TicketTag[]>([]);

  const [localFiles, setLocalFiles] = useState<LocalFile[]>([]);
  
  // Для customer - автоматический контрагент
  const [customerCounterparty, setCustomerCounterparty] = useState<Counterparty | null>(null);
  
  // Для admin/support - выбор типа (проект или контрагент)
  const [selectionType, setSelectionType] = useState<SelectionType>(null);
  
  // Для выбора контрагента
  const [selectedCounterparty, setSelectedCounterparty] = useState<Counterparty | null>(null);
  const [counterparties, setCounterparties] = useState<Counterparty[]>([]);
  const [counterpartySearch, setCounterpartySearch] = useState('');
  const [showCounterpartyDropdown, setShowCounterpartyDropdown] = useState(false);
  const [loadingCounterparties, setLoadingCounterparties] = useState(false);
  
  // Для выбора проекта
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [showProjectDropdown, setShowProjectDropdown] = useState(false);
  const [projectSearch, setProjectSearch] = useState('');
  
  // Для выбора инициатора (reporter)
  const [users, setUsers] = useState<SimpleUser[]>([]);
  const [selectedReporter, setSelectedReporter] = useState<SimpleUser | null>(null);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [showReporterDropdown, setShowReporterDropdown] = useState(false);
  const [reporterSearch, setReporterSearch] = useState('');

  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState<any>(null);
  const [newTagInput, setNewTagInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showCustomTagInput, setShowCustomTagInput] = useState(false);

  const isCustomer = user?.role === 'customer' || user?.role === 'customer_admin';
  const canSelectCounterparty = !isCustomer && CAN_SELECT_COUNTERPARTY_ROLES.includes(user?.role || '');
  const canSelectReporter = !isCustomer;

  const counterpartyDropdownRef = useRef<HTMLDivElement>(null);
  const projectDropdownRef = useRef<HTMLDivElement>(null);
  const reporterDropdownRef = useRef<HTMLDivElement>(null);

  // Закрытие дропдаунов при клике вне
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (counterpartyDropdownRef.current && !counterpartyDropdownRef.current.contains(event.target as Node)) {
        setShowCounterpartyDropdown(false);
      }
      if (projectDropdownRef.current && !projectDropdownRef.current.contains(event.target as Node)) {
        setShowProjectDropdown(false);
      }
      if (reporterDropdownRef.current && !reporterDropdownRef.current.contains(event.target as Node)) {
        setShowReporterDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Прокрутка вверх при смене шага
  useEffect(() => {
    if (pageRef.current) {
      pageRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [step]);

  // Загрузка контрагента для customer
  useEffect(() => {
    if (isCustomer && user?.counterparty_id) {
      loadCustomerCounterparty();
    }
  }, [user]);

  // Загрузка списка контрагентов для admin/support
  useEffect(() => {
    if (canSelectCounterparty) {
      loadCounterparties();
    }
  }, [canSelectCounterparty]);

  // Загрузка проектов для выбранного контрагента (когда выбран тип "контрагент")
  useEffect(() => {
    if (selectionType === 'counterparty' && selectedCounterparty) {
      loadProjects(selectedCounterparty.id);
    } else if (selectionType === 'counterparty' && !selectedCounterparty) {
      setProjects([]);
    }
  }, [selectionType, selectedCounterparty]);

  // Загрузка пользователей для выбранного контрагента (для выбора инициатора)
  useEffect(() => {
    if (selectedCounterparty) {
      loadUsers(selectedCounterparty.id);
    } else if (selectedProject && selectedProject.counterparty_id) {
      // Если выбран проект, загружаем пользователей по контрагенту проекта
      loadUsers(selectedProject.counterparty_id);
    } else {
      setUsers([]);
      setSelectedReporter(null);
      setReporterSearch('');
    }
  }, [selectedCounterparty, selectedProject]);

  // Сброс выбора контрагента/проекта при смене типа
  const handleSelectionTypeChange = (type: SelectionType) => {
    setSelectionType(type);
    setSelectedCounterparty(null);
    setSelectedProject(null);
    setCounterpartySearch('');
    setProjectSearch('');
    setProjects([]);
  };

  const loadCustomerCounterparty = async () => {
    if (!user?.counterparty_id) return;
    try {
      const cp = await counterpartiesApi.getById(user.counterparty_id);
      setCustomerCounterparty(cp);
    } catch (error) {
      console.error('Failed to load counterparty:', error);
    }
  };

  const loadCounterparties = async (search?: string) => {
    setLoadingCounterparties(true);
    try {
      const response = await counterpartiesApi.getAll(1, 50);
      let items = response.items;
      
      if (search) {
        const lowerSearch = search.toLowerCase();
        items = items.filter(cp => 
          cp.name?.toLowerCase().includes(lowerSearch) ||
          cp.legal_name?.toLowerCase().includes(lowerSearch) ||
          cp.inn?.includes(search)
        );
      }
      
      setCounterparties(items);
    } catch (error) {
      console.error('Failed to load counterparts:', error);
    } finally {
      setLoadingCounterparties(false);
    }
  };

  const loadProjects = async (counterpartyId: string) => {
    setLoadingProjects(true);
    try {
      const response = await projectsApi.getByCounterparty(counterpartyId, 1, 50);
      setProjects(response.items);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoadingProjects(false);
    }
  };

  const loadUsers = async (counterpartyId: string) => {
    setLoadingUsers(true);
    try {
      const response = await usersApi.getCustomers(counterpartyId, 1, 100);
      const formattedUsers = response.items.map(customer => ({
        id: customer.id,
        username: customer.username,
        full_name: customer.full_name,
        email: customer.email,
        role: customer.role,
      }));
      
      let allUsers = [...formattedUsers];
      const currentUserInList = formattedUsers.find(u => u.id === user?.user_id);
      
      if (!currentUserInList && user?.user_id) {
        const currentUserObj: SimpleUser = {
          id: user.user_id,
          username: user.username || '',
          full_name: user.full_name || null,
          email: user.email || '',
          role: user.role,
        };
        allUsers = [currentUserObj, ...formattedUsers];
      }
      
      setUsers(allUsers);
      setSelectedReporter(null);
      setReporterSearch('');
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoadingUsers(false);
    }
  };

  const runAI = useCallback(async () => {
    if (!title || !description) return;
    
    setAiLoading(true);
    try {
      const result = await ticketsApi.predict(title, description);
      
      setAiSuggestion(result);
      setAiSuggestedTags(result.suggested_tags || []);

      setPriority(result.suggested_priority);
      setTags(result.suggested_tags || []);
    } catch (error) {
      console.error('AI prediction failed:', error);
    } finally {
      setAiLoading(false);
    }
  }, [title, description]);

  const [aiAutoEnabled, setAiAutoEnabled] = useState(true);

  useEffect(() => {
    if (step === 1 && aiAutoEnabled) {
      const timer = setTimeout(runAI, 1000);
      return () => clearTimeout(timer);
    }
  }, [title, description, step, aiAutoEnabled, runAI]);

  useEffect(() => {
    if (step === 2) {
      setAiAutoEnabled(false);
    } else if (step === 1) {
      setAiAutoEnabled(true);
    }
  }, [step]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const newFiles: LocalFile[] = selectedFiles.map(file => ({
      id: `${file.name}_${Date.now()}_${Math.random()}`,
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      status: 'pending',
    }));
    setLocalFiles(prev => [...prev, ...newFiles].slice(0, 10));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    const newFiles: LocalFile[] = droppedFiles.map(file => ({
      id: `${file.name}_${Date.now()}_${Math.random()}`,
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      status: 'pending',
    }));
    setLocalFiles(prev => [...prev, ...newFiles].slice(0, 10));
  };

  const removeFile = (id: string) => {
    setLocalFiles(prev => prev.filter(f => f.id !== id));
  };

  const togglePresetTag = (tag: TicketTag) => {
    setTags(prev => {
      const exists = prev.some(t => t.name === tag.name);
      if (exists) return prev.filter(t => t.name !== tag.name);
      return [...prev, tag];
    });
  };

  const addCustomTag = () => {
    const trimmed = newTagInput.trim();
    if (!trimmed || tags.some(t => t.name.toLowerCase() === trimmed.toLowerCase())) return;

    const newTag: TicketTag = { name: trimmed, color: '#a1a1aa' };
    setTags(prev => [...prev, newTag]);
    setNewTagInput('');
    setShowCustomTagInput(false);
  };

  const removeTag = (tagName: string) => {
    setTags(prev => prev.filter(t => t.name !== tagName));
  };

  const uploadFiles = async (ticketId: string): Promise<boolean> => {
    const filesToUpload = localFiles.filter(f => f.status === 'pending');
    
    if (filesToUpload.length === 0) return true;
    
    setLocalFiles(prev => prev.map(f => 
      filesToUpload.some(uf => uf.id === f.id) 
        ? { ...f, status: 'uploading' }
        : f
    ));
    
    let allSuccess = true;
    
    for (const fileItem of filesToUpload) {
      try {
        const attachment = await attachmentsApi.uploadAttachment(
          fileItem.file,
          'ticket',
          ticketId
        );
        
        setLocalFiles(prev => prev.map(f =>
          f.id === fileItem.id
            ? { ...f, status: 'success', attachmentId: attachment.id }
            : f
        ));
      } catch (error) {
        console.error(`Failed to upload ${fileItem.file.name}:`, error);
        setLocalFiles(prev => prev.map(f =>
          f.id === fileItem.id
            ? { ...f, status: 'error', error: 'Ошибка загрузки' }
            : f
        ));
        allSuccess = false;
      }
    }
    
    return allSuccess;
  };

  
  // Внутри компонента NewTicketPage, рядом с loadCounterparties и loadProjects
const loadProjectsForAll = async () => {
  setLoadingProjects(true);
  try {
    const response = await projectsApi.getAll(1, 100);
    setProjects(response.items);
  } catch (error) {
    console.error('Failed to load projects:', error);
  } finally {
    setLoadingProjects(false);
  }
};
// Загрузка проектов для выбора (когда выбран тип "проект")
useEffect(() => {
  if (selectionType === 'project') {
    loadProjectsForAll();
  } else if (selectionType === 'counterparty' && selectedCounterparty) {
    loadProjects(selectedCounterparty.id);
  } else {
    setProjects([]);
  }
}, [selectionType, selectedCounterparty]);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const ticketData: any = {
        title,
        description,
        priority,
        tags: tags.length > 0 ? tags : undefined,
      };
      
      // Логика выбора: приоритет у проекта
      if (selectedProject) {
        ticketData.project_id = selectedProject.id;
      } else if (selectedCounterparty) {
        ticketData.counterparty_id = selectedCounterparty.id;
      }
      
      // Инициатор
      if (isCustomer && user?.user_id) {
        ticketData.reporter_id = user.user_id;
      } else if (canSelectReporter) {
        if (selectedReporter) {
          ticketData.reporter_id = selectedReporter.id;
        } else if (user?.user_id) {
          ticketData.reporter_id = user.user_id;
        }
      }
      
      const ticket = await ticketsApi.create(ticketData);
      
      if (localFiles.length > 0) {
        await uploadFiles(ticket.id);
      }
      
      navigate('/tickets');
    } catch (error: any) {
      console.error('Failed to create ticket:', error);
      if (error.response?.data?.detail) {
        console.error('Validation error:', error.response.data.detail);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getStatusIcon = (status: LocalFile['status']) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-green-400" />;
      case 'error':
        return <X className="w-5 h-5 text-red-400" />;
      default:
        return null;
    }
  };

  const getCounterpartyDisplayName = (cp: Counterparty) => {
    return cp.name || cp.legal_name || cp.inn || 'Без названия';
  };

  const getProjectDisplayName = (project: Project) => {
    return `${project.key} - ${project.name}`;
  };

  const getUserDisplayName = (u: SimpleUser) => {
    return u.full_name || u.username || u.email;
  };

  return (
    <div ref={pageRef} className="pb-12">
      {/* Header */}
      <div className="flex items-center gap-6 mb-8">
        <button
          onClick={() => navigate(-1)}
          className="p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
        >
          <ArrowLeft className="w-6 h-6 text-white" />
        </button>
        <div>
          <h1 className="text-4xl font-bold text-white">Новая заявка</h1>
          <p className="text-white/60">Помощник проведёт вас шаг за шагом</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="glass-card p-6 mb-10">
        <div className="flex justify-center">
          {[
            { num: 1, label: 'Описание проблемы', icon: <FileText className="w-5 h-5" /> },
            { num: 2, label: 'Приоритет и теги', icon: <Tag className="w-5 h-5" /> },
            { num: 3, label: 'Проверка и отправка', icon: <CheckCircle2 className="w-5 h-5" /> },
          ].map((s, i) => (
            <div key={s.num} className="flex items-center">
              <div className={`flex items-center gap-4 ${step >= s.num ? 'text-white' : 'text-white/40'}`}>
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border-2 transition-all
                  ${step === s.num ? 'bg-red-600 border-red-500 scale-110' : 
                    step > s.num ? 'bg-emerald-600 border-emerald-500' : 'bg-white/10 border-white/20'}`}>
                  {step > s.num ? <CheckCircle2 className="w-6 h-6" /> : s.icon}
                </div>
                <div>
                  <div className="font-semibold text-lg">Шаг {s.num}</div>
                  <div className="text-sm">{s.label}</div>
                </div>
              </div>
              {i < 2 && (
                <div className={`w-24 h-1 mx-6 rounded-full ${step > s.num ? 'bg-red-600' : 'bg-white/10'}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card p-8 md:p-12">
        {/* Step 1 */}
        {step === 1 && (
          <div className="space-y-10">
            {/* Выбор типа: Проект или Контрагент (для admin/support) */}
            {canSelectCounterparty && (
              <div>
                <label className="block text-2xl font-semibold text-white mb-4">
                  Привязать заявку к
                </label>
                <div className="flex gap-4">
                  <button
                    type="button"
                    onClick={() => handleSelectionTypeChange('project')}
                    className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 transition-all ${
                      selectionType === 'project'
                        ? 'border-purple-500 bg-purple-500/20 text-purple-400'
                        : 'border-white/20 bg-white/5 text-white/60 hover:bg-white/10'
                    }`}
                  >
                    <FolderOpen className="w-6 h-6" />
                    <span className="text-lg font-medium">Проекту</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectionTypeChange('counterparty')}
                    className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 transition-all ${
                      selectionType === 'counterparty'
                        ? 'border-blue-500 bg-blue-500/20 text-blue-400'
                        : 'border-white/20 bg-white/5 text-white/60 hover:bg-white/10'
                    }`}
                  >
                    <Building2 className="w-6 h-6" />
                    <span className="text-lg font-medium">Контрагенту</span>
                  </button>
                </div>
                {selectionType === null && (
                  <p className="text-white/40 text-sm mt-3 text-center">Выберите, к чему привязать заявку</p>
                )}
              </div>
            )}

            {/* Выбор контрагента (когда выбран тип "контрагент") */}
            {canSelectCounterparty && selectionType === 'counterparty' && (
              <div>
                <label className="block text-2xl font-semibold text-white mb-4">
                  <Building2 className="inline w-6 h-6 mr-2 text-blue-400" />
                  Выберите контрагента <span className="text-red-400">*</span>
                </label>
                <div className="relative" ref={counterpartyDropdownRef}>
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/40" />
                    <input
                      type="text"
                      value={counterpartySearch}
                      onChange={(e) => {
                        setCounterpartySearch(e.target.value);
                        setShowCounterpartyDropdown(true);
                        loadCounterparties(e.target.value);
                      }}
                      onFocus={() => {
                        setShowCounterpartyDropdown(true);
                        if (counterparties.length === 0) loadCounterparties();
                      }}
                      placeholder="Поиск по названию, ИНН или юр. имени..."
                      className="input-field pl-12 py-5 text-lg w-full"
                    />
                  </div>
                  
                  {showCounterpartyDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[#0c0c0c] border border-white/20 rounded-xl shadow-2xl max-h-96 overflow-y-auto">
                      {loadingCounterparties ? (
                        <div className="p-8 text-center">
                          <Loader2 className="w-8 h-8 animate-spin mx-auto text-white/50" />
                          <p className="text-white/50 mt-3">Загрузка контрагентов...</p>
                        </div>
                      ) : (
                        <>
                          {counterparties.map((cp) => (
                            <button
                              key={cp.id}
                              onClick={() => {
                                setSelectedCounterparty(cp);
                                setCounterpartySearch(getCounterpartyDisplayName(cp));
                                setShowCounterpartyDropdown(false);
                              }}
                              className="w-full text-left p-5 hover:bg-white/10 transition-colors border-b border-white/10 last:border-0"
                            >
                              <div className="font-semibold text-white text-base">{getCounterpartyDisplayName(cp)}</div>
                              {cp.legal_name && cp.legal_name !== cp.name && (
                                <div className="text-sm text-white/50 mt-1">{cp.legal_name}</div>
                              )}
                              <div className="flex gap-3 mt-2">
                                {cp.inn && (
                                  <div className="text-xs text-white/40">ИНН: {cp.inn}</div>
                                )}
                                {cp.kpp && (
                                  <div className="text-xs text-white/40">КПП: {cp.kpp}</div>
                                )}
                              </div>
                            </button>
                          ))}
                        </>
                      )}
                    </div>
                  )}
                </div>
                
                {selectedCounterparty && (
                  <div className="mt-4 p-5 rounded-xl bg-green-500/10 border border-green-500/30">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="w-6 h-6 text-green-400" />
                      <span className="text-white text-lg">Выбран контрагент: </span>
                      <span className="text-green-400 font-semibold text-lg">{getCounterpartyDisplayName(selectedCounterparty)}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Выбор проекта (когда выбран тип "проект") */}
            {canSelectCounterparty && selectionType === 'project' && (
              <div>
                <label className="block text-2xl font-semibold text-white mb-4">
                  <FolderOpen className="inline w-6 h-6 mr-2 text-purple-400" />
                  Выберите проект <span className="text-red-400">*</span>
                </label>
                <div className="relative" ref={projectDropdownRef}>
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/40" />
                    <input
                      type="text"
                      value={projectSearch}
                      onChange={(e) => {
                        setProjectSearch(e.target.value);
                        setShowProjectDropdown(true);
                        // Загружаем все проекты (без фильтра по контрагенту)
                        if (projects.length === 0) {
                          loadProjectsForAll();
                        }
                      }}
                      onFocus={() => {
                        setShowProjectDropdown(true);
                        if (projects.length === 0) loadProjectsForAll();
                      }}
                      placeholder="Поиск по названию или ключу проекта..."
                      className="input-field pl-12 py-5 text-lg w-full"
                    />
                  </div>
                  
                  {showProjectDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[#0c0c0c] border border-white/20 rounded-xl shadow-2xl max-h-96 overflow-y-auto">
                      {loadingProjects ? (
                        <div className="p-8 text-center">
                          <Loader2 className="w-8 h-8 animate-spin mx-auto text-white/50" />
                          <p className="text-white/50 mt-3">Загрузка проектов...</p>
                        </div>
                      ) : (
                        <>
                          {projects
                            .filter(p => !projectSearch || 
                              p.name.toLowerCase().includes(projectSearch.toLowerCase()) ||
                              p.key.toLowerCase().includes(projectSearch.toLowerCase()))
                            .map((project) => (
                              <button
                                key={project.id}
                                onClick={() => {
                                  setSelectedProject(project);
                                  setProjectSearch(getProjectDisplayName(project));
                                  setShowProjectDropdown(false);
                                }}
                                className="w-full text-left p-5 hover:bg-white/10 transition-colors border-b border-white/10 last:border-0"
                              >
                                <div className="flex items-center gap-4">
                                  <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
                                    <FolderOpen className="w-5 h-5 text-purple-400" />
                                  </div>
                                  <div className="flex-1">
                                    <div className="font-semibold text-white">
                                      <span className="text-purple-400">{project.key}</span> - {project.name}
                                    </div>
                                    {project.description && (
                                      <div className="text-sm text-white/50 mt-1 line-clamp-1">
                                        {project.description}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </button>
                            ))}
                        </>
                      )}
                    </div>
                  )}
                </div>
                
                {selectedProject && (
                  <div className="mt-4 p-5 rounded-xl bg-purple-500/10 border border-purple-500/30">
                    <div className="flex items-center gap-3">
                      <FolderOpen className="w-6 h-6 text-purple-400" />
                      <span className="text-white text-lg">Выбран проект: </span>
                      <span className="text-purple-400 font-semibold text-lg">
                        {selectedProject.key} - {selectedProject.name}
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-white/50">
                      (контрагент будет автоматически взят из проекта)
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Для customer - показываем его организацию (без выбора) */}
            {isCustomer && customerCounterparty && (
              <div>
                <label className="block text-2xl font-semibold text-white mb-4">
                  <Building2 className="inline w-6 h-6 mr-2 text-blue-400" />
                  Ваш контрагент
                </label>
                <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-blue-500/20 flex items-center justify-center">
                      <Building2 className="w-7 h-7 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-[16px] font-semibold text-white">{customerCounterparty.name || customerCounterparty.legal_name}</p>
                      {customerCounterparty.inn && (
                        <p className="text-white/60">ИНН: {customerCounterparty.inn}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Выбор инициатора для admin/support */}
            {canSelectReporter && (selectedCounterparty || selectedProject) && (
              <div>
                <label className="block text-2xl font-semibold text-white mb-4">
                  <User className="inline w-6 h-6 mr-2 text-green-400" />
                  Инициатор заявки <span className="text-white/40 text-sm">(опционально, по умолчанию - вы)</span>
                </label>
                <div className="relative" ref={reporterDropdownRef}>
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/40" />
                    <input
                      type="text"
                      value={reporterSearch}
                      onChange={(e) => {
                        setReporterSearch(e.target.value);
                        setShowReporterDropdown(true);
                      }}
                      onFocus={() => setShowReporterDropdown(true)}
                      placeholder="Выберите инициатора (по умолчанию - вы)"
                      className="input-field pl-12 py-5 text-lg w-full"
                    />
                  </div>
                  
                  {showReporterDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[#0c0c0c] border border-white/20 rounded-xl shadow-2xl max-h-96 overflow-y-auto">
                      {loadingUsers ? (
                        <div className="p-8 text-center">
                          <Loader2 className="w-8 h-8 animate-spin mx-auto text-white/50" />
                          <p className="text-white/50 mt-3">Загрузка пользователей...</p>
                        </div>
                      ) : users.length === 0 ? (
                        <div className="p-8 text-center">
                          <User className="w-12 h-12 mx-auto mb-3 text-white/20" />
                          <p className="text-white/50 text-lg">Нет пользователей</p>
                          <p className="text-white/30 text-sm mt-1">У выбранного контрагента пока нет других пользователей</p>
                        </div>
                      ) : (
                        <>
                          <button
                            onClick={() => {
                              setSelectedReporter(null);
                              setReporterSearch('');
                              setShowReporterDropdown(false);
                            }}
                            className="w-full text-left p-5 hover:bg-white/10 transition-colors border-b border-white/10"
                          >
                            <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-500 to-gray-600 flex items-center justify-center">
                                <User className="w-5 h-5 text-white" />
                              </div>
                              <div>
                                <div className="font-semibold text-white text-base">
                                  {user?.full_name || user?.username || 'Вы'} (текущий пользователь)
                                </div>
                                <div className="text-sm text-white/50">{user?.email}</div>
                              </div>
                            </div>
                          </button>
                          {users
                            .filter(u => !reporterSearch || 
                              (u.full_name?.toLowerCase().includes(reporterSearch.toLowerCase()) ||
                               u.username.toLowerCase().includes(reporterSearch.toLowerCase()) ||
                               u.email.toLowerCase().includes(reporterSearch.toLowerCase())))
                            .map((u) => (
                              <button
                                key={u.id}
                                onClick={() => {
                                  setSelectedReporter(u);
                                  setReporterSearch(getUserDisplayName(u));
                                  setShowReporterDropdown(false);
                                }}
                                className="w-full text-left p-5 hover:bg-white/10 transition-colors border-b border-white/10 last:border-0"
                              >
                                <div className="flex items-center gap-4">
                                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center">
                                    <User className="w-5 h-5 text-white" />
                                  </div>
                                  <div className="flex-1">
                                    <div className="font-semibold text-white text-base">
                                      {u.full_name || u.username}
                                    </div>
                                    <div className="text-sm text-white/50">{u.email}</div>
                                    {u.role && (
                                      <div className="text-xs text-white/40 mt-1">
                                        {u.role === 'customer_admin' ? 'Администратор' : 'Сотрудник'}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </button>
                            ))}
                        </>
                      )}
                    </div>
                  )}
                </div>
                
                {selectedReporter && (
                  <div className="mt-4 p-5 rounded-xl bg-green-500/10 border border-green-500/30">
                    <div className="flex items-center gap-3">
                      <User className="w-6 h-6 text-green-400" />
                      <span className="text-white text-lg">Инициатор: </span>
                      <span className="text-green-400 font-semibold text-lg">
                        {getUserDisplayName(selectedReporter)}
                      </span>
                    </div>
                  </div>
                )}
                
                {!selectedReporter && (
                  <div className="mt-4 p-5 rounded-xl bg-gray-500/10 border border-gray-500/30">
                    <div className="flex items-center gap-3">
                      <User className="w-6 h-6 text-gray-400" />
                      <span className="text-white text-lg">Инициатор: </span>
                      <span className="text-gray-400 font-semibold text-lg">
                        {user?.full_name || user?.username || 'Вы'} (текущий пользователь, по умолчанию)
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div>
              <label className="block text-2xl font-semibold text-white mb-4">
                Тема заявки <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Кратко опишите проблему..."
                className="input-field py-5 text-2xl w-full"
              />
            </div>

            <div>
              <label className="block text-2xl font-semibold text-white mb-4">
                Подробное описание <span className="text-red-400">*</span>
              </label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Опишите подробно: что произошло, когда возникло, какие действия выполняли..."
                rows={10}
                className="input-field py-5 text-lg resize-none w-full"
              />
            </div>
          </div>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <div className="space-y-12">
            {aiLoading && (
              <div className="p-6 rounded-2xl bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 flex items-center gap-4">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
                <div>
                  <h3 className="text-[16px] font-semibold text-white">ИИ подбирает приоритет и теги...</h3>
                  <p className="text-white/70">Это займёт пару секунд</p>
                </div>
              </div>
            )}

            {aiSuggestion && !aiLoading && (
              <div className="p-6 rounded-2xl bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30">
                <div className="flex items-center gap-3">
                  <Zap className="w-7 h-7 text-purple-400" />
                  <div>
                    <h3 className="text-2xl font-semibold text-white">ИИ изучил вашу заявку и подобрал оптимальный приоритет и теги</h3>
                    <p className="text-white/70 mt-1">Проверьте и при необходимости скорректируйте</p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="block text-2xl font-semibold text-white mb-6">Приоритет заявки</label>
              <div className="flex flex-wrap gap-3">
                {PRIORITIES.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => setPriority(p.value as TicketPriority)}
                    className={`px-8 py-5 rounded-2xl text-lg font-medium transition-all border flex-1 min-w-[200px] text-left
                      ${priority === p.value 
                        ? 'bg-white/20 text-white border-white/70' 
                        : 'bg-white/5 border-white/20 hover:bg-white/10 hover:border-white/40'
                      }`}
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-red-800">{p.icon}</span>
                      <div>
                        <div className="font-semibold">{p.label}</div>
                        <div className="text-sm opacity-70">{p.desc}</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-2xl font-semibold text-white mb-6">Теги заявки</label>

              {aiSuggestedTags.length > 0 && (
                <div className="mb-8">
                  <p className="text-white/60 text-sm mb-3 flex items-center gap-2">
                    <Sparkles className="w-4 h-4" /> Предложено ИИ
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {aiSuggestedTags.map((tag) => {
                      const isSelected = tags.some(t => t.name === tag.name);
                      return (
                        <button
                          key={tag.name}
                          onClick={() => togglePresetTag(tag)}
                          className={`px-6 py-3 rounded-2xl text-base font-medium border transition-all
                            ${isSelected ? 'bg-white/20 border-white/40' : 'bg-white/5 border-white/20 hover:bg-white/10'}`}
                        >
                          {tag.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="mb-8">
                <p className="text-white/60 text-sm mb-3">Быстрый выбор:</p>
                <div className="flex flex-wrap gap-3">
                  {PRESET_TAGS.map((tag) => {
                    const isSelected = tags.some(t => t.name === tag.name);
                    return (
                      <button
                        key={tag.name}
                        onClick={() => togglePresetTag(tag)}
                        className={`px-6 py-3 rounded-2xl text-base font-medium border transition-all
                          ${isSelected ? 'bg-white/20 border-white/40' : 'bg-white/5 border-white/20 hover:bg-white/10'}`}
                      >
                        {tag.name}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="mb-8">
                <button
                  onClick={() => setShowCustomTagInput(!showCustomTagInput)}
                  className="text-blue-400 hover:text-blue-300 flex items-center gap-2 text-sm"
                >
                  <Plus className="w-4 h-4" />
                  {showCustomTagInput ? 'Скрыть' : 'Добавить свой тег'}
                </button>

                {showCustomTagInput && (
                  <div className="flex gap-3 mt-3">
                    <input
                      type="text"
                      value={newTagInput}
                      onChange={(e) => setNewTagInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && addCustomTag()}
                      placeholder="Введите свой тег..."
                      className="input-field flex-1 py-4 text-lg"
                    />
                    <button onClick={addCustomTag} disabled={!newTagInput.trim()} className="btn-primary px-8">
                      Добавить
                    </button>
                  </div>
                )}
              </div>

              {tags.length > 0 && (
                <div className="p-6 bg-white/5 rounded-2xl">
                  <p className="text-white/60 mb-4">Выбранные теги ({tags.length})</p>
                  <div className="flex flex-wrap gap-3">
                    {tags.map((tag) => (
                      <div
                        key={tag.name}
                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-white/10 rounded-2xl text-base"
                      >
                        <span>{tag.name}</span>
                        <X 
                          className="w-4 h-4 cursor-pointer text-white/60 hover:text-red-400 transition-colors" 
                          onClick={() => removeTag(tag.name)}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div>
              <label className="block text-2xl font-semibold text-white mb-4">
                <Upload className="inline w-6 h-6 mr-2 text-green-400" />
                Прикрепить файлы
              </label>
              <div
                onDrop={handleDrop}
                onDragOver={e => e.preventDefault()}
                className="border-2 border-dashed border-white/20 rounded-xl p-10 text-center hover:border-white/40 transition-colors"
              >
                <Upload className="w-12 h-12 text-white/30 mx-auto mb-4" />
                <p className="text-2xl text-white/60 mb-2">Перетащите файлы сюда</p>
                <p className="text-base text-white/40 mb-4">или</p>
                <label className="inline-block">
                  <input
                    type="file"
                    multiple
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <span className="btn-primary py-3 px-6 text-base cursor-pointer">
                    Выбрать файлы
                  </span>
                </label>
                <p className="mt-4 text-sm text-white/40">До 10 файлов, максимум 25 МБ каждый</p>
              </div>

              {localFiles.length > 0 && (
                <div className="mt-6 space-y-3">
                  {localFiles.map((f) => (
                    <div key={f.id} className="flex items-center gap-4 p-4 rounded-xl bg-white/5">
                      {f.preview ? (
                        <img src={f.preview} alt="" className="w-14 h-14 rounded-lg object-cover" />
                      ) : (
                        <div className="w-14 h-14 rounded-lg bg-white/10 flex items-center justify-center">
                          <File className="w-7 h-7 text-white/50" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-lg text-white font-medium truncate">{f.file.name}</p>
                        <p className="text-base text-white/50">{formatFileSize(f.file.size)}</p>
                        {f.error && <p className="text-sm text-red-400">{f.error}</p>}
                      </div>
                      <div className="flex items-center gap-3">
                        {getStatusIcon(f.status)}
                        <button
                          onClick={() => removeFile(f.id)}
                          disabled={f.status === 'uploading'}
                          className="p-2 rounded-lg hover:bg-white/10 text-white/50 hover:text-red-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Review */}
        {step === 3 && (
          <div className="space-y-10">
            <div className="text-center mb-10">
              <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-12 h-12 text-green-400" />
              </div>
              <h2 className="text-3xl font-bold text-white mb-2">Проверьте заявку перед отправкой</h2>
              <p className="text-lg text-white/60">Убедитесь, что всё правильно</p>
            </div>

            <div className="space-y-8">
              {selectedProject && (
                <div className="p-8 rounded-3xl bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30">
                  <p className="text-[16px] text-white/50 mb-3 flex items-center gap-2">
                    <FolderOpen className="w-5 h-5" />
                    Проект
                  </p>
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-purple-500/20 flex items-center justify-center">
                      <FolderOpen className="w-7 h-7 text-purple-400" />
                    </div>
                    <div>
                      <p className="text-[16px] font-semibold text-white">
                        <span className="text-purple-400">{selectedProject.key}</span> - {selectedProject.name}
                      </p>
                      {selectedProject.description && (
                        <p className="text-white/60 mt-1">{selectedProject.description}</p>
                      )}
                      <p className="text-sm text-white/40 mt-2">(контрагент будет взят из проекта автоматически)</p>
                    </div>
                  </div>
                </div>
              )}

              {!selectedProject && selectedCounterparty && (
                <div className="p-8 rounded-3xl bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30">
                  <p className="text-[16px] text-white/50 mb-3 flex items-center gap-2">
                    <Building2 className="w-5 h-5" />
                    Контрагент
                  </p>
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-blue-500/20 flex items-center justify-center">
                      <Building2 className="w-7 h-7 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-[16px] font-semibold text-white">
                        {getCounterpartyDisplayName(selectedCounterparty)}
                      </p>
                      {selectedCounterparty.inn && (
                        <p className="text-white/60">ИНН: {selectedCounterparty.inn}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {isCustomer && customerCounterparty && !selectedProject && !selectedCounterparty && (
                <div className="p-8 rounded-3xl bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30">
                  <p className="text-[16px] text-white/50 mb-3 flex items-center gap-2">
                    <Building2 className="w-5 h-5" />
                    Контрагент
                  </p>
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-blue-500/20 flex items-center justify-center">
                      <Building2 className="w-7 h-7 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-[16px] font-semibold text-white">
                        {customerCounterparty.name || customerCounterparty.legal_name}
                      </p>
                      {customerCounterparty.inn && (
                        <p className="text-white/60">ИНН: {customerCounterparty.inn}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {canSelectCounterparty && !selectedProject && !selectedCounterparty && !isCustomer && (
                <div className="p-8 rounded-3xl bg-yellow-500/10 border border-yellow-500/30">
                  <p className="text-yellow-400 text-center text-lg">
                    ℹ️ Заявка создаётся без привязки к контрагенту и проекту
                  </p>
                </div>
              )}

              <div className="p-8 rounded-3xl bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/30">
                <p className="text-[16px] text-white/50 mb-3 flex items-center gap-2">
                  <User className="w-5 h-5" />
                  Инициатор
                </p>
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-xl bg-green-500/20 flex items-center justify-center">
                    <User className="w-7 h-7 text-green-400" />
                  </div>
                  <div>
                    <p className="text-[16px] font-semibold text-white">
                      {selectedReporter 
                        ? getUserDisplayName(selectedReporter)
                        : (user?.full_name || user?.username || 'Вы')}
                    </p>
                    <p className="text-white/60">
                      {selectedReporter 
                        ? selectedReporter.email 
                        : user?.email}
                    </p>
                    {!selectedReporter && (
                      <p className="text-sm text-green-400/60 mt-1">(текущий пользователь)</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="p-8 rounded-3xl bg-white/5">
                <p className="text-[16px] text-white/50 mb-2">Тема</p>
                <div className="text-[16px] font-semibold text-white break-words">{title || '—'}</div>
              </div>

              <div className="p-8 rounded-3xl bg-white/5">
                <p className="text-[16px] text-white/50 mb-2">Описание</p>
                <div className="text-[16px] font-semibold text-white whitespace-pre-wrap leading-relaxed">
                  {description || '—'}
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                <div className="p-8 rounded-3xl bg-white/5">
                  <p className="text-white/50 mb-3">Приоритет</p>
                  <div className={`inline-flex items-center gap-4 text-lg px-6 py-3 rounded-2xl ${PRIORITIES.find(p => p.value === priority)?.color || ''}`}>
                    {PRIORITIES.find(p => p.value === priority)?.icon} {priority}
                  </div>
                </div>

                {tags.length > 0 && (
                  <div className="p-8 rounded-3xl bg-white/5">
                    <p className="text-white/50 mb-4">Теги</p>
                    <div className="flex flex-wrap gap-3">
                      {tags.map(tag => (
                        <span
                          key={tag.name}
                          className="px-6 py-3 rounded-2xl text-lg font-medium"
                          style={{ 
                            backgroundColor: (tag.color || '#71717a') + '30', 
                            color: tag.color || '#d1d5db' 
                          }}
                        >
                          {tag.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {localFiles.length > 0 && (
                <div className="p-8 rounded-3xl bg-white/5">
                  <p className="text-white/50 mb-4">Вложения ({localFiles.length})</p>
                  <div className="space-y-2">
                    {localFiles.map(f => (
                      <div key={f.id} className="flex items-center gap-3 text-white">
                        <File className="w-5 h-5" />
                        <span>{f.file.name}</span>
                        {f.status === 'pending' && <span className="text-yellow-400 text-sm">(будет загружено после создания)</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-12 pt-8 border-t border-white/10">
          {step > 1 && (
            <button
              onClick={() => setStep(step - 1)}
              className="flex items-center gap-3 px-8 py-4 rounded-2xl bg-white/5 hover:bg-white/10 text-lg font-medium transition-colors"
            >
              <ArrowLeft className="w-5 h-5" /> Назад
            </button>
          )}

          {step === 1 && <div />}

          {step < 3 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="btn-primary py-4 px-10 text-lg font-semibold ml-auto"
            >
              Далее <ArrowRight className="w-5 h-5 ml-2" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="btn-primary py-4 px-12 text-lg font-semibold flex items-center gap-3 ml-auto disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <>
                  <FileText className="w-5 h-5" />
                  Создать заявку
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

