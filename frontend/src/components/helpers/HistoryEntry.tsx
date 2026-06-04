import type { ReactNode } from 'react';
import {
  Clock,
  Image as ImageIcon,
  FileText,
  Plus,
  Minus,
  RefreshCw,
  UserPlus,
  UserMinus,
  Tag,
  Archive,
  MessageSquare,
  Edit,
  Trash2,
  UserCheck,
  Building2,
  FolderOpen,
  CheckCircle,
} from 'lucide-react';

interface HistoryEntryProps {
  entry: any;
  formatDate: (date: string) => string;
  actorNames: Map<string, string>;
}

// ─── Хелперы ──────

// Новый формат
const MD_MEDIA_RE = /!\[[^\]]*\]\(media:\/\/[^)]+\)/g;

// Legacy / переходные форматы
const MD_ATTACHMENT_RE = /!\[[^\]]*\]\(attachment:[^)]+\)/g;
const MD_LOCAL_RE = /!\[[^\]]*\]\(local:[^)]+\)/g;
const LEGACY_IMAGE_RE = /\[\[image:[^\]]+\]\]/g;
const LEGACY_LOCAL_IMAGE_RE = /\[\[local-image:[^\]]+\]\]/g;

function countMatches(value = '', re: RegExp): number {
  return (value.match(re) || []).length;
}

