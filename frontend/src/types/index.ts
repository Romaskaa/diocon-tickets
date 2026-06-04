// Роли пользователей
export type UserRole = 
  | 'customer_admin'    // Администратор клиента
  | 'customer'          // Клиент
  | 'support_agent'     // Агент поддержки
  | 'support_manager'   // Менеджер поддержки
  | 'executor'          // Исполнитель
  | 'admin';            // Администратор системы

export const ROLE_LABELS: Record<UserRole, string> = {
  customer_admin: 'Администратор клиента',
  customer: 'Клиент',
  support_agent: 'Агент поддержки',
  support_manager: 'Менеджер поддержки',
  executor: 'Исполнитель',
  admin: 'Администратор',
};

export const ROLE_COLORS: Record<UserRole, string> = {
  customer_admin: 'bg-[var(--info)]/8 text-[var(--info)] border-[var(--info)]/15',
  customer: 'bg-cyan-500/20 text-[var(--info)] border-cyan-500/30',
  support_agent: 'bg-[var(--success)]/8 text-[var(--success)] border-[var(--success)]/15',
  support_manager: 'bg-[var(--info)]/8 text-[var(--info)] border-[var(--info)]/15',
  executor: 'bg-[var(--warning)]/8 text-[var(--warning)] border-[var(--warning)]/15',
  admin: 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]/15',
};

