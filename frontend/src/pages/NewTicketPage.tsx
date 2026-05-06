import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Sparkles, Loader2, FileText,
  Tag, Upload, X, CheckCircle2, File, Building2, Zap, Plus,
  Search, FolderOpen, User,
} from 'lucide-react';
import { SignalLow, SignalMedium, SignalHigh, Flame } from 'lucide-react';

import { useAuthStore } from '../stores/authStore';
import { ticketsApi, counterpartiesApi, projectsApi, usersApi } from '../api/client';
import { attachmentsApi } from '../api/attachments';
import type { Counterparty, TicketTag, TicketPriority, Project } from '../types';
import { SpellCheckField } from '../components/helpers/SpellCheckField';
import { TicketDescriptionContent } from '../components/helpers/TicketDescriptionContent';
import {
  TicketEditor, serializeBlocks, type DescriptionBlock,
} from '../components/helpers/TicketEditor';

// ─── Константы ────────────────────────────────────────────────────────────────

const PRIORITIES = [
  { value: 'Низкий',      label: 'Низкий',      color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', icon: <SignalLow className="w-10 h-10" />,    desc: 'Плановый порядок' },
  { value: 'Средний',     label: 'Средний',     color: 'bg-amber-500/20 text-amber-400 border-amber-500/40',       icon: <SignalMedium className="w-10 h-10" />,  desc: 'Стандартный' },
  { value: 'Высокий',     label: 'Высокий',     color: 'bg-orange-500/20 text-orange-400 border-orange-500/40',     icon: <SignalHigh className="w-10 h-10" />,    desc: 'Требует внимания' },
  { value: 'Критический',label: 'Критический', color: 'bg-red-500/20 text-red-400 border-red-500/40',              icon: <Flame className="w-10 h-10" />,         desc: 'Немедленно!' },
];

const PRESET_TAGS = [
  { name: 'Инцидент', color: '#ef4444' }, { name: 'Консультация', color: '#3b82f6' },
  { name: 'Доработка', color: '#8b5cf6' }, { name: 'Ошибка', color: '#f97316' },
  { name: 'Интеграция', color: '#06b6d4' }, { name: 'Обучение', color: '#10b981' },
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

// ─── Компонент ────────────────────────────────────────────────────────────────

export default function NewTicketPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const pageRef = useRef<HTMLDivElement>(null);

  const [step, setStep] = useState(1);
  const [title, setTitle] = useState('');

  // Описание — блоковая модель
  const [descriptionBlocks, setDescriptionBlocks] = useState<DescriptionBlock[]>([
    { id: 'init', type: 'text', value: '' },
  ]);
  const description = serializeBlocks(descriptionBlocks);

  const [priority, setPriority] = useState<TicketPriority>('Средний');
  const [tags, setTags] = useState<TicketTag[]>([]);
  const [aiSuggestedTags, setAiSuggestedTags] = useState<TicketTag[]>([]);

  // Обычные вложения (не картинки в тексте)
  const [generalFiles, setGeneralFiles] = useState<GeneralFile[]>([]);

  // Привязки
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
  const [newTagInput, setNewTagInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showCustomTagInput, setShowCustomTagInput] = useState(false);
  const [aiAutoEnabled, setAiAutoEnabled] = useState(true);

  const isCustomer = user?.role === 'customer' || user?.role === 'customer_admin';
  const canSelectCounterparty = !isCustomer && CAN_SELECT_COUNTERPARTY_ROLES.includes(user?.role || '');
  const canSelectReporter = !isCustomer;

  const counterpartyDropdownRef = useRef<HTMLDivElement>(null);
  const projectDropdownRef = useRef<HTMLDivElement>(null);
  const reporterDropdownRef = useRef<HTMLDivElement>(null);

  // ─── Effects ───────────────────────────────────────────────────────────────

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

  // AI
  const runAI = useCallback(async () => {
    if (!title || !description) return;
    setAiLoading(true);
    try {
      const r = await ticketsApi.predict(title, description);
      setAiSuggestion(r); setAiSuggestedTags(r.suggested_tags || []);
      setPriority(r.suggested_priority); setTags(r.suggested_tags || []);
    } catch {} finally { setAiLoading(false); }
  }, [title, description]);

  useEffect(() => {
    if (step === 1 && aiAutoEnabled) { const t = setTimeout(runAI, 1000); return () => clearTimeout(t); }
  }, [title, description, step, aiAutoEnabled, runAI]);

  useEffect(() => { if (step === 2) setAiAutoEnabled(false); else if (step === 1) setAiAutoEnabled(true); }, [step]);

  // ─── Loaders ───────────────────────────────────────────────────────────────

  const loadCustomerCounterparty = async () => {
    if (!user?.counterparty_id) return;
    try { setCustomerCounterparty(await counterpartiesApi.getById(user.counterparty_id)); } catch {}
  };

  const loadCounterparties = async (search?: string) => {
    setLoadingCounterparties(true);
    try {
      let items = (await counterpartiesApi.getAll(1, 50)).items;
      if (search) { const q = search.toLowerCase(); items = items.filter(c => c.name?.toLowerCase().includes(q) || c.legal_name?.toLowerCase().includes(q) || c.inn?.includes(search)); }
      setCounterparties(items);
    } catch {} finally { setLoadingCounterparties(false); }
  };

  const loadProjects = async (cpId: string) => {
    setLoadingProjects(true);
    try { setProjects((await projectsApi.getByCounterparty(cpId, 1, 50)).items); } catch {} finally { setLoadingProjects(false); }
  };

  const loadProjectsForAll = async () => {
    setLoadingProjects(true);
    try { setProjects((await projectsApi.getAll(1, 100)).items); } catch {} finally { setLoadingProjects(false); }
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
    } catch {} finally { setLoadingUsers(false); }
  };

  // ─── Handlers ──────────────────────────────────────────────────────────────

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
    setTags(p => [...p, { name: n, color: '#a1a1aa' }]); setNewTagInput(''); setShowCustomTagInput(false);
  };
  const removeTag = (name: string) => setTags(p => p.filter(t => t.name !== name));

  // Обычные файлы
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

  const formatFileSize = (b: number) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;

  // ─── Submit ────────────────────────────────────────────────────────────────

