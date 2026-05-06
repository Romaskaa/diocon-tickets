import React, { useCallback, useState } from 'react';
import {
  Loader2,
  ArrowLeft,
  ArrowRight,
  Check,
  X,
  Globe,
  Server,
  Smartphone,
  Monitor,
  Cpu,
  Code,
  HelpCircle,
  Package,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { productsApi } from '../api/client';
import { DynamicAttributesFields } from '../components/helpers/DynamicAttributesFields';
import { useToast } from '../components/ui/use-toast';

// ─── Reuse constants ──────────────────────────────────────────────────────────

const PRODUCT_CATEGORIES = [
  { value: 'ERP', label: 'ERP-система', icon: Server },
  { value: 'WEB', label: 'Веб-приложение', icon: Globe },
  { value: 'MOBILE', label: 'Мобильное приложение', icon: Smartphone },
  { value: 'API', label: 'API / Сервис', icon: Code },
  { value: 'DESKTOP', label: 'Десктоп-приложение', icon: Monitor },
  { value: 'HARDWARE', label: 'Оборудование', icon: Cpu },
  { value: 'OTHER', label: 'Прочее', icon: HelpCircle },
] as const;

const PRODUCT_STATUSES = [
  { value: 'active', label: 'Активный' },
  { value: 'beta', label: 'Бета' },
  { value: 'deprecated', label: 'Устаревший' },
] as const;

const getCategoryLabel = (v: string) =>
  PRODUCT_CATEGORIES.find((c) => c.value === v)?.label ?? v;

const getStatusLabel = (v: string) =>
  PRODUCT_STATUSES.find((s) => s.value === v)?.label ?? v;

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

const getAttrLabel = (key: string) => ATTRIBUTE_LABELS[key] || key.replace(/_/g, ' ');

const formatAttrValue = (value: any): string => {
  if (value === true) return 'Да';
  if (value === false) return 'Нет';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
};

const getInitialAttributes = (schemaResponse: any): Record<string, any> => {
  const props = schemaResponse?.schema?.properties || {};
  const result: Record<string, any> = {};
  Object.entries(props).forEach(([key, raw]: [string, any]) => {
    if (raw.anyOf) result[key] = raw.default ?? null;
    else if (raw.default !== undefined) result[key] = raw.default;
    else if (raw.type === 'boolean') result[key] = false;
    else if (raw.type === 'array') result[key] = [];
    else result[key] = null;
  });
  return result;
};

const cleanAttributes = (attrs: Record<string, any>, required: string[]): Record<string, any> => {
  const reqSet = new Set(required);
  const result: Record<string, any> = {};
  Object.entries(attrs).forEach(([key, value]) => {
    const isEmpty = value === null || value === '' || (Array.isArray(value) && value.length === 0);
    if (isEmpty && !reqSet.has(key)) return;
    result[key] = value;
  });
  return result;
};

const EMPTY_FORM = {
  name: '', vendor: '', category: '', description: '', version: '', status: 'active',
  attributes: {} as Record<string, any>,
};

const STEPS = ['Основное', 'Атрибуты', 'Проверка'];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CreateProductPage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [step, setStep] = useState(0);
  const [creating, setCreating] = useState(false);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [schema, setSchema] = useState<any | null>(null);
  const [form, setForm] = useState({ ...EMPTY_FORM });

  const updateForm = (key: string, value: any) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const updateAttribute = (key: string, value: any) =>
    setForm((prev) => ({
      ...prev,
      attributes: { ...prev.attributes, [key]: value },
    }));

  const handleCategoryChange = useCallback(async (category: string) => {
    setForm((prev) => ({ ...prev, category, attributes: {} }));
    setSchema(null);
    if (!category) return;

    setSchemaLoading(true);
    try {
      const res = await productsApi.getCategorySchema(category);
      setSchema(res);
      setForm((prev) => ({ ...prev, attributes: getInitialAttributes(res) }));
    } catch {
      toast({ title: 'Ошибка', description: 'Не удалось загрузить схему', variant: 'destructive' });
    } finally {
      setSchemaLoading(false);
    }
  }, [toast]);

  const canGoNext = () => {
    if (step === 0) return !!(form.name.trim() && form.vendor.trim() && form.category);
    if (step === 1) {
      const req = schema?.schema?.required || [];
      return req.every((k: string) => {
        const v = form.attributes[k];
        return v !== null && v !== '' && v !== undefined;
      });
    }
    return true;
  };

  const handleCreate = async () => {
    setCreating(true);
    const requiredAttrs = schema?.schema?.required || [];
    try {
      await productsApi.createProduct({
        name: form.name.trim(),
        vendor: form.vendor.trim(),
        category: form.category,
        description: form.description.trim() || undefined,
        version: form.version.trim() || undefined,
        status: form.status,
        attributes: cleanAttributes(form.attributes, requiredAttrs),
      });
      toast({ title: 'Успешно', description: 'Продукт создан' });
      navigate('/products');
    } catch (err: any) {
      const message = err?.response?.data?.error?.message || 'Не удалось создать продукт';
      toast({ title: 'Ошибка', description: message, variant: 'destructive' });
    } finally {
      setCreating(false);
    }
  };

  const attrEntries = Object.entries(form.attributes || {}).filter(
    ([, v]) => v !== null && v !== '' && !(Array.isArray(v) && v.length === 0)
  );

  return (
    <div className="max-w-7xl mx-auto pb-12">
        {/* Top bar */}
        <div className="flex items-center gap-3 mb-8">
          <button
            onClick={() => navigate('/products')}
            className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] text-white/50 transition-colors"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-white">Новый продукт</h1>
            <p className="text-base text-white/40">Заполните информацию о продукте</p>
          </div>
        </div>

        {/* Stepper */}
        <div className="flex items-center gap-0 mb-8">
          {STEPS.map((label, i) => (
            <React.Fragment key={label}>
              <button
                onClick={() => { if (i < step) setStep(i); }}
                className={`flex items-center gap-2 ${
                  i <= step ? 'cursor-pointer' : 'cursor-default'
                }`}
              >
                <span
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-base font-bold transition-colors ${
                    i < step
                      ? 'bg-green-700 text-white'
                      : i === step
                        ? 'bg-red-800 text-white'
                        : 'bg-white/[0.06] text-white/25'
                  }`}
                >
                  {i < step ? <Check size={14} /> : i + 1}
                </span>
                <span className={`text-base hidden sm:inline ${
                  i === step ? 'text-white font-medium' : i < step ? 'text-white/50' : 'text-white/25'
                }`}>
                  {label}
                </span>
              </button>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-px mx-4 ${i < step ? 'bg-green-700/40' : 'bg-white/[0.06]'}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Content */}
        <div className="rounded-2xl border border-white/[0.08] bg-[#1c1c1c] p-6">
          {/* Step 0: Basic info */}
          {step === 0 && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <FormField label="Название" required>
                  <input
                    value={form.name}
                    onChange={(e) => updateForm('name', e.target.value)}
                    placeholder="Например: 1С Бухгалтерия"
                    className="w-full px-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white placeholder-white/20 focus:outline-none focus:border-red-800/60 text-base transition-colors"
                  />
                </FormField>

                <FormField label="Вендор" required>
                  <input
                    value={form.vendor}
                    onChange={(e) => updateForm('vendor', e.target.value)}
                    placeholder="Например: 1С"
                    className="w-full px-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white placeholder-white/20 focus:outline-none focus:border-red-800/60 text-base transition-colors"
                  />
                </FormField>
              </div>

              <FormField label="Категория" required>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                  {PRODUCT_CATEGORIES.map((cat) => {
                    const Icon = cat.icon;
                    const sel = form.category === cat.value;
                    return (
                      <button
                        key={cat.value}
                        onClick={() => handleCategoryChange(cat.value)}
                        className={`flex items-center gap-2.5 px-3 py-3 rounded-xl border text-left transition-all text-base ${
                          sel
                            ? 'border-red-800/50 bg-red-800/10 text-white'
                            : 'border-white/[0.06] bg-white/[0.02] text-white/50 hover:bg-white/[0.04] hover:border-white/[0.1]'
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center ${sel ? 'text-red-400' : 'text-white/30'}`}>
                          <Icon size={16} />
                        </div>
                        <span>{cat.label}</span>
                      </button>
                    );
                  })}
                </div>
              </FormField>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <FormField label="Версия">
                  <input
                    value={form.version}
                    onChange={(e) => updateForm('version', e.target.value)}
                    placeholder="3.0.1"
                    className="w-full px-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white placeholder-white/20 focus:outline-none focus:border-red-800/60 text-base transition-colors"
                  />
                </FormField>

                <FormField label="Статус">
                  <select
                    value={form.status}
                    onChange={(e) => updateForm('status', e.target.value)}
                    className="w-full px-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white text-base focus:outline-none focus:border-red-800/60 transition-colors"
                  >
                    {PRODUCT_STATUSES.map((s) => (
                      <option key={s.value} value={s.value} className="bg-[#1c1c1c]">{s.label}</option>
                    ))}
                  </select>
                </FormField>
              </div>

              <FormField label="Описание">
                <textarea
                  value={form.description}
                  onChange={(e) => updateForm('description', e.target.value)}
                  rows={3}
                  placeholder="Краткое описание..."
                  className="w-full px-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white placeholder-white/20 focus:outline-none focus:border-red-800/60 text-base transition-colors resize-none"
                />
              </FormField>
            </div>
          )}

          {/* Step 1: Attributes */}
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <h3 className="text-white font-medium">
                  Атрибуты — {getCategoryLabel(form.category)}
                </h3>
                <p className="text-base text-white/40 mt-0.5">
                  Поля со звёздочкой обязательны
                </p>
              </div>

              {schemaLoading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-white/40 text-base">
                  <Loader2 size={18} className="animate-spin" />
                  Загрузка полей...
                </div>
              ) : schema ? (
                <DynamicAttributesFields
                  schemaResponse={schema}
                  values={form.attributes}
                  onChange={updateAttribute}
                  labels={ATTRIBUTE_LABELS}
                />
              ) : (
                <div className="py-16 text-base text-white/30 text-center">
                  Схема не загружена
                </div>
              )}
            </div>
          )}

          {/* Step 2: Review */}
          {step === 2 && (
            <div className="space-y-5">
              <h3 className="text-white font-medium">Проверьте данные</h3>

              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] divide-y divide-white/[0.04]">
                <SummaryRow label="Название" value={form.name} />
                <SummaryRow label="Вендор" value={form.vendor} />
                <SummaryRow label="Категория" value={getCategoryLabel(form.category)} />
                <SummaryRow label="Статус" value={getStatusLabel(form.status)} />
                {form.version && <SummaryRow label="Версия" value={form.version} />}
                {form.description && <SummaryRow label="Описание" value={form.description} />}
              </div>

              {attrEntries.length > 0 && (
                <div>
                  <div className="text-base text-white/35 mb-2">Атрибуты</div>
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] divide-y divide-white/[0.04]">
                    {attrEntries.map(([key, value]) => (
                      <SummaryRow key={key} label={getAttrLabel(key)} value={formatAttrValue(value)} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-6">
          <div>
            {step > 0 ? (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] text-white/60 text-base transition-colors"
              >
                <ArrowLeft size={14} />
                Назад
              </button>
            ) : (
              <button
                onClick={() => navigate('/products')}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] text-white/60 text-base transition-colors"
              >
                Отмена
              </button>
            )}
          </div>

          <div>
            {step < 2 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                disabled={!canGoNext()}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-red-800 hover:bg-red-700 text-white text-base font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Далее
                <ArrowRight size={14} />
              </button>
            ) : (
              <button
                onClick={handleCreate}
                disabled={creating}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-red-800 hover:bg-red-700 text-white text-base font-medium transition-colors disabled:opacity-50"
              >
                {creating ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                Создать продукт
              </button>
            )}
          </div>
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const FormField = ({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) => (
  <div className="space-y-2">
    <label className="block text-base text-white/60">
      {label}
      {required && <span className="ml-1 text-red-400">*</span>}
    </label>
    {children}
  </div>
);

const SummaryRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-start px-4 py-3">
    <span className="text-base text-white/35 w-[130px] flex-shrink-0">{label}</span>
    <span className="text-base text-white/75 break-words">{value}</span>
  </div>
);