import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Sparkles, Loader2, FileText,
  Tag, Upload, X, CheckCircle2, File, Building2, Zap, Plus,
  Search, FolderOpen, User, AlertCircle,
} from 'lucide-react';
import { SignalLow, SignalMedium, SignalHigh, Flame } from 'lucide-react';
import { MessageSquare, HelpCircle, AlertTriangle, CheckCircle, Edit3 } from 'lucide-react';

import { useAuthStore } from '../stores/authStore';
import { ticketsApi, counterpartiesApi, projectsApi, usersApi } from '../api/client';
import { attachmentsApi } from '../api/attachments';
import type { Counterparty, TicketTag, TicketPriority, TicketType, Project } from '../types';
import { SpellCheckField } from '../components/helpers/SpellCheckField';
import { TicketDescriptionContent } from '../components/helpers/TicketDescriptionContent';
import {
  TicketEditor, serializeBlocks, type DescriptionBlock,
} from '../components/helpers/TicketEditor';

// ─── Константы ────

const PRIORITIES = [
  { value: 'Низкий', label: 'Низкий', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', activeColor: 'bg-emerald-500/30 text-emerald-300 border-emerald-400 ring-2 ring-emerald-500/50', icon: <SignalLow className="w-10 h-10" />, desc: 'Плановый порядок' },
  { value: 'Средний', label: 'Средний', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40', activeColor: 'bg-yellow-500/30 text-yellow-300 border-yellow-400 ring-2 ring-yellow-500/50', icon: <SignalMedium className="w-10 h-10" />, desc: 'Стандартный' },
  { value: 'Высокий', label: 'Высокий', color: 'bg-orange-500/20 text-orange-400 border-orange-500/40', activeColor: 'bg-orange-500/30 text-orange-300 border-orange-400 ring-2 ring-orange-500/50', icon: <SignalHigh className="w-10 h-10" />, desc: 'Требует внимания' },
  { value: 'Критический', label: 'Критический', color: 'bg-red-500/20 text-red-400 border-red-500/40', activeColor: 'bg-red-500/30 text-red-300 border-red-400 ring-2 ring-red-500/50', icon: <Flame className="w-10 h-10" />, desc: 'Немедленно!' },
];

const TICKET_TYPES = [
  { value: 'Инцидент', label: 'Инцидент', icon: <AlertTriangle className="w-5 h-5" />, color: 'bg-red-500/20 text-red-400 border-red-500/40', activeColor: 'bg-red-500/30 text-red-300 border-red-400 ring-2 ring-red-500/50', desc: 'Сбой, ошибка' },
  { value: 'Запрос на услугу', label: 'Запрос на услугу', icon: <CheckCircle className="w-5 h-5" />, color: 'bg-blue-500/20 text-blue-400 border-blue-500/40', activeColor: 'bg-blue-500/30 text-blue-300 border-blue-400 ring-2 ring-blue-500/50', desc: 'Стандартная услуга' },
  { value: 'Консультация', label: 'Консультация', icon: <HelpCircle className="w-5 h-5" />, color: 'bg-gray-500/20 text-gray-400 border-gray-500/40', activeColor: 'bg-gray-500/30 text-gray-300 border-gray-400 ring-2 ring-gray-500/50', desc: 'Вопрос, консультация' },
  { value: 'Жалоба', label: 'Жалоба', icon: <AlertTriangle className="w-5 h-5" />, color: 'bg-orange-500/20 text-orange-400 border-orange-500/40', activeColor: 'bg-orange-500/30 text-orange-300 border-orange-400 ring-2 ring-orange-500/50', desc: 'Жалоба клиента' },
  { value: 'Задача', label: 'Задача', icon: <CheckCircle className="w-5 h-5" />, color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', activeColor: 'bg-emerald-500/30 text-emerald-300 border-emerald-400 ring-2 ring-emerald-500/50', desc: 'Планируемая работа' },
  { value: 'Проблема', label: 'Проблема', icon: <AlertTriangle className="w-5 h-5" />, color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40', activeColor: 'bg-yellow-500/30 text-yellow-300 border-yellow-400 ring-2 ring-yellow-500/50', desc: 'Корневая причина' },
  { value: 'Запрос на изменение', label: 'Запрос на изменение', icon: <Edit3 className="w-5 h-5" />, color: 'bg-blue-500/20 text-blue-400 border-blue-500/40', activeColor: 'bg-blue-500/30 text-blue-300 border-blue-400 ring-2 ring-blue-500/50', desc: 'Изменение системы' },
  { value: 'Улучшение', label: 'Улучшение', icon: <Sparkles className="w-5 h-5" />, color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', activeColor: 'bg-emerald-500/30 text-emerald-300 border-emerald-400 ring-2 ring-emerald-500/50', desc: 'Предложение по улучшению' },
  { value: 'Прочее', label: 'Прочее', icon: <MessageSquare className="w-5 h-5" />, color: 'bg-gray-500/20 text-gray-400 border-gray-500/40', activeColor: 'bg-gray-500/30 text-gray-300 border-gray-400 ring-2 ring-gray-500/50', desc: 'Другое' },
];

const PRESET_TAGS = [
  { name: 'Инцидент', color: '#dc2626' }, { name: 'Консультация', color: '#2563eb' },
  { name: 'Доработка', color: '#059669' }, { name: 'Ошибка', color: '#ea580c' },
  { name: 'Интеграция', color: '#2563eb' }, { name: 'Обучение', color: '#059669' },
  { name: 'Срочное', color: '#dc2626' },
];

interface GeneralFile {
  id: string; file: File; preview?: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

interface SimpleUser {
  id: string; username: string; full_name: string | null; email: string; role?: string;
}

const CAN_SELECT_COUNTERPARTY_ROLES = ['admin', 'support_agent', 'support_manager', 'executor'];
type SelectionType = 'project' | 'counterparty' | null;

// ─── Компонент ────

export default function NewTicketPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedCounterpartyId = searchParams.get('counterparty_id');
  const preselectedProjectId = searchParams.get('project_id');
  const { user } = useAuthStore();
  const pageRef = useRef<HTMLDivElement>(null);

  const [step, setStep] = useState(1);
  const [title, setTitle] = useState('');
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const [descriptionBlocks, setDescriptionBlocks] = useState<DescriptionBlock[]>([
    { id: 'init', type: 'text', value: '' },
  ]);
  const description = serializeBlocks(descriptionBlocks);

  const [priority, setPriority] = useState<TicketPriority>('Средний');
  const [type, setType] = useState<TicketType>('Инцидент');
  const [tags, setTags] = useState<TicketTag[]>([]);
  const [generalFiles, setGeneralFiles] = useState<GeneralFile[]>([]);

  const [customerCounterparty, setCustomerCounterparty] = useState<Counterparty | null>(null);
  const [selectionType, setSelectionType] = useState<SelectionType>(null);
  const [selectedCounterparty, setSelectedCounterparty] = useState<Counterparty | null>(null);
  const [counterparties, setCounterparties] = useState<Counterparty[]>([]);
  const [counterpartySearch, setCounterpartySearch] = useState('');
  const [showCounterpartyDropdown, setShowCounterpartyDropdown] = useState(false);
  const [loadingCounterparties, setLoadingCounterparties] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [showProjectDropdown, setShowProjectDropdown] = useState(false);
  const [projectSearch, setProjectSearch] = useState('');
  const [users, setUsers] = useState<SimpleUser[]>([]);
  const [selectedReporter, setSelectedReporter] = useState<SimpleUser | null>(null);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [showReporterDropdown, setShowReporterDropdown] = useState(false);
  const [reporterSearch, setReporterSearch] = useState('');

  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState<any>(null);
  const [aiSuggestedTags, setAiSuggestedTags] = useState<TicketTag[]>([]);

  /* ── Ключевое исправление: храним данные в ref, не в зависимостях ── */
  const aiDoneRef = useRef(false);          // выполнен ли AI для текущего step=2
  const aiAbortRef = useRef<AbortController | null>(null); // отмена текущего запроса
  const titleRef = useRef('');
  const descriptionRef = useRef('');

  // Синхронизируем ref с актуальными данными
  titleRef.current = title;
  descriptionRef.current = description;

  const [newTagInput, setNewTagInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showCustomTagInput, setShowCustomTagInput] = useState(false);

  const isCustomer = user?.role === 'customer' || user?.role === 'customer_admin';
  const canSelectCounterparty = !isCustomer && CAN_SELECT_COUNTERPARTY_ROLES.includes(user?.role || '');
  const canSelectReporter = !isCustomer;

  const counterpartyDropdownRef = useRef<HTMLDivElement>(null);
  const projectDropdownRef = useRef<HTMLDivElement>(null);
  const reporterDropdownRef = useRef<HTMLDivElement>(null);

  const hasDescription = descriptionBlocks.some(
    b => (b.type === 'text' && b.value.trim().length > 0) || (b.type === 'image' && b.localFile)
  );

  // ─── Effects ───

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (counterpartyDropdownRef.current && !counterpartyDropdownRef.current.contains(e.target as Node)) setShowCounterpartyDropdown(false);
      if (projectDropdownRef.current && !projectDropdownRef.current.contains(e.target as Node)) setShowProjectDropdown(false);
      if (reporterDropdownRef.current && !reporterDropdownRef.current.contains(e.target as Node)) setShowReporterDropdown(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  useEffect(() => { pageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, [step]);
  useEffect(() => { if (isCustomer && user?.counterparty_id) loadCustomerCounterparty(); }, [user]);
  useEffect(() => { if (canSelectCounterparty) loadCounterparties(); }, [canSelectCounterparty]);

  useEffect(() => {
    if (selectionType === 'counterparty' && selectedCounterparty) loadProjects(selectedCounterparty.id);
    else if (selectionType === 'project') loadProjectsForAll();
    else setProjects([]);
  }, [selectionType, selectedCounterparty]);

  useEffect(() => {
    if (selectedCounterparty) loadUsers(selectedCounterparty.id);
    else if (selectedProject?.counterparty_id) loadUsers(selectedProject.counterparty_id);
    else { setUsers([]); setSelectedReporter(null); setReporterSearch(''); }
  }, [selectedCounterparty, selectedProject]);

  useEffect(() => {
    if (!preselectedProjectId || !canSelectCounterparty) return;
    const autoSelectProject = async () => {
      setSelectionType('project');
      try {
        const items = (await projectsApi.getAll(1, 100)).items;
        setProjects(items);
        const found = items.find(p => p.id === preselectedProjectId);
        if (found) {
          setSelectedProject(found);
          setProjectSearch(`${found.key} - ${found.name}`);
          if (found.counterparty_id) {
            try {
              const cp = await counterpartiesApi.getById(found.counterparty_id);
              setSelectedCounterparty(cp);
              setCounterpartySearch(cp.name || cp.legal_name || '');
            } catch { }
          }
        }
      } catch (err) {
        console.error('Failed to auto-select project:', err);
      } finally {
        setLoadingProjects(false);
      }
    };
    autoSelectProject();
  }, [preselectedProjectId, canSelectCounterparty]);

  /* ══════════════════════════════════════════════════════════════════════
     AI — исправленная логика без бесконечного цикла
     ══════════════════════════════════════════════════════════════════════ */

  useEffect(() => {
    // Запускаем только когда переходим на шаг 2 и AI ещё не выполнялся
    if (step !== 2) {
      // При возврате на шаг 1 — сбрасываем флаг, чтобы при следующем переходе AI запустился снова
      if (step === 1) {
        aiDoneRef.current = false;
        // Отменяем текущий запрос, если он был
        aiAbortRef.current?.abort();
        aiAbortRef.current = null;
      }
      return;
    }

    // Уже выполняли для этого захода на шаг 2
    if (aiDoneRef.current) return;

    const currentTitle = titleRef.current.trim();
    const currentDesc = descriptionRef.current.trim();

    // Нечего анализировать
    if (!currentTitle || !currentDesc) {
      return;
    }

    // Отменяем предыдущий запрос если был
    aiAbortRef.current?.abort();
    const controller = new AbortController();
    aiAbortRef.current = controller;

    aiDoneRef.current = true; // сразу ставим флаг — больше не запускаем
    setAiLoading(true);
    setAiSuggestion(null);

    ticketsApi.predict(currentTitle, currentDesc)
      .then(r => {
        if (controller.signal.aborted) return;
        setAiSuggestion(r);
        setAiSuggestedTags(r.suggested_tags || []);
        setPriority(r.suggested_priority);
        setTags(r.suggested_tags || []);
      })
      .catch(err => {
        if (controller.signal.aborted) return;
        console.error('AI prediction failed:', err);
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setAiLoading(false);
      });

    // Cleanup при размонтировании или смене step
    return () => {
      controller.abort();
    };
  }, [step]); // ← ТОЛЬКО step в зависимостях — это ключевое исправление

  // ─── Loaders ───

  const loadCustomerCounterparty = async () => {
    if (!user?.counterparty_id) return;
    try { setCustomerCounterparty(await counterpartiesApi.getById(user.counterparty_id)); } catch { }
  };

  const loadCounterparties = async (search?: string) => {
    setLoadingCounterparties(true);
    try {
      let items = (await counterpartiesApi.getAll(1, 50)).items;
      if (search) {
        const q = search.toLowerCase();
        items = items.filter(c =>
          c.name?.toLowerCase().includes(q) ||
          c.legal_name?.toLowerCase().includes(q) ||
          c.inn?.includes(search)
        );
      }
      setCounterparties(items);
      if (!search && preselectedCounterpartyId && !selectedCounterparty) {
        const found = items.find(c => c.id === preselectedCounterpartyId);
        if (found) {
          setSelectionType('counterparty');
          setSelectedCounterparty(found);
          setCounterpartySearch(found.name || found.legal_name || '');
        }
      }
    } catch { }
    finally { setLoadingCounterparties(false); }
  };

  const loadProjects = async (cpId: string) => {
    setLoadingProjects(true);
    try { setProjects((await projectsApi.getByCounterparty(cpId, 1, 50)).items); }
    catch { }
    finally { setLoadingProjects(false); }
  };

  const loadProjectsForAll = async (): Promise<Project[]> => {
    setLoadingProjects(true);
    try {
      const items = (await projectsApi.getAll(1, 100)).items;
      setProjects(items);
      return items;
    } catch { return []; }
    finally { setLoadingProjects(false); }
  };

  const loadUsers = async (cpId: string) => {
    setLoadingUsers(true);
    try {
      const items = (await usersApi.getCustomers(cpId, 1, 100)).items.map(c => ({
        id: c.id, username: c.username, full_name: c.full_name, email: c.email, role: c.role,
      }));
      let all = [...items];
      if (!items.find(u => u.id === user?.user_id) && user?.user_id) {
        all = [{ id: user.user_id, username: user.username || '', full_name: user.full_name || null, email: user.email || '', role: user.role }, ...items];
      }
      setUsers(all); setSelectedReporter(null); setReporterSearch('');
    } catch { }
    finally { setLoadingUsers(false); }
  };

  // ─── Handlers ──

  const handleSelectionTypeChange = (t: SelectionType) => {
    setSelectionType(t); setSelectedCounterparty(null); setSelectedProject(null);
    setCounterpartySearch(''); setProjectSearch(''); setProjects([]);
  };

  const togglePresetTag = (tag: TicketTag) => {
    setTags(p => p.some(t => t.name === tag.name) ? p.filter(t => t.name !== tag.name) : [...p, tag]);
  };

  const addCustomTag = () => {
    const n = newTagInput.trim();
    if (!n || tags.some(t => t.name.toLowerCase() === n.toLowerCase())) return;
    setTags(p => [...p, { name: n, color: '#a1a1aa' }]);
    setNewTagInput('');
    setShowCustomTagInput(false);
  };

  const removeTag = (name: string) => setTags(p => p.filter(t => t.name !== name));

  const validateStep1 = (): boolean => {
    const errors: string[] = [];
    if (!title.trim()) errors.push('Укажите тему заявки');
    if (!hasDescription) errors.push('Добавьте описание заявки');
    setValidationErrors(errors);
    return errors.length === 0;
  };

  const handleNextStep = () => {
    if (step === 1) {
      if (!validateStep1()) return;
    }
    setValidationErrors([]);
    setStep(step + 1);
  };

  useEffect(() => {
    if (validationErrors.length > 0 && title.trim() && hasDescription) {
      setValidationErrors([]);
    }
  }, [title, descriptionBlocks]);

  const handleGeneralFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newF: GeneralFile[] = files.map(f => ({
      id: `${f.name}_${Date.now()}_${Math.random()}`, file: f,
      preview: f.type.startsWith('image/') ? URL.createObjectURL(f) : undefined, status: 'pending',
    }));
    setGeneralFiles(p => [...p, ...newF].slice(0, 10));
    e.target.value = '';
  };

  const handleGeneralDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    const newF: GeneralFile[] = files.map(f => ({
      id: `${f.name}_${Date.now()}_${Math.random()}`, file: f,
      preview: f.type.startsWith('image/') ? URL.createObjectURL(f) : undefined, status: 'pending',
    }));
    setGeneralFiles(p => [...p, ...newF].slice(0, 10));
  };

  const removeGeneralFile = (id: string) => {
    const f = generalFiles.find(x => x.id === id);
    if (f?.preview) URL.revokeObjectURL(f.preview);
    setGeneralFiles(p => p.filter(x => x.id !== id));
  };

  const formatFileSize = (b: number) =>
    b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;

  // ─── Submit ────

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const textOnlyDesc = descriptionBlocks
        .filter((b): b is Extract<DescriptionBlock, { type: 'text' }> => b.type === 'text')
        .map(b => b.value.trim())
        .filter(Boolean)
        .join('\n\n');

      const data: any = {
        title,
        description: textOnlyDesc || '(описание с изображениями)',
        priority,
        type,
        tags: tags.map(t => ({ name: t.name, color: t.color || '#64748b' })),
      };

      if (isCustomer && customerCounterparty) data.counterparty_id = customerCounterparty.id;
      else if (selectedProject) data.project_id = selectedProject.id;
      else if (selectedCounterparty) data.counterparty_id = selectedCounterparty.id;

      if (isCustomer && user?.user_id) data.reporter_id = user.user_id;
      else if (canSelectReporter) data.reporter_id = selectedReporter?.id || user?.user_id;

      const ticket = await ticketsApi.create(data);

      const imageBlocks = descriptionBlocks.filter(
        (b): b is Extract<DescriptionBlock, { type: 'image' }> => b.type === 'image' && !!b.localFile
      );

      const uploadMap: Record<string, string> = {};
      for (const block of imageBlocks) {
        try {
          const att = await attachmentsApi.uploadAttachment(block.localFile!, 'ticket', ticket.id);
          uploadMap[block.id] = att.id;
        } catch (err) {
          console.error('Image upload failed:', block.id, err);
        }
      }

      if (imageBlocks.length > 0) {
        let finalDesc = serializeBlocks(descriptionBlocks);
        for (const [blockId, attachmentId] of Object.entries(uploadMap)) {
          finalDesc = finalDesc.replaceAll(`![image](local:${blockId})`, `![image](media://${attachmentId})`);
        }
        finalDesc = finalDesc.replace(/!\[image\]\(local:[a-f0-9-]+\)\n*/gi, '');
        await ticketsApi.update(ticket.id, { description: finalDesc });
      }

      for (const f of generalFiles.filter(x => x.status === 'pending')) {
        try {
          await attachmentsApi.uploadAttachment(f.file, 'ticket', ticket.id);
        } catch (err) {
          console.error('File upload failed:', f.file.name, err);
        }
      }

      navigate('/tickets');
    } catch (err: any) {
      console.error('Submit failed:', err?.response?.data || err);
    } finally {
      setSubmitting(false);
    }
  };

  const cpName = (c: Counterparty) => c.name || c.legal_name || c.inn || '—';
  const prjName = (p: Project) => `${p.key} - ${p.name}`;
  const uName = (u: SimpleUser) => u.full_name || u.username || u.email;

  // ─── Render ────

  return (
    <div ref={pageRef} className="max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center gap-6 mb-8">
        <button onClick={() => navigate(-1)}
          className="p-3 rounded-xl bg-[var(--hover-1)] hover:bg-[var(--hover-2)] transition-colors">
          <ArrowLeft className="w-6 h-6 text-[var(--text-primary)]" />
        </button>
        <div>
          <h1 className="text-4xl font-bold text-[var(--text-primary)]">Новая заявка</h1>
          <p className="text-[var(--text-primary)]/60">Помощник проведёт вас шаг за шагом</p>
        </div>
      </div>

      {/* Progress */}
      <div className="glass-card p-6 mb-10">
        <div className="flex justify-center">
          {[
            { num: 1, label: 'Название и описание', icon: <FileText className="w-5 h-5" /> },
            { num: 2, label: 'Тип, приоритет и теги', icon: <Tag className="w-5 h-5" /> },
            { num: 3, label: 'Проверка и отправка', icon: <CheckCircle2 className="w-5 h-5" /> },
          ].map((s, i) => (
            <div key={s.num} className="flex items-center">
              <div className={`flex items-center gap-4 ${step >= s.num ? 'text-[var(--text-primary)]' : 'text-[var(--text-primary)]/40'}`}>
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border-2 transition-all
                  ${step === s.num
                    ? 'bg-red-600 border-red-500 scale-110'
                    : step > s.num
                      ? 'bg-emerald-600 border-emerald-500'
                      : 'bg-[var(--hover-1)] border-[var(--border-color)]'
                  }`}>
                  {step > s.num ? <CheckCircle2 className="w-6 h-6" /> : s.icon}
                </div>
                <div>
                  <div className="font-semibold text-lg">Шаг {s.num}</div>
                  <div className="text-sm">{s.label}</div>
                </div>
              </div>
              {i < 2 && (
                <div className={`w-24 h-1 mx-6 rounded-full ${step > s.num ? 'bg-red-600' : 'bg-[var(--hover-1)]'}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card p-8 md:p-12">

        {/* ═══ Step 1 ═══ */}
        {step === 1 && (
          <div className="space-y-10">
            {validationErrors.length > 0 && (
              <div className="p-5 rounded-2xl bg-red-500/10 border border-red-500/30 space-y-2">
                {validationErrors.map((err, i) => (
                  <div key={i} className="flex items-center gap-3 text-red-400">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span className="text-base font-medium">{err}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Привязка */}
            {canSelectCounterparty && (
              <>
                <div>
                  <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-4">Привязать заявку к</label>
                  <div className="flex gap-4">
                    <button type="button" onClick={() => handleSelectionTypeChange('project')}
                      className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 transition-all
                        ${selectionType === 'project'
                          ? 'border-amber-500 bg-amber-500/20 text-amber-400'
                          : 'border-[var(--border-color)] bg-[var(--hover-1)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)]'
                        }`}>
                      <FolderOpen className="w-6 h-6" />
                      <span className="text-lg font-medium">Проекту</span>
                    </button>
                    <button type="button" onClick={() => handleSelectionTypeChange('counterparty')}
                      className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 transition-all
                        ${selectionType === 'counterparty'
                          ? 'border-blue-500 bg-blue-500/20 text-blue-400'
                          : 'border-[var(--border-color)] bg-[var(--hover-1)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)]'
                        }`}>
                      <Building2 className="w-6 h-6" />
                      <span className="text-lg font-medium">Контрагенту</span>
                    </button>
                  </div>
                </div>
                <button type="button" onClick={() => handleSelectionTypeChange(null)}
                  className={`w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 transition-all
                    ${selectionType === null
                      ? 'border-white bg-[var(--hover-1)] text-[var(--text-primary)]'
                      : 'border-[var(--border-color)] bg-[var(--hover-1)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)]'
                    }`}>
                  <X className="w-5 h-5" />
                  <span className="text-lg font-medium">Без привязки</span>
                </button>
              </>
            )}

            {/* Контрагент */}
            {canSelectCounterparty && selectionType === 'counterparty' && (
              <div>
                <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-4">
                  Контрагент <span className="text-red-400">*</span>
                </label>
                <div className="relative" ref={counterpartyDropdownRef}>
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-primary)]/40" />
                    <input value={counterpartySearch}
                      onChange={e => { setCounterpartySearch(e.target.value); setShowCounterpartyDropdown(true); loadCounterparties(e.target.value); }}
                      onFocus={() => { setShowCounterpartyDropdown(true); if (!counterparties.length) loadCounterparties(); }}
                      placeholder="Поиск..."
                      style={{ paddingLeft: '3.5rem' }}
                      className="input-field py-5 text-lg w-full" />
                  </div>
                  {showCounterpartyDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                      {loadingCounterparties
                        ? <div className="p-6 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-[var(--text-primary)]/40" /></div>
                        : counterparties.map(cp => (
                          <button key={cp.id}
                            onClick={() => { setSelectedCounterparty(cp); setCounterpartySearch(cpName(cp)); setShowCounterpartyDropdown(false); }}
                            className="w-full text-left p-4 hover:bg-[var(--hover-1)] border-b border-[var(--border-color)] last:border-0">
                            <div className="font-semibold text-[var(--text-primary)]">{cpName(cp)}</div>
                            {cp.inn && <div className="text-xs text-[var(--text-primary)]/40 mt-1">ИНН: {cp.inn}</div>}
                          </button>
                        ))}
                    </div>
                  )}
                </div>
                {selectedCounterparty && (
                  <div className="mt-3 p-4 rounded-xl bg-green-500/10 border border-green-500/30 text-green-400">
                    ✓ {cpName(selectedCounterparty)}
                  </div>
                )}
              </div>
            )}

            {/* Проект */}
            {canSelectCounterparty && selectionType === 'project' && (
              <div>
                <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-4">
                  Проект <span className="text-red-400">*</span>
                </label>
                <div className="relative" ref={projectDropdownRef}>
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-primary)]/40" />
                    <input value={projectSearch}
                      onChange={e => { setProjectSearch(e.target.value); setShowProjectDropdown(true); }}
                      onFocus={() => { setShowProjectDropdown(true); if (!projects.length) loadProjectsForAll(); }}
                      placeholder="Поиск..."
                      style={{ paddingLeft: '3.5rem' }}
                      className="input-field py-5 text-lg w-full" />
                  </div>
                  {showProjectDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                      {loadingProjects
                        ? <div className="p-6 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-[var(--text-primary)]/40" /></div>
                        : projects
                          .filter(p => !projectSearch || p.name.toLowerCase().includes(projectSearch.toLowerCase()) || p.key.toLowerCase().includes(projectSearch.toLowerCase()))
                          .map(p => (
                            <button key={p.id}
                              onClick={() => { setSelectedProject(p); setProjectSearch(prjName(p)); setShowProjectDropdown(false); }}
                              className="w-full text-left p-4 hover:bg-[var(--hover-1)] border-b border-[var(--border-color)] last:border-0">
                              <span className="text-amber-400">{p.key}</span> — {p.name}
                            </button>
                          ))}
                    </div>
                  )}
                </div>
                {selectedProject && (
                  <div className="mt-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
                    ✓ {prjName(selectedProject)}
                  </div>
                )}
              </div>
            )}

            {/* Customer контрагент */}
            {isCustomer && customerCounterparty && (
              <div className="p-6 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center gap-4">
                <Building2 className="w-8 h-8 text-blue-400" />
                <div>
                  <p className="text-base font-semibold text-[var(--text-primary)]">{customerCounterparty.name}</p>
                  {customerCounterparty.inn && (
                    <p className="text-[var(--text-primary)]/50 text-sm">ИНН: {customerCounterparty.inn}</p>
                  )}
                </div>
              </div>
            )}

            {/* Инициатор */}
            {canSelectReporter && (selectedCounterparty || selectedProject) && (
              <div>
                <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-4">
                  Инициатор <span className="text-[var(--text-primary)]/40 text-sm">(по умолчанию — вы)</span>
                </label>
                <div className="relative" ref={reporterDropdownRef}>
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-primary)]/40" />
                  <input value={reporterSearch}
                    onChange={e => { setReporterSearch(e.target.value); setShowReporterDropdown(true); }}
                    onFocus={() => setShowReporterDropdown(true)}
                    placeholder="Выберите..."
                    style={{ paddingLeft: '3.5rem' }}
                    className="input-field py-5 text-lg w-full" />
                  {showReporterDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                      {loadingUsers
                        ? <div className="p-6 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-[var(--text-primary)]/40" /></div>
                        : (
                          <>
                            <button onClick={() => { setSelectedReporter(null); setReporterSearch(''); setShowReporterDropdown(false); }}
                              className="w-full text-left p-4 hover:bg-[var(--hover-1)] border-b border-[var(--border-color)]">
                              <span className="text-[var(--text-primary)]">{user?.full_name || 'Вы'}</span>{' '}
                              <span className="text-[var(--text-primary)]/40">(текущий)</span>
                            </button>
                            {users
                              .filter(u => !reporterSearch ||
                                u.full_name?.toLowerCase().includes(reporterSearch.toLowerCase()) ||
                                u.email.toLowerCase().includes(reporterSearch.toLowerCase()))
                              .map(u => (
                                <button key={u.id}
                                  onClick={() => { setSelectedReporter(u); setReporterSearch(uName(u)); setShowReporterDropdown(false); }}
                                  className="w-full text-left p-4 hover:bg-[var(--hover-1)] border-b border-[var(--border-color)] last:border-0">
                                  <div className="text-[var(--text-primary)]">{uName(u)}</div>
                                  <div className="text-[var(--text-primary)]/40 text-sm">{u.email}</div>
                                </button>
                              ))}
                          </>
                        )}
                    </div>
                  )}
                </div>
                <div className="mt-3 p-4 rounded-xl bg-[var(--hover-1)] text-[var(--text-primary)]/60">
                  Инициатор:{' '}
                  <span className="text-[var(--text-primary)] font-medium">
                    {selectedReporter ? uName(selectedReporter) : (user?.full_name || 'Вы')}
                  </span>
                </div>
              </div>
            )}

            {/* Тема */}
            <SpellCheckField value={title} onChange={setTitle} label="Тема заявки *">
              <input type="text" value={title} onChange={e => setTitle(e.target.value)}
                placeholder="Кратко опишите проблему..."
                className={`input-field py-5 text-2xl w-full ${validationErrors.includes('Укажите тему заявки') ? 'border-red-500 ring-1 ring-red-500/50' : ''}`} />
            </SpellCheckField>

            {/* Описание */}
            <div>
              <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-4">
                Подробное описание <span className="text-red-400">*</span>
              </label>
              <div className={validationErrors.includes('Добавьте описание заявки') ? 'ring-1 ring-red-500/50 rounded-2xl' : ''}>
                <TicketEditor blocks={descriptionBlocks} onChange={setDescriptionBlocks} />
              </div>
            </div>

            {/* Вложения */}
            <div>
              <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-4">
                <Upload className="inline w-6 h-6 mr-2 text-[var(--text-primary)]/40" />
                Прикрепить файлы
              </label>
              <div onDrop={handleGeneralDrop} onDragOver={e => e.preventDefault()}
                className="border-2 border-dashed border-[var(--border-color)] rounded-xl p-8 text-center hover:border-[var(--border-color)] transition-colors">
                <Upload className="w-10 h-10 text-[var(--text-primary)]/20 mx-auto mb-3" />
                <p className="text-lg text-[var(--text-primary)]/50 mb-2">Перетащите файлы сюда</p>
                <label className="inline-block">
                  <input type="file" multiple onChange={handleGeneralFileSelect} className="hidden" />
                  <span className="px-5 py-2.5 rounded-xl bg-red-700 hover:bg-red-600 text-white text-base font-medium cursor-pointer transition-colors">
                    Выбрать файлы
                  </span>
                </label>
                <p className="mt-3 text-sm text-[var(--text-primary)]/30">До 10 файлов, максимум 25 МБ</p>
              </div>

              {generalFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  {generalFiles.map(f => (
                    <div key={f.id} className="flex items-center gap-3 p-3 rounded-xl bg-[var(--hover-2)] border border-[var(--border-color)]">
                      {f.preview
                        ? <img src={f.preview} alt="" className="w-12 h-12 rounded-lg object-cover" />
                        : <div className="w-12 h-12 rounded-lg bg-[var(--hover-2)] flex items-center justify-center">
                          <File className="w-5 h-5 text-[var(--text-primary)]/40" />
                        </div>}
                      <div className="flex-1 min-w-0">
                        <p className="text-base text-[var(--text-primary)] truncate">{f.file.name}</p>
                        <p className="text-sm text-[var(--text-primary)]/40">{formatFileSize(f.file.size)}</p>
                      </div>
                      <button onClick={() => removeGeneralFile(f.id)}
                        className="p-1.5 rounded-lg hover:bg-[var(--hover-3)] text-[var(--text-primary)]/30 hover:text-red-400 transition-colors">
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══ Step 2 ═══ */}
        {step === 2 && (
          <div className="space-y-12">

            {/* AI Loading */}
            {aiLoading && (
              <div className="p-8 rounded-2xl bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/20 flex flex-col items-center gap-4">
                <div className="relative">
                  <div className="w-16 h-16 rounded-full bg-yellow-500/20 flex items-center justify-center">
                    <Sparkles className="w-8 h-8 text-yellow-400 animate-pulse" />
                  </div>
                  <Loader2 className="w-16 h-16 text-yellow-400 animate-spin absolute inset-0" />
                </div>
                <div className="text-center">
                  <h3 className="text-xl font-semibold text-[var(--text-primary)]">ИИ анализирует вашу заявку...</h3>
                  <p className="text-[var(--text-secondary)] mt-2">Подбираем оптимальный приоритет и теги</p>
                </div>
              </div>
            )}

            {/* AI Success */}
            {aiSuggestion && !aiLoading && (
              <div className="p-6 rounded-2xl bg-gradient-to-r from-yellow-500/20 to-orange-500/15
                              border border-yellow-500/20 flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                  <Zap className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[var(--text-primary)]">ИИ предложил приоритет и теги</h3>
                  <p className="text-[var(--text-secondary)] mt-1">Проверьте и внесите правки при необходимости</p>
                </div>
              </div>
            )}

            <div className={aiLoading ? 'opacity-40 pointer-events-none transition-opacity' : 'transition-opacity'}>

              {/* Тип */}
              <div>
                <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-6">Тип заявки</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {TICKET_TYPES.map(t => {
                    const isSelected = type === t.value;
                    return (
                      <button key={t.value} onClick={() => setType(t.value as TicketType)}
                        className={`px-6 py-4 rounded-2xl text-left border transition-all
                          ${isSelected
                            ? `${t.activeColor} scale-[1.02] shadow-lg`
                            : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)]'
                          }`}>
                        <div className="flex items-start gap-3">
                          <div className={`flex-shrink-0 mt-0.5 ${isSelected ? '' : 'opacity-50'}`}>{t.icon}</div>
                          <div className="flex-1">
                            <div className="font-semibold text-lg">{t.label}</div>
                            <div className="text-sm opacity-70 mt-1">{t.desc}</div>
                          </div>
                          {isSelected && <CheckCircle2 className="w-6 h-6 flex-shrink-0 mt-0.5" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Приоритет */}
              <div className="mt-12">
                <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-6">Приоритет</label>
                <div className="flex flex-wrap gap-3">
                  {PRIORITIES.map(p => {
                    const isSelected = priority === p.value;
                    return (
                      <button key={p.value} onClick={() => setPriority(p.value as TicketPriority)}
                        className={`px-8 py-5 rounded-2xl text-lg font-medium border flex-1 min-w-[200px] text-left transition-all
                          ${isSelected
                            ? `${p.activeColor} scale-[1.02] shadow-lg`
                            : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)]'
                          }`}>
                        <div className="flex items-center gap-4">
                          <div className={isSelected ? '' : 'opacity-40'}>{p.icon}</div>
                          <div>
                            <div className="font-semibold">{p.label}</div>
                            <div className="text-sm opacity-70">{p.desc}</div>
                          </div>
                          {isSelected && <CheckCircle2 className="w-6 h-6 ml-auto flex-shrink-0" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Теги */}
              <div className="mt-12">
                <label className="block text-2xl font-semibold text-[var(--text-primary)] mb-6">Теги</label>

                {aiSuggestedTags.length > 0 && (
                  <div className="mb-6">
                    <p className="text-[var(--text-primary)]/50 text-sm mb-3 flex items-center gap-2">
                      <Sparkles className="w-4 h-4" /> Предложено ИИ
                    </p>
                    <div className="flex flex-wrap gap-3">
                      {aiSuggestedTags.map(t => {
                        const isSelected = tags.some(x => x.name === t.name);
                        return (
                          <button key={t.name} onClick={() => togglePresetTag(t)}
                            className={`px-6 py-3 rounded-2xl text-base font-medium border transition-all
                              ${isSelected
                                ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 ring-1 ring-amber-500/30'
                                : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)]'
                              }`}>
                            <span className="flex items-center gap-2">
                              {isSelected && <CheckCircle2 className="w-4 h-4" />}
                              {t.name}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap gap-3 mb-6">
                  {PRESET_TAGS.map(t => {
                    const isSelected = tags.some(x => x.name === t.name);
                    return (
                      <button key={t.name} onClick={() => togglePresetTag(t)}
                        className={`px-6 py-3 rounded-2xl text-base font-medium border transition-all
                          ${isSelected ? '' : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)]'}`}
                        style={{
                          backgroundColor: isSelected ? `${t.color}25` : undefined,
                          color: isSelected ? t.color : undefined,
                          borderColor: isSelected ? `${t.color}80` : undefined,
                        }}>
                        <span className="flex items-center gap-2">
                          {isSelected && <CheckCircle2 className="w-4 h-4" />}
                          {t.name}
                        </span>
                      </button>
                    );
                  })}
                </div>

                <button onClick={() => setShowCustomTagInput(!showCustomTagInput)}
                  className="text-blue-400 hover:text-blue-300 flex items-center gap-2 text-sm mb-4">
                  <Plus className="w-4 h-4" />{showCustomTagInput ? 'Скрыть' : 'Свой тег'}
                </button>

                {showCustomTagInput && (
                  <div className="flex gap-3 mb-6">
                    <input value={newTagInput} onChange={e => setNewTagInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && addCustomTag()}
                      placeholder="Тег..." className="input-field flex-1 py-4 text-lg" />
                    <button onClick={addCustomTag} disabled={!newTagInput.trim()}
                      className="px-6 py-3 rounded-xl bg-red-700 hover:bg-red-600 text-white font-medium disabled:opacity-40">
                      Добавить
                    </button>
                  </div>
                )}

                {tags.length > 0 && (
                  <div className="p-5 bg-[var(--hover-1)] rounded-2xl">
                    <p className="text-[var(--text-primary)]/50 mb-3">Выбрано: {tags.length}</p>
                    <div className="flex flex-wrap gap-3">
                      {tags.map(t => (
                        <div key={t.name} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl border"
                          style={{
                            backgroundColor: `${t.color || '#71717a'}20`,
                            borderColor: `${t.color || '#71717a'}50`,
                            color: t.color || '#d1d5db',
                          }}>
                          {t.name}
                          <X className="w-4 h-4 cursor-pointer opacity-60 hover:opacity-100 hover:text-red-400 transition-all"
                            onClick={() => removeTag(t.name)} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ═══ Step 3 ═══ */}
        {step === 3 && (
          <div className="space-y-10">
            <div className="text-center mb-10">
              <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-12 h-12 text-green-400" />
              </div>
              <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Проверьте заявку</h2>
              <p className="text-lg text-[var(--text-primary)]/60">Убедитесь, что всё правильно</p>
            </div>

            <div className="space-y-6 animate-in fade-in duration-500">
              {selectedProject && (
                <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-4">
                  <FolderOpen className="w-8 h-8 text-amber-400" />
                  <div>
                    <p className="text-[var(--text-primary)] font-semibold">{prjName(selectedProject)}</p>
                    <p className="text-[var(--text-primary)]/40 text-sm">контрагент из проекта</p>
                  </div>
                </div>
              )}
              {!selectedProject && selectedCounterparty && (
                <div className="p-6 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center gap-4">
                  <Building2 className="w-8 h-8 text-blue-400" />
                  <p className="text-[var(--text-primary)] font-semibold">{cpName(selectedCounterparty)}</p>
                </div>
              )}
              {isCustomer && customerCounterparty && !selectedProject && !selectedCounterparty && (
                <div className="p-6 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center gap-4">
                  <Building2 className="w-8 h-8 text-blue-400" />
                  <p className="text-[var(--text-primary)] font-semibold">{customerCounterparty.name}</p>
                </div>
              )}
              {canSelectCounterparty && selectionType === null && (
                <div className="p-6 rounded-2xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-center">
                  Без привязки
                </div>
              )}

              <div className="p-6 rounded-2xl bg-green-500/10 border border-green-500/30 flex items-center gap-4">
                <User className="w-8 h-8 text-green-400" />
                <div>
                  <p className="text-[var(--text-primary)] font-semibold">
                    {selectedReporter ? uName(selectedReporter) : (user?.full_name || 'Вы')}
                  </p>
                  <p className="text-[var(--text-primary)]/40 text-sm">
                    {selectedReporter ? selectedReporter.email : user?.email}
                  </p>
                </div>
              </div>

              <div className="p-6 rounded-2xl bg-[var(--hover-1)]">
                <p className="text-[var(--text-primary)]/50 mb-2">Тема</p>
                <p className="text-[var(--text-primary)] font-semibold text-lg break-words">{title || '—'}</p>
              </div>

              <div className="p-6 rounded-2xl bg-[var(--hover-1)]">
                <p className="text-[var(--text-primary)]/50 mb-4">Описание</p>
                <div className="space-y-4">
                  {descriptionBlocks.map(block => {
                    if (block.type === 'text') {
                      if (!block.value.trim()) return null;
                      return (
                        <TicketDescriptionContent key={block.id} text={block.value}
                          className="text-[var(--text-primary)] text-base leading-relaxed" />
                      );
                    }
                    if (block.type === 'image' && block.localPreview) {
                      return (
                        <img key={block.id} src={block.localPreview} alt="вложение"
                          className="max-w-full max-h-[400px] rounded-2xl border border-[var(--border-color)] object-contain" />
                      );
                    }
                    return null;
                  })}
                  {descriptionBlocks.every(b =>
                    (b.type === 'text' && !b.value.trim()) ||
                    (b.type === 'image' && !b.localPreview)
                  ) && <p className="text-[var(--text-primary)]/30">—</p>}
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div className="p-6 rounded-2xl bg-[var(--hover-1)]">
                  <p className="text-[var(--text-primary)]/50 mb-3">Тип</p>
                  <div className={`inline-flex items-center gap-2 text-lg px-5 py-2.5 rounded-2xl ${TICKET_TYPES.find(t => t.value === type)?.color || ''}`}>
                    {TICKET_TYPES.find(t => t.value === type)?.icon} {type}
                  </div>
                </div>
                <div className="p-6 rounded-2xl bg-[var(--hover-1)]">
                  <p className="text-[var(--text-primary)]/50 mb-3">Приоритет</p>
                  <div className={`inline-flex items-center gap-3 text-lg px-5 py-2.5 rounded-2xl ${PRIORITIES.find(p => p.value === priority)?.color || ''}`}>
                    {PRIORITIES.find(p => p.value === priority)?.icon} {priority}
                  </div>
                </div>
              </div>

              {tags.length > 0 && (
                <div className="p-6 rounded-2xl bg-[var(--hover-1)]">
                  <p className="text-[var(--text-primary)]/50 mb-3">Теги</p>
                  <div className="flex flex-wrap gap-2">
                    {tags.map(t => (
                      <span key={t.name} className="px-4 py-2 rounded-xl text-base font-medium"
                        style={{
                          backgroundColor: (t.color || '#71717a') + '30',
                          color: t.color || '#d1d5db',
                        }}>
                        {t.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {generalFiles.length > 0 && (
                <div className="p-6 rounded-2xl bg-[var(--hover-1)]">
                  <p className="text-[var(--text-primary)]/50 mb-3">Вложения ({generalFiles.length})</p>
                  <div className="space-y-2">
                    {generalFiles.map(f => (
                      <div key={f.id} className="flex items-center gap-3 text-[var(--text-primary)]">
                        <File className="w-5 h-5 text-[var(--text-primary)]/40" />
                        <span>{f.file.name}</span>
                        <span className="text-yellow-400 text-sm">(загрузится при создании)</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-12 pt-8 border-t border-[var(--border-color)]">
          {step > 1 ? (
            <button onClick={() => setStep(step - 1)}
              className="flex items-center gap-3 px-8 py-4 rounded-2xl bg-[var(--hover-1)] hover:bg-[var(--hover-2)] text-lg font-medium transition-colors">
              <ArrowLeft className="w-5 h-5" /> Назад
            </button>
          ) : <div />}

          {step < 3 ? (
            <button onClick={handleNextStep}
              disabled={step === 1 && (!title.trim() || !hasDescription)}
              className="px-10 py-4 rounded-2xl bg-red-700 hover:bg-red-600 text-white text-lg font-semibold ml-auto
                         shadow-lg shadow-red-900/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-red-700">
              Далее <ArrowRight className="w-5 h-5 inline ml-2" />
            </button>
          ) : (
            <button onClick={handleSubmit} disabled={submitting}
              className="px-12 py-4 rounded-2xl bg-red-700 hover:bg-red-600 text-white text-lg font-semibold
                         flex items-center gap-3 ml-auto disabled:opacity-50 shadow-lg shadow-red-900/30">
              {submitting
                ? <Loader2 className="w-6 h-6 animate-spin" />
                : <><FileText className="w-5 h-5" /> Создать заявку</>}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}