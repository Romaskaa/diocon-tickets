import React, { useCallback, useEffect, useState, useRef, useLayoutEffect, useMemo } from 'react';
import {
  Loader2, Plus, RefreshCcw, Search, Package,
  ChevronLeft, ChevronRight, Globe, Server, Smartphone,
  Monitor, Cpu, Code, HelpCircle, X, Building2, Tag,
  ChevronDown, Check, Filter,
} from 'lucide-react';
import { productsApi } from '../api/client';
import { useNavigate } from 'react-router-dom';

// ─── Constants ────

const CATEGORIES = [
  { value: 'ERP', label: 'ERP', icon: Server, color: 'text-[var(--warning)]', bg: 'bg-orange-500/10' },
  { value: 'WEB', label: 'Web', icon: Globe, color: 'text-[var(--info)]', bg: 'bg-blue-500/10' },
  { value: 'MOBILE', label: 'Mobile', icon: Smartphone, color: 'text-[var(--success)]', bg: 'bg-[var(--success)]/8' },
  { value: 'API', label: 'API', icon: Code, color: 'text-violet-400', bg: 'bg-violet-500/10' },
  { value: 'DESKTOP', label: 'Desktop', icon: Monitor, color: 'text-[var(--info)]', bg: 'bg-cyan-500/10' },
  { value: 'HARDWARE', label: 'Hardware', icon: Cpu, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  { value: 'OTHER', label: 'Прочее', icon: HelpCircle, color: 'text-[var(--text-primary)]/50', bg: 'bg-[var(--hover-2)]' },
] as const;

const STATUSES = [
  { value: 'active', label: 'Активный', dot: 'bg-emerald-400', color: 'text-[var(--success)]' },
  { value: 'beta', label: 'Бета', dot: 'bg-blue-400', color: 'text-[var(--info)]' },
  { value: 'deprecated', label: 'Устаревший', dot: 'bg-[var(--hover-1)]', color: 'text-[var(--text-primary)]/40' },
] as const;

const catMeta = (v: string) => CATEGORIES.find(c => c.value === v);
const statusMeta = (v: string) => STATUSES.find(s => s.value === v);
const statusLabel = (v: string) => statusMeta(v)?.label ?? v;
const statusDot = (s: string) => statusMeta(s)?.dot ?? 'bg-[var(--hover-1)]';

const ATTRIBUTE_LABELS: Record<string, string> = {
  license_type: 'Лицензия', environment: 'Среда', db_connection_ref: 'Подключение к БД',
  modules_enabled: 'Модули', max_concurrent_users: 'Макс. пользователей',
  integration_points: 'Интеграции', backup_policy_ref: 'Политика бэкапов',
  base_url: 'URL', admin_url: 'Админ-панель', hosting_provider: 'Хостинг',
  tech_stack: 'Стек', ssl_expiry_date: 'SSL до', cdn_enabled: 'CDN',
  cms_or_platform: 'Платформа', platform: 'Платформа', app_store_url: 'App Store',
  google_play_url: 'Google Play', min_os_version: 'Мин. ОС', sdk_framework: 'Фреймворк',
  push_provider: 'Push', backend_api_version: 'API версия', swagger_url: 'Swagger',
  auth_method: 'Авторизация', rate_limit: 'Rate Limit', versioning_strategy: 'Версионирование',
  webhook_endpoints: 'Webhooks', health_check_url: 'Health Check', data_format: 'Формат',
  os_compatibility: 'ОС', architecture: 'Архитектура', default_install_path: 'Путь установки',
  runtime_dependencies: 'Зависимости', auto_update_enabled: 'Автообновление',
  distribution_method: 'Дистрибуция', model_sku: 'Модель', firmware_version: 'Прошивка',
  network_config: 'Сеть', physical_location: 'Расположение', warranty_expiry: 'Гарантия до',
  maintenance_contract_ref: 'Договор ТО', monitoring_agent: 'Мониторинг',
  serial_prefix_pattern: 'Серийный №', notes: 'Заметки', support_group: 'Поддержка',
};

const getAttrLabel = (k: string) => ATTRIBUTE_LABELS[k] || k.replace(/_/g, ' ');
const formatAttrValue = (v: any): string => {
  if (v === true) return 'Да';
  if (v === false) return 'Нет';
  if (Array.isArray(v)) return v.join(', ');
  return String(v);
};

// ─── Filter Dropdown ───

interface FilterOption { value: string; label: string; icon?: React.ReactNode; dot?: string; }

function FilterDropdown({
  value, onChange, options, placeholder, icon,
}: {
  value: string;
  onChange: (v: string) => void;
  options: FilterOption[];
  placeholder: string;
  icon: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [openUp, setOpenUp] = useState(false);
  const [alignRight, setAlignRight] = useState(false);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    setOpenUp(window.innerHeight - rect.bottom < 260);
    setAlignRight(window.innerWidth - rect.left < 220);
  }, [open]);

  const selected = options.find(o => o.value === value);

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={btnRef}
        type="button"
        onClick={() => setOpen(!open)}
        className={`
          flex items-center gap-2 px-3.5 py-2.5 rounded-xl border text-base
          transition-all whitespace-nowrap cursor-pointer
          ${open
            ? 'bg-[var(--hover-2)] border-[var(--accent)]/30 text-[var(--text-primary)]'
            : value
              ? 'bg-[var(--hover-2)] border-[var(--border-color)] text-[var(--text-primary)]/90'
              : 'bg-[var(--hover-1)] border-[var(--border-color)] text-[var(--text-primary)]/50 hover:border-[var(--border-color)] hover:text-[var(--text-primary)]/70'
          }
        `}
      >
        <span className={value ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]/40'}>{icon}</span>
        <span>{selected ? selected.label : placeholder}</span>
        {value ? (
          <span
            onClick={e => { e.stopPropagation(); onChange(''); setOpen(false); }}
            className="ml-1 p-0.5 rounded-md hover:bg-[var(--hover-1)] text-[var(--text-primary)]/30 hover:text-[var(--text-primary)]/60 cursor-pointer transition-colors"
          >
            <X size={14} />
          </span>
        ) : (
          <ChevronDown size={16} className={`text-[var(--text-primary)]/30 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        )}
      </button>

      {open && (
        <div
          className={`
            absolute z-[100]             min-w-[200px] w-max bg-[var(--bg-card)] border border-[var(--border-color)]
            rounded-xl overflow-hidden
            ${openUp ? 'bottom-full mb-2' : 'top-full mt-2'}
            ${alignRight ? 'right-0' : 'left-0'}
          `}
          style={{ boxShadow: 'var(--shadow-lg)' }}
        >
          <div className="py-1.5 max-h-[300px] overflow-y-auto">
            <button
              type="button"
              onClick={() => { onChange(''); setOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left text-base transition-colors ${!value ? 'bg-[var(--accent-soft)] text-[var(--text-primary)]' : 'text-[var(--text-primary)]/60 hover:bg-[var(--hover-1)]'
                }`}
            >
              {!value ? <Check size={16} className="text-[var(--accent)] flex-shrink-0" /> : <span className="w-4 flex-shrink-0" />}
              <span>{placeholder}</span>
            </button>
            <div className="h-px bg-[var(--hover-2)] mx-3 my-1" />
            {options.map(opt => {
              const active = opt.value === value;
              return (
                <button
                  type="button"
                  key={opt.value}
                  onClick={() => { onChange(opt.value); setOpen(false); }}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left text-base transition-colors ${active ? 'bg-[var(--accent-soft)] text-[var(--text-primary)]' : 'text-[var(--text-primary)]/70 hover:bg-[var(--hover-1)]'
                    }`}
                >
                  {active ? <Check size={16} className="text-[var(--accent)] flex-shrink-0" /> : <span className="w-4 flex-shrink-0" />}
                  <span className="flex items-center gap-2.5">
                    {opt.dot && <span className={`w-2.5 h-2.5 rounded-full ${opt.dot}`} />}
                    {opt.icon}
                    {opt.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Active Filters ────

function ActiveFilters({
  category, status, onClearCategory, onClearStatus, onClearAll,
}: {
  category: string; status: string;
  onClearCategory: () => void; onClearStatus: () => void; onClearAll: () => void;
}) {
  if (!category && !status) return null;
  const catInfo = catMeta(category);
  const sInfo = statusMeta(status);

  return (
    <div className="flex items-center gap-2.5 flex-wrap">
      <span className="text-base text-[var(--text-primary)]/40 flex items-center gap-1.5">
        <Filter size={14} /> Фильтры:
      </span>
      {category && catInfo && (
        <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg ${catInfo.bg} border border-[var(--border-color)] text-base ${catInfo.color}`}>
          <catInfo.icon size={14} />
          {catInfo.label}
          <span onClick={onClearCategory} className="ml-0.5 p-0.5 rounded hover:bg-[var(--hover-1)] text-[var(--text-primary)]/30 hover:text-[var(--text-primary)]/60 cursor-pointer transition-colors">
            <X size={12} />
          </span>
        </span>
      )}
      {status && sInfo && (
        <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--hover-2)] border border-[var(--border-color)] text-base text-[var(--text-primary)]/80">
          <span className={`w-2.5 h-2.5 rounded-full ${sInfo.dot}`} />
          {sInfo.label}
          <span onClick={onClearStatus} className="ml-0.5 p-0.5 rounded hover:bg-[var(--hover-1)] text-[var(--text-primary)]/30 hover:text-[var(--text-primary)]/60 cursor-pointer transition-colors">
            <X size={12} />
          </span>
        </span>
      )}
      <button onClick={onClearAll} className="text-base text-[var(--accent)]/60 hover:text-[var(--accent)] transition-colors ml-1">
        Сбросить
      </button>
    </div>
  );
}

