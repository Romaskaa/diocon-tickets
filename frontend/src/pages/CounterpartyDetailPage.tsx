import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Building2, Phone, Mail, Users, FileText, Clock,
  Edit, Trash2, Plus, User, MessageSquare, Loader2, ExternalLink, Calendar,
  Hash, CheckCircle2, Briefcase, CreditCard, MapPinned, AtSign,
  PhoneCall, UserPlus, Ticket, History, Info, UserCheck,
  Package, Server, Globe, Smartphone, Monitor, Cpu, Code, HelpCircle,
  X, Tag, Link2, Layers, RefreshCcw, AlertTriangle,
  ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Search, GitBranch,
} from 'lucide-react';
import { counterpartiesApi, ticketsApi, productsApi } from '../api/client';
import type { Counterparty, CounterpartyCustomer, TicketListItem } from '../types';

// ─── Phone mask ───

function formatPhone(raw: string): string {
  const digits = raw.replace(/\D/g, '');
  if (!digits) return '';
  let d = digits;
  if (d.startsWith('8')) d = '7' + d.slice(1);
  if (!d.startsWith('7')) d = '7' + d;
  d = d.slice(0, 11);
  let out = '+7';
  if (d.length > 1) out += ' (' + d.slice(1, 4);
  if (d.length >= 4) out += ') ' + d.slice(4, 7);
  if (d.length >= 7) out += '-' + d.slice(7, 9);
  if (d.length >= 9) out += '-' + d.slice(9, 11);
  return out;
}

function phoneToApi(formatted: string): string {
  const digits = formatted.replace(/\D/g, '');
  if (!digits) return '';
  if (digits.startsWith('7')) return '8' + digits.slice(1);
  return digits;
}

function PhoneInput({ value, onChange, placeholder = '+7 (999) 123-45-67', className = '' }: {
  value: string; onChange: (v: string) => void; placeholder?: string; className?: string;
}) {
  return (
    <input
      type="tel"
      value={value}
      onChange={e => {
        const digits = e.target.value.replace(/\D/g, '');
        onChange(formatPhone(digits));
      }}
      onKeyDown={e => {
        if (e.key === 'Backspace') {
          const digits = value.replace(/\D/g, '');
          if (digits.length > 0) {
            onChange(digits.length <= 1 ? '' : formatPhone(digits.slice(0, -1)));
            e.preventDefault();
          }
        }
      }}
      placeholder={placeholder}
      className={className}
    />
  );
}

// ─── Helpers ──────

function getInitials(name?: string | null): string {
  if (!name) return '?';
  return name.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
}

