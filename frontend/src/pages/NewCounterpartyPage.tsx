import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, User, Briefcase, ArrowLeft, Save, Phone, Mail, MapPin,
  FileText, UserCircle, MessageSquare, Plus, Trash2, GitBranch, X,
  Loader2, Package, Server, Globe, Smartphone, Monitor, Cpu, Code, HelpCircle,
  AlertCircle, Search, Check,
} from 'lucide-react';
import { counterpartiesApi, productsApi } from '../api/client';
import type {
  CounterpartyType, CreateCounterpartyInput, ContactPersonInput, CreateBranchInput,
} from '../types';

// ─── Маска телефона ───────────────────────────────────────────────────────────

function formatPhoneInput(raw: string): string {
  // Оставляем только цифры
  let digits = raw.replace(/\D/g, '');

  // Нормализуем начало: 8 → 7, добавляем 7 если нет
  if (digits.startsWith('8')) digits = '7' + digits.slice(1);
  if (digits.length > 0 && !digits.startsWith('7')) digits = '7' + digits;

  // Ограничиваем 11 цифрами
  digits = digits.slice(0, 11);

  // Форматируем
  if (digits.length === 0) return '';
  if (digits.length <= 1) return '+7';
  if (digits.length <= 4) return `+7 (${digits.slice(1)}`;
  if (digits.length <= 7) return `+7 (${digits.slice(1, 4)}) ${digits.slice(4)}`;
  if (digits.length <= 9) return `+7 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  return `+7 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7, 9)}-${digits.slice(9, 11)}`;
}

function getPhoneDigits(formatted: string): string {
  const digits = formatted.replace(/\D/g, '');
  if (digits.startsWith('8')) return '7' + digits.slice(1);
  return digits;
}

function isPhoneComplete(formatted: string): boolean {
  return getPhoneDigits(formatted).length === 11;
}

// Хук для маски
function usePhoneMask(initial = '') {
  const [display, setDisplay] = useState(() => formatPhoneInput(initial));

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneInput(e.target.value);
    setDisplay(formatted);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    // Позволяем Backspace удалять нормально
    if (e.key === 'Backspace' && display.length > 0) {
      e.preventDefault();
      const digits = getPhoneDigits(display);
      const newDigits = digits.slice(0, -1);
      setDisplay(formatPhoneInput(newDigits));
    }
  }, [display]);

  // Значение для отправки на backend: +7XXXXXXXXXX
  const rawValue = '+' + getPhoneDigits(display);

  return { display, setDisplay, handleChange, handleKeyDown, rawValue, isComplete: isPhoneComplete(display) };
}

// ─── Парсинг ошибок backend ───────────────────────────────────────────────────

interface FieldError {
  field: string;
  message: string;
}

function parseBackendErrors(err: any): { general: string; fields: FieldError[] } {
  const data = err?.response?.data;
  const status = err?.response?.status;

  if (!data) {
    return { general: 'Произошла неизвестная ошибка', fields: [] };
  }

  const detail = data.detail;

  // Pydantic validation errors (422)
  if (status === 422 && Array.isArray(detail)) {
    const fields: FieldError[] = detail.map((e: any) => {
      const loc = e.loc || [];
      // loc обычно: ["body", "field_name"] или ["body", "contact_persons", 0, "phone"]
      const fieldPath = loc.filter((l: any) => l !== 'body').join('.');
      return {
        field: fieldPath || 'unknown',
        message: e.msg || JSON.stringify(e),
      };
    });

    const general = fields.length > 0
      ? 'Проверьте правильность заполнения полей'
      : 'Ошибка валидации';

    return { general, fields };
  }

  // Domain errors (400) — строка
  if (typeof detail === 'string') {
    // Пытаемся определить поле по ключевым словам
    const fields: FieldError[] = [];
    const lower = detail.toLowerCase();

    if (lower.includes('inn') || lower.includes('инн'))  fields.push({ field: 'inn', message: detail });
    if (lower.includes('kpp') || lower.includes('кпп'))  fields.push({ field: 'kpp', message: detail });
    if (lower.includes('okpo') || lower.includes('окпо')) fields.push({ field: 'okpo', message: detail });
    if (lower.includes('phone') || lower.includes('телефон')) fields.push({ field: 'phone', message: detail });
    if (lower.includes('email'))                         fields.push({ field: 'email', message: detail });

    return { general: detail, fields };
  }

  // Массив строк
  if (Array.isArray(detail)) {
    return {
      general: detail.map((x: any) => typeof x === 'string' ? x : x.msg || JSON.stringify(x)).join('; '),
      fields: [],
    };
  }

  return { general: JSON.stringify(detail), fields: [] };
}

// ─── Inline FieldError component ──────────────────────────────────────────────

function FieldErrorMsg({ fieldErrors, fieldName }: { fieldErrors: FieldError[]; fieldName: string }) {
  const errors = fieldErrors.filter(e =>
    e.field === fieldName ||
    e.field.startsWith(fieldName + '.') ||
    e.field.endsWith('.' + fieldName)
  );
  if (errors.length === 0) return null;
  return (
    <div className="mt-1.5 flex items-start gap-1.5">
      <AlertCircle className="w-3.5 h-3.5 text-red-400 mt-0.5 flex-shrink-0" />
      <p className="text-sm text-red-400">{errors.map(e => e.message).join('; ')}</p>
    </div>
  );
}

function hasFieldError(fieldErrors: FieldError[], fieldName: string): boolean {
  return fieldErrors.some(e =>
    e.field === fieldName ||
    e.field.startsWith(fieldName + '.') ||
    e.field.endsWith('.' + fieldName)
  );
}

// ─── Константы ────────────────────────────────────────────────────────────────

const COUNTERPARTY_TYPES: { value: CounterpartyType; label: string; desc: string; icon: React.ReactNode }[] = [
  { value: 'Юридическое лицо', label: 'Юридическое лицо', desc: 'ИНН 10 цифр, КПП обязателен', icon: <Building2 className="w-7 h-7" /> },
  { value: 'Физическое лицо',  label: 'Физическое лицо',  desc: 'ИНН 12 цифр, КПП не нужен',   icon: <User className="w-7 h-7" /> },
  { value: 'Индивидуальный предприниматель',               label: 'Индивидуальный предприниматель', desc: 'ИНН 12 цифр, КПП не нужен', icon: <Briefcase className="w-7 h-7" /> },
];

const PRODUCT_CATEGORIES = [
  { value: 'ERP', label: 'ERP', icon: Server },
  { value: 'WEB', label: 'Web', icon: Globe },
  { value: 'MOBILE', label: 'Mobile', icon: Smartphone },
  { value: 'API', label: 'API', icon: Code },
  { value: 'DESKTOP', label: 'Desktop', icon: Monitor },
  { value: 'HARDWARE', label: 'Hardware', icon: Cpu },
  { value: 'OTHER', label: 'Прочее', icon: HelpCircle },
] as const;

const ENVIRONMENTS = [
  { value: 'production',  label: 'Production' },
  { value: 'staging',     label: 'Staging' },
  { value: 'testing',     label: 'Testing' },
  { value: 'development', label: 'Development' },
] as const;

const catMeta = (v: string) => PRODUCT_CATEGORIES.find(c => c.value === v);
const envLabel = (v: string) => ENVIRONMENTS.find(e => e.value === v)?.label ?? v;

const envBadgeClass = (e: string) => {
  if (e === 'production')  return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
  if (e === 'staging')     return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
  if (e === 'testing')     return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
  if (e === 'development') return 'bg-purple-500/10 text-purple-400 border border-purple-500/20';
  return 'bg-white/5 text-white/40 border border-white/10';
};

// Валидация
function getInnMaxLength(type: CounterpartyType) { return type === 'Юридическое лицо' ? 10 : 12; }
function getInnPlaceholder(type: CounterpartyType) { return type === 'Юридическое лицо' ? '10 цифр' : '12 цифр'; }
function isKppAllowed(type: CounterpartyType) { return type === 'Юридическое лицо'; }
function isKppRequired(type: CounterpartyType) { return type === 'Юридическое лицо'; }

const emptyContactPerson = (): ContactPersonInput => ({
  first_name: '', last_name: '', middle_name: '', phone: '', email: '',
  messengers: { telegram: '', vk: '' },
});

interface BranchFormData {
  name: string; legal_name: string; kpp: string;
  okpo: string; phone: string; email: string; address: string;
}
const emptyBranch = (): BranchFormData => ({
  name: '', legal_name: '', kpp: '', okpo: '', phone: '', email: '', address: '',
});

interface LinkedProduct {
  product: any;
  environment: string;
  is_primary: boolean;
}

// ─── Input стили ──────────────────────────────────────────────────────────────

const inputCls = (hasError = false) =>
  `w-full px-4 py-3.5 text-base bg-white/[0.04] border rounded-xl text-white
   placeholder-white/30 focus:outline-none focus:ring-2 transition-all ${
    hasError
      ? 'border-red-500/60 focus:border-red-500 focus:ring-red-500/20'
      : 'border-white/[0.08] focus:border-red-500/40 focus:ring-red-500/10'
  }`;

const labelCls = 'block text-base font-medium text-white/80 mb-2';

// ─── Компонент ────────────────────────────────────────────────────────────────

export default function NewCounterpartyPage() {
  const navigate = useNavigate();

  const [isLoading, setIsLoading]     = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldError[]>([]);
  const [step, setStep]               = useState(1);

  // Шаг 1
  const [formData, setFormData] = useState<CreateCounterpartyInput>({
    counterparty_type: 'Юридическое лицо',
    name: '', legal_name: '', inn: '', kpp: '', okpo: '',
    phone: '', email: '', address: '',
  });

  // Телефон компании — с маской
  const companyPhone = usePhoneMask(formData.phone);

  // Шаг 3: контактные лица
  const [contactPersons, setContactPersons] = useState<ContactPersonInput[]>([]);
  const [includeContacts, setIncludeContacts] = useState(false);

  // Шаг 4: филиалы
  const [branches, setBranches] = useState<BranchFormData[]>([]);
  const [includeBranches, setIncludeBranches] = useState(false);

  // Шаг 5: продукты
  const [linkedProducts, setLinkedProducts] = useState<LinkedProduct[]>([]);
  const [showProductForm, setShowProductForm] = useState(false);

  // Продукты — полный список + фильтр
  const [allProducts, setAllProducts] = useState<any[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [productFilter, setProductFilter] = useState('');
  const [selectedProductToLink, setSelectedProductToLink] = useState<any | null>(null);
  const [productEnv, setProductEnv] = useState('production');
  const [productIsPrimary, setProductIsPrimary] = useState(false);

  // Загрузка продуктов при открытии формы
  useEffect(() => {
    if (showProductForm && allProducts.length === 0) {
      setLoadingProducts(true);
      productsApi.getProducts({ page: 1, size: 15 })
        .then(res => setAllProducts(res.items ?? []))
        .catch(() => {})
        .finally(() => setLoadingProducts(false));
    }
  }, [showProductForm]);

  // Фильтрация продуктов по запросу
  const filteredProducts = productFilter.trim()
    ? allProducts.filter(p => {
        const q = productFilter.toLowerCase();
        return (
          (p.display_name || p.name || '').toLowerCase().includes(q) ||
          (p.vendor || '').toLowerCase().includes(q)
        );
      })
    : allProducts;

  // Исключаем уже добавленные
  const availableProducts = filteredProducts.filter(
    p => !linkedProducts.some(lp => lp.product.id === p.id)
  );

  // ─── Handlers ────────────────────────────────────────────────────────────

  const clearErrors = () => { setGeneralError(null); setFieldErrors([]); };

  const handleTypeChange = (type: CounterpartyType) => {
    clearErrors();
    setFormData({
      ...formData,
      counterparty_type: type,
      inn: '',
      kpp: isKppAllowed(type) ? formData.kpp : '',
    });
    if (type !== 'Юридическое лицо') { setIncludeBranches(false); setBranches([]); }
  };

  const addContactPerson = () => setContactPersons([...contactPersons, emptyContactPerson()]);
  const removeContactPerson = (i: number) => setContactPersons(contactPersons.filter((_, idx) => idx !== i));
  const updateContactPerson = (i: number, v: ContactPersonInput) =>
    setContactPersons(contactPersons.map((cp, idx) => idx === i ? v : cp));

  const addBranch = () => setBranches([...branches, emptyBranch()]);
  const removeBranch = (i: number) => setBranches(branches.filter((_, idx) => idx !== i));
  const updateBranch = (i: number, v: BranchFormData) =>
    setBranches(branches.map((b, idx) => idx === i ? v : b));

  const addLinkedProduct = () => {
    if (!selectedProductToLink) return;
    setLinkedProducts([...linkedProducts, {
      product: selectedProductToLink, environment: productEnv, is_primary: productIsPrimary,
    }]);
    setSelectedProductToLink(null);
    setProductFilter('');
    setProductEnv('production');
    setProductIsPrimary(false);
  };

  const removeLinkedProduct = (i: number) =>
    setLinkedProducts(linkedProducts.filter((_, idx) => idx !== i));

  // ─── Submit ──────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    setIsLoading(true);
    clearErrors();

    try {
      const payload: any = {
        counterparty_type: formData.counterparty_type,
        name: formData.name.trim(),
        legal_name: formData.legal_name.trim(),
        inn: formData.inn,
        phone: companyPhone.rawValue,
        email: formData.email.trim(),
      };
      if (isKppAllowed(formData.counterparty_type) && formData.kpp) payload.kpp = formData.kpp;
      if (formData.okpo)    payload.okpo    = formData.okpo;
      if (formData.address?.trim()) payload.address = formData.address.trim();

      if (includeContacts && contactPersons.length > 0) {
        payload.contact_persons = contactPersons.map(cp => {
          const p: any = { first_name: cp.first_name, last_name: cp.last_name };
          if (cp.middle_name) p.middle_name = cp.middle_name;
          if (cp.phone) p.phone = cp.phone;
          if (cp.email) p.email = cp.email;
          const m: any = {};
          if (cp.messengers?.telegram) m.telegram = cp.messengers.telegram;
          if (cp.messengers?.vk) m.vk = cp.messengers.vk;
          if (Object.keys(m).length) p.messengers = m;
          return p;
        });
      }

      const created = await counterpartiesApi.create(payload);

      // Филиалы
      if (includeBranches && branches.length > 0) {
        for (const b of branches) {
          const bp: CreateBranchInput = {
            name: b.name, legal_name: b.legal_name, kpp: b.kpp,
            phone: b.phone, email: b.email,
          };
          if (b.okpo) bp.okpo = b.okpo;
          if (b.address) bp.address = b.address;
          await counterpartiesApi.createBranch(created.id, bp);
        }
      }

      // Продукты
      if (linkedProducts.length > 0) {
        for (const lp of linkedProducts) {
          await counterpartiesApi.linkProduct(created.id, {
            product_id: lp.product.id,
            environment: lp.environment,
            is_primary: lp.is_primary,
          });
        }
      }

      navigate('/counterparties');
    } catch (err: any) {
      const parsed = parseBackendErrors(err);
      setGeneralError(parsed.general);
      setFieldErrors(parsed.fields);

      // Если ошибки в полях шага 1 — перекинуть на шаг 1
      const step1Fields = ['inn', 'kpp', 'okpo', 'name', 'legal_name', 'counterparty_type'];
      const step2Fields = ['phone', 'email', 'address'];
      if (parsed.fields.some(f => step1Fields.includes(f.field))) setStep(1);
      else if (parsed.fields.some(f => step2Fields.includes(f.field))) setStep(2);
    } finally {
      setIsLoading(false);
    }
  };

  // ─── Валидация ────────────────────────────────────────────────────────────

  const innLength  = getInnMaxLength(formData.counterparty_type);
  const isInnValid = formData.inn.length === innLength && /^\d+$/.test(formData.inn);
  const isKppValid = isKppRequired(formData.counterparty_type)
    ? !!formData.kpp && formData.kpp.length === 9 && /^\d+$/.test(formData.kpp)
    : true;
  const isStep1Valid = !!(formData.counterparty_type && formData.name.trim() && formData.legal_name.trim() && isInnValid && isKppValid);
  const isStep2Valid = companyPhone.isComplete && !!formData.email.trim();

  const totalSteps = formData.counterparty_type === 'Юридическое лицо' ? 5 : 4;
  const productsStep = formData.counterparty_type === 'Юридическое лицо' ? 5 : 4;
  const productsPrevStep = formData.counterparty_type === 'Юридическое лицо' ? 4 : 3;

  const stepLabels: Record<number, string> = {
    1: 'Основное', 2: 'Контакты', 3: 'Контактные лица',
    4: formData.counterparty_type === 'Юридическое лицо' ? 'Филиалы' : 'Продукты',
    5: 'Продукты',
  };

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="max-w-5xl mx-auto pb-12 space-y-8">

      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/counterparties')}
                className="p-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06]
                           text-white/60 hover:text-white transition-all">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Новый контрагент</h1>
          <p className="text-base text-white/50 mt-0.5">Заполните данные контрагента</p>
        </div>
      </div>

      {/* Progress */}
      <div className="flex items-center justify-center gap-2 flex-wrap">
        {Array.from({ length: totalSteps }, (_, i) => i + 1).map(s => (
          <div key={s} className="flex items-center gap-2">
            <button
              onClick={() => { if (s < step) setStep(s); }}
              disabled={s > step}
              className={`w-9 h-9 rounded-full flex items-center justify-center text-base font-semibold transition-all ${
                step === s
                  ? 'bg-red-700 text-white shadow-lg shadow-red-900/30'
                  : step > s
                    ? 'bg-emerald-600 text-white cursor-pointer hover:bg-emerald-500'
                    : 'bg-white/[0.06] text-white/30'
              }`}
            >
              {step > s ? <Check className="w-4 h-4" /> : s}
            </button>
            <span className={`text-sm font-medium hidden sm:block ${step >= s ? 'text-white/70' : 'text-white/30'}`}>
              {stepLabels[s]}
            </span>
            {s < totalSteps && <div className="w-6 h-0.5 bg-white/[0.08]" />}
          </div>
        ))}
      </div>

      {/* Global Error */}
      {generalError && (
        <div className="p-4 bg-red-900/30 border border-red-700/40 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-base text-red-300 font-medium">{generalError}</p>
            {fieldErrors.length > 0 && (
              <ul className="mt-2 space-y-1">
                {fieldErrors.map((fe, i) => (
                  <li key={i} className="text-sm text-red-400/80">
                    <span className="text-red-400 font-mono">{fe.field}</span>: {fe.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* ═══ Шаг 1: Основное ═══ */}
      {step === 1 && (
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 space-y-7">

          {/* Тип */}
          <div>
            <p className={labelCls}>Тип контрагента</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {COUNTERPARTY_TYPES.map(type => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => handleTypeChange(type.value)}
                  className={`p-5 rounded-xl border-2 text-left transition-all ${
                    formData.counterparty_type === type.value
                      ? 'border-red-500/60 bg-red-500/[0.06]'
                      : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]'
                  }`}
                >
                  <div className={`mb-2 ${formData.counterparty_type === type.value ? 'text-red-400' : 'text-white/40'}`}>
                    {type.icon}
                  </div>
                  <p className={`text-base font-semibold ${formData.counterparty_type === type.value ? 'text-white' : 'text-white/70'}`}>
                    {type.label}
                  </p>
                  <p className="text-sm text-white/30 mt-1">{type.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Название */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className={labelCls}>Краткое название <span className="text-red-400">*</span></label>
              <input type="text" value={formData.name}
                     onChange={e => { clearErrors(); setFormData({ ...formData, name: e.target.value }); }}
                     placeholder={formData.counterparty_type === 'Физическое лицо' ? 'Иванов И.И.' : formData.counterparty_type === 'Индивидуальный предприниматель' ? 'ИП Иванов' : 'ООО Компания'}
                     className={inputCls(hasFieldError(fieldErrors, 'name'))} />
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="name" />
            </div>
            <div>
              <label className={labelCls}>Полное наименование <span className="text-red-400">*</span></label>
              <input type="text" value={formData.legal_name}
                     onChange={e => { clearErrors(); setFormData({ ...formData, legal_name: e.target.value }); }}
                     placeholder={formData.counterparty_type === 'Юридическое лицо' ? 'ООО «Компания»' : 'Полное ФИО'}
                     className={inputCls(hasFieldError(fieldErrors, 'legal_name'))} />
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="legal_name" />
            </div>
          </div>

          {/* Реквизиты */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div>
              <label className={labelCls}>ИНН <span className="text-red-400">*</span></label>
              <input type="text" value={formData.inn}
                     onChange={e => {
                       clearErrors();
                       const val = e.target.value.replace(/\D/g, '');
                       if (val.length <= innLength) setFormData({ ...formData, inn: val });
                     }}
                     placeholder={getInnPlaceholder(formData.counterparty_type)}
                     maxLength={innLength}
                     className={inputCls(!isInnValid && formData.inn.length > 0 || hasFieldError(fieldErrors, 'inn'))} />
              {formData.inn && !isInnValid && (
                <p className="mt-1.5 text-sm text-amber-400">ИНН: {formData.inn.length}/{innLength} цифр</p>
              )}
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="inn" />
            </div>

            {isKppAllowed(formData.counterparty_type) && (
              <div>
                <label className={labelCls}>КПП <span className="text-red-400">*</span></label>
                <input type="text" value={formData.kpp}
                       onChange={e => {
                         clearErrors();
                         const val = e.target.value.replace(/\D/g, '');
                         if (val.length <= 9) setFormData({ ...formData, kpp: val });
                       }}
                       placeholder="9 цифр" maxLength={9}
                       className={inputCls((!!formData.kpp && formData.kpp.length !== 9) || hasFieldError(fieldErrors, 'kpp'))} />
                {formData.kpp && formData.kpp.length !== 9 && (
                  <p className="mt-1.5 text-sm text-amber-400">КПП: {formData.kpp.length}/9 цифр</p>
                )}
                <FieldErrorMsg fieldErrors={fieldErrors} fieldName="kpp" />
              </div>
            )}

            <div>
              <label className={labelCls}>ОКПО</label>
              <input type="text" value={formData.okpo}
                     onChange={e => {
                       clearErrors();
                       const val = e.target.value.replace(/\D/g, '');
                       if (val.length <= 10) setFormData({ ...formData, okpo: val });
                     }}
                     placeholder="8–10 цифр" maxLength={10}
                     className={inputCls(hasFieldError(fieldErrors, 'okpo'))} />
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="okpo" />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button onClick={() => setStep(2)} disabled={!isStep1Valid}
                    className="px-6 py-3 text-base font-semibold text-white bg-red-800 hover:bg-red-700 rounded-xl
                               transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-red-900/30">
              Далее
            </button>
          </div>
        </div>
      )}

      {/* ═══ Шаг 2: Контакты ═══ */}
      {step === 2 && (
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className={labelCls}>
                <Phone className="w-4 h-4 inline mr-1.5 text-white/40" />
                Телефон <span className="text-red-400">*</span>
              </label>
              <input
                type="tel"
                value={companyPhone.display}
                onChange={companyPhone.handleChange}
                onKeyDown={companyPhone.handleKeyDown}
                placeholder="+7 (___) ___-__-__"
                className={inputCls(!companyPhone.isComplete && companyPhone.display.length > 3 || hasFieldError(fieldErrors, 'phone'))}
              />
              {companyPhone.display.length > 3 && !companyPhone.isComplete && (
                <p className="mt-1.5 text-sm text-amber-400">
                  Введите полный номер: +7 (XXX) XXX-XX-XX
                </p>
              )}
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="phone" />
            </div>

            <div>
              <label className={labelCls}>
                <Mail className="w-4 h-4 inline mr-1.5 text-white/40" />
                Email <span className="text-red-400">*</span>
              </label>
              <input type="email" value={formData.email}
                     onChange={e => { clearErrors(); setFormData({ ...formData, email: e.target.value }); }}
                     placeholder="info@company.ru"
                     className={inputCls(hasFieldError(fieldErrors, 'email'))} />
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="email" />
            </div>
          </div>

          <div>
            <label className={labelCls}>
              <MapPin className="w-4 h-4 inline mr-1.5 text-white/40" />
              Адрес
            </label>
            <textarea value={formData.address}
                      onChange={e => setFormData({ ...formData, address: e.target.value })}
                      placeholder="г. Москва, ул. Примерная, д. 1" rows={3}
                      className={`${inputCls()} resize-none`} />
          </div>

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(1)}
                    className="px-6 py-3 text-base font-medium text-white/70 bg-white/[0.05] hover:bg-white/[0.08] rounded-xl transition-all">
              Назад
            </button>
            <button onClick={() => setStep(3)} disabled={!isStep2Valid}
                    className="px-6 py-3 text-base font-semibold text-white bg-red-800 hover:bg-red-700 rounded-xl
                               transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-red-900/30">
              Далее
            </button>
          </div>
        </div>
      )}

      {/* ═══ Шаг 3: Контактные лица ═══ */}
      {step === 3 && (
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between p-4 bg-white/[0.03] rounded-xl border border-white/[0.06]">
            <div className="flex items-center gap-3">
              <UserCircle className="w-6 h-6 text-white/40" />
              <div>
                <p className="text-base font-medium text-white">Контактные лица</p>
                <p className="text-sm text-white/40">Ответственные сотрудники</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                if (includeContacts) { setIncludeContacts(false); setContactPersons([]); }
                else { setIncludeContacts(true); if (!contactPersons.length) setContactPersons([emptyContactPerson()]); }
              }}
              className={`relative w-12 h-6 rounded-full transition-colors ${includeContacts ? 'bg-red-600' : 'bg-white/10'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${includeContacts ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          {includeContacts && contactPersons.map((cp, i) => (
            <div key={i} className="p-5 bg-white/[0.02] border border-white/[0.06] rounded-xl space-y-5">
              <div className="flex items-center justify-between">
                <p className="text-base font-medium text-white">Контакт #{i + 1}</p>
                {contactPersons.length > 1 && (
                  <button onClick={() => removeContactPerson(i)}
                          className="p-1.5 text-white/30 hover:text-red-400 hover:bg-white/[0.06] rounded-lg transition-all">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className={labelCls}>Фамилия <span className="text-red-400">*</span></label>
                  <input type="text" value={cp.last_name} onChange={e => updateContactPerson(i, { ...cp, last_name: e.target.value })}
                         placeholder="Иванов" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>Имя <span className="text-red-400">*</span></label>
                  <input type="text" value={cp.first_name} onChange={e => updateContactPerson(i, { ...cp, first_name: e.target.value })}
                         placeholder="Иван" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>Отчество</label>
                  <input type="text" value={cp.middle_name} onChange={e => updateContactPerson(i, { ...cp, middle_name: e.target.value })}
                         placeholder="Иванович" className={inputCls()} />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Телефон</label>
                  <input type="tel" value={cp.phone} onChange={e => updateContactPerson(i, { ...cp, phone: e.target.value })}
                         placeholder="+7 (999) 123-45-67" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>Email</label>
                  <input type="email" value={cp.email} onChange={e => updateContactPerson(i, { ...cp, email: e.target.value })}
                         placeholder="ivanov@company.ru" className={inputCls()} />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}><MessageSquare className="w-3.5 h-3.5 inline mr-1.5 text-white/40" />Telegram</label>
                  <input type="text" value={cp.messengers?.telegram || ''}
                         onChange={e => updateContactPerson(i, { ...cp, messengers: { ...cp.messengers, telegram: e.target.value } })}
                         placeholder="@username" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>VK</label>
                  <input type="text" value={cp.messengers?.vk || ''}
                         onChange={e => updateContactPerson(i, { ...cp, messengers: { ...cp.messengers, vk: e.target.value } })}
                         placeholder="vk.com/id" className={inputCls()} />
                </div>
              </div>
            </div>
          ))}

          {includeContacts && (
            <button onClick={addContactPerson}
                    className="flex items-center gap-2 px-5 py-3 text-base text-white/50 hover:text-white
                               bg-white/[0.02] hover:bg-white/[0.05] border border-dashed border-white/[0.1]
                               hover:border-white/[0.2] rounded-xl transition-all w-full justify-center">
              <Plus className="w-4 h-4" /> Добавить ещё
            </button>
          )}

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(2)}
                    className="px-6 py-3 text-base font-medium text-white/70 bg-white/[0.05] hover:bg-white/[0.08] rounded-xl transition-all">
              Назад
            </button>
            <button onClick={() => setStep(4)}
                    className="px-6 py-3 text-base font-semibold text-white bg-red-800 hover:bg-red-700 rounded-xl
                               transition-all shadow-lg shadow-red-900/30">
              Далее
            </button>
          </div>
        </div>
      )}

      {/* ═══ Шаг 4: Филиалы (юр. лицо) ═══ */}
      {step === 4 && formData.counterparty_type === 'Юридическое лицо' && (
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between p-4 bg-white/[0.03] rounded-xl border border-white/[0.06]">
            <div className="flex items-center gap-3">
              <GitBranch className="w-6 h-6 text-white/40" />
              <div>
                <p className="text-base font-medium text-white">Обособленные подразделения</p>
                <p className="text-sm text-white/40">Филиалы наследуют ИНН</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                if (includeBranches) { setIncludeBranches(false); setBranches([]); }
                else { setIncludeBranches(true); if (!branches.length) setBranches([emptyBranch()]); }
              }}
              className={`relative w-12 h-6 rounded-full transition-colors ${includeBranches ? 'bg-red-600' : 'bg-white/10'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${includeBranches ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          {includeBranches && branches.map((branch, i) => (
            <div key={i} className="p-5 bg-white/[0.02] border border-white/[0.06] rounded-xl space-y-5">
              <div className="flex items-center justify-between">
                <p className="text-base font-medium text-white flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-white/40" /> Филиал #{i + 1}
                </p>
                {branches.length > 1 && (
                  <button onClick={() => removeBranch(i)}
                          className="p-1.5 text-white/30 hover:text-red-400 hover:bg-white/[0.06] rounded-lg transition-all">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div className="px-3 py-2 bg-white/[0.03] rounded-lg border border-white/[0.06]">
                <p className="text-sm text-white/40">
                  ИНН наследуется: <span className="text-white font-mono">{formData.inn}</span>
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Название <span className="text-red-400">*</span></label>
                  <input type="text" value={branch.name} onChange={e => updateBranch(i, { ...branch, name: e.target.value })}
                         placeholder="Филиал в СПб" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>Полное наименование <span className="text-red-400">*</span></label>
                  <input type="text" value={branch.legal_name} onChange={e => updateBranch(i, { ...branch, legal_name: e.target.value })}
                         placeholder="Филиал ООО «Компания»" className={inputCls()} />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>КПП <span className="text-red-400">*</span></label>
                  <input type="text" value={branch.kpp}
                         onChange={e => { const v = e.target.value.replace(/\D/g, ''); if (v.length <= 9) updateBranch(i, { ...branch, kpp: v }); }}
                         placeholder="9 цифр" maxLength={9}
                         className={inputCls(!!branch.kpp && branch.kpp.length !== 9)} />
                  {branch.kpp && branch.kpp.length !== 9 && (
                    <p className="mt-1.5 text-sm text-amber-400">КПП: {branch.kpp.length}/9</p>
                  )}
                </div>
                <div>
                  <label className={labelCls}>ОКПО</label>
                  <input type="text" value={branch.okpo}
                         onChange={e => { const v = e.target.value.replace(/\D/g, ''); if (v.length <= 10) updateBranch(i, { ...branch, okpo: v }); }}
                         placeholder="8–10 цифр" maxLength={10} className={inputCls()} />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Телефон <span className="text-red-400">*</span></label>
                  <input type="tel" value={branch.phone} onChange={e => updateBranch(i, { ...branch, phone: e.target.value })}
                         placeholder="+7 (999) 123-45-67" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>Email <span className="text-red-400">*</span></label>
                  <input type="email" value={branch.email} onChange={e => updateBranch(i, { ...branch, email: e.target.value })}
                         placeholder="branch@company.ru" className={inputCls()} />
                </div>
              </div>

              <div>
                <label className={labelCls}>Адрес</label>
                <input type="text" value={branch.address} onChange={e => updateBranch(i, { ...branch, address: e.target.value })}
                       placeholder="г. Санкт-Петербург, ул..." className={inputCls()} />
              </div>
            </div>
          ))}

          {includeBranches && (
            <button onClick={addBranch}
                    className="flex items-center gap-2 px-5 py-3 text-base text-white/50 hover:text-white
                               bg-white/[0.02] hover:bg-white/[0.05] border border-dashed border-white/[0.1]
                               hover:border-white/[0.2] rounded-xl transition-all w-full justify-center">
              <Plus className="w-4 h-4" /> Добавить филиал
            </button>
          )}

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(3)}
                    className="px-6 py-3 text-base font-medium text-white/70 bg-white/[0.05] hover:bg-white/[0.08] rounded-xl transition-all">
              Назад
            </button>
            <button onClick={() => setStep(5)}
                    className="px-6 py-3 text-base font-semibold text-white bg-red-800 hover:bg-red-700 rounded-xl
                               transition-all shadow-lg shadow-red-900/30">
              Далее
            </button>
          </div>
        </div>
      )}

      {/* ═══ Шаг «Продукты» ═══ */}
      {step === productsStep && (
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between p-4 bg-white/[0.03] rounded-xl border border-white/[0.06]">
            <div className="flex items-center gap-3">
              <Package className="w-6 h-6 text-white/40" />
              <div>
                <p className="text-base font-medium text-white">Привязать продукты</p>
                <p className="text-sm text-white/40">ПО и оборудование</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setShowProductForm(!showProductForm)}
              className={`relative w-12 h-6 rounded-full transition-colors ${showProductForm ? 'bg-red-600' : 'bg-white/10'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${showProductForm ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          {showProductForm && (
            <div className="space-y-5">
              {/* Выбор продукта — из полного списка с фильтром */}
              <div className="p-5 bg-white/[0.02] border border-white/[0.06] rounded-xl space-y-4">
                <p className="text-base font-medium text-white">Выберите продукт</p>

                {selectedProductToLink ? (
                  <div className="flex items-center gap-3 p-3 bg-white/[0.04] border border-white/[0.08] rounded-xl">
                    {(() => {
                      const Icon = catMeta(selectedProductToLink.category)?.icon || Package;
                      return <Icon className="w-5 h-5 text-white/40 flex-shrink-0" />;
                    })()}
                    <div className="flex-1 min-w-0">
                      <p className="text-base font-medium text-white truncate">{selectedProductToLink.display_name || selectedProductToLink.name}</p>
                      <p className="text-sm text-white/40">{selectedProductToLink.vendor}</p>
                    </div>
                    <button onClick={() => setSelectedProductToLink(null)}
                            className="p-1.5 text-white/30 hover:text-red-400 transition-colors">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="relative">
                      <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 pointer-events-none" />
                      <input value={productFilter}
                             onChange={e => setProductFilter(e.target.value)}
                             placeholder="Фильтр по названию или вендору..."
                             className="w-full pl-10 pr-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl text-base text-white
                                        placeholder-white/30 focus:outline-none focus:border-red-500/40 focus:ring-2 focus:ring-red-500/10 transition-all" />
                    </div>

                    <div className="max-h-56 overflow-y-auto rounded-xl border border-white/[0.06] bg-[#161616] divide-y divide-white/[0.04]">
                      {loadingProducts ? (
                        <div className="flex justify-center py-10">
                          <Loader2 className="w-5 h-5 animate-spin text-white/20" />
                        </div>
                      ) : availableProducts.length === 0 ? (
                        <div className="py-10 text-center">
                          <Package className="w-8 h-8 mx-auto mb-2 text-white/10" />
                          <p className="text-base text-white/30">
                            {productFilter ? 'Ничего не найдено' : 'Нет продуктов'}
                          </p>
                        </div>
                      ) : (
                        availableProducts.slice(0, 30).map(p => {
  const PIcon = catMeta(p.category)?.icon || Package;
  return (
    <button 
      key={p.id} 
      onClick={() => {
        // Автоматически добавляем в список
        setLinkedProducts(prev => [...prev, {
          product: p,
          environment: productEnv,
          is_primary: productIsPrimary,
        }]);
        // Очищаем поиск
        setProductFilter('');
      }}
      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.04] transition-colors"
    >
      <PIcon className="w-4 h-4 text-white/30 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-base text-white truncate">{p.display_name || p.name}</p>
        <p className="text-sm text-white/30">{p.vendor}</p>
      </div>
    </button>
  );
})
                      )}
                    </div>
                  </>
                )}

                {/* Среда */}
                {selectedProductToLink && (
                  <>
                    <div>
                      <label className="block text-sm text-white/40 mb-2">Среда</label>
                      <div className="grid grid-cols-2 gap-2">
                        {ENVIRONMENTS.map(env => (
                          <button key={env.value} onClick={() => setProductEnv(env.value)}
                                  className={`px-3 py-2.5 rounded-xl text-base font-medium transition-all ${
                                    productEnv === env.value
                                      ? envBadgeClass(env.value)
                                      : 'border border-white/[0.06] bg-white/[0.02] text-white/40 hover:bg-white/[0.04]'
                                  }`}>
                            {env.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-white/[0.03] rounded-xl border border-white/[0.06]">
                      <div>
                        <p className="text-base text-white/70">Основной продукт</p>
                        <p className="text-sm text-white/30">Отмечает как основной</p>
                      </div>
                      <button onClick={() => setProductIsPrimary(!productIsPrimary)}
                              className={`relative w-11 h-6 rounded-full transition-colors ${productIsPrimary ? 'bg-red-600' : 'bg-white/10'}`}>
                        <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${productIsPrimary ? 'translate-x-5' : ''}`} />
                      </button>
                    </div>

                    <button onClick={addLinkedProduct}
                            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                                       bg-white/[0.05] hover:bg-white/[0.08] border border-white/[0.08]
                                       text-white text-base font-medium transition-colors">
                      <Plus className="w-4 h-4" /> Добавить в список
                    </button>
                  </>
                )}
              </div>

              {/* Список добавленных */}
              {linkedProducts.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm text-white/40">Будет привязано: {linkedProducts.length}</p>
                  {linkedProducts.map((lp, idx) => {
                    const PIcon = catMeta(lp.product.category)?.icon || Package;
                    return (
                      <div key={idx} className="flex items-center gap-3 p-3 bg-white/[0.03] border border-white/[0.06] rounded-xl">
                        <PIcon className="w-4 h-4 text-white/30 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-base text-white truncate">{lp.product.display_name || lp.product.name}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${envBadgeClass(lp.environment)}`}>
                              {envLabel(lp.environment)}
                            </span>
                            {lp.is_primary && (
                              <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-red-800/20 text-red-400 border border-red-800/30">
                                Основной
                              </span>
                            )}
                          </div>
                        </div>
                        <button onClick={() => removeLinkedProduct(idx)}
                                className="p-1.5 text-white/30 hover:text-red-400 transition-colors">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(productsPrevStep)}
                    className="px-6 py-3 text-base font-medium text-white/70 bg-white/[0.05] hover:bg-white/[0.08] rounded-xl transition-all">
              Назад
            </button>
            <button onClick={handleSubmit} disabled={isLoading}
                    className="flex items-center gap-2 px-6 py-3 text-base font-semibold text-white bg-red-800 hover:bg-red-700
                               rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-red-900/30">
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
              {isLoading ? 'Сохранение...' : 'Создать контрагента'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}