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

// ─── Маска телефона ────

function formatPhoneInput(raw: string): string {
  let digits = raw.replace(/\D/g, '');
  if (digits.startsWith('8')) digits = '7' + digits.slice(1);
  if (digits.length > 0 && !digits.startsWith('7')) digits = '7' + digits;
  digits = digits.slice(0, 11);
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

function isPhoneValid(formatted: string): boolean {
  if (!formatted || formatted === '+7') return true; // пустое — ок (если не обязательное)
  return isPhoneComplete(formatted);
}

function usePhoneMask(initial = '') {
  const [display, setDisplay] = useState(() => formatPhoneInput(initial));

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setDisplay(formatPhoneInput(e.target.value));
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && display.length > 0) {
      e.preventDefault();
      const digits = getPhoneDigits(display);
      setDisplay(formatPhoneInput(digits.slice(0, -1)));
    }
  }, [display]);

  const rawValue = display ? '+' + getPhoneDigits(display) : '';
  const isEmpty = getPhoneDigits(display).length <= 1;

  return {
    display, setDisplay, handleChange, handleKeyDown,
    rawValue, isComplete: isPhoneComplete(display), isEmpty,
  };
}

// ─── Валидация email ───

function isEmailValid(email: string): boolean {
  if (!email) return true; // пустое — ок если необязательное
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim());
}

// ─── Проверка уникальности email ──────────────────────────────────────────────

function collectAllEmails(
  companyEmail: string,
  contactPersons: ContactPersonInput[],
  includeContacts: boolean,
  branches: BranchFormData[],
  includeBranches: boolean,
): { email: string; source: string }[] {
  const all: { email: string; source: string }[] = [];

  if (companyEmail.trim()) {
    all.push({ email: companyEmail.trim().toLowerCase(), source: 'Компания' });
  }

  if (includeContacts) {
    contactPersons.forEach((cp, i) => {
      if (cp.email?.trim()) {
        all.push({
          email: cp.email.trim().toLowerCase(),
          source: `Контакт #${i + 1} (${cp.last_name || 'без фамилии'})`,
        });
      }
    });
  }

  if (includeBranches) {
    branches.forEach((b, i) => {
      if (b.email.trim()) {
        all.push({
          email: b.email.trim().toLowerCase(),
          source: `Подразделение #${i + 1} (${b.name || 'без названия'})`,
        });
      }
    });
  }

  return all;
}

function findDuplicateEmails(
  companyEmail: string,
  contactPersons: ContactPersonInput[],
  includeContacts: boolean,
  branches: BranchFormData[],
  includeBranches: boolean,
): { email: string; sources: string[] }[] {
  const all = collectAllEmails(
    companyEmail, contactPersons, includeContacts, branches, includeBranches,
  );

  const grouped = new Map<string, string[]>();
  for (const { email, source } of all) {
    if (!grouped.has(email)) grouped.set(email, []);
    grouped.get(email)!.push(source);
  }

  return Array.from(grouped.entries())
    .filter(([_, sources]) => sources.length > 1)
    .map(([email, sources]) => ({ email, sources }));
}

function DuplicateEmailWarning({ duplicates }: {
  duplicates: { email: string; sources: string[] }[];
}) {
  if (duplicates.length === 0) return null;
  return (
    <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-2">
      <div className="flex items-center gap-2">
        <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
        <p className="text-base font-medium text-amber-400">
          Обнаружены одинаковые email-адреса
        </p>
      </div>
      {duplicates.map((d, i) => (
        <div key={i} className="ml-7 text-sm text-amber-400/80">
          <span className="font-mono font-medium">{d.email}</span>
          {' — '}
          {d.sources.join(', ')}
        </div>
      ))}
      <p className="ml-7 text-xs text-amber-400/60">
        В системе нельзя использовать один email для разных сущностей.
        Измените дублирующиеся адреса.
      </p>
    </div>
  );
}

// ─── Валидация ИНН 

function validateInn(inn: string, type: CounterpartyType): { valid: boolean; message: string } {
  if (!inn) return { valid: false, message: '' };
  if (!/^\d+$/.test(inn)) return { valid: false, message: 'ИНН должен содержать только цифры' };

  const expectedLen = type === 'Юридическое лицо' ? 10 : 12;
  if (inn.length !== expectedLen) {
    return { valid: false, message: `ИНН: ${inn.length}/${expectedLen} цифр` };
  }



  return { valid: true, message: '' };
}

// ─── Валидация КПП 

function validateKpp(kpp: string): { valid: boolean; message: string } {
  if (!kpp) return { valid: false, message: '' };
  if (!/^\d{9}$/.test(kpp)) return { valid: false, message: `КПП: ${kpp.length}/9 цифр` };
  // КПП формат: NNNNPPXXX — первые 4 цифры (код ИФНС), следующие 2 (причина), последние 3 (порядковый)
  if (!/^\d{4}[\dA-Z]{2}\d{3}$/.test(kpp)) {
    return { valid: false, message: 'Неверный формат КПП' };
  }
  return { valid: true, message: '' };
}

// ─── Валидация ОКПО ────

function validateOkpo(okpo: string): { valid: boolean; message: string } {
  if (!okpo) return { valid: true, message: '' }; // необязательное
  if (!/^\d+$/.test(okpo)) return { valid: false, message: 'ОКПО должен содержать только цифры' };
  if (okpo.length !== 8 && okpo.length !== 10) {
    return { valid: false, message: `ОКПО: ${okpo.length} цифр (нужно 8 или 10)` };
  }
  return { valid: true, message: '' };
}

// ─── Парсинг ошибок backend ───────────────────────────────────────────────────

interface FieldError { field: string; message: string; }

function parseBackendErrors(err: any): { general: string; fields: FieldError[] } {
  const data = err?.response?.data;
  const status = err?.response?.status;
  if (!data) return { general: 'Произошла неизвестная ошибка', fields: [] };
  const detail = data.detail;
  if (status === 422 && Array.isArray(detail)) {
    const fields: FieldError[] = detail.map((e: any) => {
      const loc = e.loc || [];
      const fieldPath = loc.filter((l: any) => l !== 'body').join('.');
      return { field: fieldPath || 'unknown', message: e.msg || JSON.stringify(e) };
    });
    return { general: fields.length > 0 ? 'Проверьте правильность заполнения полей' : 'Ошибка валидации', fields };
  }
  if (typeof detail === 'string') {
    const fields: FieldError[] = [];
    const lower = detail.toLowerCase();
    if (lower.includes('inn') || lower.includes('инн')) fields.push({ field: 'inn', message: detail });
    if (lower.includes('kpp') || lower.includes('кпп')) fields.push({ field: 'kpp', message: detail });
    if (lower.includes('okpo') || lower.includes('окпо')) fields.push({ field: 'okpo', message: detail });
    if (lower.includes('phone') || lower.includes('телефон')) fields.push({ field: 'phone', message: detail });
    if (lower.includes('email')) fields.push({ field: 'email', message: detail });
    return { general: detail, fields };
  }
  if (Array.isArray(detail)) {
    return {
      general: detail.map((x: any) => typeof x === 'string' ? x : x.msg || JSON.stringify(x)).join('; '),
      fields: [],
    };
  }
  return { general: JSON.stringify(detail), fields: [] };
}