// Пользователь
export interface User {
  user_id: string;
  username: string;
  full_name: string | null;
  email: string;
  role: UserRole;
  avatar_url?: string | null;
  counterparty_id?: string | null;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

// Ответ при загрузке аватара
export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  counterparty_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Мессенджеры контактного лица
export interface ContactMessengers {
  telegram?: string;
  vk?: string;
  whatsapp?: string;
}

// Контактное лицо (для создания)
export interface ContactPersonInput {
  first_name: string;
  last_name: string;
  middle_name?: string;
  phone?: string;
  email?: string;
  messengers?: ContactMessengers;
}

// Контактное лицо (из API)
export interface ContactPerson {
  full_name: string;
  phone?: string;
  email?: string;
  messengers?: ContactMessengers;
}

// Тип контрагента
export type CounterpartyType = 'Физическое лицо' | 'Юридическое лицо' | 'ИП';

// Контрагент
export interface Counterparty {
  id: string;
  created_at: string;
  updated_at: string;
  counterparty_type: CounterpartyType;
  name: string;
  legal_name: string;
  inn: string;
  kpp?: string;
  okpo?: string;
  phone?: string;
  email?: string;
  address: string;
  avatar_url?: string | null;
  contact_person?: ContactPerson | null;
  parent_id?: string | null;
  is_active: boolean;
  is_head: boolean;
  is_branch: boolean;
}

// Создание контрагента
export interface CreateCounterpartyInput {
  counterparty_type: CounterpartyType;
  name: string;
  legal_name: string;
  inn: string;
  kpp?: string;
  okpo?: string;
  phone?: string;
  email?: string;
  address: string;
  contact_person?: ContactPersonInput;
}

// Создание подразделения
export interface CreateBranchInput {
  name: string;
  legal_name: string;
  kpp?: string;
  okpo?: string;
  phone?: string;
  email?: string;
  address: string;
}

// Пагинированный ответ
export interface PaginatedResponse<T> {
  page: number;
  size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  items: T[];
}

// Клиент контрагента
export interface CounterpartyCustomer {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  counterparty_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}


export interface SimpleUser {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  counterparty_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}


// ========== ЗАЯВКИ (ТИКЕТЫ) ==========


export const ALL_STATUSES: TicketStatus[] = [
  'Новый',
  'Открыт',
  'В работе',
  'Ожидает ответа',
  'Решён',
  'Закрыт',
  'Переоткрыт',
];

// Статус заявки (из API)
export type TicketStatus = 
  | 'Новый'
  | 'Открыт'
  | 'В работе'
  | 'Ожидает ответа'
  | 'Решён'
  | 'Закрыт'
  | 'Переоткрыт';

export const TICKET_STATUS_LIST: TicketStatus[] = [
  'Новый',
  'Открыт',
  'В работе',
  'Ожидает ответа',
  'Решён',
  'Закрыт',
  'Переоткрыт',
];

export const TICKET_STATUS_COLORS: Record<TicketStatus, string> = {
  'Новый': 'bg-[var(--info)]/8 text-[var(--info)] border-[var(--info)]/15',
  'Открыт': 'bg-cyan-500/20 text-[var(--info)] border-cyan-500/30',
  'В работе': 'bg-[var(--warning)]/8 text-[var(--warning)] border-[var(--warning)]/15',
  'Ожидает ответа': 'bg-[var(--info)]/8 text-[var(--info)] border-[var(--info)]/15',
  'Решён': 'bg-[var(--success)]/8 text-[var(--success)] border-[var(--success)]/15',
  'Закрыт': 'bg-[var(--text-muted)]/8 text-[var(--text-muted)] border-[var(--text-muted)]/15',
  'Переоткрыт': 'bg-[var(--warning)]/8 text-[var(--warning)] border-[var(--warning)]/15',
};

// Приоритет заявки (из API)
export type TicketPriority = 'Низкий' | 'Средний' | 'Высокий' | 'Критический';

export const TICKET_PRIORITY_LIST: TicketPriority[] = [
  'Низкий',
  'Средний',
  'Высокий',
  'Критический',
];

// Тип тикета
export type TicketType =
  | 'Инцидент'
  | 'Запрос на услугу'
  | 'Консультация'
  | 'Жалоба'
  | 'Задача'
  | 'Проблема'
  | 'Запрос на изменение'
  | 'Улучшение'
  | 'Прочее';

export const TICKET_TYPE_LIST: TicketType[] = [
  'Инцидент',
  'Запрос на услугу',
  'Консультация',
  'Жалоба',
  'Задача',
  'Проблема',
  'Запрос на изменение',
  'Улучшение',
  'Прочее',
];

export const TICKET_TYPE_COLORS: Record<TicketType, string> = {
  'Инцидент': 'bg-red-500/20 text-red-400 border-red-500/30',
  'Запрос на услугу': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  'Консультация': 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  'Жалоба': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  'Задача': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  'Проблема': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  'Запрос на изменение': 'bg-green-500/20 text-green-400 border-green-500/30',
  'Улучшение': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  'Прочее': 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

export const TICKET_PRIORITY_COLORS: Record<TicketPriority, string> = {
  'Низкий': 'bg-[var(--success)]/8 text-[var(--success)] border-[var(--success)]/15',
  'Средний': 'bg-[var(--warning)]/8 text-[var(--warning)] border-[var(--warning)]/15',
  'Высокий': 'bg-[var(--warning)]/8 text-[var(--warning)] border-[var(--warning)]/15',
  'Критический': 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]/15',
};

// Тег заявки
export interface TicketTag {
  name: string;
  color: string;
}

// Вложение
export interface TicketAttachment {
  id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  storage_key: string;
  owner_type: string;
  owner_id: string;
  uploaded_by: string;
  uploaded_at: string;
}

// Комментарий
export interface TicketComment {
  id: string;
  created_at: string;
  updated_at: string;
  author_id: string;
  author_role: UserRole;
  text: string;
  type: 'public' | 'internal';
  attachments: TicketAttachment[];
}

// История изменений
export interface TicketHistoryItem {
  created_at: string;
  actor_id: string;
  action: string;
  old_value: string | null;
  new_value: string | null;
  description: string;
}

// Заявка (полная, из GET /tickets/{id})
export interface Ticket {
  id: string;
  created_at: string;
  counterparty_id: string | null;
  created_by_role: UserRole;
  created_by: string;
  title: string;
  description: string;
  status: TicketStatus;
  reporter_id: string | null;
  priority: TicketPriority;
  type: TicketType;
  assigned_to: string | null;
  closed_at: string | null;
  tags: TicketTag[];
  attachments: TicketAttachment[];
  comments: TicketComment[];
  history: TicketHistoryItem[];
  number: string;
  is_archived: boolean;
}

// Заявка (краткая, из GET /tickets списка)
export interface TicketListItem {
  id: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  title: string;
  status: TicketStatus;
  priority: TicketPriority;
  type: TicketType;
  number: string;
  closed_at: string | null;
  project_id?: string | null;
  counterparty_id?: string | null;
  reporter_id?: string | null;
}

// Создание заявки
export interface CreateTicketInput {
  title: string;
  description: string;
  priority: TicketPriority;
  counterparty_id?: string | null;
  tags?: TicketTag[];
}

export interface Comment {
  id: string;
  created_at: string;
  updated_at: string;
  ticket_id: string;
  parent_comment_id: string;
  author_id: string;
  author_role: string;
  text: string;
  type: 'public' | 'internal' | 'note';
  attachments: any[];
}

// ========== УВЕДОМЛЕНИЯ ==========

export interface Notification {
  id: string;
  type: 'ticket_created' | 'ticket_assigned' | 'ticket_updated' | 'comment_added' | 'ticket_resolved';
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  ticket_id?: string;
}

export interface NotificationSettings {
  email_new_ticket: boolean;
  email_assigned: boolean;
  email_comment: boolean;
  email_resolved: boolean;
  email_daily_digest: boolean;
  push_enabled: boolean;
  push_new_ticket: boolean;
  push_comment: boolean;
  sound_enabled: boolean;
}

// ========== ПРИГЛАШЕНИЯ ==========

// Приглашение (из API)
export interface Invitation {
  id: string;
  created_at: string;
  invited_by: string;
  email: string;
  assigned_role: UserRole;
  counterparty_id: string | null;
  expires_at: string;
  used_at: string | null;
  is_used: boolean;
}

// Создание приглашения (ВАЖНО: assigned_role, не role!)
export interface InvitationCreate {
  email: string;
  assigned_role: UserRole;
  counterparty_id?: string;
}

// Роли которые можно приглашать
export const INVITABLE_ROLES: UserRole[] = [
  'customer',
  'customer_admin',
  'support_agent',
  'support_manager',
  'executor',
];

// Роли которые требуют контрагента
export const ROLES_REQUIRE_COUNTERPARTY: UserRole[] = [
  'customer',
  'customer_admin',
];

// Роли которые могут отправлять приглашения
export const CAN_INVITE_ROLES: UserRole[] = [
  'support_agent',
  'support_manager',
  'executor',
  'admin',
];

// Регистрация по приглашению
export interface RegisterInput {
  username: string;
  full_name: string;
  password: string;
}

// ========== СОТРУДНИКИ ==========

export interface Employee {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  role: UserRole;
  position: string;
  department: string;
  avatar_url?: string | null;
  is_active: boolean;
  tickets_in_progress: number;
  tickets_resolved: number;
}


export interface Attachment {
  id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  storage_key: string;
  owner_type: string;
  owner_id: string;
  uploaded_by: string;
  uploaded_at: string;
}


// ==================== PROJECTS ====================

export type ProjectStatus = 'active' | 'archived' | 'deleted';

export interface ProjectParticipant {
  user_id: string;
  project_role: 'owner' | 'manager' | 'member' | 'viewer';
  added_at: string;
  added_by: string;
}

export interface Project {
  memberships: any;
  id: string;
  name: string;
  key: string;
  description: string | null;
  counterparty_id: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  status: ProjectStatus;
  participants: ProjectParticipant[];
}

export interface KeySuggestionResponse {
  key: string;
}

export interface KeyAvailabilityResponse {
  available: boolean;
  suggestions: string[];
}

export interface CreateProjectInput {
  name: string;
  key: string;
  description?: string;
  counterparty_id: string;
  owner_id?: string; // если не указан, ставится текущий пользователь
}

export interface UpdateProjectInput {
  name?: string;
  description?: string;
  status?: ProjectStatus;
}

// Обновляем тип для создания тикета
export interface CreateTicketInput {
  title: string;
  description: string;
  priority: TicketPriority;
  type: TicketType;
  project_id?: string | null;
  counterparty_id?: string | null;
  counterparty_name?: string | null;
  reporter_id?: string | null;
  tags?: TicketTag[];
}





// ==================== PRODUCT ====================

export interface Product {
  id: string;
  name: string;
  vendor: string;
  category: string;
  description?: string;
  version?: string;
  status: string;
  attributes: Record<string, any>;
  created_at: string;
  updated_at: string;
  display_name?: string;
  created_by?: string;
  updated_by?: string;
}

export interface ProductsListResponse {
  page: number;
  size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  items: Product[];
}

export interface JsonSchemaProperty {
  type?: string;
  title?: string;
  description?: string;
  enum?: string[];
  default?: any;
  items?: {
    type?: string;
  };
  anyOf?: JsonSchemaProperty[];
}

export interface ProductAttributesSchemaResponse {
  category: string;
  schema: {
    type: string;
    title?: string;
    description?: string;
    required?: string[];
    properties: Record<string, JsonSchemaProperty>;
    additionalProperties?: boolean;
    $schema?: string;
  };
}

export interface CreateProductPayload {
  name: string;
  vendor: string;
  category: string;
  description?: string;
  version?: string;
  status: string;
  attributes: Record<string, any>;
}



// ==================== TASKS / ЗАДАЧИ ====================

export type TaskPriority = 'Низкий' | 'Средний' | 'Высокий' | 'Критический';

export const TASK_PRIORITY_LIST: TaskPriority[] = [
  'Низкий',
  'Средний',
  'Высокий',
  'Критический',
];

export const TASK_PRIORITY_COLORS: Record<TaskPriority, string> = {
  'Низкий': 'bg-[var(--success)]/8 text-[var(--success)] border-emerald-500/30',
  'Средний': 'bg-yellow-500/15 text-[var(--warning)] border-yellow-500/30',
  'Высокий': 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  'Критический': 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]/15',
};

