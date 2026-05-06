import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Building2, Phone, Mail, Users, FileText, Clock,
  Edit, Trash2, Plus, User, MessageSquare, Loader2, ExternalLink, Calendar,
  Hash, CheckCircle2, Briefcase, CreditCard, MapPinned, AtSign,
  PhoneCall, UserPlus, Ticket, History, Info, UserCheck,
  Package, Server, Globe, Smartphone, Monitor, Cpu, Code, HelpCircle,
  X, Tag, Link2, Layers, RefreshCcw, AlertTriangle,
  ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Search,
} from 'lucide-react';
import { counterpartiesApi, ticketsApi, productsApi } from '../api/client';
import type { Counterparty, CounterpartyCustomer, TicketListItem } from '../types';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getInitials(name?: string | null): string {
  if (!name) return '?';
  return name.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
}

function Avatar({ name, size = 'md' }: { name?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const cls = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base' }[size];
  return (
    <div className={`${cls} rounded-full bg-gradient-to-br from-red-800 to-red-700
                    flex items-center justify-center font-bold text-white flex-shrink-0 select-none`}>
      {getInitials(name)}
    </div>
  );
}

const shouldShowKpp = (type?: string) =>
  type === 'Юридическое лицо' || type === 'Обособленное подразделение';

// ─── Продукты: константы ──────────────────────────────────────────────────────

const PRODUCT_CATEGORIES = [
  { value: 'ERP',      label: 'ERP',      icon: Server,     color: 'text-orange-400',  bg: 'bg-orange-500/10' },
  { value: 'WEB',      label: 'Web',      icon: Globe,      color: 'text-blue-400',    bg: 'bg-blue-500/10' },
  { value: 'MOBILE',   label: 'Mobile',   icon: Smartphone, color: 'text-green-400',   bg: 'bg-green-500/10' },
  { value: 'API',      label: 'API',      icon: Code,       color: 'text-violet-400',  bg: 'bg-violet-500/10' },
  { value: 'DESKTOP',  label: 'Desktop',  icon: Monitor,    color: 'text-cyan-400',    bg: 'bg-cyan-500/10' },
  { value: 'HARDWARE', label: 'Hardware',  icon: Cpu,        color: 'text-amber-400',   bg: 'bg-amber-500/10' },
  { value: 'OTHER',    label: 'Прочее',    icon: HelpCircle, color: 'text-white/50',    bg: 'bg-white/[0.06]' },
] as const;

const ENVIRONMENTS = [
  { value: 'production',  label: 'Production' },
  { value: 'staging',     label: 'Staging' },
  { value: 'testing',     label: 'Testing' },
  { value: 'development', label: 'Development' },
] as const;

const PRODUCT_STATUSES = [
  { value: 'active',     label: 'Активный',   dot: 'bg-emerald-400', color: 'text-emerald-400' },
  { value: 'beta',       label: 'Бета',       dot: 'bg-blue-400',    color: 'text-blue-400' },
  { value: 'deprecated', label: 'Устаревший', dot: 'bg-white/30',    color: 'text-white/40' },
] as const;

const catMeta    = (v: string) => PRODUCT_CATEGORIES.find(c => c.value === v);
const statusMeta = (v: string) => PRODUCT_STATUSES.find(s => s.value === v);
const statusLabel = (v: string) => statusMeta(v)?.label ?? v;
const statusDot   = (s: string) => statusMeta(s)?.dot ?? 'bg-white/20';
const envLabel    = (v: string) => ENVIRONMENTS.find(e => e.value === v)?.label ?? v;

const envBadgeClass = (e: string) => {
  if (e === 'production')  return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
  if (e === 'staging')     return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
  if (e === 'testing')     return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
  if (e === 'development') return 'bg-purple-500/10 text-purple-400 border border-purple-500/20';
  return 'bg-white/5 text-white/40 border border-white/10';
};

const ATTRIBUTE_LABELS: Record<string, string> = {
  license_type: 'Лицензия', environment: 'Среда', db_connection_ref: 'БД',
  modules_enabled: 'Модули', max_concurrent_users: 'Макс. пользователей',
  base_url: 'URL', admin_url: 'Админ', hosting_provider: 'Хостинг',
  tech_stack: 'Стек', ssl_expiry_date: 'SSL до', cdn_enabled: 'CDN',
  platform: 'Платформа', auth_method: 'Авторизация',
};
const getAttrLabel   = (k: string) => ATTRIBUTE_LABELS[k] || k.replace(/_/g, ' ');
const formatAttrValue = (v: any): string => {
  if (v === true) return 'Да';
  if (v === false) return 'Нет';
  if (Array.isArray(v)) return v.join(', ');
  return String(v);
};

// ─── Модалка удаления ────────────────────────────────────────────────────────

function DeleteModal({ name, loading, onConfirm, onClose }: {
  name: string; loading: boolean; onConfirm: () => void; onClose: () => void;
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
      <div className="relative w-full max-w-md bg-[#1a1a1a] border border-white/[0.1] rounded-2xl overflow-hidden"
           style={{ boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 24px 80px rgba(0,0,0,0.7)' }}>
        <div className="pt-8 flex justify-center">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
        </div>
        <div className="px-7 pt-5 pb-2 text-center">
          <h2 className="text-xl font-bold text-white mb-3">Удалить контрагента?</h2>
          <p className="text-base text-white/60 leading-relaxed">
            Контрагент <span className="text-white font-semibold">«{name}»</span> будет удалён.
            Это действие нельзя отменить.
          </p>
        </div>
        <div className="flex gap-3 p-6">
          <button onClick={onClose} disabled={loading}
                  className="flex-1 px-4 py-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.09]
                             text-white/70 text-base font-medium transition-colors disabled:opacity-50">
            Отмена
          </button>
          <button onClick={onConfirm} disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                             bg-red-600/20 hover:bg-red-600/30 border border-red-600/30
                             text-red-400 text-base font-medium transition-all
                             disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            {loading ? 'Удаление...' : 'Удалить'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Вкладка продуктов ────────────────────────────────────────────────────────

function ProductsTab({ counterpartyId }: { counterpartyId: string }) {
  const [products, setProducts]     = useState<any[]>([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [page, setPage]             = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [showForm, setShowForm]           = useState(false);
  const [allProducts, setAllProducts]     = useState<any[]>([]);
  const [loadingAll, setLoadingAll]       = useState(false);
  const [filterQuery, setFilterQuery]     = useState('');
  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);
  const [linkEnv, setLinkEnv]             = useState('production');
  const [linkPrimary, setLinkPrimary]     = useState(false);
  const [linking, setLinking]             = useState(false);
  const [linkError, setLinkError]         = useState<string | null>(null);

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
      catch {}
      finally { if (!cancelled) setLoadingAll(false); }
    })();
    return () => { cancelled = true; };
  }, [showForm]);

  const filtered = filterQuery.trim()
    ? allProducts.filter(p =>
        (p.display_name || p.name || '').toLowerCase().includes(filterQuery.toLowerCase()) ||
        (p.vendor || '').toLowerCase().includes(filterQuery.toLowerCase()))
    : allProducts;

  const handleLink = async () => {
    if (!selectedProduct) return;
    setLinking(true); setLinkError(null);
    try {
      await counterpartiesApi.linkProduct(counterpartyId, {
        product_id: selectedProduct.id, environment: linkEnv, is_primary: linkPrimary,
      });
      setSelectedProduct(null); setFilterQuery(''); setLinkEnv('production');
      setLinkPrimary(false); setShowForm(false); setPage(1); load();
    } catch (err: any) {
      const d = err?.response?.data?.detail;
      setLinkError(typeof d === 'string' ? d : 'Не удалось привязать продукт');
    } finally { setLinking(false); }
  };

  const closeForm = () => {
    setShowForm(false); setSelectedProduct(null); setFilterQuery('');
    setLinkEnv('production'); setLinkPrimary(false); setLinkError(null);
  };

  return (
    <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Шапка */}
      <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.01]">
        <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
          <Layers className="w-5 h-5 text-white/40" />
          Продукты
          {totalItems > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-white/[0.08] text-sm text-white/50">{totalItems}</span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 rounded-xl hover:bg-white/[0.06] text-white/40 hover:text-white/70 transition-colors">
            <RefreshCcw size={16} />
          </button>
          <button onClick={() => showForm ? closeForm() : setShowForm(true)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-base font-medium transition-all ${
                    showForm
                      ? 'bg-white/[0.06] text-white/70'
                      : 'bg-red-800 hover:bg-red-700 text-white shadow-md shadow-red-900/30'
                  }`}>
            {showForm ? <X size={16} /> : <Link2 size={16} />}
            {showForm ? 'Отмена' : 'Привязать'}
          </button>
        </div>
      </div>

      {/* Inline форма */}
      {showForm && (
        <div className="border-b border-white/[0.08] bg-white/[0.01] p-6 space-y-5">
          {linkError && (
            <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-xl text-base text-red-300 flex items-start gap-2">
              <X size={16} className="mt-0.5 flex-shrink-0" />{linkError}
            </div>
          )}
          <div>
            <label className="block text-base text-white/60 mb-2">Выберите продукт <span className="text-red-400">*</span></label>
            {selectedProduct ? (
              <div className="flex items-center gap-3 p-4 bg-white/[0.04] border border-white/[0.08] rounded-xl">
                {(() => { const c = catMeta(selectedProduct.category); const I = c?.icon || Package;
                  return <div className={`w-11 h-11 rounded-xl ${c?.bg || 'bg-white/[0.06]'} flex items-center justify-center ${c?.color || 'text-white/40'} flex-shrink-0`}><I size={20} /></div>;
                })()}
                <div className="flex-1 min-w-0">
                  <p className="text-base font-medium text-white truncate">{selectedProduct.display_name || selectedProduct.name}</p>
                  <p className="text-sm text-white/40">{selectedProduct.vendor}</p>
                </div>
                <button onClick={() => { setSelectedProduct(null); setFilterQuery(''); }}
                        className="p-1.5 rounded-lg text-white/30 hover:text-red-400 transition-colors">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="relative">
                  <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
                  <input value={filterQuery} onChange={e => setFilterQuery(e.target.value)}
                         placeholder="Фильтр по названию..."
                         className="w-full pl-10 pr-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl text-base text-white placeholder-white/30 focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10 transition-all" />
                </div>
                <div className="max-h-56 overflow-y-auto rounded-xl border border-white/[0.08] bg-[#1a1a1a] divide-y divide-white/[0.04]"
                     style={{ boxShadow: '0 16px 48px rgba(0,0,0,0.4)' }}>
                  {loadingAll ? (
                    <div className="flex justify-center py-10"><Loader2 size={20} className="text-white/20 animate-spin" /></div>
                  ) : filtered.length === 0 ? (
                    <div className="py-10 text-center"><Package size={32} className="mx-auto mb-2 text-white/15" /><p className="text-base text-white/40">{filterQuery ? 'Ничего не найдено' : 'Нет продуктов'}</p></div>
                  ) : filtered.map(p => {
                    const c = catMeta(p.category); const I = c?.icon || Package;
                    return (
                      <button key={p.id} onClick={() => { setSelectedProduct(p); setFilterQuery(''); }}
                              className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-white/[0.04] transition-colors">
                        <div className={`w-10 h-10 rounded-lg ${c?.bg || 'bg-white/[0.06]'} flex items-center justify-center ${c?.color || 'text-white/30'} flex-shrink-0`}><I size={18} /></div>
                        <div className="flex-1 min-w-0">
                          <p className="text-base text-white truncate">{p.display_name || p.name}</p>
                          <p className="text-sm text-white/40">{p.vendor}</p>
                        </div>
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
                <label className="block text-base text-white/60 mb-2">Среда</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {ENVIRONMENTS.map(env => (
                    <button key={env.value} onClick={() => setLinkEnv(env.value)}
                            className={`px-3 py-3 rounded-xl text-base font-medium transition-all ${
                              linkEnv === env.value ? envBadgeClass(env.value) : 'border border-white/[0.06] bg-white/[0.02] text-white/40 hover:bg-white/[0.04]'
                            }`}>{env.label}</button>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                <div><p className="text-base text-white/80">Основной продукт</p><p className="text-sm text-white/40">Отмечает как основной</p></div>
                <button onClick={() => setLinkPrimary(!linkPrimary)}
                        className={`relative w-11 h-6 rounded-full transition-colors ${linkPrimary ? 'bg-red-700' : 'bg-white/10'}`}>
                  <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform ${linkPrimary ? 'translate-x-5' : ''}`} />
                </button>
              </div>
              <button onClick={handleLink} disabled={linking}
                      className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-red-800 hover:bg-red-700 text-white text-base font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-red-900/30">
                {linking ? <Loader2 size={18} className="animate-spin" /> : <Link2 size={18} />}
                Привязать продукт
              </button>
            </>
          )}
        </div>
      )}

      {/* Список */}
      <div className="divide-y divide-white/[0.04]">
        {loading ? (
          <div className="flex justify-center py-20"><Loader2 size={24} className="text-red-500/40 animate-spin" /></div>
        ) : error ? (
          <div className="py-12 text-center text-base text-red-400">{error}</div>
        ) : products.length === 0 ? (
          <div className="flex flex-col items-center py-20 text-center px-6">
            <Package size={36} className="text-white/15 mb-4" />
            <p className="text-white/60 text-base font-semibold mb-1">Нет привязанных продуктов</p>
            <p className="text-white/40 text-sm mb-5">Привяжите продукты к контрагенту</p>
            {!showForm && (
              <button onClick={() => setShowForm(true)}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-800/20 hover:bg-red-800/30 border border-red-800/30 text-red-400 text-base font-medium transition-colors">
                <Link2 size={16} /> Привязать
              </button>
            )}
          </div>
        ) : products.map(product => {
          const cat = catMeta(product.category);
          const Icon = cat?.icon || Package;
          const sInfo = statusMeta(product.status);
          const isExpanded = expandedId === product.id;
          const attrs = Object.entries(product.attributes || {}).filter(
            ([, v]) => v !== null && v !== '' && !(Array.isArray(v) && (v as any[]).length === 0));

          return (
            <div key={product.id} className={isExpanded ? 'bg-white/[0.02]' : ''}>
              <button onClick={() => setExpandedId(isExpanded ? null : product.id)}
                      className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-white/[0.03] transition-colors group">
                <div className={`w-11 h-11 rounded-xl ${cat?.bg || 'bg-white/[0.06]'} flex items-center justify-center ${cat?.color || 'text-white/40'} group-hover:scale-105 transition-transform flex-shrink-0`}>
                  <Icon size={20} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-base font-semibold text-white truncate">{product.display_name || product.name}</span>
                    {product.is_primary && <span className="px-2 py-0.5 rounded-md bg-red-800/20 border border-red-800/30 text-xs text-red-400 font-medium flex-shrink-0">Основной</span>}
                  </div>
                  <p className="text-sm text-white/40">{product.vendor}</p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  {product.environment && <span className={`px-2.5 py-1 rounded-lg text-sm font-medium hidden sm:block ${envBadgeClass(product.environment)}`}>{envLabel(product.environment)}</span>}
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${statusDot(product.status)}`} />
                    <span className={`text-sm hidden sm:block ${sInfo?.color || 'text-white/40'}`}>{statusLabel(product.status)}</span>
                  </div>
                  {isExpanded ? <ChevronUp size={18} className="text-white/40" /> : <ChevronDown size={18} className="text-white/20" />}
                </div>
              </button>
              {isExpanded && (
                <div className="px-6 pb-6 pl-20 space-y-5 border-t border-white/[0.04]">
                  <div className="flex flex-wrap gap-2.5 pt-4">
                    <span className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.05] text-base text-white/60 border border-white/[0.06]">
                      <Building2 size={16} className="text-white/40" />{product.vendor}
                    </span>
                    {product.version && <span className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.05] text-base text-white/60 border border-white/[0.06] font-mono"><Tag size={16} className="text-white/40" />v{product.version}</span>}
                  </div>
                  {product.description && (
                    <div>
                      <p className="text-xs uppercase tracking-widest text-white/30 mb-2 font-semibold">Описание</p>
                      <p className="text-base text-white/70 leading-relaxed whitespace-pre-wrap">{product.description}</p>
                    </div>
                  )}
                  {attrs.length > 0 && (
                    <div>
                      <p className="text-xs uppercase tracking-widest text-white/30 mb-3 font-semibold">Характеристики</p>
                      <div className="rounded-xl border border-white/[0.08] divide-y divide-white/[0.06] bg-white/[0.02]">
                        {attrs.map(([key, value]) => (
                          <div key={key} className="flex items-start gap-4 px-5 py-3.5">
                            <span className="text-base text-white/40 w-[140px] flex-shrink-0">{getAttrLabel(key)}</span>
                            <span className="text-base text-white/80 break-words min-w-0">{formatAttrValue(value)}</span>
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
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/[0.08]">
          <span className="text-base text-white/40">Стр. {page} из {totalPages}</span>
          <div className="flex gap-1.5">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="p-2 rounded-lg hover:bg-white/[0.06] text-white/40 disabled:opacity-20"><ChevronLeft size={18} /></button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="p-2 rounded-lg hover:bg-white/[0.06] text-white/40 disabled:opacity-20"><ChevronRight size={18} /></button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Типы вкладок ─────────────────────────────────────────────────────────────

type TabType = 'info' | 'contact' | 'products' | 'customers' | 'tickets' | 'history';

// ─── Основная страница ────────────────────────────────────────────────────────

export default function CounterpartyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [counterparty, setCounterparty] = useState<Counterparty | null>(null);
  const [customers, setCustomers]       = useState<CounterpartyCustomer[]>([]);
  const [tickets, setTickets]           = useState<TicketListItem[]>([]);
  const [loading, setLoading]           = useState(true);
  const [activeTab, setActiveTab]       = useState<TabType>('info');

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting]               = useState(false);
    // Контактное лицо
  const [showContactForm, setShowContactForm] = useState(false);
  const [contactForm, setContactForm] = useState({
  last_name: '',
  first_name: '',
  middle_name: '',
  phone: '',
  email: '',
  telegram: '',
  vk: '',
});
  const [savingContact, setSavingContact] = useState(false);

  useEffect(() => { if (id) loadData(); }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const cp = await counterpartiesApi.getById(id!);
      setCounterparty(cp);
      try { const r = await counterpartiesApi.getCustomers(id!); setCustomers(Array.isArray(r?.items) ? r.items : []); } catch { setCustomers([]); }
      try { const r = await ticketsApi.getAllWithFilters(1, 100, { counterparty_id: id }); setTickets(Array.isArray(r?.items) ? r.items : []); } catch { setTickets([]); }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

const openContactForm = (person?: any) => {
  if (person) {
    // Если приходит full_name — пробуем разбить на части
    let lastName = person.last_name || '';
    let firstName = person.first_name || '';
    let middleName = person.middle_name || '';

    if (!lastName && !firstName && person.full_name) {
      const parts = person.full_name.trim().split(/\s+/);
      lastName = parts[0] || '';
      firstName = parts[1] || '';
      middleName = parts.slice(2).join(' ') || '';
    }

    setContactForm({
      last_name: lastName,
      first_name: firstName,
      middle_name: middleName,
      phone: person.phone || '',
      email: person.email || '',
      telegram: person.messengers?.telegram?.replace('@', '') || '',
      vk: person.messengers?.vk || '',
    });
  } else {
    setContactForm({
      last_name: '', first_name: '', middle_name: '',
      phone: '', email: '', telegram: '', vk: '',
    });
  }
  setShowContactForm(true);
};

const handleSaveContact = async () => {
  if (!contactForm.last_name.trim() || !contactForm.first_name.trim()) return;
  setSavingContact(true);
  try {
    const messengers: Record<string, string> = {};
    if (contactForm.telegram.trim()) messengers.telegram = contactForm.telegram.trim();
    if (contactForm.vk.trim()) messengers.vk = contactForm.vk.trim();

    await counterpartiesApi.updateContactPerson(id!, {
      first_name: contactForm.first_name.trim(),
      last_name: contactForm.last_name.trim(),
      middle_name: contactForm.middle_name.trim() || undefined,
      phone: contactForm.phone.trim() || undefined,
      email: contactForm.email.trim() || undefined,
      messengers: Object.keys(messengers).length > 0 ? messengers : undefined,
    });
    setShowContactForm(false);
    loadData();
  } catch (e) {
    console.error('Failed to save contact person:', e);
  } finally {
    setSavingContact(false);
  }
};

  const handleDelete = async () => {
    setDeleting(true);
    try { await counterpartiesApi.delete(id!); navigate('/counterparties'); }
    catch (e) { console.error(e); }
    finally { setDeleting(false); }
  };

  const statusClr = (s: string) => ({
    'Новый':          'bg-blue-500/15 text-blue-400 border-blue-500/30',
    'Открыт':         'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
    'В работе':       'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    'Ожидает ответа': 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    'Решён':          'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    'Закрыт':         'bg-neutral-500/15 text-neutral-400 border-neutral-500/30',
    'Переоткрыт':     'bg-orange-500/15 text-orange-400 border-orange-500/30',
  }[s] ?? 'bg-neutral-500/15 text-neutral-400 border-neutral-500/30');

  const priorityClr = (p: string) => ({
    'Низкий':      'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    'Средний':     'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    'Высокий':     'bg-orange-500/15 text-orange-400 border-orange-500/30',
    'Критический': 'bg-red-500/15 text-red-400 border-red-500/30',
  }[p] ?? 'bg-neutral-500/15 text-neutral-400 border-neutral-500/30');

  const fmtDate = (d: string) => new Date(d).toLocaleString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
  const fmtDateShort = (d: string) => new Date(d).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'short', year: 'numeric',
  });

  const tabs: { id: TabType; label: string; icon: any; count?: number }[] = [
    { id: 'info',      label: 'Информация',      icon: Info },
    { id: 'contact',   label: 'Контактные лица',  icon: UserCheck },
    { id: 'products',  label: 'Продукты',         icon: Layers },
    { id: 'customers', label: 'Сотрудники',       icon: Users,  count: customers.length },
    { id: 'tickets',   label: 'Заявки',           icon: Ticket, count: tickets.length },
    { id: 'history',   label: 'История',          icon: History },
  ];

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="w-10 h-10 text-red-500 animate-spin" />
    </div>
  );

  if (!counterparty) return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-16 text-center">
      <Building2 className="w-20 h-20 text-white/15 mx-auto mb-5" />
      <h2 className="text-2xl font-bold text-white mb-3">Контрагент не найден</h2>
      <button onClick={() => navigate('/counterparties')}
              className="px-6 py-2.5 rounded-xl bg-red-800 hover:bg-red-700 text-white text-base font-medium transition-colors">
        Вернуться к списку
      </button>
    </div>
  );

  return (
    <div className="space-y-8">

      {/* ── Header ── */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
        <div className="flex items-start gap-4">
          <button onClick={() => navigate('/counterparties')}
                  className="p-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06]
                             text-white/60 hover:text-white transition-all mt-1">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-800 to-red-700
                            flex items-center justify-center shadow-lg shadow-red-900/30 flex-shrink-0">
              <Building2 className="w-8 h-8 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap mb-2">
                <h1 className="text-3xl font-bold text-white">{counterparty.name}</h1>
                <span className={`px-3 py-1 rounded-lg text-base font-medium border ${
                  counterparty.is_active
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    : 'bg-white/[0.06] text-white/40 border-white/[0.1]'
                }`}>{counterparty.is_active ? 'Активен' : 'Неактивен'}</span>
              </div>
              <p className="text-white/60 text-base">{counterparty.legal_name}</p>
              <div className="flex items-center gap-3 mt-2">
                <span className="px-3 py-1.5 rounded-lg text-sm font-medium bg-white/[0.06] text-white/70 border border-white/[0.08]">
                  {counterparty.counterparty_type}
                </span>
                <span className="text-white/40 text-sm font-mono">ИНН {counterparty.inn}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex gap-2.5 flex-shrink-0">
          <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.05]
                             hover:bg-white/[0.08] border border-white/[0.08] text-white/80 text-base font-medium transition-colors">
            <Edit size={16} /> Редактировать
          </button>
          <button onClick={() => setShowDeleteModal(true)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-900/15
                             hover:bg-red-900/30 border border-red-800/20 text-red-400
                             text-base font-medium transition-colors">
            <Trash2 size={16} /> Удалить
          </button>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1.5 border-b border-white/[0.08] overflow-x-auto">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-5 py-3 rounded-t-xl transition-all whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'bg-red-800/50 text-white border-b-2 border-red-500'
                      : 'text-white/50 hover:text-white/70 hover:bg-white/[0.04]'
                  }`}>
            <tab.icon size={16} />
            <span className="text-base font-medium">{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span className="ml-0.5 px-2 py-0.5 rounded-full bg-white/[0.1] text-sm">{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Content ── */}
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">

          {/* Информация */}
          {activeTab === 'info' && (
            <div className="space-y-6">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2"><Hash className="w-3.5 h-3.5" /> ИНН</p>
                  <p className="text-white text-base font-mono">{counterparty.inn || '—'}</p>
                </div>
                {shouldShowKpp(counterparty.counterparty_type) && counterparty.kpp && (
                  <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                    <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2"><CreditCard className="w-3.5 h-3.5" /> КПП</p>
                    <p className="text-white text-base font-mono">{counterparty.kpp}</p>
                  </div>
                )}
                {counterparty.okpo && (
                  <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                    <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2"><Briefcase className="w-3.5 h-3.5" /> ОКПО</p>
                    <p className="text-white text-base font-mono">{counterparty.okpo}</p>
                  </div>
                )}
                {counterparty.phone && (
                  <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                    <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2"><PhoneCall className="w-3.5 h-3.5" /> Телефон</p>
                    <a href={`tel:${counterparty.phone}`} className="text-white text-base hover:text-red-400 transition-colors">{counterparty.phone}</a>
                  </div>
                )}
                {counterparty.email && (
                  <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                    <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2"><AtSign className="w-3.5 h-3.5" /> Email</p>
                    <a href={`mailto:${counterparty.email}`} className="text-white text-base hover:text-red-400 transition-colors break-all">{counterparty.email}</a>
                  </div>
                )}
                {counterparty.address && (
                  <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                    <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2"><MapPinned className="w-3.5 h-3.5" /> Адрес</p>
                    <p className="text-white text-base leading-relaxed">{counterparty.address}</p>
                  </div>
                )}
                <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
                  <p className="text-xs uppercase tracking-widest text-white/30 mb-4 flex items-center gap-2"><Calendar className="w-3.5 h-3.5" /> Создан</p>
                  <p className="text-white text-base">{fmtDate(counterparty.created_at)}</p>
                </div>
              </div>
            </div>
          )}

          {/* Контактные лица */}
          {activeTab === 'contact' && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] bg-white/[0.01] flex items-center justify-between">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <UserCheck size={18} className="text-white/40" /> Контактные лица
                </h2>
                <button
                  onClick={() => openContactForm()}
                  className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-red-800 hover:bg-red-700
                             text-white text-base font-medium transition-colors shadow-md shadow-red-900/30"
                >
                  <Plus size={16} />
                  {counterparty.contact_persons?.length ? 'Добавить' : 'Изменить'}
                </button>
              </div>

              <div className="p-6">
                {/* Inline-форма */}
                                {showContactForm && (
                  <div className="mb-6 p-5 space-y-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-base font-semibold text-white flex items-center gap-2">
                        <UserPlus size={16} className="text-red-400" />
                        {counterparty.contact_persons?.length ? 'Новое контактное лицо' : 'Новое контактное лицо'}
                      </h3>
                      <button
                        onClick={() => setShowContactForm(false)}
                        className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/30 hover:text-white/60 transition-colors"
                      >
                        <X size={16} />
                      </button>
                    </div>

                    {/* ФИО — три поля */}
                    <div className="grid md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm text-white/50 mb-1.5">
                          Фамилия <span className="text-red-400">*</span>
                        </label>
                        <input
                          value={contactForm.last_name}
                          onChange={e => setContactForm(p => ({ ...p, last_name: e.target.value }))}
                          placeholder="Иванов"
                          className="w-full px-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl
                                     text-white text-base placeholder-white/25
                                     focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10
                                     transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-white/50 mb-1.5">
                          Имя <span className="text-red-400">*</span>
                        </label>
                        <input
                          value={contactForm.first_name}
                          onChange={e => setContactForm(p => ({ ...p, first_name: e.target.value }))}
                          placeholder="Иван"
                          className="w-full px-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl
                                     text-white text-base placeholder-white/25
                                     focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10
                                     transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-white/50 mb-1.5">Отчество</label>
                        <input
                          value={contactForm.middle_name}
                          onChange={e => setContactForm(p => ({ ...p, middle_name: e.target.value }))}
                          placeholder="Иванович"
                          className="w-full px-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl
                                     text-white text-base placeholder-white/25
                                     focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10
                                     transition-all"
                        />
                      </div>
                    </div>

                    {/* Телефон + Email */}
                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-white/50 mb-1.5">Телефон</label>
                        <div className="relative">
                          <Phone size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/25" />
                          <input
                            value={contactForm.phone}
                            onChange={e => setContactForm(p => ({ ...p, phone: e.target.value }))}
                            placeholder="+7 (999) 123-45-67"
                            className="w-full pl-10 pr-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl
                                       text-white text-base placeholder-white/25
                                       focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10
                                       transition-all"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm text-white/50 mb-1.5">Email</label>
                        <div className="relative">
                          <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/25" />
                          <input
                            type="email"
                            value={contactForm.email}
                            onChange={e => setContactForm(p => ({ ...p, email: e.target.value }))}
                            placeholder="contact@company.ru"
                            className="w-full pl-10 pr-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl
                                       text-white text-base placeholder-white/25
                                       focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10
                                       transition-all"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Мессенджеры: Telegram + VK */}
                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-white/50 mb-1.5">Telegram</label>
                        <div className="relative">
                          <MessageSquare size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/25" />
                          <input
                            value={contactForm.telegram}
                            onChange={e => setContactForm(p => ({ ...p, telegram: e.target.value }))}
                            placeholder="username"
                            className="w-full pl-10 pr-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl
                                       text-white text-base placeholder-white/25
                                       focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10
                                       transition-all"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm text-white/50 mb-1.5">ВКонтакте</label>
                        <div className="relative">
                          <Globe size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/25" />
                          <input
                            value={contactForm.vk}
                            onChange={e => setContactForm(p => ({ ...p, vk: e.target.value }))}
                            placeholder="id или username"
                            className="w-full pl-10 pr-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl
                                       text-white text-base placeholder-white/25
                                       focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10
                                       transition-all"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Кнопки */}
                    <div className="flex items-center justify-end gap-3 pt-2">
                      <button
                        onClick={() => setShowContactForm(false)}
                        disabled={savingContact}
                        className="px-4 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.08]
                                   text-white/70 text-base font-medium transition-colors disabled:opacity-50"
                      >
                        Отмена
                      </button>
                      <button
                        onClick={handleSaveContact}
                        disabled={savingContact || !contactForm.last_name.trim() || !contactForm.first_name.trim()}
                        className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-800 hover:bg-red-700
                                   text-white text-base font-medium transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-red-900/30"
                      >
                        {savingContact
                          ? <Loader2 size={16} className="animate-spin" />
                          : <CheckCircle2 size={16} />}
                        {savingContact ? 'Сохранение...' : 'Сохранить'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Список контактных лиц */}
                {counterparty.contact_persons?.length ? (
                  <div className="space-y-4">
                    {counterparty.contact_persons.map((person, i) => (
                      <div key={i} className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <Avatar name={person.full_name} size="lg" />
                            <div>
                              <h3 className="text-base font-bold text-white">{person.full_name}</h3>
                              <p className="text-sm text-white/40">Контактное лицо</p>
                            </div>
                          </div>
                          
                        </div>

                        <div className="grid md:grid-cols-2 gap-3">
                          {person.phone && (
                            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
                              <p className="text-xs text-white/30 mb-1 flex items-center gap-1.5">
                                <Phone size={12} /> Телефон
                              </p>
                              <a href={`tel:${person.phone}`}
                                 className="text-white text-base hover:text-red-400 transition-colors">
                                {person.phone}
                              </a>
                            </div>
                          )}
                          {person.email && (
                            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
                              <p className="text-xs text-white/30 mb-1 flex items-center gap-1.5">
                                <Mail size={12} /> Email
                              </p>
                              <a href={`mailto:${person.email}`}
                                 className="text-white text-base hover:text-red-400 transition-colors break-all">
                                {person.email}
                              </a>
                            </div>
                          )}
                        </div>

                        {person.messengers?.telegram && (
                          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
                            <p className="text-xs text-white/30 mb-1 flex items-center gap-1.5">
                              <MessageSquare size={12} /> Telegram
                            </p>
                            <a href={`https://t.me/${person.messengers.telegram.replace('@', '')}`}
                               target="_blank" rel="noopener noreferrer"
                               className="text-white text-base hover:text-red-400 transition-colors flex items-center gap-2">
                              @{person.messengers.telegram.replace('@', '')}
                              <ExternalLink size={14} className="text-white/30" />
                            </a>
                          </div>
                          
                        )}
                                                {person.messengers?.vk && (
                          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
                            <p className="text-xs text-white/30 mb-1 flex items-center gap-1.5">
                              <Globe size={12} /> ВКонтакте
                            </p>
                            <a href={`https://vk.com/${person.messengers.vk}`}
                               target="_blank" rel="noopener noreferrer"
                               className="text-white text-base hover:text-red-400 transition-colors flex items-center gap-2">
                              {person.messengers.vk}
                              <ExternalLink size={14} className="text-white/30" />
                            </a>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : !showContactForm ? (
                  <div className="text-center py-16">
                    <User size={36} className="text-white/15 mx-auto mb-4" />
                    <p className="text-white/50 text-base font-semibold mb-1">Контактные лица не указаны</p>
                    <p className="text-white/30 text-sm mb-5">Добавьте контактное лицо для связи</p>
                    <button
                      onClick={() => openContactForm()}
                      className="text-red-400 hover:text-red-300 transition-colors text-base"
                    >
                      Добавить контактное лицо →
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          )}

          {/* Продукты */}
          {activeTab === 'products' && <ProductsTab counterpartyId={id!} />}

          {/* Сотрудники */}
          {activeTab === 'customers' && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] bg-white/[0.01] flex items-center justify-between">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <Users size={18} className="text-white/40" /> Сотрудники
                  {customers.length > 0 && <span className="px-2 py-0.5 rounded-full bg-white/[0.08] text-sm text-white/50">{customers.length}</span>}
                </h2>
                <button className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-red-800 hover:bg-red-700 text-white text-base font-medium transition-colors shadow-md shadow-red-900/30">
                  <UserPlus size={16} /> Пригласить
                </button>
              </div>
              <div className="p-6">
                {customers.length === 0 ? (
                  <div className="text-center py-16">
                    <Users size={36} className="text-white/15 mx-auto mb-4" />
                    <p className="text-white/50 text-base">Нет сотрудников</p>
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {customers.map(c => (
                      <div key={c.id} className="flex items-center gap-4 py-4 px-2">
                        {c.avatar_url ? (
                          <img src={c.avatar_url} alt="" className="w-10 h-10 rounded-full object-cover border border-white/[0.08]" />
                        ) : (
                          <Avatar name={c.full_name || c.username} />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-base font-semibold text-white truncate">{c.full_name || c.username || 'Без имени'}</p>
                          <p className="text-sm text-white/40 truncate">{c.email}</p>
                        </div>
                        <span className={`px-3 py-1.5 rounded-lg text-sm font-medium border flex-shrink-0 ${
                          c.is_active
                            ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20'
                            : 'bg-white/[0.06] text-white/40 border-white/[0.1]'
                        }`}>{c.is_active ? 'Активен' : 'Неактивен'}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Заявки */}
          {activeTab === 'tickets' && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] bg-white/[0.01] flex items-center justify-between">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <Ticket size={18} className="text-white/40" /> Заявки
                </h2>
                <Link to="/tickets/new" className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-red-800 hover:bg-red-700 text-white text-base font-medium transition-colors shadow-md shadow-red-900/30">
                  <Plus size={16} /> Создать
                </Link>
              </div>
              <div className="p-6">
                {tickets.length === 0 ? (
                  <div className="text-center py-16">
                    <FileText size={36} className="text-white/15 mx-auto mb-4" />
                    <p className="text-white/50 text-base">Нет заявок</p>
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {tickets.map(ticket => (
                      <Link key={ticket.id} to={`/tickets/${ticket.number}`}
                            className="flex items-start justify-between gap-4 py-4 px-2 hover:bg-white/[0.03] rounded-xl transition-colors group">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <span className="text-red-400 font-mono text-sm bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-lg">#{ticket.number}</span>
                            <span className={`px-2.5 py-0.5 rounded-lg text-sm font-medium border ${statusClr(ticket.status)}`}>{ticket.status}</span>
                            <span className={`px-2.5 py-0.5 rounded-lg text-sm font-medium border ${priorityClr(ticket.priority)}`}>{ticket.priority}</span>
                          </div>
                          <p className="text-base font-medium text-white truncate group-hover:text-red-400 transition-colors">{ticket.title}</p>
                          <p className="text-sm text-white/30 mt-1">{fmtDateShort(ticket.created_at)}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-red-400 transition-all flex-shrink-0 mt-1" />
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* История */}
          {activeTab === 'history' && (
            <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08] bg-white/[0.01]">
                <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                  <History size={18} className="text-white/40" /> История
                </h2>
              </div>
              <div className="p-6 space-y-5">
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
                    <CheckCircle2 size={20} className="text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-white font-semibold text-base">Контрагент создан</p>
                    <p className="text-white/50 text-sm mt-1">{fmtDate(counterparty.created_at)}</p>
                  </div>
                </div>
                {counterparty.updated_at !== counterparty.created_at && (
                  <div className="flex gap-4">
                    <div className="w-10 h-10 rounded-full bg-blue-500/15 flex items-center justify-center flex-shrink-0">
                      <Clock size={20} className="text-blue-400" />
                    </div>
                    <div>
                      <p className="text-white font-semibold text-base">Данные обновлены</p>
                      <p className="text-white/50 text-sm mt-1">{fmtDate(counterparty.updated_at)}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Sidebar ── */}
        <div className="space-y-5">
          <div className="bg-white/[0.04] rounded-2xl border border-white/[0.08] p-5">
            <p className="text-xs uppercase tracking-widest text-white/30 mb-5 flex items-center gap-2">
              <Info className="w-3.5 h-3.5" /> Сводка
            </p>
            <div className="divide-y divide-white/[0.06]">
              {[
                { label: 'Тип',         value: <span className="text-white/80 text-sm">{counterparty.counterparty_type}</span> },
                { label: 'ИНН',         value: <span className="font-mono text-white/80">{counterparty.inn}</span> },
                { label: 'Сотрудников', value: <span className="text-white font-bold">{customers.length}</span> },
                { label: 'Заявок',      value: <span className="text-white font-bold">{tickets.length}</span> },
                { label: 'Активных',    value: <span className="text-white font-bold">{tickets.filter(t => t.status !== 'Закрыт' && t.status !== 'Решён').length}</span> },
                { label: 'Создан',      value: <span className="text-white/70 text-sm">{fmtDateShort(counterparty.created_at)}</span> },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between py-3">
                  <span className="text-white/40 text-base">{row.label}</span>
                  {row.value}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Модал удаления */}
      {showDeleteModal && (
        <DeleteModal
          name={counterparty.name}
          loading={deleting}
          onConfirm={handleDelete}
          onClose={() => setShowDeleteModal(false)}
        />
      )}
    </div>
  );
}