function FieldErrorMsg({ fieldErrors, fieldName }: { fieldErrors: FieldError[]; fieldName: string }) {
  const errors = fieldErrors.filter(e =>
    e.field === fieldName || e.field.startsWith(fieldName + '.') || e.field.endsWith('.' + fieldName)
  );
  if (errors.length === 0) return null;
  return (
    <div className="mt-1.5 flex items-start gap-1.5">
      <AlertCircle className="w-3.5 h-3.5 text-[var(--accent)] mt-0.5 flex-shrink-0" />
      <p className="text-sm text-[var(--accent)]">{errors.map(e => e.message).join('; ')}</p>
    </div>
  );
}

function hasFieldError(fieldErrors: FieldError[], fieldName: string): boolean {
  return fieldErrors.some(e =>
    e.field === fieldName || e.field.startsWith(fieldName + '.') || e.field.endsWith('.' + fieldName)
  );
}

// ─── Inline hint ─

function Hint({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-1.5 text-sm text-amber-400 flex items-center gap-1">
      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
      {children}
    </p>
  );
}

function SuccessHint({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-1.5 text-sm text-emerald-400 flex items-center gap-1">
      <Check className="w-3.5 h-3.5 flex-shrink-0" />
      {children}
    </p>
  );
}

// ─── Константы ────

const COUNTERPARTY_TYPES: { value: CounterpartyType; label: string; desc: string; icon: React.ReactNode }[] = [
  { value: 'Юридическое лицо', label: 'Юридическое лицо', desc: 'ИНН 10 цифр, КПП обязателен', icon: <Building2 className="w-7 h-7" /> },
  { value: 'Физическое лицо', label: 'Физическое лицо', desc: 'ИНН 12 цифр, КПП не нужен', icon: <User className="w-7 h-7" /> },
  { value: 'Индивидуальный предприниматель', label: 'Индивидуальный предприниматель', desc: 'ИНН 12 цифр, КПП не нужен', icon: <Briefcase className="w-7 h-7" /> },
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
  { value: 'production', label: 'Production' },
  { value: 'staging', label: 'Staging' },
  { value: 'testing', label: 'Testing' },
  { value: 'development', label: 'Development' },
] as const;

const catMeta = (v: string) => PRODUCT_CATEGORIES.find(c => c.value === v);
const envLabel = (v: string) => ENVIRONMENTS.find(e => e.value === v)?.label ?? v;

const envBadgeClass = (e: string) => {
  if (e === 'production') return 'bg-emerald-500/10 text-[var(--success)] border border-emerald-500/20';
  if (e === 'staging') return 'bg-yellow-500/10 text-[var(--warning)] border border-yellow-500/20';
  if (e === 'testing') return 'bg-blue-500/10 text-[var(--info)] border border-blue-500/20';
  if (e === 'development') return 'bg-purple-500/10 text-[var(--info)] border border-purple-500/20';
  return 'bg-[var(--hover-1)] text-[var(--text-primary)]/40 border border-white/10';
};

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

interface LinkedProduct { product: any; environment: string; is_primary: boolean; }

const inputCls = (hasError = false) =>
  `w-full px-4 py-3.5 text-base bg-[var(--hover-2)] border rounded-xl text-[var(--text-primary)]
   placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 transition-all ${hasError
    ? 'border-red-500/60 focus:border-red-500 focus:ring-red-500/20'
    : 'border-[var(--border-color)] focus:border-[var(--accent)]/30 focus:ring-[var(--accent-ring)]'
  }`;

const labelCls = 'block text-base font-medium text-[var(--text-primary)]/80 mb-2';

// ─── Компонент телефона контактного лица (с маской) ──────────────────────────

function ContactPhoneInput({ value, onChange }: {
  value: string;
  onChange: (raw: string, display: string) => void;
}) {
  const [display, setDisplay] = useState(() => formatPhoneInput(value));

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneInput(e.target.value);
    setDisplay(formatted);
    const digits = getPhoneDigits(formatted);
    onChange(digits.length > 1 ? '+' + digits : '', formatted);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && display.length > 0) {
      e.preventDefault();
      const digits = getPhoneDigits(display);
      const newFormatted = formatPhoneInput(digits.slice(0, -1));
      setDisplay(newFormatted);
      const newDigits = getPhoneDigits(newFormatted);
      onChange(newDigits.length > 1 ? '+' + newDigits : '', newFormatted);
    }
  };

  const hasValue = getPhoneDigits(display).length > 1;
  const isComplete = isPhoneComplete(display);
  const showError = hasValue && !isComplete;
  const showOk = hasValue && isComplete;

  return (
    <div>
      <input
        type="tel"
        value={display}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="+7 (___) ___-__-__"
        className={inputCls(showError)}
      />
      {showError && <Hint>Введите полный номер: +7 (XXX) XXX-XX-XX</Hint>}
      {showOk && <SuccessHint>{display}</SuccessHint>}
    </div>
  );
}

// ─── Компонент телефона подразделения (с маской) ─────────────────────────────

function BranchPhoneInput({ value, onChange, required }: {
  value: string;
  onChange: (raw: string) => void;
  required?: boolean;
}) {
  const [display, setDisplay] = useState(() => formatPhoneInput(value));

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneInput(e.target.value);
    setDisplay(formatted);
    const digits = getPhoneDigits(formatted);
    onChange(digits.length > 1 ? '+' + digits : '');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && display.length > 0) {
      e.preventDefault();
      const digits = getPhoneDigits(display);
      const newFormatted = formatPhoneInput(digits.slice(0, -1));
      setDisplay(newFormatted);
      const newDigits = getPhoneDigits(newFormatted);
      onChange(newDigits.length > 1 ? '+' + newDigits : '');
    }
  };

  const hasValue = getPhoneDigits(display).length > 1;
  const isComplete = isPhoneComplete(display);
  const showError = (hasValue && !isComplete) || (required && !hasValue);
  const showOk = hasValue && isComplete;

  return (
    <div>
      <input
        type="tel"
        value={display}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="+7 (___) ___-__-__"
        className={inputCls(showError)}
      />
      {hasValue && !isComplete && <Hint>Введите полный номер: +7 (XXX) XXX-XX-XX</Hint>}
      {showOk && <SuccessHint>{display}</SuccessHint>}
    </div>
  );
}