const handleSubmit = async () => {
  setSubmitting(true);
  try {
    // Собираем только текстовую часть для первичного создания
    // (чтобы в БД не попал [[local-image:...]])
    const textOnlyDesc = descriptionBlocks
      .filter(
        (b): b is Extract<DescriptionBlock, { type: 'text' }> =>
          b.type === 'text'
      )
      .map((b) => b.value.trim())
      .filter(Boolean)
      .join('\n\n');

    const data: any = {
      title,
      description: textOnlyDesc || '(описание с изображениями)',
      priority,
      tags: tags.map((t) => ({ name: t.name, color: t.color || '#64748b' })),
    };

    if (isCustomer && customerCounterparty)
      data.counterparty_id = customerCounterparty.id;
    else if (selectedProject) data.project_id = selectedProject.id;
    else if (selectedCounterparty)
      data.counterparty_id = selectedCounterparty.id;

    if (isCustomer && user?.user_id) data.reporter_id = user.user_id;
    else if (canSelectReporter)
      data.reporter_id = selectedReporter?.id || user?.user_id;

    const ticket = await ticketsApi.create(data);

    // 1. Загружаем картинки из блоков описания
    const imageBlocks = descriptionBlocks.filter(
      (b): b is Extract<DescriptionBlock, { type: 'image' }> =>
        b.type === 'image' && !!b.localFile
    );

    const uploadMap: Record<string, string> = {};

    for (const block of imageBlocks) {
      try {
        const att = await attachmentsApi.uploadAttachment(
          block.localFile!,
          'ticket',
          ticket.id
        );
        uploadMap[block.id] = att.id;
      } catch (err) {
        console.error('Image upload failed:', block.id, err);
      }
    }

    // 2. Собираем финальное описание с реальными ID вложений
    if (imageBlocks.length > 0) {
      let finalDesc = serializeBlocks(descriptionBlocks);

      for (const [blockId, attachmentId] of Object.entries(uploadMap)) {
        finalDesc = finalDesc.replaceAll(
          `[[local-image:${blockId}]]`,
          `[[image:${attachmentId}]]`
        );
      }

      // Убираем оставшиеся local-image (если upload упал)
      finalDesc = finalDesc.replace(
        /\[\[local-image:[^\]]+\]\]\n*/g,
        ''
      );

      await ticketsApi.update(ticket.id, { description: finalDesc });
    }

    // 3. Загружаем обычные файлы
    for (const f of generalFiles.filter((x) => x.status === 'pending')) {
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

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div ref={pageRef} className="max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center gap-6 mb-8">
        <button onClick={() => navigate(-1)} className="p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors">
          <ArrowLeft className="w-6 h-6 text-white" />
        </button>
        <div>
          <h1 className="text-4xl font-bold text-white">Новая заявка</h1>
          <p className="text-white/60">Помощник проведёт вас шаг за шагом</p>
        </div>
      </div>

      {/* Progress */}
      <div className="glass-card p-6 mb-10">
        <div className="flex justify-center">
          {[
            { num: 1, label: 'Описание', icon: <FileText className="w-5 h-5" /> },
            { num: 2, label: 'Приоритет и теги', icon: <Tag className="w-5 h-5" /> },
            { num: 3, label: 'Проверка', icon: <CheckCircle2 className="w-5 h-5" /> },
          ].map((s, i) => (
            <div key={s.num} className="flex items-center">
              <div className={`flex items-center gap-4 ${step >= s.num ? 'text-white' : 'text-white/40'}`}>
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border-2 transition-all ${
                  step === s.num ? 'bg-red-600 border-red-500 scale-110' : step > s.num ? 'bg-emerald-600 border-emerald-500' : 'bg-white/10 border-white/20'
                }`}>{step > s.num ? <CheckCircle2 className="w-6 h-6" /> : s.icon}</div>
                <div><div className="font-semibold text-lg">Шаг {s.num}</div><div className="text-sm">{s.label}</div></div>
              </div>
              {i < 2 && <div className={`w-24 h-1 mx-6 rounded-full ${step > s.num ? 'bg-red-600' : 'bg-white/10'}`} />}
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card p-8 md:p-12">

        {/* ═══ Step 1 ═══ */}
        {step === 1 && (
          <div className="space-y-10">
            {/* Привязка (admin/support) */}
            {canSelectCounterparty && (
              <>
                <div>
                  <label className="block text-2xl font-semibold text-white mb-4">Привязать заявку к</label>
                  <div className="flex gap-4">
                    <button type="button" onClick={() => handleSelectionTypeChange('project')}
                            className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 transition-all ${selectionType === 'project' ? 'border-purple-500 bg-purple-500/20 text-purple-400' : 'border-white/20 bg-white/5 text-white/60 hover:bg-white/10'}`}>
                      <FolderOpen className="w-6 h-6" /><span className="text-lg font-medium">Проекту</span>
                    </button>
                    <button type="button" onClick={() => handleSelectionTypeChange('counterparty')}
                            className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 transition-all ${selectionType === 'counterparty' ? 'border-blue-500 bg-blue-500/20 text-blue-400' : 'border-white/20 bg-white/5 text-white/60 hover:bg-white/10'}`}>
                      <Building2 className="w-6 h-6" /><span className="text-lg font-medium">Контрагенту</span>
                    </button>
                  </div>
                </div>
                <button type="button" onClick={() => handleSelectionTypeChange(null)}
                        className={`w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 transition-all ${selectionType === null ? 'border-white bg-white/10 text-white' : 'border-white/20 bg-white/5 text-white/60 hover:bg-white/10'}`}>
                  <X className="w-5 h-5" /><span className="text-lg font-medium">Без привязки</span>
                </button>
              </>
            )}

            {/* Контрагент */}
            {canSelectCounterparty && selectionType === 'counterparty' && (
              <div>
                <label className="block text-2xl font-semibold text-white mb-4">Контрагент <span className="text-red-400">*</span></label>
                <div className="relative" ref={counterpartyDropdownRef}>
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                    <input value={counterpartySearch}
                           onChange={e => { setCounterpartySearch(e.target.value); setShowCounterpartyDropdown(true); loadCounterparties(e.target.value); }}
                           onFocus={() => { setShowCounterpartyDropdown(true); if (!counterparties.length) loadCounterparties(); }}
                           placeholder="Поиск..." className="input-field pl-12 py-5 text-lg w-full" />
                  </div>
                  {showCounterpartyDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[#0c0c0c] border border-white/20 rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                      {loadingCounterparties ? <div className="p-6 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-white/40" /></div> :
                        counterparties.map(cp => (
                          <button key={cp.id} onClick={() => { setSelectedCounterparty(cp); setCounterpartySearch(cpName(cp)); setShowCounterpartyDropdown(false); }}
                                  className="w-full text-left p-4 hover:bg-white/10 border-b border-white/10 last:border-0">
                            <div className="font-semibold text-white">{cpName(cp)}</div>
                            {cp.inn && <div className="text-xs text-white/40 mt-1">ИНН: {cp.inn}</div>}
                          </button>
                        ))
                      }
                    </div>
                  )}
                </div>
                {selectedCounterparty && <div className="mt-3 p-4 rounded-xl bg-green-500/10 border border-green-500/30 text-green-400">✓ {cpName(selectedCounterparty)}</div>}
              </div>
            )}

            {/* Проект */}
            {canSelectCounterparty && selectionType === 'project' && (
              <div>
                <label className="block text-2xl font-semibold text-white mb-4">Проект <span className="text-red-400">*</span></label>
                <div className="relative" ref={projectDropdownRef}>
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                    <input value={projectSearch}
                           onChange={e => { setProjectSearch(e.target.value); setShowProjectDropdown(true); }}
                           onFocus={() => { setShowProjectDropdown(true); if (!projects.length) loadProjectsForAll(); }}
                           placeholder="Поиск..." className="input-field pl-12 py-5 text-lg w-full" />
                  </div>
                  {showProjectDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[#0c0c0c] border border-white/20 rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                      {loadingProjects ? <div className="p-6 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-white/40" /></div> :
                        projects.filter(p => !projectSearch || p.name.toLowerCase().includes(projectSearch.toLowerCase()) || p.key.toLowerCase().includes(projectSearch.toLowerCase())).map(p => (
                          <button key={p.id} onClick={() => { setSelectedProject(p); setProjectSearch(prjName(p)); setShowProjectDropdown(false); }}
                                  className="w-full text-left p-4 hover:bg-white/10 border-b border-white/10 last:border-0">
                            <span className="text-purple-400">{p.key}</span> — {p.name}
                          </button>
                        ))
                      }
                    </div>
                  )}
                </div>
                {selectedProject && <div className="mt-3 p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">✓ {prjName(selectedProject)}</div>}
              </div>
            )}

            {/* Customer контрагент */}
            {isCustomer && customerCounterparty && (
              <div className="p-6 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center gap-4">
                <Building2 className="w-8 h-8 text-blue-400" />
                <div>
                  <p className="text-base font-semibold text-white">{customerCounterparty.name}</p>
                  {customerCounterparty.inn && <p className="text-white/50 text-sm">ИНН: {customerCounterparty.inn}</p>}
                </div>
              </div>
            )}

            {/* Инициатор */}
            {canSelectReporter && (selectedCounterparty || selectedProject) && (
              <div>
                <label className="block text-2xl font-semibold text-white mb-4">Инициатор <span className="text-white/40 text-sm">(по умолчанию — вы)</span></label>
                <div className="relative" ref={reporterDropdownRef}>
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                  <input value={reporterSearch}
                         onChange={e => { setReporterSearch(e.target.value); setShowReporterDropdown(true); }}
                         onFocus={() => setShowReporterDropdown(true)}
                         placeholder="Выберите..." className="input-field pl-12 py-5 text-lg w-full" />
                  {showReporterDropdown && (
                    <div className="absolute z-50 mt-2 w-full bg-[#0c0c0c] border border-white/20 rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                      {loadingUsers ? <div className="p-6 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-white/40" /></div> : (
                        <>
                          <button onClick={() => { setSelectedReporter(null); setReporterSearch(''); setShowReporterDropdown(false); }}
                                  className="w-full text-left p-4 hover:bg-white/10 border-b border-white/10">
                            <span className="text-white">{user?.full_name || 'Вы'}</span> <span className="text-white/40">(текущий)</span>
                          </button>
                          {users.filter(u => !reporterSearch || (u.full_name?.toLowerCase().includes(reporterSearch.toLowerCase()) || u.email.toLowerCase().includes(reporterSearch.toLowerCase()))).map(u => (
                            <button key={u.id} onClick={() => { setSelectedReporter(u); setReporterSearch(uName(u)); setShowReporterDropdown(false); }}
                                    className="w-full text-left p-4 hover:bg-white/10 border-b border-white/10 last:border-0">
                              <div className="text-white">{uName(u)}</div>
                              <div className="text-white/40 text-sm">{u.email}</div>
                            </button>
                          ))}
                        </>
                      )}
                    </div>
                  )}
                </div>
                <div className="mt-3 p-4 rounded-xl bg-white/5 text-white/60">
                  Инициатор: <span className="text-white font-medium">{selectedReporter ? uName(selectedReporter) : (user?.full_name || 'Вы')}</span>
                </div>
              </div>
            )}

            {/* Тема */}
            <SpellCheckField value={title} onChange={setTitle} label="Тема заявки *">
              <input type="text" value={title} onChange={e => setTitle(e.target.value)}
                     placeholder="Кратко опишите проблему..." className="input-field py-5 text-2xl w-full" />
            </SpellCheckField>

            {/* Описание */}
            <div>
              <label className="block text-2xl font-semibold text-white mb-4">
                Подробное описание <span className="text-red-400">*</span>
              </label>
              <TicketEditor blocks={descriptionBlocks} onChange={setDescriptionBlocks} />
            </div>

            {/* Обычные вложения */}
            <div>
              <label className="block text-2xl font-semibold text-white mb-4">
                <Upload className="inline w-6 h-6 mr-2 text-white/40" />
                Прикрепить файлы
              </label>
              <div onDrop={handleGeneralDrop} onDragOver={e => e.preventDefault()}
                   className="border-2 border-dashed border-white/20 rounded-xl p-8 text-center hover:border-white/40 transition-colors">
                <Upload className="w-10 h-10 text-white/20 mx-auto mb-3" />
                <p className="text-lg text-white/50 mb-2">Перетащите файлы сюда</p>
                <label className="inline-block">
                  <input type="file" multiple onChange={handleGeneralFileSelect} className="hidden" />
                  <span className="px-5 py-2.5 rounded-xl bg-red-700 hover:bg-red-600 text-white text-base font-medium cursor-pointer transition-colors">
                    Выбрать файлы
                  </span>
                </label>
                <p className="mt-3 text-sm text-white/30">До 10 файлов, максимум 25 МБ</p>
              </div>

              {generalFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  {generalFiles.map(f => (
                    <div key={f.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
                      {f.preview
                        ? <img src={f.preview} alt="" className="w-12 h-12 rounded-lg object-cover" />
                        : <div className="w-12 h-12 rounded-lg bg-white/[0.06] flex items-center justify-center"><File className="w-5 h-5 text-white/40" /></div>
                      }
                      <div className="flex-1 min-w-0">
                        <p className="text-base text-white truncate">{f.file.name}</p>
                        <p className="text-sm text-white/40">{formatFileSize(f.file.size)}</p>
                      </div>
                      <button onClick={() => removeGeneralFile(f.id)}
                              className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/30 hover:text-red-400 transition-colors">
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
            {aiSuggestion && !aiLoading && (
              <div className="p-6 rounded-2xl bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 flex items-center gap-3">
                <Zap className="w-7 h-7 text-purple-400" />
                <div>
                  <h3 className="text-xl font-semibold text-white">ИИ подобрал приоритет и теги</h3>
                  <p className="text-white/60 mt-1">Проверьте и скорректируйте</p>
                </div>
              </div>
            )}

            <div>
              <label className="block text-2xl font-semibold text-white mb-6">Приоритет</label>
              <div className="flex flex-wrap gap-3">
                {PRIORITIES.map(p => (
                  <button key={p.value} onClick={() => setPriority(p.value as TicketPriority)}
                          className={`px-8 py-5 rounded-2xl text-lg font-medium border flex-1 min-w-[200px] text-left transition-all ${
                            priority === p.value ? 'bg-white/20 text-white border-white/70' : 'bg-white/5 border-white/20 hover:bg-white/10'
                          }`}>
                    <div className="flex items-center gap-4">{p.icon}<div><div className="font-semibold">{p.label}</div><div className="text-sm opacity-70">{p.desc}</div></div></div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-2xl font-semibold text-white mb-6">Теги</label>
              {aiSuggestedTags.length > 0 && (
                <div className="mb-6">
                  <p className="text-white/50 text-sm mb-3 flex items-center gap-2"><Sparkles className="w-4 h-4" />Предложено ИИ</p>
                  <div className="flex flex-wrap gap-3">
                    {aiSuggestedTags.map(t => (
                      <button key={t.name} onClick={() => togglePresetTag(t)}
                              className={`px-6 py-3 rounded-2xl text-base font-medium border transition-all ${tags.some(x => x.name === t.name) ? 'bg-white/20 border-white/40' : 'bg-white/5 border-white/20 hover:bg-white/10'}`}>
                        {t.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex flex-wrap gap-3 mb-6">
                {PRESET_TAGS.map(t => (
                  <button key={t.name} onClick={() => togglePresetTag(t)}
                          className={`px-6 py-3 rounded-2xl text-base font-medium border transition-all ${tags.some(x => x.name === t.name) ? 'bg-white/20 border-white/40' : 'bg-white/5 border-white/20 hover:bg-white/10'}`}>
                    {t.name}
                  </button>
                ))}
              </div>
              <button onClick={() => setShowCustomTagInput(!showCustomTagInput)} className="text-blue-400 hover:text-blue-300 flex items-center gap-2 text-sm mb-4">
                <Plus className="w-4 h-4" />{showCustomTagInput ? 'Скрыть' : 'Свой тег'}
              </button>
              {showCustomTagInput && (
                <div className="flex gap-3 mb-6">
                  <input value={newTagInput} onChange={e => setNewTagInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && addCustomTag()}
                         placeholder="Тег..." className="input-field flex-1 py-4 text-lg" />
                  <button onClick={addCustomTag} disabled={!newTagInput.trim()}
                          className="px-6 py-3 rounded-xl bg-red-700 hover:bg-red-600 text-white font-medium disabled:opacity-40">Добавить</button>
                </div>
              )}
              {tags.length > 0 && (
                <div className="p-5 bg-white/5 rounded-2xl">
                  <p className="text-white/50 mb-3">Выбрано: {tags.length}</p>
                  <div className="flex flex-wrap gap-3">
                    {tags.map(t => (
                      <div key={t.name} className="inline-flex items-center gap-2 px-5 py-2.5 bg-white/10 rounded-2xl">
                        {t.name}<X className="w-4 h-4 cursor-pointer text-white/50 hover:text-red-400" onClick={() => removeTag(t.name)} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
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
              <h2 className="text-3xl font-bold text-white mb-2">Проверьте заявку</h2>
              <p className="text-lg text-white/60">Убедитесь, что всё правильно</p>
            </div>

            <div className="space-y-6">
              {/* Привязка */}
              {selectedProject && (
                <div className="p-6 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center gap-4">
                  <FolderOpen className="w-8 h-8 text-purple-400" />
                  <div><p className="text-white font-semibold">{prjName(selectedProject)}</p><p className="text-white/40 text-sm">контрагент из проекта</p></div>
                </div>
              )}
              {!selectedProject && selectedCounterparty && (
                <div className="p-6 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center gap-4">
                  <Building2 className="w-8 h-8 text-blue-400" />
                  <p className="text-white font-semibold">{cpName(selectedCounterparty)}</p>
                </div>
              )}
              {isCustomer && customerCounterparty && !selectedProject && !selectedCounterparty && (
                <div className="p-6 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center gap-4">
                  <Building2 className="w-8 h-8 text-blue-400" />
                  <p className="text-white font-semibold">{customerCounterparty.name}</p>
                </div>
              )}
              {canSelectCounterparty && selectionType === null && (
                <div className="p-6 rounded-2xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-center">
                  Без привязки
                </div>
              )}

              {/* Инициатор */}
              <div className="p-6 rounded-2xl bg-green-500/10 border border-green-500/30 flex items-center gap-4">
                <User className="w-8 h-8 text-green-400" />
                <div>
                  <p className="text-white font-semibold">{selectedReporter ? uName(selectedReporter) : (user?.full_name || 'Вы')}</p>
                  <p className="text-white/40 text-sm">{selectedReporter ? selectedReporter.email : user?.email}</p>
                </div>
              </div>

              {/* Тема */}
              <div className="p-6 rounded-2xl bg-white/5">
                <p className="text-white/50 mb-2">Тема</p>
                <p className="text-white font-semibold text-lg break-words">{title || '—'}</p>
              </div>

              {/* Описание — с картинками и форматированием */}
              <div className="p-6 rounded-2xl bg-white/5">
                <p className="text-white/50 mb-4">Описание</p>
                <div className="space-y-4">
                  {descriptionBlocks.map(block => {
                    if (block.type === 'text') {
                      if (!block.value.trim()) return null;
                      return (
                        <TicketDescriptionContent
                          key={block.id}
                          text={block.value}
                          className="text-white text-base leading-relaxed"
                        />
                      );
                    }
                    if (block.type === 'image' && block.localPreview) {
                      return <img key={block.id} src={block.localPreview} alt="вложение"
                                  className="max-w-full max-h-[400px] rounded-2xl border border-white/[0.08] object-contain" />;
                    }
                    return null;
                  })}
                  {descriptionBlocks.every(b => (b.type === 'text' && !b.value.trim()) || (b.type === 'image' && !b.localPreview)) && (
                    <p className="text-white/30">—</p>
                  )}
                </div>
              </div>

              {/* Приоритет + теги */}
              <div className="grid md:grid-cols-2 gap-6">
                <div className="p-6 rounded-2xl bg-white/5">
                  <p className="text-white/50 mb-3">Приоритет</p>
                  <div className={`inline-flex items-center gap-3 text-lg px-5 py-2.5 rounded-2xl ${PRIORITIES.find(p => p.value === priority)?.color || ''}`}>
                    {PRIORITIES.find(p => p.value === priority)?.icon} {priority}
                  </div>
                </div>
                {tags.length > 0 && (
                  <div className="p-6 rounded-2xl bg-white/5">
                    <p className="text-white/50 mb-3">Теги</p>
                    <div className="flex flex-wrap gap-2">
                      {tags.map(t => (
                        <span key={t.name} className="px-4 py-2 rounded-xl text-base font-medium"
                              style={{ backgroundColor: (t.color || '#71717a') + '30', color: t.color || '#d1d5db' }}>
                          {t.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Обычные вложения */}
              {generalFiles.length > 0 && (
                <div className="p-6 rounded-2xl bg-white/5">
                  <p className="text-white/50 mb-3">Вложения ({generalFiles.length})</p>
                  <div className="space-y-2">
                    {generalFiles.map(f => (
                      <div key={f.id} className="flex items-center gap-3 text-white">
                        <File className="w-5 h-5 text-white/40" />
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
        <div className="flex justify-between mt-12 pt-8 border-t border-white/10">
          {step > 1 ? (
            <button onClick={() => setStep(step - 1)}
                    className="flex items-center gap-3 px-8 py-4 rounded-2xl bg-white/5 hover:bg-white/10 text-lg font-medium">
              <ArrowLeft className="w-5 h-5" /> Назад
            </button>
          ) : <div />}

          {step < 3 ? (
            <button onClick={() => setStep(step + 1)}
                    className="px-10 py-4 rounded-2xl bg-red-700 hover:bg-red-600 text-white text-lg font-semibold ml-auto shadow-lg shadow-red-900/30 transition-colors">
              Далее <ArrowRight className="w-5 h-5 inline ml-2" />
            </button>
          ) : (
            <button onClick={handleSubmit} disabled={submitting}
                    className="px-12 py-4 rounded-2xl bg-red-700 hover:bg-red-600 text-white text-lg font-semibold flex items-center gap-3 ml-auto disabled:opacity-50 shadow-lg shadow-red-900/30">
              {submitting ? <Loader2 className="w-6 h-6 animate-spin" /> : <><FileText className="w-5 h-5" /> Создать заявку</>}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}