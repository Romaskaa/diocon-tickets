import { 
  Clock, Image as ImageIcon, FileText, Plus, Minus, RefreshCw, 
  UserPlus, UserMinus, Tag, Archive, MessageSquare, Edit, Trash2,
  UserCheck, Building2, FolderOpen, CheckCircle
} from 'lucide-react';
interface HistoryEntryProps {
  entry: any;
  formatDate: (date: string) => string;
  actorNames: Map<string, string>;
}

// ─── Хелперы ──────────────────────────────────────────────────────────────────

const MEDIA_RE = /\[\[(local-image|image):([^\]]+)\]\]/g;

/** Убрать все токены картинок из текста */
function stripMedia(value = ''): string {
  return value
    .replace(MEDIA_RE, '')
    .replace(/\*\*\*([^*]+)\*\*\*/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/** Посчитать токены определённого типа */
function countTokens(value = '', type?: 'image' | 'local-image'): number {
  const re = type
    ? new RegExp(`\\[\\[${type}:[^\\]]+\\]\\]`, 'g')
    : MEDIA_RE;
  return (value.match(re) || []).length;
}

/** Обрезать длинный текст */
function shorten(value: string, max = 160): string {
  return value.length <= max ? value : value.slice(0, max) + '…';
}

// ─── Классификация записи истории ─────────────────────────────────────────────

interface EntryAnalysis {
  /** Полностью скрыть (технический мусор) */
  hidden: boolean;
  /** Текст изменился */
  textChanged: boolean;
  /** Старый текст (без медиа) */
  oldText: string;
  /** Новый текст (без медиа) */
  newText: string;
  /** Сколько картинок добавлено */
  imagesAdded: number;
  /** Сколько картинок удалено */
  imagesRemoved: number;
  /** Только техническая обработка медиа (local→server) */
  technicalMediaOnly: boolean;
}

function analyzeEntry(entry: any): EntryAnalysis {
  const oldVal = entry.old_value || '';
  const newVal = entry.new_value || '';

  const oldText = stripMedia(oldVal);
  const newText = stripMedia(newVal);
  const textChanged = oldText !== newText;

  const oldTotal = countTokens(oldVal);
  const newTotal = countTokens(newVal);
  const oldLocal = countTokens(oldVal, 'local-image');
  const newLocal = countTokens(newVal, 'local-image');
  const oldServer = countTokens(oldVal, 'image');
  const newServer = countTokens(newVal, 'image');

  const imagesAdded = Math.max(0, newTotal - oldTotal);
  const imagesRemoved = Math.max(0, oldTotal - newTotal);

  // Техническая запись: текст не менялся, просто local-image → image
  const technicalMediaOnly =
    !textChanged &&
    oldTotal === newTotal &&
    oldLocal !== newLocal;

  // Полностью скрыть:
  // 1. Технический upload (local→server, текст тот же)
  // 2. Промежуточные состояния (только local-image ↔ local-image)
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

const ACTION_CONFIG: Record<string, {
  label: string;
  icon: React.ReactNode;
  color: string;
}> = {
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
  },
  unassigned: {
    label: 'Снял исполнителя',
    icon: <UserMinus className="w-4.5 h-4.5" />,
    color: 'bg-red-500/15 text-red-400',
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
  color: 'bg-white/10 text-white/50',
};

// ─── Компонент ────────────────────────────────────────────────────────────────

export const HistoryEntry = ({
  entry,
  formatDate,
  actorNames,
}: HistoryEntryProps) => {
  const isDescEdit = entry.action === 'description_edited';
  const analysis = isDescEdit
    ? analyzeEntry(entry)
    : null;

  // Скрываем технические записи
  if (analysis?.hidden) return null;

  const actorName = entry.actor_id
    ? actorNames.get(entry.actor_id) || 'Поддержка'
    : 'Система';

  const config = ACTION_CONFIG[entry.action] || DEFAULT_ACTION_CONFIG;

  // Для description_edited уточняем label
  let actionLabel = config.label;
  if (isDescEdit && analysis) {
    if (!analysis.textChanged && (analysis.imagesAdded > 0 || analysis.imagesRemoved > 0)) {
      actionLabel = 'Изменил вложения';
    }
  }

  const hasMediaChanges =
    analysis && (analysis.imagesAdded > 0 || analysis.imagesRemoved > 0);

  // Для не-description действий показываем simple diff если есть old/new
  const showSimpleDiff =
    !isDescEdit &&
    entry.old_value &&
    entry.new_value;

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
        <p className="text-white text-base font-medium">
          {actorName} <span className="text-white/40 font-normal">• {actionLabel}</span>
        </p>
        <p className="text-white/35 text-sm mt-0.5">{formatDate(entry.created_at)}</p>

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

        {/* Simple diff для статуса, приоритета и т.д. */}
        {showSimpleDiff && (
          <div className="mt-2 text-sm">
            <span className="text-white/30 line-through">{entry.old_value}</span>
            <span className="text-white/30 mx-2">→</span>
            <span className="text-white/60">{entry.new_value}</span>
          </div>
        )}

        {/* Описание для ticket_created и других без diff */}
        {entry.action === 'ticket_created' && entry.description && (
          <p className="mt-1 text-sm text-white/35">{entry.description}</p>
        )}
      </div>
    </div>
  );
};