// ─── Email input с валидацией ─────────────────────────────────────────────────

function EmailInput({ value, onChange, placeholder, required, hasBackendError }: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  hasBackendError?: boolean;
}) {
  const [touched, setTouched] = useState(false);
  const valid = isEmailValid(value);
  const showError = hasBackendError || (touched && value.length > 0 && !valid);
  const showOk = touched && value.length > 0 && valid;

  return (
    <div>
      <input
        type="email"
        value={value}
        onChange={e => onChange(e.target.value)}
        onBlur={() => setTouched(true)}
        placeholder={placeholder ?? 'email@example.ru'}
        className={inputCls(showError)}
      />
      {showError && !hasBackendError && <Hint>Введите корректный email: example@domain.ru</Hint>}
      {showOk && <SuccessHint>{value.trim()}</SuccessHint>}
    </div>
  );
}

// ─── Основной компонент 

export default function NewCounterpartyPage() {
  const navigate = useNavigate();

  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldError[]>([]);
  const [step, setStep] = useState(1);

  const [formData, setFormData] = useState<CreateCounterpartyInput>({
    counterparty_type: 'Юридическое лицо',
    name: '', legal_name: '', inn: '', kpp: '', okpo: '',
    phone: '', email: '', address: '',
  });

  const companyPhone = usePhoneMask(formData.phone);

  const [contactPersons, setContactPersons] = useState<ContactPersonInput[]>([]);
  const [includeContacts, setIncludeContacts] = useState(false);
  const [branches, setBranches] = useState<BranchFormData[]>([]);
  const [includeBranches, setIncludeBranches] = useState(false);
  const [linkedProducts, setLinkedProducts] = useState<LinkedProduct[]>([]);
  const [showProductForm, setShowProductForm] = useState(false);
  const [allProducts, setAllProducts] = useState<any[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [productFilter, setProductFilter] = useState('');
  const [selectedProductToLink, setSelectedProductToLink] = useState<any | null>(null);
  const [productEnv, setProductEnv] = useState('production');
  const [productIsPrimary, setProductIsPrimary] = useState(false);

  useEffect(() => {
    if (showProductForm && allProducts.length === 0) {
      setLoadingProducts(true);
      productsApi.getProducts({ page: 1, size: 50 })
        .then(res => setAllProducts(res.items ?? []))
        .catch(() => { })
        .finally(() => setLoadingProducts(false));
    }
  }, [showProductForm]);

  const filteredProducts = productFilter.trim()
    ? allProducts.filter(p => {
      const q = productFilter.toLowerCase();
      return (p.display_name || p.name || '').toLowerCase().includes(q) ||
        (p.vendor || '').toLowerCase().includes(q);
    })
    : allProducts;

  const availableProducts = filteredProducts.filter(
    p => !linkedProducts.some(lp => lp.product.id === p.id)
  );

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

  const removeLinkedProduct = (i: number) =>
    setLinkedProducts(linkedProducts.filter((_, idx) => idx !== i));

const handleSubmit = async () => {
  // ── Предварительные проверки ─────────────────────────────
  clearErrors();

  // Проверка дубликатов email
  const dupes = findDuplicateEmails(
    formData.email, contactPersons, includeContacts, branches, includeBranches,
  );
  if (dupes.length > 0) {
    setGeneralError(
      `Дубликаты email: ${dupes.map(d => d.email).join(', ')}. ` +
      'В системе нельзя использовать одинаковые email для разных сущностей.'
    );
    return;
  }

  // Проверка валидности email во всех полях
  const allEmails = collectAllEmails(
    formData.email, contactPersons, includeContacts, branches, includeBranches,
  );
  const invalidEmail = allEmails.find(e => !isEmailValid(e.email));
  if (invalidEmail) {
    setGeneralError(`Некорректный email "${invalidEmail.email}" в: ${invalidEmail.source}`);
    return;
  }

  setIsLoading(true);

  try {
    // ── 1. Подготовка payload ──────────────────────────────
    const payload: any = {
      counterparty_type: formData.counterparty_type,
      name: formData.name.trim(),
      legal_name: formData.legal_name.trim(),
      inn: formData.inn,
      phone: companyPhone.rawValue,
      email: formData.email.trim(),
    };
    if (isKppAllowed(formData.counterparty_type) && formData.kpp) payload.kpp = formData.kpp;
    if (formData.okpo) payload.okpo = formData.okpo;
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

    // ── 2. Создание контрагента ───────────────────────────
    const created = await counterpartiesApi.create(payload);

    // ── 3. Подразделения (с откатом при ошибке) ───────────
    if (includeBranches && branches.length > 0) {
      try {
        for (const b of branches) {
          const bp: CreateBranchInput = {
            name: b.name,
            legal_name: b.legal_name,
            kpp: b.kpp,
            phone: b.phone,
            email: b.email,
          };
          if (b.okpo) bp.okpo = b.okpo;
          if (b.address) bp.address = b.address;
          await counterpartiesApi.createBranch(created.id, bp);
        }
      } catch (branchErr: any) {
        // Откатываем — удаляем созданного контрагента
        try {
          await counterpartiesApi.delete(created.id);
        } catch {
          // Если удаление тоже упало — логируем но показываем оригинальную ошибку
          console.error('Не удалось откатить создание контрагента', created.id);
        }

        const parsed = parseBackendErrors(branchErr);
        setGeneralError(
          `Ошибка при создании подразделения: ${parsed.general}. ` +
          'Контрагент НЕ был создан — исправьте ошибку и попробуйте снова.'
        );
        setFieldErrors(parsed.fields);

        // Перекинуть на шаг подразделений
        if (formData.counterparty_type === 'Юридическое лицо') setStep(4);
        return;
      }
    }

    // ── 4. Продукты (с откатом при ошибке) ────────────────
    if (linkedProducts.length > 0) {
      try {
        for (const lp of linkedProducts) {
          await counterpartiesApi.linkProduct(created.id, {
            product_id: lp.product.id,
            environment: lp.environment,
            is_primary: lp.is_primary,
          });
        }
      } catch (productErr: any) {
        // Откатываем — удаляем контрагента
        try {
          await counterpartiesApi.delete(created.id);
        } catch {
          console.error('Не удалось откатить создание контрагента', created.id);
        }

        const parsed = parseBackendErrors(productErr);
        setGeneralError(
          `Ошибка при привязке продукта: ${parsed.general}. ` +
          'Контрагент НЕ был создан — исправьте ошибку и попробуйте снова.'
        );
        setFieldErrors(parsed.fields);
        setStep(productsStep);
        return;
      }
    }

    // ── 5. Успех ──────────────────────────────────────────
    navigate('/counterparties');
  } catch (err: any) {
    // Ошибка создания самого контрагента — откат не нужен
    const parsed = parseBackendErrors(err);
    setGeneralError(parsed.general);
    setFieldErrors(parsed.fields);

    const step1Fields = ['inn', 'kpp', 'okpo', 'name', 'legal_name', 'counterparty_type'];
    const step2Fields = ['phone', 'email', 'address'];
    if (parsed.fields.some(f => step1Fields.includes(f.field))) setStep(1);
    else if (parsed.fields.some(f => step2Fields.includes(f.field))) setStep(2);
  } finally {
    setIsLoading(false);
  }
};

  // ─── Валидация полей ─────────────────────────────────────────────────────

  const innLength = getInnMaxLength(formData.counterparty_type);
  const innValidation = validateInn(formData.inn, formData.counterparty_type);
  const kppValidation = validateKpp(formData.kpp ?? '');
  const okpoValidation = validateOkpo(formData.okpo ?? '');

  const isInnValid = innValidation.valid;
  const isKppValid = isKppRequired(formData.counterparty_type)
    ? kppValidation.valid
    : true;
  const isOkpoValid = okpoValidation.valid;

  const isEmailFilled = formData.email.trim().length > 0;
  const isEmailCorrect = isEmailValid(formData.email);

  const isStep1Valid = !!(
    formData.counterparty_type &&
    formData.name.trim() &&
    formData.legal_name.trim() &&
    isInnValid &&
    isKppValid &&
    isOkpoValid
  );

  const isStep2Valid = companyPhone.isComplete && isEmailFilled && isEmailCorrect;

  const totalSteps = formData.counterparty_type === 'Юридическое лицо' ? 5 : 4;
  const productsStep = formData.counterparty_type === 'Юридическое лицо' ? 5 : 4;
  const productsPrevStep = formData.counterparty_type === 'Юридическое лицо' ? 4 : 3;

  const stepLabels: Record<number, string> = {
    1: 'Основное', 2: 'Контакты', 3: 'Контактные лица',
    4: formData.counterparty_type === 'Юридическое лицо' ? 'Подразделение' : 'Продукты',
    5: 'Продукты',
  };

  return (
    <div className="max-w-5xl mx-auto pb-12 space-y-8">

      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/counterparties')}
          className="p-2.5 rounded-xl bg-[var(--hover-2)] hover:bg-[var(--hover-3)] border border-[var(--border-color)]
                     text-[var(--text-primary)]/60 hover:text-[var(--text-primary)] transition-all">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Новый контрагент</h1>
          <p className="text-base text-[var(--text-primary)]/50 mt-0.5">Заполните данные контрагента</p>
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
                  ? 'bg-[var(--accent)] text-white shadow-[var(--shadow-md)]'
                  : step > s
                    ? 'bg-emerald-600 text-white cursor-pointer hover:bg-emerald-500'
                    : 'bg-[var(--hover-2)] text-[var(--text-primary)]/30'
              }`}
            >
              {step > s ? <Check className="w-4 h-4" /> : s}
            </button>
            <span className={`text-sm font-medium hidden sm:block ${step >= s ? 'text-[var(--text-primary)]/70' : 'text-[var(--text-primary)]/30'}`}>
              {stepLabels[s]}
            </span>
            {s < totalSteps && <div className="w-6 h-0.5 bg-[var(--hover-3)]" />}
          </div>
        ))}
      </div>

      {/* Global Error */}
      {generalError && (
        <div className="p-4 bg-[var(--accent)]/10 border border-[var(--accent)]/30 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-[var(--accent)] mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-base text-[var(--accent)] font-medium">{generalError}</p>
            {fieldErrors.length > 0 && (
              <ul className="mt-2 space-y-1">
                {fieldErrors.map((fe, i) => (
                  <li key={i} className="text-sm text-[var(--accent)]/80">
                    <span className="font-mono">{fe.field}</span>: {fe.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* ═══ Шаг 1: Основное ═══ */}
      {step === 1 && (
        <div className="bg-[var(--hover-2)] border border-[var(--border-color)] rounded-2xl p-6 space-y-7">

          {/* Тип */}
          <div>
            <p className={labelCls}>Тип контрагента</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {COUNTERPARTY_TYPES.map(type => (
                <button key={type.value} type="button" onClick={() => handleTypeChange(type.value)}
                  className={`p-5 rounded-xl border-2 text-left transition-all ${
                    formData.counterparty_type === type.value
                      ? 'border-[var(--accent)]/60 bg-[var(--accent)]/[0.06]'
                      : 'border-[var(--border-color)] bg-[var(--hover-1)] hover:border-[var(--accent)]/20'
                  }`}>
                  <div className={`mb-2 ${formData.counterparty_type === type.value ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]/40'}`}>
                    {type.icon}
                  </div>
                  <p className={`text-base font-semibold ${formData.counterparty_type === type.value ? 'text-[var(--text-primary)]' : 'text-[var(--text-primary)]/70'}`}>
                    {type.label}
                  </p>
                  <p className="text-sm text-[var(--text-primary)]/30 mt-1">{type.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Названия */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className={labelCls}>Краткое название <span className="text-[var(--accent)]">*</span></label>
              <input
                type="text"
                value={formData.name}
                onChange={e => { clearErrors(); setFormData({ ...formData, name: e.target.value }); }}
                placeholder={
                  formData.counterparty_type === 'Физическое лицо' ? 'Иванов И.И.'
                    : formData.counterparty_type === 'Индивидуальный предприниматель' ? 'ИП Иванов'
                    : 'ООО Компания'
                }
                className={inputCls(hasFieldError(fieldErrors, 'name'))}
              />
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="name" />
            </div>
            <div>
              <label className={labelCls}>Полное наименование <span className="text-[var(--accent)]">*</span></label>
              <input
                type="text"
                value={formData.legal_name}
                onChange={e => { clearErrors(); setFormData({ ...formData, legal_name: e.target.value }); }}
                placeholder={formData.counterparty_type === 'Юридическое лицо' ? 'ООО «Компания»' : 'Полное ФИО'}
                className={inputCls(hasFieldError(fieldErrors, 'legal_name'))}
              />
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="legal_name" />
            </div>
          </div>

          {/* Реквизиты */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* ИНН */}
            <div>
              <label className={labelCls}>ИНН <span className="text-[var(--accent)]">*</span></label>
              <input
                type="text"
                inputMode="numeric"
                value={formData.inn}
                onChange={e => {
                  clearErrors();
                  const val = e.target.value.replace(/\D/g, '');
                  if (val.length <= innLength) setFormData({ ...formData, inn: val });
                }}
                placeholder={getInnPlaceholder(formData.counterparty_type)}
                maxLength={innLength}
                className={inputCls(
                  (formData.inn.length > 0 && !innValidation.valid) ||
                  hasFieldError(fieldErrors, 'inn')
                )}
              />
              {/* Прогресс ввода */}
              {formData.inn.length > 0 && formData.inn.length < innLength && (
                <Hint>ИНН: {formData.inn.length}/{innLength} цифр</Hint>
              )}
              {/* Ошибка контрольной суммы */}
              {formData.inn.length === innLength && !innValidation.valid && innValidation.message && (
                <Hint>{innValidation.message}</Hint>
              )}
              {/* Успех */}
              {innValidation.valid && (
                <SuccessHint>ИНН корректен</SuccessHint>
              )}
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="inn" />
            </div>

            {/* КПП */}
            {isKppAllowed(formData.counterparty_type) && (
              <div>
                <label className={labelCls}>КПП <span className="text-[var(--accent)]">*</span></label>
                <input
                  type="text"
                  inputMode="numeric"
                  value={formData.kpp}
                  onChange={e => {
                    clearErrors();
                    const val = e.target.value.replace(/\D/g, '');
                    if (val.length <= 9) setFormData({ ...formData, kpp: val });
                  }}
                  placeholder="9 цифр"
                  maxLength={9}
                  className={inputCls(
                    (!!formData.kpp && !kppValidation.valid) ||
                    hasFieldError(fieldErrors, 'kpp')
                  )}
                />
                {formData.kpp && formData.kpp.length < 9 && (
                  <Hint>КПП: {formData.kpp.length}/9 цифр</Hint>
                )}
                {formData.kpp && formData.kpp.length === 9 && !kppValidation.valid && (
                  <Hint>{kppValidation.message}</Hint>
                )}
                {kppValidation.valid && formData.kpp && (
                  <SuccessHint>КПП корректен</SuccessHint>
                )}
                <FieldErrorMsg fieldErrors={fieldErrors} fieldName="kpp" />
              </div>
            )}

            {/* ОКПО */}
            <div>
              <label className={labelCls}>ОКПО <span className="text-[var(--text-primary)]/30 text-sm font-normal">(необяз.)</span></label>
              <input
                type="text"
                inputMode="numeric"
                value={formData.okpo}
                onChange={e => {
                  clearErrors();
                  const val = e.target.value.replace(/\D/g, '');
                  if (val.length <= 10) setFormData({ ...formData, okpo: val });
                }}
                placeholder="8 или 10 цифр"
                maxLength={10}
                className={inputCls(
                  (!!formData.okpo && !okpoValidation.valid) ||
                  hasFieldError(fieldErrors, 'okpo')
                )}
              />
              {formData.okpo && !okpoValidation.valid && (
                <Hint>{okpoValidation.message}</Hint>
              )}
              {formData.okpo && okpoValidation.valid && (
                <SuccessHint>ОКПО: {formData.okpo}</SuccessHint>
              )}
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="okpo" />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setStep(2)}
              disabled={!isStep1Valid}
              className="px-6 py-3 text-base font-semibold text-white bg-[var(--accent)]
                         hover:bg-[var(--accent-light)] rounded-xl transition-all
                         disabled:opacity-40 disabled:cursor-not-allowed shadow-[var(--shadow-md)]"
            >
              Далее
            </button>
          </div>
        </div>
      )}

      {/* ═══ Шаг 2: Контакты ═══ */}
      {step === 2 && (
        <div className="bg-[var(--hover-2)] border border-[var(--border-color)] rounded-2xl p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

            {/* Телефон компании */}
            <div>
              <label className={labelCls}>
                <Phone className="w-4 h-4 inline mr-1.5 text-[var(--text-primary)]/40" />
                Телефон <span className="text-[var(--accent)]">*</span>
              </label>
              <input
                type="tel"
                value={companyPhone.display}
                onChange={companyPhone.handleChange}
                onKeyDown={companyPhone.handleKeyDown}
                placeholder="+7 (___) ___-__-__"
                className={inputCls(
                  (!companyPhone.isEmpty && !companyPhone.isComplete) ||
                  hasFieldError(fieldErrors, 'phone')
                )}
              />
              {!companyPhone.isEmpty && !companyPhone.isComplete && (
                <Hint>Введите полный номер: +7 (XXX) XXX-XX-XX</Hint>
              )}
              {companyPhone.isComplete && (
                <SuccessHint>{companyPhone.display}</SuccessHint>
              )}
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="phone" />
            </div>

            {/* Email компании */}
            <div>
              <label className={labelCls}>
                <Mail className="w-4 h-4 inline mr-1.5 text-[var(--text-primary)]/40" />
                Email <span className="text-[var(--accent)]">*</span>
              </label>
              <EmailInput
                value={formData.email}
                onChange={v => { clearErrors(); setFormData({ ...formData, email: v }); }}
                placeholder="info@company.ru"
                required
                hasBackendError={hasFieldError(fieldErrors, 'email')}
              />
              <FieldErrorMsg fieldErrors={fieldErrors} fieldName="email" />
            </div>
          </div>

          {/* Адрес */}
          <div>
            <label className={labelCls}>
              <MapPin className="w-4 h-4 inline mr-1.5 text-[var(--text-primary)]/40" />
              Адрес <span className="text-[var(--text-primary)]/30 text-sm font-normal">(необяз.)</span>
            </label>
            <textarea
              value={formData.address}
              onChange={e => setFormData({ ...formData, address: e.target.value })}
              placeholder="г. Москва, ул. Примерная, д. 1"
              rows={3}
              className={`${inputCls()} resize-none`}
            />
          </div>

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(1)}
              className="px-6 py-3 text-base font-medium text-[var(--text-primary)]/70
                         bg-[var(--hover-2)] hover:bg-[var(--hover-3)] rounded-xl transition-all">
              Назад
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!isStep2Valid}
              className="px-6 py-3 text-base font-semibold text-white bg-[var(--accent)]
                         hover:bg-[var(--accent-light)] rounded-xl transition-all
                         disabled:opacity-40 disabled:cursor-not-allowed shadow-[var(--shadow-md)]"
            >
              Далее
            </button>
          </div>
        </div>
      )}

      {/* ═══ Шаг 3: Контактные лица ═══ */}
      {step === 3 && (
        <div className="bg-[var(--hover-2)] border border-[var(--border-color)] rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between p-4 bg-[var(--hover-1)] rounded-xl border border-[var(--border-color)]">
            <div className="flex items-center gap-3">
              <UserCircle className="w-6 h-6 text-[var(--text-primary)]/40" />
              <div>
                <p className="text-base font-medium text-[var(--text-primary)]">Контактные лица</p>
                <p className="text-sm text-[var(--text-primary)]/40">Ответственные сотрудники</p>
              </div>
            </div>
            <button type="button"
              onClick={() => {
                if (includeContacts) { setIncludeContacts(false); setContactPersons([]); }
                else { setIncludeContacts(true); if (!contactPersons.length) setContactPersons([emptyContactPerson()]); }
              }}
              className={`relative w-12 h-6 rounded-full transition-colors ${includeContacts ? 'bg-[var(--accent)]' : 'bg-[var(--hover-3)]'}`}>
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${includeContacts ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          {includeContacts && contactPersons.map((cp, i) => (
            <div key={i} className="p-5 bg-[var(--hover-1)] border border-[var(--border-color)] rounded-xl space-y-5">
              <div className="flex items-center justify-between">
                <p className="text-base font-medium text-[var(--text-primary)]">Контакт #{i + 1}</p>
                {contactPersons.length > 1 && (
                  <button onClick={() => removeContactPerson(i)}
                    className="p-1.5 text-[var(--text-primary)]/30 hover:text-[var(--accent)] hover:bg-[var(--hover-2)] rounded-lg transition-all">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* ФИО */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className={labelCls}>Фамилия <span className="text-[var(--accent)]">*</span></label>
                  <input type="text" value={cp.last_name}
                    onChange={e => updateContactPerson(i, { ...cp, last_name: e.target.value })}
                    placeholder="Иванов" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>Имя <span className="text-[var(--accent)]">*</span></label>
                  <input type="text" value={cp.first_name}
                    onChange={e => updateContactPerson(i, { ...cp, first_name: e.target.value })}
                    placeholder="Иван" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>Отчество</label>
                  <input type="text" value={cp.middle_name}
                    onChange={e => updateContactPerson(i, { ...cp, middle_name: e.target.value })}
                    placeholder="Иванович" className={inputCls()} />
                </div>
              </div>

              {/* Телефон + Email контакта */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Телефон</label>
                  <ContactPhoneInput
                    value={cp.phone}
                    onChange={(raw) => updateContactPerson(i, { ...cp, phone: raw })}
                  />
                </div>
                <div>
                  <label className={labelCls}>Email</label>
                  <EmailInput
                    value={cp.email ?? ''}
                    onChange={v => updateContactPerson(i, { ...cp, email: v })}
                    placeholder="ivanov@company.ru"
                  />
                </div>
              </div>

              {/* Мессенджеры */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>
                    <MessageSquare className="w-3.5 h-3.5 inline mr-1.5 text-[var(--text-primary)]/40" />
                    Telegram
                  </label>
                  <div className="relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/30 text-base select-none">@</span>
                    <input
                      type="text"
                      value={(cp.messengers?.telegram || '').replace(/^@/, '')}
                      onChange={e => updateContactPerson(i, {
                        ...cp,
                        messengers: { ...cp.messengers, telegram: e.target.value ? '@' + e.target.value.replace(/^@/, '') : '' },
                      })}
                      placeholder="username"
                      className={`${inputCls()} pl-8`}
                    />
                  </div>
                </div>
                <div>
                  <label className={labelCls}>VK</label>
                  <div className="relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/30 text-sm select-none">vk.com/</span>
                    <input
                      type="text"
                      value={(cp.messengers?.vk || '').replace(/^vk\.com\//, '')}
                      onChange={e => updateContactPerson(i, {
                        ...cp,
                        messengers: { ...cp.messengers, vk: e.target.value ? 'vk.com/' + e.target.value.replace(/^vk\.com\//, '') : '' },
                      })}
                      placeholder="id123456"
                      className={`${inputCls()} pl-16`}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}

          {includeContacts && (
            <button onClick={addContactPerson}
              className="flex items-center gap-2 px-5 py-3 text-base text-[var(--text-primary)]/50
                         hover:text-[var(--text-primary)] bg-[var(--hover-1)] hover:bg-[var(--hover-2)]
                         border border-dashed border-[var(--border-color)] rounded-xl transition-all w-full justify-center">
              <Plus className="w-4 h-4" /> Добавить ещё
            </button>
          )}
          
          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(2)}
              className="px-6 py-3 text-base font-medium text-[var(--text-primary)]/70
                         bg-[var(--hover-2)] hover:bg-[var(--hover-3)] rounded-xl transition-all">
              Назад
            </button>
            <button onClick={() => setStep(4)}
              className="px-6 py-3 text-base font-semibold text-white bg-[var(--accent)]
                         hover:bg-[var(--accent-light)] rounded-xl transition-all shadow-[var(--shadow-md)]">
              Далее
            </button>
          </div>
        </div>
      )}

      {/* ═══ Шаг 4: Подразделение (юр. лицо) ═══ */}
      {step === 4 && formData.counterparty_type === 'Юридическое лицо' && (
        <div className="bg-[var(--hover-2)] border border-[var(--border-color)] rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between p-4 bg-[var(--hover-1)] rounded-xl border border-[var(--border-color)]">
            <div className="flex items-center gap-3">
              <GitBranch className="w-6 h-6 text-[var(--text-primary)]/40" />
              <div>
                <p className="text-base font-medium text-[var(--text-primary)]">Обособленные подразделения</p>
                <p className="text-sm text-[var(--text-primary)]/40">Подразделения наследуют ИНН</p>
              </div>
            </div>
            <button type="button"
              onClick={() => {
                if (includeBranches) { setIncludeBranches(false); setBranches([]); }
                else { setIncludeBranches(true); if (!branches.length) setBranches([emptyBranch()]); }
              }}
              className={`relative w-12 h-6 rounded-full transition-colors ${includeBranches ? 'bg-[var(--accent)]' : 'bg-[var(--hover-3)]'}`}>
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${includeBranches ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          {includeBranches && branches.map((branch, i) => (
            <div key={i} className="p-5 bg-[var(--hover-1)] border border-[var(--border-color)] rounded-xl space-y-5">
              <div className="flex items-center justify-between">
                <p className="text-base font-medium text-[var(--text-primary)] flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-[var(--text-primary)]/40" />
                  Подразделение #{i + 1}
                </p>
                {branches.length > 1 && (
                  <button onClick={() => removeBranch(i)}
                    className="p-1.5 text-[var(--text-primary)]/30 hover:text-[var(--accent)] hover:bg-[var(--hover-2)] rounded-lg transition-all">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* ИНН наследуется */}
              <div className="px-3 py-2 bg-[var(--hover-2)] rounded-lg border border-[var(--border-color)] flex items-center gap-2">
                <FileText className="w-4 h-4 text-[var(--text-primary)]/30 flex-shrink-0" />
                <p className="text-sm text-[var(--text-primary)]/40">
                  ИНН наследуется:{' '}
                  <span className="text-[var(--text-primary)] font-mono tracking-widest">{formData.inn}</span>
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Название <span className="text-[var(--accent)]">*</span></label>
                  <input type="text" value={branch.name}
                    onChange={e => updateBranch(i, { ...branch, name: e.target.value })}
                    placeholder="Подразделение в СПб" className={inputCls()} />
                </div>
                <div>
                  <label className={labelCls}>Полное наименование <span className="text-[var(--accent)]">*</span></label>
                  <input type="text" value={branch.legal_name}
                    onChange={e => updateBranch(i, { ...branch, legal_name: e.target.value })}
                    placeholder="Подразделение ООО «Компания»" className={inputCls()} />
                </div>
              </div>

              {/* КПП + ОКПО подразделения */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>КПП <span className="text-[var(--accent)]">*</span></label>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={branch.kpp}
                    onChange={e => {
                      const v = e.target.value.replace(/\D/g, '');
                      if (v.length <= 9) updateBranch(i, { ...branch, kpp: v });
                    }}
                    placeholder="9 цифр"
                    maxLength={9}
                    className={inputCls(!!branch.kpp && branch.kpp.length !== 9)}
                  />
                  {branch.kpp && branch.kpp.length < 9 && (
                    <Hint>КПП: {branch.kpp.length}/9 цифр</Hint>
                  )}
                  {branch.kpp && branch.kpp.length === 9 && !validateKpp(branch.kpp).valid && (
                    <Hint>{validateKpp(branch.kpp).message}</Hint>
                  )}
                  {branch.kpp && validateKpp(branch.kpp).valid && (
                    <SuccessHint>КПП корректен</SuccessHint>
                  )}
                </div>
                <div>
                  <label className={labelCls}>ОКПО <span className="text-[var(--text-primary)]/30 text-sm font-normal">(необяз.)</span></label>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={branch.okpo}
                    onChange={e => {
                      const v = e.target.value.replace(/\D/g, '');
                      if (v.length <= 10) updateBranch(i, { ...branch, okpo: v });
                    }}
                    placeholder="8 или 10 цифр"
                    maxLength={10}
                    className={inputCls(!!branch.okpo && !validateOkpo(branch.okpo).valid)}
                  />
                  {branch.okpo && !validateOkpo(branch.okpo).valid && (
                    <Hint>{validateOkpo(branch.okpo).message}</Hint>
                  )}
                  {branch.okpo && validateOkpo(branch.okpo).valid && (
                    <SuccessHint>ОКПО: {branch.okpo}</SuccessHint>
                  )}
                </div>
              </div>

              {/* Телефон + Email подразделения */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>
                    <Phone className="w-4 h-4 inline mr-1.5 text-[var(--text-primary)]/40" />
                    Телефон <span className="text-[var(--accent)]">*</span>
                  </label>
                  <BranchPhoneInput
                    value={branch.phone}
                    onChange={raw => updateBranch(i, { ...branch, phone: raw })}
                    required
                  />
                </div>
                <div>
                  <label className={labelCls}>
                    <Mail className="w-4 h-4 inline mr-1.5 text-[var(--text-primary)]/40" />
                    Email <span className="text-[var(--accent)]">*</span>
                  </label>
                  <EmailInput
                    value={branch.email}
                    onChange={v => updateBranch(i, { ...branch, email: v })}
                    placeholder="branch@company.ru"
                    required
                  />
                </div>
              </div>

              {/* Адрес подразделения */}
              <div>
                <label className={labelCls}>
                  <MapPin className="w-4 h-4 inline mr-1.5 text-[var(--text-primary)]/40" />
                  Адрес
                </label>
                <input type="text" value={branch.address}
                  onChange={e => updateBranch(i, { ...branch, address: e.target.value })}
                  placeholder="г. Санкт-Петербург, ул. ..." className={inputCls()} />
              </div>
            </div>
          ))}

          {includeBranches && (
            <button onClick={addBranch}
              className="flex items-center gap-2 px-5 py-3 text-base text-[var(--text-primary)]/50
                         hover:text-[var(--text-primary)] bg-[var(--hover-1)] hover:bg-[var(--hover-2)]
                         border border-dashed border-[var(--border-color)] rounded-xl transition-all w-full justify-center">
              <Plus className="w-4 h-4" /> Добавить подразделение
            </button>
          )}

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(3)}
              className="px-6 py-3 text-base font-medium text-[var(--text-primary)]/70
                         bg-[var(--hover-2)] hover:bg-[var(--hover-3)] rounded-xl transition-all">
              Назад
            </button>
            <button onClick={() => setStep(5)}
              className="px-6 py-3 text-base font-semibold text-white bg-[var(--accent)]
                         hover:bg-[var(--accent-light)] rounded-xl transition-all shadow-[var(--shadow-md)]">
              Далее
            </button>
          </div>
        </div>
      )}

      {/* ═══ Шаг «Продукты» ═══ */}
      {step === productsStep && (
        <div className="bg-[var(--hover-2)] border border-[var(--border-color)] rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between p-4 bg-[var(--hover-1)] rounded-xl border border-[var(--border-color)]">
            <div className="flex items-center gap-3">
              <Package className="w-6 h-6 text-[var(--text-primary)]/40" />
              <div>
                <p className="text-base font-medium text-[var(--text-primary)]">Привязать продукты</p>
                <p className="text-sm text-[var(--text-primary)]/40">ПО и оборудование</p>
              </div>
            </div>
            <button type="button"
              onClick={() => setShowProductForm(!showProductForm)}
              className={`relative w-12 h-6 rounded-full transition-colors ${showProductForm ? 'bg-[var(--accent)]' : 'bg-[var(--hover-3)]'}`}>
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${showProductForm ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          {showProductForm && (
            <div className="space-y-5">
              <div className="p-5 bg-[var(--hover-1)] border border-[var(--border-color)] rounded-xl space-y-4">
                <p className="text-base font-medium text-[var(--text-primary)]">Выберите продукт</p>

                <div className="relative">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-primary)]/30 pointer-events-none" />
                  <input
                    value={productFilter}
                    onChange={e => setProductFilter(e.target.value)}
                    placeholder="Фильтр по названию или вендору..."
                    className="w-full pl-10 pr-4 py-3 bg-[var(--hover-2)] border border-[var(--border-color)] rounded-xl
                               text-base text-[var(--text-primary)] placeholder-[var(--text-muted)]
                               focus:outline-none focus:border-[var(--accent)]/30 focus:ring-2
                               focus:ring-[var(--accent-ring)] transition-all"
                  />
                </div>

                <div className="max-h-56 overflow-y-auto rounded-xl border border-[var(--border-color)]
                               bg-[var(--bg-secondary)] divide-y divide-[var(--border-color)]">
                  {loadingProducts ? (
                    <div className="flex justify-center py-10">
                      <Loader2 className="w-5 h-5 animate-spin text-[var(--text-primary)]/20" />
                    </div>
                  ) : availableProducts.length === 0 ? (
                    <div className="py-10 text-center">
                      <Package className="w-8 h-8 mx-auto mb-2 text-[var(--text-primary)]/10" />
                      <p className="text-base text-[var(--text-primary)]/30">
                        {productFilter ? 'Ничего не найдено' : 'Нет продуктов'}
                      </p>
                    </div>
                  ) : (
                    availableProducts.slice(0, 30).map(p => {
                      const PIcon = catMeta(p.category)?.icon || Package;
                      return (
                        <button key={p.id}
                          onClick={() => {
                            setLinkedProducts(prev => [...prev, {
                              product: p, environment: productEnv, is_primary: productIsPrimary,
                            }]);
                            setProductFilter('');
                          }}
                          className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--hover-2)] transition-colors">
                          <PIcon className="w-4 h-4 text-[var(--text-primary)]/30 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-base text-[var(--text-primary)] truncate">
                              {p.display_name || p.name}
                            </p>
                            <p className="text-sm text-[var(--text-primary)]/30">{p.vendor}</p>
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>

                {/* Среда и флаг «основной» — показываем всегда в форме */}
                <div>
                  <label className="block text-sm text-[var(--text-primary)]/40 mb-2">
                    Среда по умолчанию для новых продуктов
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {ENVIRONMENTS.map(env => (
                      <button key={env.value} onClick={() => setProductEnv(env.value)}
                        className={`px-3 py-2.5 rounded-xl text-base font-medium transition-all ${
                          productEnv === env.value
                            ? envBadgeClass(env.value)
                            : 'border border-[var(--border-color)] bg-[var(--hover-1)] text-[var(--text-primary)]/40 hover:bg-[var(--hover-2)]'
                        }`}>
                        {env.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 bg-[var(--hover-1)] rounded-xl border border-[var(--border-color)]">
                  <div>
                    <p className="text-base text-[var(--text-primary)]/70">Основной продукт</p>
                    <p className="text-sm text-[var(--text-primary)]/30">Отмечать следующие как основные</p>
                  </div>
                  <button onClick={() => setProductIsPrimary(!productIsPrimary)}
                    className={`relative w-11 h-6 rounded-full transition-colors ${productIsPrimary ? 'bg-[var(--accent)]' : 'bg-[var(--hover-3)]'}`}>
                    <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${productIsPrimary ? 'translate-x-5' : ''}`} />
                  </button>
                </div>
              </div>

              {/* Список добавленных */}
              {linkedProducts.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm text-[var(--text-primary)]/40 font-medium">
                    Будет привязано: {linkedProducts.length}
                  </p>
                  {linkedProducts.map((lp, idx) => {
                    const PIcon = catMeta(lp.product.category)?.icon || Package;
                    return (
                      <div key={idx} className="flex items-center gap-3 p-3 bg-[var(--hover-1)] border border-[var(--border-color)] rounded-xl">
                        <PIcon className="w-4 h-4 text-[var(--text-primary)]/30 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-base text-[var(--text-primary)] truncate">
                            {lp.product.display_name || lp.product.name}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${envBadgeClass(lp.environment)}`}>
                              {envLabel(lp.environment)}
                            </span>
                            {lp.is_primary && (
                              <span className="px-1.5 py-0.5 rounded text-xs font-medium
                                             bg-[var(--accent)]/15 text-[var(--accent)] border border-[var(--accent)]/20">
                                Основной
                              </span>
                            )}
                          </div>
                        </div>
                        <button onClick={() => removeLinkedProduct(idx)}
                          className="p-1.5 text-[var(--text-primary)]/30 hover:text-[var(--accent)] transition-colors">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
          {/* Предупреждение о дубликатах email */}
        <DuplicateEmailWarning
          duplicates={findDuplicateEmails(
            formData.email, contactPersons, includeContacts, branches, includeBranches,
          )}
        />

          <div className="flex justify-between pt-2">
            <button
            onClick={handleSubmit}
            disabled={
              isLoading ||
              findDuplicateEmails(
                formData.email, contactPersons, includeContacts, branches, includeBranches,
              ).length > 0
            }
            className="flex items-center gap-2 px-6 py-3 text-base font-semibold text-white
                      bg-[var(--accent)] hover:bg-[var(--accent-light)] rounded-xl transition-all
                      disabled:opacity-40 disabled:cursor-not-allowed shadow-[var(--shadow-md)]"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
            {isLoading ? 'Сохранение...' : 'Создать контрагента'}
          </button>
          </div>
        </div>
      )}
    </div>
  );
}