/** Убрать все токены картинок из текста */
function stripMedia(value = ''): string {
  return value
    .replace(MD_MEDIA_RE, '')
    .replace(MD_ATTACHMENT_RE, '')
    .replace(MD_LOCAL_RE, '')
    .replace(LEGACY_IMAGE_RE, '')
    .replace(LEGACY_LOCAL_IMAGE_RE, '')
    .replace(/\*\*\*([^*]+)\*\*\*/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/** Сколько уже сохранённых изображений */
function countStoredImages(value = ''): number {
  return (
    countMatches(value, MD_MEDIA_RE) +
    countMatches(value, MD_ATTACHMENT_RE) +
    countMatches(value, LEGACY_IMAGE_RE)
  );
}

/** Сколько временных local-изображений */
function countLocalImages(value = ''): number {
  return (
    countMatches(value, MD_LOCAL_RE) +
    countMatches(value, LEGACY_LOCAL_IMAGE_RE)
  );
}

/** Сколько всего изображений, независимо от типа */
function countAllImages(value = ''): number {
  return countStoredImages(value) + countLocalImages(value);
}

/** Обрезать длинный текст */
function shorten(value: string, max = 160): string {
  return value.length <= max ? value : value.slice(0, max) + '…';
}

/** Получить отображаемое имя для ID */
function getDisplayName(id: string | null | undefined, actorNames: Map<string, string>): string {
  if (!id) return '';
  // Сначала ищем в actorNames
  const fromActor = actorNames.get(id);
  if (fromActor) return fromActor;
  // Иначе показываем ID в усечённом виде
  return id.slice(0, 8);
}

// ─── Классификация записи истории ─────────────────────────────────────────────

interface EntryAnalysis {
  hidden: boolean;
  textChanged: boolean;
  oldText: string;
  newText: string;
  imagesAdded: number;
  imagesRemoved: number;
  technicalMediaOnly: boolean;
}

function analyzeEntry(entry: any): EntryAnalysis {
  const oldVal = entry.old_value || '';
  const newVal = entry.new_value || '';

  const oldText = stripMedia(oldVal);
  const newText = stripMedia(newVal);
  const textChanged = oldText !== newText;

  const oldTotal = countAllImages(oldVal);
  const newTotal = countAllImages(newVal);

  const oldLocal = countLocalImages(oldVal);
  const newLocal = countLocalImages(newVal);

  const imagesAdded = Math.max(0, newTotal - oldTotal);
  const imagesRemoved = Math.max(0, oldTotal - newTotal);

  // Техническая запись: текст тот же, число картинок то же,
  // но local заменились на server/media
  const technicalMediaOnly =
    !textChanged &&
    oldTotal === newTotal &&
    oldLocal !== newLocal;

  // Полностью local → local, без реального изменения текста
  const onlyLocalOld = oldTotal > 0 && oldLocal === oldTotal;
  const onlyLocalNew = newTotal > 0 && newLocal === newTotal;

  const hidden =
    technicalMediaOnly ||
    (!textChanged && onlyLocalOld && onlyLocalNew);

  return {
    hidden,
    textChanged,
    oldText,
    newText,
    imagesAdded,
    imagesRemoved,
    technicalMediaOnly,
  };
}

// ─── Мета-данные действий ─────────────────────────────────────────────────────

const ACTION_CONFIG: Record<
  string,
  {
    label: string;
    icon: ReactNode;
    color: string;
    formatValue?: (oldVal: string | null, newVal: string | null, actorNames: Map<string, string>) => string;
  }
> = {
  ticket_created: {
    label: 'Создал заявку',
    icon: <Plus className="w-4.5 h-4.5" />,
    color: 'bg-green-500/15 text-green-400',
  },
  description_edited: {
    label: 'Изменил описание',
    icon: <FileText className="w-4.5 h-4.5" />,
    color: 'bg-blue-500/15 text-blue-400',
  },
  status_changed: {
    label: 'Изменил статус',
    icon: <RefreshCw className="w-4.5 h-4.5" />,
    color: 'bg-yellow-500/15 text-yellow-400',
  },
  priority_changed: {
    label: 'Изменил приоритет',
    icon: <RefreshCw className="w-4.5 h-4.5" />,
    color: 'bg-orange-500/15 text-orange-400',
  },
  assigned: {
    label: 'Назначил исполнителя',
    icon: <UserPlus className="w-4.5 h-4.5" />,
    color: 'bg-cyan-500/15 text-cyan-400',
    formatValue: (oldVal, newVal, actorNames) => {
      if (newVal && !oldVal) return ` → ${getDisplayName(newVal, actorNames)}`;
      if (oldVal && !newVal) return `${getDisplayName(oldVal, actorNames)} → Не назначен`;
      if (oldVal && newVal) return `${getDisplayName(oldVal, actorNames)} → ${getDisplayName(newVal, actorNames)}`;
      return '';
    },
  },
  unassigned: {
    label: 'Снял исполнителя',
    icon: <UserMinus className="w-4.5 h-4.5" />,
    color: 'bg-red-500/15 text-red-400',
    formatValue: (oldVal, newVal, actorNames) => {
      if (oldVal) return `${getDisplayName(oldVal, actorNames)} → Не назначен`;
      return '';
    },
  },
  title_edited: {
    label: 'Изменил тему',
    icon: <FileText className="w-4.5 h-4.5" />,
    color: 'bg-blue-500/15 text-blue-400',
  },
  tags_updated: {
    label: 'Обновил теги',
    icon: <Tag className="w-4.5 h-4.5" />,
    color: 'bg-purple-500/15 text-purple-400',
  },
  archived: {
    label: 'Архивировал заявку',
    icon: <Archive className="w-4.5 h-4.5" />,
    color: 'bg-amber-500/15 text-amber-400',
  },
  comment_added: {
    label: 'Добавил комментарий',
    icon: <MessageSquare className="w-4.5 h-4.5" />,
    color: 'bg-blue-500/15 text-blue-400',
  },
  comment_edited: {
    label: 'Изменил комментарий',
    icon: <Edit className="w-4.5 h-4.5" />,
    color: 'bg-blue-500/15 text-blue-400',
  },
  comment_deleted: {
    label: 'Удалил комментарий',
    icon: <Trash2 className="w-4.5 h-4.5" />,
    color: 'bg-red-500/15 text-red-400',
  },
  assigned_to_updated: {
    label: 'Изменил исполнителя',
    icon: <UserCheck className="w-4.5 h-4.5" />,
    color: 'bg-cyan-500/15 text-cyan-400',
    formatValue: (oldVal, newVal, actorNames) => {
      if (oldVal && newVal) return `${getDisplayName(oldVal, actorNames)} → ${getDisplayName(newVal, actorNames)}`;
      if (newVal) return ` → ${getDisplayName(newVal, actorNames)}`;
      if (oldVal) return `${getDisplayName(oldVal, actorNames)} → Не назначен`;
      return '';
    },
  },
  counterparty_changed: {
    label: 'Изменил контрагента',
    icon: <Building2 className="w-4.5 h-4.5" />,
    color: 'bg-purple-500/15 text-purple-400',
  },
  project_changed: {
    label: 'Изменил проект',
    icon: <FolderOpen className="w-4.5 h-4.5" />,
    color: 'bg-purple-500/15 text-purple-400',
  },
  reopened: {
    label: 'Переоткрыл заявку',
    icon: <RefreshCw className="w-4.5 h-4.5" />,
    color: 'bg-orange-500/15 text-orange-400',
  },
  closed: {
    label: 'Закрыл заявку',
    icon: <CheckCircle className="w-4.5 h-4.5" />,
    color: 'bg-green-500/15 text-green-400',
  },
};

const DEFAULT_ACTION_CONFIG = {
  label: 'Изменение',
  icon: <Clock className="w-4.5 h-4.5" />,
  color: 'bg-[var(--hover-1)] text-[var(--text-primary)]/50',
};

// ─── Компонент ────

export const HistoryEntry = ({
  entry,
  formatDate,
  actorNames,
}: HistoryEntryProps) => {
  const isDescEdit = entry.action === 'description_edited';
  const analysis = isDescEdit ? analyzeEntry(entry) : null;

  // Скрываем технические записи
  if (analysis?.hidden) return null;

  const actorName = entry.actor_id
    ? actorNames.get(entry.actor_id) || 'Поддержка'
    : 'Система';

  const config = ACTION_CONFIG[entry.action] || DEFAULT_ACTION_CONFIG;

  let actionLabel = config.label;
  if (isDescEdit && analysis) {
    if (
      !analysis.textChanged &&
      (analysis.imagesAdded > 0 || analysis.imagesRemoved > 0)
    ) {
      actionLabel = 'Изменил вложения';
    }
  }

  const hasMediaChanges =
    !!analysis &&
    (analysis.imagesAdded > 0 || analysis.imagesRemoved > 0);

  const showSimpleDiff =
    !isDescEdit &&
    entry.old_value &&
    entry.new_value;

  // Форматированное значение для diff (с маппингом ID в имя)
  let formattedOldValue = entry.old_value;
  let formattedNewValue = entry.new_value;

  if (config.formatValue) {
    // Если есть кастомный форматтер — используем его для полной строки
    const formatted = config.formatValue(entry.old_value, entry.new_value, actorNames);
    if (formatted) {
      return (
        <div className="flex gap-4">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${config.color}`}>
            {config.icon}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[var(--text-primary)] text-base font-medium">
              {actorName}{' '}
              <span className="text-[var(--text-primary)]/40 font-normal">
                • {actionLabel}
              </span>
            </p>
            <p className="text-[var(--text-primary)]/35 text-sm mt-0.5">
              {formatDate(entry.created_at)}
            </p>
            <div className="mt-2 text-sm">
              <span className="text-[var(--text-primary)]/60">
                {formatted}
              </span>
            </div>
          </div>
        </div>
      );
    }
  }

  // Для assigned/unassigned без кастомного форматтера — маппим ID в имя
  if (entry.action === 'assigned' || entry.action === 'unassigned' || entry.action === 'assigned_to_updated') {
    if (entry.old_value) {
      formattedOldValue = getDisplayName(entry.old_value, actorNames);
    }
    if (entry.new_value) {
      formattedNewValue = getDisplayName(entry.new_value, actorNames);
    }
  }

  return (
    <div className="flex gap-4">
      {/* Иконка */}
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
          isDescEdit && hasMediaChanges
            ? 'bg-violet-500/15 text-violet-400'
            : config.color
        }`}
      >
        {isDescEdit && hasMediaChanges ? (
          <ImageIcon className="w-4.5 h-4.5" />
        ) : (
          config.icon
        )}
      </div>

      <div className="flex-1 min-w-0">
        {/* Заголовок */}
        <p className="text-[var(--text-primary)] text-base font-medium">
          {actorName}{' '}
          <span className="text-[var(--text-primary)]/40 font-normal">
            • {actionLabel}
          </span>
        </p>
        <p className="text-[var(--text-primary)]/35 text-sm mt-0.5">
          {formatDate(entry.created_at)}
        </p>

        {/* Плашка про картинки */}
        {isDescEdit && hasMediaChanges && (
          <div className="mt-2 flex flex-wrap gap-2">
            {analysis!.imagesAdded > 0 && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-green-500/10 border border-green-500/20 text-green-400">
                <Plus className="w-3.5 h-3.5" />
                {analysis!.imagesAdded === 1
                  ? 'Добавлено изображение'
                  : `Добавлено: ${analysis!.imagesAdded}`}
              </span>
            )}

            {analysis!.imagesRemoved > 0 && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400">
                <Minus className="w-3.5 h-3.5" />
                {analysis!.imagesRemoved === 1
                  ? 'Удалено изображение'
                  : `Удалено: ${analysis!.imagesRemoved}`}
              </span>
            )}
          </div>
        )}

        {/* Текстовый diff для описания */}
        {isDescEdit && analysis?.textChanged && (
          <div className="mt-2 space-y-1.5 text-sm">
            {analysis.oldText && (
              <div className="px-3 py-2 rounded-lg bg-red-500/[0.06] border border-red-500/[0.12]">
                <span className="text-red-400/70 line-through break-words">
                  {shorten(analysis.oldText)}
                </span>
              </div>
            )}
            {analysis.newText && (
              <div className="px-3 py-2 rounded-lg bg-green-500/[0.06] border border-green-500/[0.12]">
                <span className="text-green-400/70 break-words">
                  → {shorten(analysis.newText)}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Обычный diff для статуса, приоритета и т.п. */}
        {showSimpleDiff && (
          <div className="mt-2 text-sm">
            <span className="text-[var(--text-primary)]/30 line-through">
              {formattedOldValue}
            </span>
            <span className="text-[var(--text-primary)]/30 mx-2">→</span>
            <span className="text-[var(--text-primary)]/60">
              {formattedNewValue}
            </span>
          </div>
        )}

        {/* Описание для ticket_created */}
        {entry.action === 'ticket_created' && entry.description && (
          <p className="mt-1 text-sm text-[var(--text-primary)]/35">
            {entry.description}
          </p>
        )}
      </div>
    </div>
  );
};