export type TaskStatus =
  | 'backlog'
  | 'todo'
  | 'in_progress'
  | 'blocked'
  | 'review'
  | 'done'
  | 'cancelled';

export const TASK_STATUS_LIST: TaskStatus[] = [
  'backlog',
  'todo',
  'in_progress',
  'blocked',
  'review',
  'done',
  'cancelled',
];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  backlog: 'Бэклог',
  todo: 'К выполнению',
  in_progress: 'В работе',
  blocked: 'Заблокировано',
  review: 'На ревью',
  done: 'Готово',
  cancelled: 'Отменено',
};

export const TASK_STATUS_COLORS: Record<TaskStatus, string> = {
  backlog: 'bg-[var(--hover-2)] text-[var(--text-primary)]/60 border-[var(--border-color)]',
  todo: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  in_progress: 'bg-yellow-500/15 text-[var(--warning)] border-yellow-500/30',
  blocked: 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]/15',
  review: 'bg-violet-500/15 text-violet-400 border-violet-500/30',
  done: 'bg-[var(--success)]/8 text-[var(--success)] border-emerald-500/30',
  cancelled: 'bg-neutral-500/15 text-[var(--text-muted)] border-[var(--text-muted)]/15',
};

export interface TaskCreateInput {
  ticket_id?: string | null;
  project_id?: string | null;
  title: string;
  description?: string | null;
  priority: TaskPriority;
  story_points?: number | null;
  assignee_id?: string | null;
  reviewer_id?: string | null;
  estimated_hours?: number | string | null;
  due_date?: string | null;
  mark_as_todo?: boolean;
}

