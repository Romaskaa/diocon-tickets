import React from 'react';

interface DynamicAttributesFieldsProps {
  schemaResponse: any;
  values: Record<string, any>;
  onChange: (key: string, value: any) => void;
  labels?: Record<string, string>; // ← ДОБАВЬ
}

const normalize = (raw: any) => {
  if (!raw.anyOf) return { ...raw, nullable: false };
  const nonNull = raw.anyOf.filter((x: any) => x.type !== 'null');
  const base = nonNull[0] || {};
  return {
    ...base,
    title: raw.title ?? base.title,
    description: raw.description ?? base.description,
    default: raw.default ?? base.default,
    examples: raw.examples ?? base.examples,
    nullable: raw.anyOf.some((x: any) => x.type === 'null'),
  };
};

const parseArrayValue = (value: string) =>
  value.split('\n').map((item) => item.trim()).filter(Boolean);

export const DynamicAttributesFields: React.FC<DynamicAttributesFieldsProps> = ({
  schemaResponse,
  values,
  onChange,
  labels = {}, // ← ДОБАВЬ
}) => {
  if (!schemaResponse?.schema?.properties) return null;

  const required = new Set<string>(schemaResponse.schema.required || []);
  const entries = Object.entries(schemaResponse.schema.properties);

  return (
    <div className="space-y-4">
      {entries.map(([key, rawProp]: [string, any]) => {
        const prop = normalize(rawProp);
        // ← ТУТ ИЗМЕНЕНИЕ: сначала словарь, потом title из schema, потом key
        const label = labels[key] || prop.title || key;
        const desc = prop.description;
        const isRequired = required.has(key);
        const examples = prop.examples;

        const placeholder = examples?.length
          ? Array.isArray(examples[0])
            ? examples[0].join(', ')
            : String(examples[0])
          : undefined;

        // ── Enum (select) ──────────────────────────────────────────────
        if (prop.enum?.length) {
          return (
            <Field key={key} label={label} required={isRequired} description={desc}>
              <select
                value={values[key] ?? ''}
                onChange={(e) => onChange(key, e.target.value || null)}
                className="w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-red-800/60 transition-colors text-sm"
              >
                {!isRequired && (
                  <option value="" className="bg-[#1c1c1c]">
                    — не выбрано —
                  </option>
                )}
                {prop.enum.map((opt: string) => (
                  <option key={opt} value={opt} className="bg-[#1c1c1c]">
                    {opt}
                  </option>
                ))}
              </select>
            </Field>
          );
        }

        // ── Boolean (toggle) ───────────────────────────────────────────
        if (prop.type === 'boolean') {
          return (
            <Field key={key} label={label} required={isRequired} description={desc}>
              <label className="inline-flex items-center gap-3 cursor-pointer select-none">
                <button
                  type="button"
                  role="switch"
                  aria-checked={!!values[key]}
                  onClick={() => onChange(key, !values[key])}
                  className={`relative w-10 h-6 rounded-full transition-colors duration-200 ${
                    values[key] ? 'bg-green-600' : 'bg-white/10'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200 ${
                      values[key] ? 'translate-x-4' : 'translate-x-0'
                    }`}
                  />
                </button>
                <span className="text-sm text-white/70">
                  {values[key] ? 'Да' : 'Нет'}
                </span>
              </label>
            </Field>
          );
        }

        // ── Integer / Number ───────────────────────────────────────────
        if (prop.type === 'integer' || prop.type === 'number') {
          return (
            <Field key={key} label={label} required={isRequired} description={desc}>
              <input
                type="number"
                value={values[key] ?? ''}
                onChange={(e) => {
                  const v = e.target.value;
                  onChange(key, v === '' ? null : Number(v));
                }}
                placeholder={placeholder}
                className="w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-red-800/60 transition-colors text-sm"
              />
            </Field>
          );
        }

        // ── Array<string> ──────────────────────────────────────────────
        if (prop.type === 'array' && prop.items?.type === 'string') {
          const arrayValue = Array.isArray(values[key]) ? values[key] : [];

          return (
            <Field key={key} label={label} required={isRequired} description={desc}>
              <TagInput
                values={arrayValue}
                onChange={(newArr) => onChange(key, newArr.length > 0 ? newArr : null)}
                placeholder={placeholder || 'Введите и нажмите Enter'}
              />
            </Field>
          );
        }

        // ── Date (format: "date") ──────────────────────────────────────
        if (prop.type === 'string' && prop.format === 'date') {
          return (
            <Field key={key} label={label} required={isRequired} description={desc}>
              <input
                type="date"
                value={values[key] ?? ''}
                onChange={(e) => onChange(key, e.target.value || null)}
                className="w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-red-800/60 transition-colors text-sm [color-scheme:dark]"
              />
            </Field>
          );
        }

        // ── Default: string input ──────────────────────────────────────
        return (
          <Field key={key} label={label} required={isRequired} description={desc}>
            <input
              type="text"
              value={values[key] ?? ''}
              onChange={(e) => onChange(key, e.target.value || null)}
              placeholder={placeholder}
              className="w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-red-800/60 transition-colors text-sm"
            />
          </Field>
        );
      })}
    </div>
  );
};

// ─── Sub-components ───────────────────────────────────────────────────────────

const Field = ({
  label,
  required,
  description,
  children,
}: {
  label: string;
  required: boolean;
  description?: string;
  children: React.ReactNode;
}) => (
  <div className="space-y-1.5">
    <label className="block text-sm text-white/60">
      {label}
      {required && <span className="ml-1 text-red-400">*</span>}
    </label>
    {children}
    {description && (
      <p className="text-xs text-white/30 leading-relaxed">{description}</p>
    )}
  </div>
);

const TagInput = ({
  values,
  onChange,
  placeholder,
}: {
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}) => {
  const [input, setInput] = React.useState('');

  const addTag = () => {
    const trimmed = input.trim();
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed]);
    }
    setInput('');
  };

  const removeTag = (index: number) => {
    onChange(values.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
    if (e.key === 'Backspace' && !input && values.length > 0) {
      removeTag(values.length - 1);
    }
  };

  return (
    <div className="w-full min-h-[42px] px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl focus-within:border-red-800/60 transition-colors">
      <div className="flex flex-wrap gap-1.5">
        {values.map((tag, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-white/10 text-sm text-white/80"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(i)}
              className="text-white/40 hover:text-red-400 ml-0.5 transition-colors"
            >
              ×
            </button>
          </span>
        ))}

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={addTag}
          placeholder={values.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[120px] bg-transparent text-white text-sm outline-none placeholder-white/25"
        />
      </div>
    </div>
  );
};