// ─── Product Row ──

const ProductRow = ({ product, onClick }: { product: any; onClick: () => void }) => {
  const cat = catMeta(product.category);
  const Icon = cat?.icon || Package;
  const sInfo = statusMeta(product.status);

  const truncate = (text: string, max = 60) =>
    text.length <= max ? text : text.slice(0, max) + '...';

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 px-5 py-4 text-left rounded-xl
                 hover:bg-[var(--hover-1)] active:bg-[var(--hover-2)] transition-colors duration-100 group"
    >
      <div className={`flex-shrink-0 w-10 h-10 rounded-xl ${cat?.bg || 'bg-[var(--hover-2)]'}
                      flex items-center justify-center ${cat?.color || 'text-[var(--text-primary)]/40'}
                      group-hover:scale-105 transition-transform`}>
        <Icon size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-base text-[var(--text-primary)] font-medium truncate block">
          {product.display_name || product.name}
        </span>
        {product.description && (
          <p className="text-base text-[var(--text-primary)]/40 mt-0.5 leading-snug">
            {truncate(product.description)}
          </p>
        )}
      </div>
      <div className="flex items-center gap-5 flex-shrink-0">
        <span className="text-base text-[var(--text-primary)]/50 hidden md:block w-[110px] truncate text-right">{product.vendor}</span>
        <span className="text-base text-[var(--text-primary)]/30 hidden lg:block w-[70px] text-right font-mono">
          {product.version ? `v${product.version}` : '—'}
        </span>
        <span className={`text-base px-2.5 py-1 rounded-lg ${cat?.bg || 'bg-[var(--hover-2)]'} ${cat?.color || 'text-[var(--text-primary)]/50'} hidden sm:block w-[90px] text-center`}>
          {cat?.label || product.category}
        </span>
        <div className="flex items-center gap-2 w-[100px] justify-end">
          <div className={`w-2 h-2 rounded-full ${statusDot(product.status)}`} />
          <span className={`text-base ${sInfo?.color || 'text-[var(--text-primary)]/40'}`}>{statusLabel(product.status)}</span>
        </div>
      </div>
    </button>
  );
};