function Avatar({ name, size = 'md' }: { name?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const cls = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base' }[size];
  return (
    <div className={`${cls} rounded-full bg-[var(--accent)] flex items-center justify-center font-bold text-white flex-shrink-0 select-none`}>
      {getInitials(name)}
    </div>
  );
}

const shouldShowKpp = (type?: string) =>
  type === 'Юридическое лицо' || type === 'Обособленное подразделение';

const inputCls = `w-full px-4 py-3 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl
  text-[var(--text-primary)] text-base placeholder-white/25
  focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)] transition-all`;

const inputWithIconCls = `w-full pl-10 pr-4 py-3 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl
  text-[var(--text-primary)] text-base placeholder-white/25
  focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)] transition-all`;

// ─── Продукты: константы ──────────────────────────────────────────────────────

const PRODUCT_CATEGORIES = [
  { value: 'ERP', label: 'ERP', icon: Server, color: 'text-[var(--warning)]', bg: 'bg-orange-500/10' },
  { value: 'WEB', label: 'Web', icon: Globe, color: 'text-[var(--info)]', bg: 'bg-blue-500/10' },
  { value: 'MOBILE', label: 'Mobile', icon: Smartphone, color: 'text-[var(--success)]', bg: 'bg-[var(--success)]/8' },
  { value: 'API', label: 'API', icon: Code, color: 'text-[var(--info)]', bg: 'bg-violet-500/10' },
  { value: 'DESKTOP', label: 'Desktop', icon: Monitor, color: 'text-[var(--info)]', bg: 'bg-cyan-500/10' },
  { value: 'HARDWARE', label: 'Hardware', icon: Cpu, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  { value: 'OTHER', label: 'Прочее', icon: HelpCircle, color: 'text-[var(--text-primary)]/50', bg: 'bg-[var(--hover-2)]' },
] as const;

const ENVIRONMENTS = [
  { value: 'production', label: 'Production' },
  { value: 'staging', label: 'Staging' },
  { value: 'testing', label: 'Testing' },
  { value: 'development', label: 'Development' },
] as const;

const PRODUCT_STATUSES = [
  { value: 'active', label: 'Активный', dot: 'bg-emerald-400', color: 'text-emerald-400' },
  { value: 'beta', label: 'Бета', dot: 'bg-blue-400', color: 'text-[var(--info)]' },
  { value: 'deprecated', label: 'Устаревший', dot: 'bg-[var(--hover-1)]', color: 'text-[var(--text-primary)]/40' },
] as const;

const catMeta = (v: string) => PRODUCT_CATEGORIES.find(c => c.value === v);
const statusMeta = (v: string) => PRODUCT_STATUSES.find(s => s.value === v);
const statusLabel = (v: string) => statusMeta(v)?.label ?? v;
const statusDot = (s: string) => statusMeta(s)?.dot ?? 'bg-[var(--hover-1)]';
const envLabel = (v: string) => ENVIRONMENTS.find(e => e.value === v)?.label ?? v;

const envBadgeClass = (e: string) => {
  if (e === 'production') return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
  if (e === 'staging') return 'bg-yellow-500/10 text-[var(--warning)] border border-[var(--warning)]/15';
  if (e === 'testing') return 'bg-blue-500/10 text-[var(--info)] border border-blue-500/20';
  if (e === 'development') return 'bg-purple-500/10 text-[var(--info)] border border-[var(--info)]/15';
  return 'bg-[var(--hover-1)] text-[var(--text-primary)]/40 border border-white/10';
};

const ATTRIBUTE_LABELS: Record<string, string> = {
  license_type: 'Лицензия', environment: 'Среда', db_connection_ref: 'БД',
  modules_enabled: 'Модули', max_concurrent_users: 'Макс. пользователей',
  base_url: 'URL', admin_url: 'Админ', hosting_provider: 'Хостинг',
  tech_stack: 'Стек', ssl_expiry_date: 'SSL до', cdn_enabled: 'CDN',
  platform: 'Платформа', auth_method: 'Авторизация',
};
const getAttrLabel = (k: string) => ATTRIBUTE_LABELS[k] || k.replace(/_/g, ' ');
const formatAttrValue = (v: any): string => {
  if (v === true) return 'Да';
  if (v === false) return 'Нет';
  if (Array.isArray(v)) return v.join(', ');
  return String(v);
};

// ─── Модалка удаления ──

function DeleteModal({ title, name, loading, onConfirm, onClose }: {
  title?: string; name: string; loading: boolean; onConfirm: () => void; onClose: () => void;
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !loading) onClose(); };
    document.addEventListener('keydown', h);
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', h); document.body.style.overflow = ''; };
  }, [onClose, loading]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => !loading && onClose()} />
      <div className="relative w-full max-w-md bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden"
        style={{ boxShadow: 'var(--shadow-lg)' }}>
        <div className="pt-8 flex justify-center">
          <div className="w-16 h-16 rounded-2xl bg-[var(--accent-soft)] border border-[var(--accent)]/15 flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-[var(--accent)]" />
          </div>
        </div>
        <div className="px-7 pt-5 pb-2 text-center">
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-3">{title || 'Удалить?'}</h2>
          <p className="text-base text-[var(--text-primary)]/60 leading-relaxed">
            <span className="text-[var(--text-primary)] font-semibold">«{name}»</span> будет удалён.
            Это действие нельзя отменить.
          </p>
        </div>
        <div className="flex gap-3 p-6">
          <button onClick={onClose} disabled={loading}
            className="flex-1 px-4 py-3 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)]
                       text-[var(--text-primary)]/70 text-base font-medium transition-colors disabled:opacity-50">
            Отмена
          </button>
          <button onClick={onConfirm} disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                       bg-[var(--accent)]/20 hover:bg-[var(--accent)]/30 border border-[var(--accent)]/30
                       text-[var(--accent)] text-base font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            {loading ? 'Удаление...' : 'Удалить'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Модалка редактирования контрагента ──────────────────────────────────────

function EditCounterpartyModal({ counterparty, onSave, onClose }: {
  counterparty: Counterparty;
  onSave: (data: Counterparty) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    name: counterparty.name || '',
    legal_name: counterparty.legal_name || '',
    okpo: counterparty.okpo || '',
    phone: counterparty.phone ? formatPhone(counterparty.phone.replace(/\D/g, '')) : '',
    email: counterparty.email || '',
    address: counterparty.address || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !saving) onClose(); };
    document.addEventListener('keydown', h);
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', h); document.body.style.overflow = ''; };
  }, [onClose, saving]);

  const set = (f: string) => (v: string) => setForm(p => ({ ...p, [f]: v }));

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true); setError(null);
    try {
      const payload: any = { name: form.name.trim() };
      if (form.legal_name.trim()) payload.legal_name = form.legal_name.trim();
      if (form.okpo.trim()) payload.okpo = form.okpo.trim();
      if (form.phone.trim()) payload.phone = phoneToApi(form.phone);
      if (form.email.trim()) payload.email = form.email.trim();
      if (form.address.trim()) payload.address = form.address.trim();
      const updated = await counterpartiesApi.update(counterparty.id, payload);
      onSave(updated);
    } catch (e: any) {
      setError(typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : 'Не удалось сохранить');
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => !saving && onClose()} />
      <div className="relative w-full max-w-lg bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden"
        style={{ boxShadow: 'var(--shadow-lg)' }}>
        <div className="flex items-center justify-between px-6 py-5 border-b border-[var(--border-color)]">
          <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2.5">
            <Edit size={18} className="text-[var(--accent)]" /> Редактировать контрагента
          </h2>
          <button onClick={() => !saving && onClose()}
            className="p-2 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          {error && (
            <div className="p-3 bg-[var(--accent)]/10 border border-[var(--accent)]/30 rounded-xl text-sm text-[var(--accent)] flex items-center gap-2">
              <AlertTriangle size={15} className="flex-shrink-0" />{error}
            </div>
          )}
          <div>
            <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Название <span className="text-[var(--accent)]">*</span></label>
            <input value={form.name} onChange={e => set('name')(e.target.value)} placeholder="Название" className={inputCls} />
          </div>
          <div>
            <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Полное наименование</label>
            <input value={form.legal_name} onChange={e => set('legal_name')(e.target.value)} placeholder="ООО «Название»" className={inputCls} />
          </div>
          <div>
            <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">ОКПО</label>
            <input value={form.okpo} onChange={e => set('okpo')(e.target.value.replace(/\D/g, '').slice(0, 10))} placeholder="12345678" className={inputCls} />
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Телефон</label>
              <div className="relative">
                <Phone size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 pointer-events-none" />
                <PhoneInput value={form.phone} onChange={set('phone')} className={inputWithIconCls} />
              </div>
            </div>
            <div>
              <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 pointer-events-none" />
                <input type="email" value={form.email} onChange={e => set('email')(e.target.value)} placeholder="email@company.ru" className={inputWithIconCls} />
              </div>
            </div>
          </div>
          <div>
            <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Адрес</label>
            <div className="relative">
              <MapPinned size={16} className="absolute left-3.5 top-3.5 text-[var(--text-primary)]/25 pointer-events-none" />
              <textarea value={form.address} onChange={e => set('address')(e.target.value)} placeholder="г. Москва, ..." rows={2}
                className="w-full pl-10 pr-4 py-3 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] text-base placeholder-white/25 resize-none focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)] transition-all" />
            </div>
          </div>
        </div>
        <div className="flex gap-3 px-6 py-5 border-t border-[var(--border-color)]">
          <button onClick={() => !saving && onClose()} disabled={saving}
            className="flex-1 px-4 py-3 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-base font-medium transition-colors disabled:opacity-50">
            Отмена
          </button>
          <button onClick={handleSave} disabled={saving || !form.name.trim()}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[var(--accent)] text-white text-base font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md">
            {saving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Вкладка контактных лиц ───────────────────────────────────────────────────

function ContactsTab({ counterpartyId, persons, onRefresh }: {
  counterpartyId: string; persons: any[]; onRefresh: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ last_name: '', first_name: '', middle_name: '', phone: '', email: '', telegram: '', vk: '' });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<any | null>(null);
  const [deleting, setDeleting] = useState(false);

  const set = (f: string) => (v: string) => setForm(p => ({ ...p, [f]: v }));

  const resetForm = () => {
    setForm({ last_name: '', first_name: '', middle_name: '', phone: '', email: '', telegram: '', vk: '' });
    setShowForm(false);
  };

  const handleSave = async () => {
    if (!form.last_name.trim() || !form.first_name.trim()) return;
    setSaving(true);
    try {
      const messengers: Record<string, string> = {};
      if (form.telegram.trim()) messengers.telegram = form.telegram.trim().replace('@', '');
      if (form.vk.trim()) messengers.vk = form.vk.trim();
      await counterpartiesApi.updateContactPerson(counterpartyId, {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        middle_name: form.middle_name.trim() || undefined,
        phone: form.phone.trim() ? phoneToApi(form.phone) : undefined,
        email: form.email.trim() || undefined,
        messengers: Object.keys(messengers).length > 0 ? messengers : undefined,
      });
      resetForm();
      onRefresh();
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  const handleDelete = async (person: any) => {
    if (!person.phone && !person.email) return;
    setDeleting(true);
    try {
      await counterpartiesApi.deleteContactPerson(counterpartyId, { phone: person.phone, email: person.email });
      setConfirmDelete(null);
      onRefresh();
    } catch (e) { console.error(e); }
    finally { setDeleting(false); }
  };

  return (
    <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] overflow-hidden">
      <div className="px-6 py-5 border-b border-[var(--border-color)] bg-[var(--hover-1)] flex items-center justify-between">
        <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2.5">
          <UserCheck size={18} className="text-[var(--text-primary)]/40" /> Контактные лица
          {persons.length > 0 && <span className="px-2 py-0.5 rounded-full bg-[var(--hover-3)] text-sm text-[var(--text-primary)]/50">{persons.length}</span>}
        </h2>
        <button onClick={() => showForm ? resetForm() : setShowForm(true)}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-base font-medium transition-all ${showForm
            ? 'bg-[var(--hover-2)] text-[var(--text-primary)]/70'
            : 'bg-[var(--accent)] text-white shadow-md'}`}>
          {showForm ? <X size={16} /> : <Plus size={16} />}
          {showForm ? 'Отмена' : 'Добавить'}
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* Форма добавления */}
        {showForm && (
          <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--hover-1)] p-5 space-y-4">
            <h3 className="text-base font-semibold text-[var(--text-primary)] flex items-center gap-2">
              <UserPlus size={16} className="text-[var(--accent)]" /> Новое контактное лицо
            </h3>
            <div className="grid md:grid-cols-3 gap-3">
              <div>
                <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Фамилия <span className="text-[var(--accent)]">*</span></label>
                <input value={form.last_name} onChange={e => set('last_name')(e.target.value)} placeholder="Иванов" className={inputCls} />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Имя <span className="text-[var(--accent)]">*</span></label>
                <input value={form.first_name} onChange={e => set('first_name')(e.target.value)} placeholder="Иван" className={inputCls} />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Отчество</label>
                <input value={form.middle_name} onChange={e => set('middle_name')(e.target.value)} placeholder="Иванович" className={inputCls} />
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Телефон</label>
                <div className="relative">
                  <Phone size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 pointer-events-none" />
                  <PhoneInput value={form.phone} onChange={set('phone')} className={inputWithIconCls} />
                </div>
              </div>
              <div>
                <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Email</label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 pointer-events-none" />
                  <input type="email" value={form.email} onChange={e => set('email')(e.target.value)} placeholder="contact@company.ru" className={inputWithIconCls} />
                </div>
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Telegram</label>
                <div className="relative">
                  <MessageSquare size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 pointer-events-none" />
                  <input value={form.telegram} onChange={e => set('telegram')(e.target.value)} placeholder="username" className={inputWithIconCls} />
                </div>
              </div>
              <div>
                <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">ВКонтакте</label>
                <div className="relative">
                  <Globe size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 pointer-events-none" />
                  <input value={form.vk} onChange={e => set('vk')(e.target.value)} placeholder="id или username" className={inputWithIconCls} />
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-1">
              <button onClick={resetForm} disabled={saving}
                className="flex-1 px-4 py-2.5 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-base font-medium transition-colors disabled:opacity-50">
                Отмена
              </button>
              <button onClick={handleSave} disabled={saving || !form.last_name.trim() || !form.first_name.trim()}
                className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--accent)] text-white text-base font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-md">
                {saving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                {saving ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        )}

        {/* Подтверждение удаления */}
        {confirmDelete && (
          <div className="rounded-2xl border border-[var(--accent)]/30 bg-[var(--accent)]/5 p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="text-[var(--accent)] flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-base font-semibold text-[var(--text-primary)] mb-1">Удалить контактное лицо?</p>
                <p className="text-sm text-[var(--text-primary)]/60 mb-4">
                  <span className="font-medium text-[var(--text-primary)]">{confirmDelete.full_name}</span> будет удалён.
                </p>
                <div className="flex gap-2">
                  <button onClick={() => setConfirmDelete(null)}
                    className="flex-1 px-3 py-2 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-sm font-medium transition-colors">
                    Отмена
                  </button>
                  <button onClick={() => handleDelete(confirmDelete)} disabled={deleting}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-[var(--accent)]/20 hover:bg-[var(--accent)]/30 border border-[var(--accent)]/30 text-[var(--accent)] text-sm font-medium transition-colors disabled:opacity-50">
                    {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                    Удалить
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Список */}
        {persons.length === 0 && !showForm ? (
          <div className="text-center py-16">
            <User size={36} className="text-[var(--text-primary)]/15 mx-auto mb-4" />
            <p className="text-[var(--text-primary)]/50 text-base font-semibold mb-1">Контактные лица не указаны</p>
            <p className="text-[var(--text-primary)]/30 text-sm mb-5">Добавьте контактное лицо для связи</p>
            <button onClick={() => setShowForm(true)}
              className="text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors text-base">
              Добавить контактное лицо →
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {persons.map((person, i) => (
              <div key={i} className="rounded-2xl border border-[var(--border-color)] bg-[var(--hover-1)] overflow-hidden">
                <div className="flex items-center justify-between gap-4 px-5 py-4 border-b border-[var(--border-color)]">
                  <div className="flex items-center gap-3">
                    <Avatar name={person.full_name} size="md" />
                    <div>
                      <p className="text-base font-semibold text-[var(--text-primary)]">{person.full_name}</p>
                      <p className="text-sm text-[var(--text-primary)]/40">Контактное лицо</p>
                    </div>
                  </div>
                  <button onClick={() => setConfirmDelete(confirmDelete?.full_name === person.full_name ? null : person)}
                    className="p-2 rounded-xl hover:bg-[var(--accent)]/10 text-[var(--text-primary)]/30 hover:text-[var(--accent)] transition-colors flex-shrink-0" title="Удалить">
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="p-4 grid md:grid-cols-2 gap-3">
                  {person.phone && (
                    <div className="flex items-start gap-3 p-3.5 ">
                      <Phone size={15} className="text-[var(--text-primary)]/30 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-xs text-[var(--text-primary)]/30 mb-0.5">Телефон</p>
                        <a href={`tel:${person.phone}`} className="text-sm text-[var(--text-primary)] hover:text-[var(--accent)] transition-colors">{person.phone}</a>
                      </div>
                    </div>
                  )}
                  {person.email && (
                    <div className="flex items-start gap-3 p-3.5 ">
                      <Mail size={15} className="text-[var(--text-primary)]/30 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-xs text-[var(--text-primary)]/30 mb-0.5">Email</p>
                        <a href={`mailto:${person.email}`} className="text-sm text-[var(--text-primary)] hover:text-[var(--accent)] transition-colors break-all">{person.email}</a>
                      </div>
                    </div>
                  )}
                  {person.messengers?.telegram && (
                    <div className="flex items-start gap-3 p-3.5 ">
                      <MessageSquare size={15} className="text-[var(--text-primary)]/30 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-xs text-[var(--text-primary)]/30 mb-0.5">Telegram</p>
                        <a href={`https://t.me/${person.messengers.telegram.replace('@', '')}`} target="_blank" rel="noopener noreferrer"
                          className="text-sm text-[var(--text-primary)] hover:text-[var(--accent)] transition-colors flex items-center gap-1.5">
                          @{person.messengers.telegram.replace('@', '')} <ExternalLink size={12} className="text-[var(--text-primary)]/30" />
                        </a>
                      </div>
                    </div>
                  )}
                  {person.messengers?.vk && (
                    <div className="flex items-start gap-3 p-3.5 ">
                      <Globe size={15} className="text-[var(--text-primary)]/30 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-xs text-[var(--text-primary)]/30 mb-0.5">ВКонтакте</p>
                        <a href={`https://vk.com/${person.messengers.vk}`} target="_blank" rel="noopener noreferrer"
                          className="text-sm text-[var(--text-primary)] hover:text-[var(--accent)] transition-colors flex items-center gap-1.5">
                          {person.messengers.vk} <ExternalLink size={12} className="text-[var(--text-primary)]/30" />
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Вкладка подразделений ───────────────────────────────────────────────────

function BranchesTab({ counterpartyId, counterpartyName }: {
  counterpartyId: string; counterpartyName: string;
}) {
  const navigate = useNavigate();
  const [branches, setBranches] = useState<Counterparty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', legal_name: '', kpp: '', okpo: '', phone: '', email: '', address: '' });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await counterpartiesApi.getBranches(counterpartyId);
      setBranches(res);
    } catch { setError('Не удалось загрузить подразделения'); }
    finally { setLoading(false); }
  }, [counterpartyId]);

  useEffect(() => { load(); }, [load]);

  const set = (f: string) => (v: string) => setForm(p => ({ ...p, [f]: v }));

  const resetForm = () => {
    setForm({ name: '', legal_name: '', kpp: '', okpo: '', phone: '', email: '', address: '' });
    setShowForm(false);
    setFormError(null);
  };

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setSaving(true); setFormError(null);
    try {
      const payload: any = { name: form.name.trim() };
      if (form.legal_name.trim()) payload.legal_name = form.legal_name.trim();
      if (form.kpp.trim()) payload.kpp = form.kpp.trim();
      if (form.okpo.trim()) payload.okpo = form.okpo.trim();
      if (form.phone.trim()) payload.phone = phoneToApi(form.phone);
      if (form.email.trim()) payload.email = form.email.trim();
      if (form.address.trim()) payload.address = form.address.trim();
      await counterpartiesApi.createBranch(counterpartyId, payload);
      resetForm();
      load();
    } catch (e: any) {
      setFormError(typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : 'Не удалось создать подразделение');
    } finally { setSaving(false); }
  };

  return (
    <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] overflow-hidden">
      {/* Шапка */}
      <div className="px-6 py-5 border-b border-[var(--border-color)] bg-[var(--hover-1)] flex items-center justify-between">
        <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2.5">
          <GitBranch size={18} className="text-[var(--text-primary)]/40" />
          Подразделения
          {branches.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-[var(--hover-3)] text-sm text-[var(--text-primary)]/50">{branches.length}</span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]/70 transition-colors">
            <RefreshCcw size={16} />
          </button>
          <button onClick={() => showForm ? resetForm() : setShowForm(true)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-base font-medium transition-all ${showForm
              ? 'bg-[var(--hover-2)] text-[var(--text-primary)]/70'
              : 'bg-[var(--accent)] text-white shadow-md'}`}>
            {showForm ? <X size={16} /> : <Plus size={16} />}
            {showForm ? 'Отмена' : 'Добавить'}
          </button>
        </div>
      </div>

      {/* Inline-форма */}
      {showForm && (
        <div className="border-b border-[var(--border-color)] bg-[var(--hover-1)] p-6 space-y-4">
          <h3 className="text-base font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <GitBranch size={16} className="text-[var(--accent)]" /> Новое подразделение
          </h3>
          <p className="text-sm text-[var(--text-primary)]/40 -mt-2">К: {counterpartyName}</p>

          {formError && (
            <div className="p-3 bg-[var(--accent)]/10 border border-[var(--accent)]/30 rounded-xl text-sm text-[var(--accent)] flex items-center gap-2">
              <AlertTriangle size={15} className="flex-shrink-0" />{formError}
            </div>
          )}

          <div>
            <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Название <span className="text-[var(--accent)]">*</span></label>
            <input value={form.name} onChange={e => set('name')(e.target.value)} placeholder="Филиал в г. Казань" className={inputCls} />
          </div>
          <div>
            <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Полное наименование</label>
            <input value={form.legal_name} onChange={e => set('legal_name')(e.target.value)} placeholder="ООО «Название» — филиал" className={inputCls} />
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">КПП</label>
              <input value={form.kpp} onChange={e => set('kpp')(e.target.value.replace(/\D/g, '').slice(0, 9))} placeholder="770101001" className={inputCls} />
            </div>
            <div>
              <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">ОКПО</label>
              <input value={form.okpo} onChange={e => set('okpo')(e.target.value.replace(/\D/g, '').slice(0, 10))} placeholder="12345678" className={inputCls} />
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Телефон</label>
              <div className="relative">
                <Phone size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 pointer-events-none" />
                <PhoneInput value={form.phone} onChange={set('phone')} className={inputWithIconCls} />
              </div>
            </div>
            <div>
              <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/25 pointer-events-none" />
                <input type="email" value={form.email} onChange={e => set('email')(e.target.value)} placeholder="branch@company.ru" className={inputWithIconCls} />
              </div>
            </div>
          </div>
          <div>
            <label className="block text-sm text-[var(--text-primary)]/50 mb-1.5">Адрес</label>
            <div className="relative">
              <MapPinned size={16} className="absolute left-3.5 top-3.5 text-[var(--text-primary)]/25 pointer-events-none" />
              <textarea value={form.address} onChange={e => set('address')(e.target.value)} placeholder="г. Казань, ул. Примерная, д. 1" rows={2}
                className="w-full pl-10 pr-4 py-3 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] text-base placeholder-white/25 resize-none focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)] transition-all" />
            </div>
          </div>
          <div className="flex gap-3 pt-1">
            <button onClick={resetForm} disabled={saving}
              className="flex-1 px-4 py-3 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 text-base font-medium transition-colors disabled:opacity-50">
              Отмена
            </button>
            <button onClick={handleCreate} disabled={saving || !form.name.trim()}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[var(--accent)] text-white text-base font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <GitBranch size={16} />}
              {saving ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </div>
      )}

      {/* Список */}
      <div className="divide-y divide-[var(--border-color)]">
        {loading ? (
          <div className="flex justify-center py-20"><Loader2 size={24} className="text-[var(--accent)]/40 animate-spin" /></div>
        ) : error ? (
          <div className="py-12 text-center text-base text-[var(--accent)]">{error}</div>
        ) : branches.length === 0 && !showForm ? (
          <div className="flex flex-col items-center py-20 text-center px-6">
            <GitBranch size={36} className="text-[var(--text-primary)]/15 mb-4" />
            <p className="text-[var(--text-primary)]/60 text-base font-semibold mb-1">Нет подразделений</p>
            <p className="text-[var(--text-primary)]/40 text-sm mb-5">Добавьте обособленное подразделение</p>
            <button onClick={() => setShowForm(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--accent)]/20 hover:bg-[var(--accent)]/30 border border-[var(--accent)]/15 text-[var(--accent)] text-base font-medium transition-colors">
              <Plus size={16} /> Добавить подразделение
            </button>
          </div>
        ) : branches.map(branch => (
          <button key={branch.id}
            onClick={() => navigate(`/counterparties/${branch.id}`)}
            className="w-full flex items-center gap-4 px-6 py-5 text-left hover:bg-[var(--hover-1)] transition-colors group">
            <div className="w-11 h-11 rounded-xl bg-[var(--accent)]/10 flex items-center justify-center text-[var(--accent)] flex-shrink-0 group-hover:scale-105 transition-transform">
              <Building2 size={20} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-base font-semibold text-[var(--text-primary)] truncate group-hover:text-[var(--accent)] transition-colors">
                  {branch.name}
                </span>
                <span className={`px-2 py-0.5 rounded-md text-xs font-medium flex-shrink-0 ${branch.is_active
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                  : 'bg-[var(--hover-2)] text-[var(--text-primary)]/40 border border-[var(--border-color)]'}`}>
                  {branch.is_active ? 'Активен' : 'Неактивен'}
                </span>
              </div>
              <p className="text-sm text-[var(--text-primary)]/40 truncate">{branch.legal_name || '—'}</p>
              <div className="flex items-center gap-4 mt-1.5 text-xs text-[var(--text-primary)]/30">
                {branch.inn && <span className="font-mono">ИНН {branch.inn}</span>}
                {branch.kpp && <span className="font-mono">КПП {branch.kpp}</span>}
                {branch.address && (
                  <span className="flex items-center gap-1 truncate max-w-[200px]">
                    <MapPinned size={11} />{branch.address}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              {branch.phone && (
                <span className="hidden sm:flex items-center gap-1.5 text-sm text-[var(--text-primary)]/40">
                  <Phone size={13} />{branch.phone}
                </span>
              )}
              <ChevronRight size={18} className="text-[var(--text-primary)]/20 group-hover:text-[var(--accent)] transition-colors" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Вкладка продуктов ─

function ProductsTab({ counterpartyId }: { counterpartyId: string }) {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [allProducts, setAllProducts] = useState<any[]>([]);
  const [loadingAll, setLoadingAll] = useState(false);
  const [filterQuery, setFilterQuery] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);
  const [linkEnv, setLinkEnv] = useState('production');
  const [linkPrimary, setLinkPrimary] = useState(false);
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await counterpartiesApi.getProducts(counterpartyId, page, 10);
      setProducts(res.items); setTotalPages(res.total_pages); setTotalItems(res.total_items);
    } catch { setError('Не удалось загрузить продукты'); }
    finally { setLoading(false); }
  }, [counterpartyId, page]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!showForm) return;
    let cancelled = false;
    (async () => {
      setLoadingAll(true);
      try { const res = await productsApi.getProducts({ page: 1, size: 100 }); if (!cancelled) setAllProducts(res.items); }
      catch { } finally { if (!cancelled) setLoadingAll(false); }
    })();
    return () => { cancelled = true; };
  }, [showForm]);

  const filtered = filterQuery.trim()
    ? allProducts.filter(p => (p.display_name || p.name || '').toLowerCase().includes(filterQuery.toLowerCase()) || (p.vendor || '').toLowerCase().includes(filterQuery.toLowerCase()))
    : allProducts;

  const handleLink = async () => {
    if (!selectedProduct) return;
    setLinking(true); setLinkError(null);
    try {
      await counterpartiesApi.linkProduct(counterpartyId, { product_id: selectedProduct.id, environment: linkEnv, is_primary: linkPrimary });
      setSelectedProduct(null); setFilterQuery(''); setLinkEnv('production'); setLinkPrimary(false); setShowForm(false); setPage(1); load();
    } catch (err: any) {
      setLinkError(typeof err?.response?.data?.detail === 'string' ? err.response.data.detail : 'Не удалось привязать продукт');
    } finally { setLinking(false); }
  };

  const closeForm = () => { setShowForm(false); setSelectedProduct(null); setFilterQuery(''); setLinkEnv('production'); setLinkPrimary(false); setLinkError(null); };

  return (
    <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] overflow-hidden">
      <div className="px-6 py-5 border-b border-[var(--border-color)] flex items-center justify-between bg-[var(--hover-1)]">
        <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2.5">
          <Layers className="w-5 h-5 text-[var(--text-primary)]/40" /> Продукты
          {totalItems > 0 && <span className="px-2 py-0.5 rounded-full bg-[var(--hover-3)] text-sm text-[var(--text-primary)]/50">{totalItems}</span>}
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]/70 transition-colors"><RefreshCcw size={16} /></button>
          <button onClick={() => showForm ? closeForm() : setShowForm(true)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-base font-medium transition-all ${showForm ? 'bg-[var(--hover-2)] text-[var(--text-primary)]/70' : 'bg-[var(--accent)] text-white shadow-md'}`}>
            {showForm ? <X size={16} /> : <Link2 size={16} />}
            {showForm ? 'Отмена' : 'Привязать'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="border-b border-[var(--border-color)] bg-[var(--hover-1)] p-6 space-y-5">
          {linkError && (
            <div className="p-3 bg-[var(--accent)]/30 border border-red-700/50 rounded-xl text-base text-[var(--accent-hover)] flex items-start gap-2">
              <X size={16} className="mt-0.5 flex-shrink-0" />{linkError}
            </div>
          )}
          <div>
            <label className="block text-base text-[var(--text-primary)]/60 mb-2">Выберите продукт <span className="text-[var(--accent)]">*</span></label>
            {selectedProduct ? (
              <div className="flex items-center gap-3 p-4 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl">
                {(() => { const c = catMeta(selectedProduct.category); const I = c?.icon || Package; return <div className={`w-11 h-11 rounded-xl ${c?.bg || 'bg-[var(--hover-2)]'} flex items-center justify-center ${c?.color || 'text-[var(--text-primary)]/40'} flex-shrink-0`}><I size={20} /></div>; })()}
                <div className="flex-1 min-w-0">
                  <p className="text-base font-medium text-[var(--text-primary)] truncate">{selectedProduct.display_name || selectedProduct.name}</p>
                  <p className="text-sm text-[var(--text-primary)]/40">{selectedProduct.vendor}</p>
                </div>
                <button onClick={() => { setSelectedProduct(null); setFilterQuery(''); }} className="p-1.5 rounded-lg text-[var(--text-primary)]/30 hover:text-[var(--accent)] transition-colors"><X size={16} /></button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="relative">
                  <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/30 pointer-events-none" />
                  <input value={filterQuery} onChange={e => setFilterQuery(e.target.value)} placeholder="Фильтр по названию..."
                    className="w-full pl-10 pr-4 py-3 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl text-base text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)] transition-all" />
                </div>
                <div className="max-h-56 overflow-y-auto rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] divide-y divide-[var(--border-color)]">
                  {loadingAll ? <div className="flex justify-center py-10"><Loader2 size={20} className="text-[var(--text-primary)]/20 animate-spin" /></div>
                    : filtered.length === 0 ? <div className="py-10 text-center"><Package size={32} className="mx-auto mb-2 text-[var(--text-primary)]/15" /><p className="text-base text-[var(--text-primary)]/40">{filterQuery ? 'Ничего не найдено' : 'Нет продуктов'}</p></div>
                      : filtered.map(p => {
                        const c = catMeta(p.category); const I = c?.icon || Package;
                        return (
                          <button key={p.id} onClick={() => { setSelectedProduct(p); setFilterQuery(''); }}
                            className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-[var(--hover-2)] transition-colors">
                            <div className={`w-10 h-10 rounded-lg ${c?.bg || 'bg-[var(--hover-2)]'} flex items-center justify-center ${c?.color || 'text-[var(--text-primary)]/30'} flex-shrink-0`}><I size={18} /></div>
                            <div className="flex-1 min-w-0"><p className="text-base text-[var(--text-primary)] truncate">{p.display_name || p.name}</p><p className="text-sm text-[var(--text-primary)]/40">{p.vendor}</p></div>
                            <div className={`w-2 h-2 rounded-full ${statusDot(p.status)} flex-shrink-0`} />
                          </button>
                        );
                      })}
                </div>
              </div>
            )}
          </div>
          {selectedProduct && (
            <>
              <div>
                <label className="block text-base text-[var(--text-primary)]/60 mb-2">Среда</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {ENVIRONMENTS.map(env => (
                    <button key={env.value} onClick={() => setLinkEnv(env.value)}
                      className={`px-3 py-3 rounded-xl text-base font-medium transition-all ${linkEnv === env.value ? envBadgeClass(env.value) : 'border border-[var(--border-color)] bg-[var(--hover-1)] text-[var(--text-primary)]/40 hover:bg-[var(--hover-2)]'}`}>
                      {env.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between p-4 bg-[var(--hover-1)] border border-[var(--border-color)] rounded-xl">
                <div><p className="text-base text-[var(--text-primary)]/80">Основной продукт</p><p className="text-sm text-[var(--text-primary)]/40">Отмечает как основной</p></div>
                <button onClick={() => setLinkPrimary(!linkPrimary)} className={`relative w-11 h-6 rounded-full transition-colors ${linkPrimary ? 'bg-[var(--accent)]' : 'bg-[var(--hover-1)]'}`}>
                  <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform ${linkPrimary ? 'translate-x-5' : ''}`} />
                </button>
              </div>
              <button onClick={handleLink} disabled={linking}
                className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-[var(--accent)] text-white text-base font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-md">
                {linking ? <Loader2 size={18} className="animate-spin" /> : <Link2 size={18} />}
                Привязать продукт
              </button>
            </>
          )}
        </div>
      )}

      <div className="divide-y divide-[var(--border-color)]">
        {loading ? <div className="flex justify-center py-20"><Loader2 size={24} className="text-[var(--accent)]/40 animate-spin" /></div>
          : error ? <div className="py-12 text-center text-base text-[var(--accent)]">{error}</div>
            : products.length === 0 ? (
              <div className="flex flex-col items-center py-20 text-center px-6">
                <Package size={36} className="text-[var(--text-primary)]/15 mb-4" />
                <p className="text-[var(--text-primary)]/60 text-base font-semibold mb-1">Нет привязанных продуктов</p>
                <p className="text-[var(--text-primary)]/40 text-sm mb-5">Привяжите продукты к контрагенту</p>
                {!showForm && <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--accent)]/20 hover:bg-[var(--accent)]/30 border border-[var(--accent)]/15 text-[var(--accent)] text-base font-medium transition-colors"><Link2 size={16} /> Привязать</button>}
              </div>
            ) : products.map(product => {
              const cat = catMeta(product.category); const Icon = cat?.icon || Package;
              const sInfo = statusMeta(product.status); const isExpanded = expandedId === product.id;
              const attrs = Object.entries(product.attributes || {}).filter(([, v]) => v !== null && v !== '' && !(Array.isArray(v) && (v as any[]).length === 0));
              return (
                <div key={product.id} className={isExpanded ? 'bg-[var(--hover-1)]' : ''}>
                  <button onClick={() => setExpandedId(isExpanded ? null : product.id)}
                    className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-[var(--hover-1)] transition-colors group">
                    <div className={`w-11 h-11 rounded-xl ${cat?.bg || 'bg-[var(--hover-2)]'} flex items-center justify-center ${cat?.color || 'text-[var(--text-primary)]/40'} group-hover:scale-105 transition-transform flex-shrink-0`}><Icon size={20} /></div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-base font-semibold text-[var(--text-primary)] truncate">{product.display_name || product.name}</span>
                        {product.is_primary && <span className="px-2 py-0.5 rounded-md bg-[var(--accent)]/20 border border-[var(--accent)]/15 text-xs text-[var(--accent)] font-medium flex-shrink-0">Основной</span>}
                      </div>
                      <p className="text-sm text-[var(--text-primary)]/40">{product.vendor}</p>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      {product.environment && <span className={`px-2.5 py-1 rounded-lg text-sm font-medium hidden sm:block ${envBadgeClass(product.environment)}`}>{envLabel(product.environment)}</span>}
                      <div className="flex items-center gap-2"><div className={`w-2.5 h-2.5 rounded-full ${statusDot(product.status)}`} /><span className={`text-sm hidden sm:block ${sInfo?.color || 'text-[var(--text-primary)]/40'}`}>{statusLabel(product.status)}</span></div>
                      {isExpanded ? <ChevronUp size={18} className="text-[var(--text-primary)]/40" /> : <ChevronDown size={18} className="text-[var(--text-primary)]/20" />}
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="px-6 pb-6 pl-20 space-y-5 border-t border-[var(--border-color)]">
                      <div className="flex flex-wrap gap-2.5 pt-4">
                        <span className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--hover-2)] text-base text-[var(--text-primary)]/60 border border-[var(--border-color)]"><Building2 size={16} className="text-[var(--text-primary)]/40" />{product.vendor}</span>
                        {product.version && <span className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--hover-2)] text-base text-[var(--text-primary)]/60 border border-[var(--border-color)] font-mono"><Tag size={16} className="text-[var(--text-primary)]/40" />v{product.version}</span>}
                      </div>
                      {product.description && <div><p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-2 font-semibold">Описание</p><p className="text-base text-[var(--text-primary)]/70 leading-relaxed whitespace-pre-wrap">{product.description}</p></div>}
                      {attrs.length > 0 && (
                        <div>
                          <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-3 font-semibold">Характеристики</p>
                          <div className="rounded-xl border border-[var(--border-color)] divide-y divide-white/[0.06] bg-[var(--hover-1)]">
                            {attrs.map(([key, value]) => (
                              <div key={key} className="flex items-start gap-4 px-5 py-3.5">
                                <span className="text-base text-[var(--text-primary)]/40 w-[140px] flex-shrink-0">{getAttrLabel(key)}</span>
                                <span className="text-base text-[var(--text-primary)]/80 break-words min-w-0">{formatAttrValue(value)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-4 border-t border-[var(--border-color)]">
          <span className="text-base text-[var(--text-primary)]/40">Стр. {page} из {totalPages}</span>
          <div className="flex gap-1.5">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="p-2 rounded-lg hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 disabled:opacity-20"><ChevronLeft size={18} /></button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="p-2 rounded-lg hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 disabled:opacity-20"><ChevronRight size={18} /></button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Типы вкладок ─

type TabType = 'info' | 'contact' | 'products' | 'branches' | 'customers' | 'tickets' | 'history';

// ─── Основная страница ─

export default function CounterpartyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [counterparty, setCounterparty] = useState<Counterparty | null>(null);
  const [customers, setCustomers] = useState<CounterpartyCustomer[]>([]);
  const [tickets, setTickets] = useState<TicketListItem[]>([]);
  const [branches, setBranches] = useState<Counterparty[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('info');

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => { if (id) loadData(); }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const cp = await counterpartiesApi.getById(id!);
      setCounterparty(cp);
      try { const r = await counterpartiesApi.getCustomers(id!); setCustomers(Array.isArray(r?.items) ? r.items : Array.isArray(r) ? r : []); } catch { setCustomers([]); }
      try { const r = await ticketsApi.getAllWithFilters(1, 100, { counterparty_id: id }); setTickets(Array.isArray(r?.items) ? r.items : []); } catch { setTickets([]); }
      try { const r = await counterpartiesApi.getBranches(id!); setBranches(r); } catch { setBranches([]); }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try { await counterpartiesApi.delete(id!); navigate('/counterparties'); }
    catch (e) { console.error(e); }
    finally { setDeleting(false); }
  };

  const canAddBranch = counterparty?.counterparty_type === 'Юридическое лицо';

  const statusClr = (s: string) => ({
    'Новый': 'bg-blue-500/15 text-[var(--info)] border-[var(--info)]/15',
    'Открыт': 'bg-cyan-500/15 text-[var(--info)] border-cyan-500/30',
    'В работе': 'bg-yellow-500/15 text-[var(--warning)] border-[var(--warning)]/15',
    'Ожидает ответа': 'bg-purple-500/15 text-[var(--info)] border-[var(--info)]/15',
    'Решён': 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    'Закрыт': 'bg-neutral-500/15 text-[var(--text-muted)] border-[var(--text-muted)]/15',
    'Переоткрыт': 'bg-orange-500/15 text-[var(--warning)] border-[var(--warning)]/15',
  }[s] ?? 'bg-neutral-500/15 text-[var(--text-muted)] border-[var(--text-muted)]/15');

  const priorityClr = (p: string) => ({
    'Низкий': 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    'Средний': 'bg-yellow-500/15 text-[var(--warning)] border-[var(--warning)]/15',
    'Высокий': 'bg-orange-500/15 text-[var(--warning)] border-[var(--warning)]/15',
    'Критический': 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]/15',
  }[p] ?? 'bg-neutral-500/15 text-[var(--text-muted)] border-[var(--text-muted)]/15');

  const fmtDate = (d: string) => new Date(d).toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  const fmtDateShort = (d: string) => new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });

  const tabs: { id: TabType; label: string; icon: any; count?: number; hidden?: boolean }[] = [
    { id: 'info', label: 'Информация', icon: Info },
    { id: 'contact', label: 'Контакты', icon: UserCheck, count: counterparty?.contact_persons?.length },
    { id: 'products', label: 'Продукты', icon: Layers },
    { id: 'branches', label: 'Подразделения', icon: GitBranch, count: branches.length, hidden: !canAddBranch },
    { id: 'customers', label: 'Сотрудники', icon: Users, count: customers.length },
    { id: 'tickets', label: 'Заявки', icon: Ticket, count: tickets.length },
    { id: 'history', label: 'История', icon: History },
  ];

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="w-10 h-10 text-[var(--accent)] animate-spin" />
    </div>
  );

  if (!counterparty) return (
    <div className="bg-[var(--hover-2)] border border-[var(--border-color)] rounded-2xl p-16 text-center">
      <Building2 className="w-20 h-20 text-[var(--text-primary)]/15 mx-auto mb-5" />
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-3">Контрагент не найден</h2>
      <button onClick={() => navigate('/counterparties')} className="px-6 py-2.5 rounded-xl bg-[var(--accent)] text-white text-base font-medium transition-colors">
        Вернуться к списку
      </button>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">

      {/* ── Header ── */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          <button onClick={() => navigate('/counterparties')}
            className="p-2.5 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] border border-[var(--border-color)]
                       text-[var(--text-primary)]/60 hover:text-[var(--text-primary)] transition-all mt-1">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-[var(--accent)] flex items-center justify-center shadow-[var(--shadow-md)] flex-shrink-0">
              <Building2 className="w-8 h-8 text-[var(--text-primary)]" />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap mb-2">
                <h1 className="text-3xl font-bold text-[var(--text-primary)]">{counterparty.name}</h1>
                <span className={`px-3 py-1 rounded-lg text-base font-medium border ${counterparty.is_active
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-[var(--hover-2)] text-[var(--text-primary)]/40 border-[var(--border-color)]'}`}>
                  {counterparty.is_active ? 'Активен' : 'Неактивен'}
                </span>
              </div>
              <p className="text-[var(--text-primary)]/60 text-base">{counterparty.legal_name}</p>
              <div className="flex items-center gap-3 mt-2">
                <span className="px-3 py-1.5 rounded-lg text-sm font-medium bg-[var(--hover-2)] text-[var(--text-primary)]/70 border border-[var(--border-color)]">
                  {counterparty.counterparty_type}
                </span>
                <span className="text-[var(--text-primary)]/40 text-sm font-mono">ИНН {counterparty.inn}</span>
                {counterparty.parent_id && (
                  <Link to={`/counterparties/${counterparty.parent_id}`}
                    className="flex items-center gap-1.5 text-sm text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors">
                    <ArrowLeft size={12} /> К головному контрагенту
                  </Link>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-2.5 flex-shrink-0 flex-wrap">
          <button onClick={() => setShowEditModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--hover-2)]
                       hover:bg-[var(--hover-3)] border border-[var(--border-color)] text-[var(--text-primary)]/80 text-base font-medium transition-colors">
            <Edit size={16} /> Редактировать
          </button>
          <button onClick={() => setShowDeleteModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--accent)]/15
                       hover:bg-[var(--accent)]/30 border border-[var(--accent)]/15 text-[var(--accent)]
                       text-base font-medium transition-colors">
            <Trash2 size={16} /> Удалить
          </button>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1.5 border-b border-[var(--border-color)] overflow-x-auto">
        {tabs.filter(t => !t.hidden).map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-5 py-3 rounded-t-xl transition-all whitespace-nowrap ${activeTab === tab.id
              ? 'bg-[var(--accent)]/50 text-white border-b-2 border-red-500'
              : 'text-[var(--text-primary)]/50 hover:text-[var(--text-primary)]/70 hover:bg-[var(--hover-2)]'}`}>
            <tab.icon size={16} />
            <span className="text-base font-medium">{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span className="ml-0.5 px-2 py-0.5 rounded-full bg-[var(--hover-3)] text-sm">{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Content ── */}
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">

          {/* Информация */}
          {activeTab === 'info' && (
            <div className="space-y-6 animate-in fade-in duration-500">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
                  <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-4 flex items-center gap-2"><Hash className="w-3.5 h-3.5" /> ИНН</p>
                  <p className="text-[var(--text-primary)] text-base font-mono">{counterparty.inn || '—'}</p>
                </div>
                {shouldShowKpp(counterparty.counterparty_type) && counterparty.kpp && (
                  <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
                    <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-4 flex items-center gap-2"><CreditCard className="w-3.5 h-3.5" /> КПП</p>
                    <p className="text-[var(--text-primary)] text-base font-mono">{counterparty.kpp}</p>
                  </div>
                )}
                {counterparty.okpo && (
                  <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
                    <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-4 flex items-center gap-2"><Briefcase className="w-3.5 h-3.5" /> ОКПО</p>
                    <p className="text-[var(--text-primary)] text-base font-mono">{counterparty.okpo}</p>
                  </div>
                )}
                {counterparty.phone && (
                  <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
                    <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-4 flex items-center gap-2"><PhoneCall className="w-3.5 h-3.5" /> Телефон</p>
                    <a href={`tel:${counterparty.phone}`} className="text-[var(--text-primary)] text-base hover:text-[var(--accent)] transition-colors">{counterparty.phone}</a>
                  </div>
                )}
                {counterparty.email && (
                  <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
                    <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-4 flex items-center gap-2"><AtSign className="w-3.5 h-3.5" /> Email</p>
                    <a href={`mailto:${counterparty.email}`} className="text-[var(--text-primary)] text-base hover:text-[var(--accent)] transition-colors break-all">{counterparty.email}</a>
                  </div>
                )}
                {counterparty.address && (
                  <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
                    <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-4 flex items-center gap-2"><MapPinned className="w-3.5 h-3.5" /> Адрес</p>
                    <p className="text-[var(--text-primary)] text-base leading-relaxed">{counterparty.address}</p>
                  </div>
                )}
                <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
                  <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-4 flex items-center gap-2"><Calendar className="w-3.5 h-3.5" /> Создан</p>
                  <p className="text-[var(--text-primary)] text-base">{fmtDate(counterparty.created_at)}</p>
                </div>
              </div>
            </div>
          )}

          {/* Контактные лица */}
          {activeTab === 'contact' && (
            <ContactsTab counterpartyId={id!} persons={counterparty.contact_persons || []} onRefresh={loadData} />
          )}

          {/* Продукты */}
          {activeTab === 'products' && <ProductsTab counterpartyId={id!} />}

          {/* Подразделения */}
          {activeTab === 'branches' && canAddBranch && (
            <BranchesTab counterpartyId={id!} counterpartyName={counterparty.name} />
          )}

          {/* Сотрудники */}
          {activeTab === 'customers' && (
            <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] overflow-hidden">
              <div className="px-6 py-5 border-b border-[var(--border-color)] bg-[var(--hover-1)] flex items-center justify-between">
                <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2.5">
                  <Users size={18} className="text-[var(--text-primary)]/40" /> Сотрудники
                  {customers.length > 0 && <span className="px-2 py-0.5 rounded-full bg-[var(--hover-3)] text-sm text-[var(--text-primary)]/50">{customers.length}</span>}
                </h2>
                <button className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[var(--accent)] text-white text-base font-medium shadow-md">
                  <UserPlus size={16} /> Пригласить
                </button>
              </div>
              <div className="p-6">
                {customers.length === 0 ? (
                  <div className="text-center py-16"><Users size={36} className="text-[var(--text-primary)]/15 mx-auto mb-4" /><p className="text-[var(--text-primary)]/50 text-base">Нет сотрудников</p></div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {customers.map(c => (
                      <div key={c.id} className="flex items-center gap-4 py-4 px-2">
                        {c.avatar_url ? <img src={c.avatar_url} alt="" className="w-10 h-10 rounded-full object-cover border border-[var(--border-color)]" /> : <Avatar name={c.full_name || c.username} />}
                        <div className="flex-1 min-w-0">
                          <p className="text-base font-semibold text-[var(--text-primary)] truncate">{c.full_name || c.username || 'Без имени'}</p>
                          <p className="text-sm text-[var(--text-primary)]/40 truncate">{c.email}</p>
                        </div>
                        <span className={`px-3 py-1.5 rounded-lg text-sm font-medium border flex-shrink-0 ${c.is_active ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20' : 'bg-[var(--hover-2)] text-[var(--text-primary)]/40 border-[var(--border-color)]'}`}>
                          {c.is_active ? 'Активен' : 'Неактивен'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Заявки */}
          {activeTab === 'tickets' && (
            <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] overflow-hidden">
              <div className="px-6 py-5 border-b border-[var(--border-color)] bg-[var(--hover-1)] flex items-center justify-between">
                <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2.5">
                  <Ticket size={18} className="text-[var(--text-primary)]/40" /> Заявки
                </h2>
                <Link to={`/tickets/new?counterparty_id=${id}`} className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[var(--accent)] text-white text-base font-medium shadow-md">
                  <Plus size={16} /> Создать
                </Link>
              </div>
              <div className="p-6">
                {tickets.length === 0 ? (
                  <div className="text-center py-16"><FileText size={36} className="text-[var(--text-primary)]/15 mx-auto mb-4" /><p className="text-[var(--text-primary)]/50 text-base">Нет заявок</p></div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {tickets.map(ticket => (
                      <Link key={ticket.id} to={`/tickets/${ticket.number}`}
                        className="flex items-start justify-between gap-4 py-4 px-2 hover:bg-[var(--hover-1)] rounded-xl transition-colors group">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <span className="text-[var(--accent)] font-mono text-sm bg-[var(--accent-soft)] border border-[var(--accent)]/15 px-2 py-0.5 rounded-lg">#{ticket.number}</span>
                            <span className={`px-2.5 py-0.5 rounded-lg text-sm font-medium border ${statusClr(ticket.status)}`}>{ticket.status}</span>
                            <span className={`px-2.5 py-0.5 rounded-lg text-sm font-medium border ${priorityClr(ticket.priority)}`}>{ticket.priority}</span>
                          </div>
                          <p className="text-base font-medium text-[var(--text-primary)] truncate group-hover:text-[var(--accent)] transition-colors">{ticket.title}</p>
                          <p className="text-sm text-[var(--text-primary)]/30 mt-1">{fmtDateShort(ticket.created_at)}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-[var(--text-primary)]/20 group-hover:text-[var(--accent)] flex-shrink-0 mt-1" />
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* История */}
          {activeTab === 'history' && (
            <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] overflow-hidden">
              <div className="px-6 py-5 border-b border-[var(--border-color)] bg-[var(--hover-1)]">
                <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2.5">
                  <History size={18} className="text-[var(--text-primary)]/40" /> История
                </h2>
              </div>
              <div className="p-6 space-y-5">
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-emerald-500/15 flex items-center justify-center flex-shrink-0"><CheckCircle2 size={20} className="text-emerald-400" /></div>
                  <div><p className="text-[var(--text-primary)] font-semibold text-base">Контрагент создан</p><p className="text-[var(--text-primary)]/50 text-sm mt-1">{fmtDate(counterparty.created_at)}</p></div>
                </div>
                {counterparty.updated_at !== counterparty.created_at && (
                  <div className="flex gap-4">
                    <div className="w-10 h-10 rounded-full bg-blue-500/15 flex items-center justify-center flex-shrink-0"><Clock size={20} className="text-[var(--info)]" /></div>
                    <div><p className="text-[var(--text-primary)] font-semibold text-base">Данные обновлены</p><p className="text-[var(--text-primary)]/50 text-sm mt-1">{fmtDate(counterparty.updated_at)}</p></div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Sidebar ── */}
        <div className="space-y-5">
          <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
            <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-5 flex items-center gap-2"><Info className="w-3.5 h-3.5" /> Сводка</p>
            <div className="divide-y divide-white/[0.06]">
              {[
                { label: 'Тип', value: <span className="text-[var(--text-primary)]/80 text-sm">{counterparty.counterparty_type}</span> },
                { label: 'ИНН', value: <span className="font-mono text-[var(--text-primary)]/80">{counterparty.inn}</span> },
                { label: 'Контактов', value: <span className="text-[var(--text-primary)] font-bold">{counterparty.contact_persons?.length ?? 0}</span> },
                ...(canAddBranch ? [{ label: 'Подразделений', value: <span className="text-[var(--text-primary)] font-bold">{branches.length}</span> }] : []),
                { label: 'Сотрудников', value: <span className="text-[var(--text-primary)] font-bold">{customers.length}</span> },
                { label: 'Заявок', value: <span className="text-[var(--text-primary)] font-bold">{tickets.length}</span> },
                { label: 'Активных', value: <span className="text-[var(--text-primary)] font-bold">{tickets.filter(t => t.status !== 'Закрыт' && t.status !== 'Решён').length}</span> },
                { label: 'Создан', value: <span className="text-[var(--text-primary)]/70 text-sm">{fmtDateShort(counterparty.created_at)}</span> },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between py-3">
                  <span className="text-[var(--text-primary)]/40 text-base">{row.label}</span>
                  {row.value}
                </div>
              ))}
            </div>
          </div>

          {/* Быстрые действия */}
          <div className="bg-[var(--hover-2)] rounded-2xl border border-[var(--border-color)] p-5">
            <p className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-4">Действия</p>
            <div className="space-y-1">
              <button onClick={() => setShowEditModal(true)}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 hover:text-[var(--text-primary)] text-sm font-medium transition-colors text-left">
                <Edit size={15} className="text-[var(--text-primary)]/40" /> Редактировать данные
              </button>
              <button onClick={() => setActiveTab('contact')}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 hover:text-[var(--text-primary)] text-sm font-medium transition-colors text-left">
                <UserPlus size={15} className="text-[var(--text-primary)]/40" /> Добавить контакт
              </button>
              {canAddBranch && (
                <button onClick={() => setActiveTab('branches')}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 hover:text-[var(--text-primary)] text-sm font-medium transition-colors text-left">
                  <GitBranch size={15} className="text-[var(--text-primary)]/40" /> Подразделения
                </button>
              )}
              <Link to={`/tickets/new?counterparty_id=${id}`}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-[var(--hover-3)] text-[var(--text-primary)]/70 hover:text-[var(--text-primary)] text-sm font-medium transition-colors">
                <Ticket size={15} className="text-[var(--text-primary)]/40" /> Создать заявку
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ── Модалки ── */}
      {showDeleteModal && (
        <DeleteModal title="Удалить контрагента?" name={counterparty.name} loading={deleting}
          onConfirm={handleDelete} onClose={() => setShowDeleteModal(false)} />
      )}
      {showEditModal && (
        <EditCounterpartyModal counterparty={counterparty}
          onSave={updated => { setCounterparty(updated); setShowEditModal(false); }}
          onClose={() => setShowEditModal(false)} />
      )}
    </div>
  );
}