export interface TaskUpdateInput {
  title?: string;
  description?: string | null;
  priority?: TaskPriority;
  story_points?: number | null;
  estimated_hours?: number | string | null;
  due_date?: string | null;
}

export interface TaskAttachment {
  id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  storage_key: string;
  owner_type: string;
  owner_id: string;
  uploaded_by: string;
  uploaded_at: string;
}

export interface TaskResponse {
  ticket_id: string | null;
  project_id: string | null;
  title: string;
  description: string | null;
  priority: TaskPriority;
  story_points: number | null;
  assignee_id: string | null;
  reviewer_id: string | null;
  estimated_hours: string | null;
  due_date: string | null;

  id: string;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  number: string;
  status: TaskStatus;
  actual_hours: string;
  started_at: string | null;
  completed_at: string | null;
  created_by: string;
  attachments: TaskAttachment[];
}

export interface TaskKanbanItem {
  id: string;
  created_at: string;
  updated_at: string;
  number: string;
  title: string;
  priority: TaskPriority;
  story_points: number | null;
  assignee_id: string | null;
  status: TaskStatus;
  due_date: string | null;
  ticket_id: string | null;
  project_id: string | null;
}

export interface TaskKanbanColumn {
  status: TaskStatus;
  label: string;
  tasks: PaginatedResponse<TaskKanbanItem>;
}

export type TaskKanbanContext =
  | { type: 'project'; project_id: string }
  | { type: 'ticket'; ticket_id: string }
  | { type: 'internal' }
  | { type: 'assignee'; assignee_id: string }
  | { type: 'my' };

export interface TaskKanbanResponse {
  context: TaskKanbanContext;
  columns: TaskKanbanColumn[];
  total_tasks: number;
}

export interface TaskKanbanFilters {
  page?: number;
  size?: number;
  priorities?: TaskPriority[];
  overdue_only?: boolean;
}

export interface TaskChangeStatusInput {
  new_status: TaskStatus;
}

export interface TaskAssignInput {
  assignee_id: string;
}

export interface TaskRequestReviewInput {
  reviewer_id: string;
}

export type TaskReviewAction = 'approve' | 'reject';

export interface TaskReviewInput {
  action: TaskReviewAction;
}