// ─── Product Modal 

const ProductModal = ({ product, onClose }: { product: any; onClose: () => void }) => {
  const cat = catMeta(product.category);
  const Icon = cat?.icon || Package;
  const sInfo = statusMeta(product.status);
  const attrEntries = Object.entries(product.attributes || {}).filter(
    ([, v]) => v !== null && v !== '' && !(Array.isArray(v) && (v as any[]).length === 0)
  );

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', h);
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', h); document.body.style.overflow = ''; };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div
        className="relative w-full max-w-2xl max-h-[85vh] flex flex-col
                   bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl overflow-hidden"
        style={{ boxShadow: 'var(--shadow-lg)' }}
      >
        <div className="flex items-center justify-between gap-4 px-6 py-5 border-b border-[var(--border-color)] flex-shrink-0 bg-[var(--hover-1)]">
          <div className="flex items-center gap-4 min-w-0">
            <div className={`w-12 h-12 rounded-xl ${cat?.bg || 'bg-[var(--hover-2)]'} flex items-center justify-center ${cat?.color || 'text-[var(--text-primary)]/40'} flex-shrink-0`}>
              <Icon size={22} />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-[var(--text-primary)] truncate">{product.display_name || product.name}</h2>
              <p className="text-base text-[var(--text-primary)]/50 truncate">{product.vendor}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2.5 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)] transition-colors flex-shrink-0">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-6">
          <div className="flex flex-wrap gap-2.5">
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--hover-1)] text-base text-[var(--text-primary)]/60 border border-[var(--border-color)]">
              <Building2 size={16} className="text-[var(--text-primary)]/40" />{product.vendor}
            </div>
            {product.version && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--hover-1)] text-base text-[var(--text-primary)]/60 border border-[var(--border-color)] font-mono">
                <Tag size={16} className="text-[var(--text-primary)]/40" />v{product.version}
              </div>
            )}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-xl ${cat?.bg || 'bg-[var(--hover-1)]'} text-base ${cat?.color || 'text-[var(--text-primary)]/60'} border border-[var(--border-color)]`}>
              {cat && <cat.icon size={16} />}{cat?.label || product.category}
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--hover-1)] text-base border border-[var(--border-color)]">
              <div className={`w-2.5 h-2.5 rounded-full ${statusDot(product.status)}`} />
              <span className={sInfo?.color || 'text-[var(--text-primary)]/50'}>{statusLabel(product.status)}</span>
            </div>
          </div>

          {product.description && (
            <div>
              <div className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-3 font-semibold">Описание</div>
              <p className="text-base text-[var(--text-primary)]/70 leading-relaxed whitespace-pre-wrap">{product.description}</p>
            </div>
          )}

          {attrEntries.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-widest text-[var(--text-primary)]/30 mb-3 font-semibold">Характеристики</div>
              <div className="rounded-xl border border-[var(--border-color)] divide-y divide-[var(--border-color)] bg-[var(--hover-1)]">
                {attrEntries.map(([key, value]) => (
                  <div key={key} className="flex items-start gap-4 px-5 py-3.5">
                    <span className="text-base text-[var(--text-primary)]/40 w-[150px] flex-shrink-0 pt-0.5">{getAttrLabel(key)}</span>
                    <span className="text-base text-[var(--text-primary)]/80 break-words min-w-0">{formatAttrValue(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!product.description && attrEntries.length === 0 && (
            <div className="text-center py-12 text-[var(--text-primary)]/30 text-base">Нет дополнительной информации</div>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── Main ─────────

export default function ProductsPage() {
  const navigate = useNavigate();

  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await productsApi.getProducts({
        page, size: 30,
        category: filterCategory || undefined,
        status: filterStatus || undefined,
      });
      setProducts(res.items);
      setTotalPages(res.total_pages);
    } catch {
      setError('Не удалось загрузить продукты');
    } finally {
      setLoading(false);
    }
  }, [page, filterCategory, filterStatus]);

  useEffect(() => { loadProducts(); }, [loadProducts]);

  const normalizedSearch = searchQuery.trim().toLowerCase();

  const filteredProducts = useMemo(() => {
    if (!normalizedSearch) return products;
    return products.filter(p =>
      (p.display_name || p.name || '').toLowerCase().includes(normalizedSearch) ||
      (p.vendor || '').toLowerCase().includes(normalizedSearch) ||
      (p.description || '').toLowerCase().includes(normalizedSearch)
    );
  }, [products, normalizedSearch]);

  const categoryOptions: FilterOption[] = CATEGORIES.map(c => ({
    value: c.value, label: c.label, icon: <c.icon size={16} className={c.color} />,
  }));
  const statusOptions: FilterOption[] = STATUSES.map(s => ({
    value: s.value, label: s.label, dot: s.dot,
  }));

  return (
    <div className="space-y-6 animate-in fade-in duration-500">

      {/* ── Header ── */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)] mb-1.5">Продукты</h2>
          <p className="text-base text-[var(--text-primary)]/50">Справочник ПО и оборудования</p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={loadProducts}
            className="p-2.5 rounded-xl hover:bg-[var(--hover-2)] text-[var(--text-primary)]/40 hover:text-[var(--text-primary)]/70 transition-colors"
            title="Обновить"
          >
            <RefreshCcw size={18} />
          </button>
          <button
            onClick={() => navigate('/products/new')}
            className="btn-primary py-4 px-8 text-base font-semibold"
          >
            <Plus size={18} />
            Добавить продукт
          </button>
        </div>
      </div>

      {/* ── Поиск + фильтры ──────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2.5">
        {/* Поиск — единый визуал */}
        <div className="relative flex-1 min-w-[220px]">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/30 pointer-events-none" />
          <input
            value={searchQuery}
            onChange={e => { setSearchQuery(e.target.value); setPage(1); }}
            placeholder="Поиск по названию, вендору..."
            className="w-full pl-10 pr-10 py-3 glass-card border border-[var(--border-color)]
                       rounded-xl text-[var(--text-primary)] text-base placeholder-[var(--text-muted)]
                       focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2 focus:ring-[var(--accent-ring)]
                       transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-md
                         text-[var(--text-primary)]/30 hover:text-[var(--text-primary)]/60 hover:bg-[var(--hover-2)] transition-colors"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <FilterDropdown
          value={filterCategory}
          onChange={v => { setFilterCategory(v); setPage(1); }}
          options={categoryOptions}
          placeholder="Категория"
          icon={<Package size={16} />}
        />
        <FilterDropdown
          value={filterStatus}
          onChange={v => { setFilterStatus(v); setPage(1); }}
          options={statusOptions}
          placeholder="Статус"
          icon={<Filter size={16} />}
        />
      </div>

      {/* ── Активные фильтры ─────────────────────────────────────────────── */}
      <ActiveFilters
        category={filterCategory} status={filterStatus}
        onClearCategory={() => { setFilterCategory(''); setPage(1); }}
        onClearStatus={() => { setFilterStatus(''); setPage(1); }}
        onClearAll={() => { setFilterCategory(''); setFilterStatus(''); setPage(1); }}
      />

      {/* ── Заголовок таблицы ────────────────────────────────────────────── */}
      <div className="flex items-center gap-4 px-5 py-2.5 text-xs uppercase
                      tracking-wider text-[var(--text-primary)]/30 border-b border-[var(--border-color)] font-semibold">
        <div className="w-10" />
        <div className="flex-1">Название</div>
        <div className="hidden md:block w-[110px] text-right">Вендор</div>
        <div className="hidden lg:block w-[70px] text-right">Версия</div>
        <div className="hidden sm:block w-[90px] text-center">Тип</div>
        <div className="w-[100px] text-right">Статус</div>
      </div>

      {/* ── Список ── */}
      {loading ? (
        <div className="flex justify-center py-24">
          <Loader2 size={24} className="animate-spin text-[var(--accent)]/50" />
        </div>
      ) : error ? (
        <div className="px-5 py-10 text-base text-[var(--accent)]">{error}</div>
      ) : filteredProducts.length === 0 ? (
        <div className="flex flex-col items-center py-24 text-[var(--text-primary)]/30">
          <Package size={40} className="mb-4 text-[var(--text-primary)]/15" />
          <p className="text-base">
            {searchQuery ? 'На текущей странице ничего не найдено' : 'Нет продуктов'}
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[var(--border-color)]">
          {filteredProducts.map(product => (
            <ProductRow key={product.id} product={product} onClick={() => setSelectedProduct(product)} />
          ))}
        </div>
      )}

      {/* ── Пагинация ────────────────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4 border-t border-[var(--border-color)]">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card border border-[var(--border-color)]
                       hover:bg-[var(--hover-2)] disabled:opacity-40 disabled:cursor-not-allowed
                       text-[var(--text-primary)] text-base transition-colors"
          >
            <ChevronLeft size={16} /> Назад
          </button>

          <div className="flex items-center gap-1.5">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
              if (pageNum > totalPages) return null;
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`w-10 h-10 rounded-xl text-base font-medium transition-colors ${pageNum === page
                      ? 'bg-[var(--accent)] text-white'
                      : 'glass-card text-[var(--text-primary)]/60 border border-[var(--border-color)] hover:bg-[var(--hover-2)]'
                    }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card border border-[var(--border-color)]
                       hover:bg-[var(--hover-2)] disabled:opacity-40 disabled:cursor-not-allowed
                       text-[var(--text-primary)] text-base transition-colors"
          >
            Вперёд <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* ── Модалка продукта ─────────────────────────────────────────────── */}
      {selectedProduct && (
        <ProductModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
      )}
    </div>
  );
}