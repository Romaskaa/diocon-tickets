// client.ts
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  User,
  UserProfile,
  Counterparty,
  CreateCounterpartyInput,
  CreateBranchInput,
  ContactPersonInput,
  ContactPerson,
  CounterpartyCustomer,
  PaginatedResponse,
  Invitation,
  RegisterInput,
  Ticket,
  TicketListItem,
  CreateTicketInput,
  TicketStatus,
  TicketPriority,
  InvitationCreate,
  ProjectStatus,
  Project,
  CreateProjectInput,
  UpdateProjectInput,
  ProductsListResponse,
  CreateProductPayload,
  Product,
  ProductAttributesSchemaResponse,
} from '@/types';
import apiClient from './apiClient';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Создаем экземпляр axios
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==== Хелперы для работы с токенами ====
const TOKEN_KEYS = {
  ACCESS: 'access_token',
  REFRESH: 'refresh_token',
  EXPIRES_AT: 'token_expires_at',
} as const;

export const tokenStorage = {
  getAccessToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEYS.ACCESS);
  },

  getRefreshToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEYS.REFRESH);
  },

  setTokens: (accessToken: string, refreshToken: string, expiresAt: number) => {
    localStorage.setItem(TOKEN_KEYS.ACCESS, accessToken);
    localStorage.setItem(TOKEN_KEYS.REFRESH, refreshToken);
    localStorage.setItem(TOKEN_KEYS.EXPIRES_AT, expiresAt.toString());
  },

  clearTokens: () => {
    localStorage.removeItem(TOKEN_KEYS.ACCESS);
    localStorage.removeItem(TOKEN_KEYS.REFRESH);
    localStorage.removeItem(TOKEN_KEYS.EXPIRES_AT);
    localStorage.removeItem('user');
  },

  isTokenExpired: (): boolean => {
    const expiresAt = localStorage.getItem(TOKEN_KEYS.EXPIRES_AT);
    if (!expiresAt) return true;
    // Добавляем буфер в 30 секунд, чтобы обновить токен заранее
    const bufferSeconds = 30;
    return Date.now() >= (parseInt(expiresAt) - bufferSeconds) * 1000;
  }
};

// ==== Флаг для предотвращения множественных refresh запросов ====
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
  config: InternalAxiosRequestConfig;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach(promise => {
    if (error) {
      promise.reject(error);
    } else if (token && promise.config.headers) {
      promise.config.headers.Authorization = `Bearer ${token}`;
      promise.resolve(api(promise.config));
    } else {
      promise.reject(new Error('No token provided'));
    }
  });
  failedQueue = [];
};

// Интерцептор для добавления токена
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Интерцептор для обработки ошибок с бесшовным обновлением токена
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Если ошибка не 401 или запрос уже повторялся - просто отклоняем
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Если уже идет процесс обновления - добавляем запрос в очередь
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject, config: originalRequest });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken = tokenStorage.getRefreshToken();

    if (!refreshToken) {
      // Нет refresh токена - выходим
      tokenStorage.clearTokens();
      window.location.href = '/login';
      return Promise.reject(error);
    }

    try {
      // Вызываем ручку обновления токена
      const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token, expires_at } = response.data;

      // Сохраняем новые токены
      tokenStorage.setTokens(access_token, refresh_token, expires_at);

      // Обновляем заголовок для оригинального запроса
      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
      }

      // Обрабатываем очередь ожидающих запросов
      processQueue(null, access_token);

      // Повторяем оригинальный запрос
      return api(originalRequest);

    } catch (refreshError) {
      // Refresh токен тоже протух или невалиден - очищаем всё и редирект на логин
      console.error('Refresh token failed:', refreshError);
      tokenStorage.clearTokens();
      processQueue(refreshError as Error, null);
      window.location.href = '/login';
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

// ==== Типы ====
interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: number;
}

// ==== Auth API ====
export const authApi = {
  // Вход
  login: async (email: string, password: string): Promise<AuthTokens> => {
    const formData = new URLSearchParams();
    formData.append('grant_type', 'password');
    formData.append('username', email);
    formData.append('password', password);
    formData.append('scope', '');
    formData.append('client_id', 'string');
    formData.append('client_secret', 'string');

    const response = await api.post<AuthTokens>('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    // Автоматически сохраняем токены при логине
    tokenStorage.setTokens(
      response.data.access_token,
      response.data.refresh_token,
      response.data.expires_at
    );

    return response.data;
  },

  // Выход
  logout: () => {
    tokenStorage.clearTokens();
    window.location.href = '/login';
  },

  // Получить текущего пользователя
  getMe: async (): Promise<User> => {
    const response = await api.get<User>('/api/v1/auth/userinfo');
    return response.data;
  },

  // Загрузить аватар
  uploadAvatar: async (file: File): Promise<UserProfile> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<UserProfile>('/api/v1/users/me/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Регистрация по приглашению
  register: async (token: string, data: RegisterInput): Promise<User> => {
    const response = await api.post<User>(`/api/v1/auth/register/${token}`, data);
    return response.data;
  },
};

// ==== Counterparties API ====
export const counterpartiesApi = {
  // Получить список контрагентов (с пагинацией)
  getAll: async (page: number = 1, size: number = 10): Promise<PaginatedResponse<Counterparty>> => {
    const response = await api.get<PaginatedResponse<Counterparty>>('/api/v1/counterparties', {
      params: { page, size },
    });
    return response.data;
  },

  // Получить контрагента по ID
  getById: async (id: string): Promise<Counterparty> => {
    const response = await api.get<Counterparty>(`/api/v1/counterparties/${id}`);
    return response.data;
  },

  // Создать контрагента
  create: async (data: CreateCounterpartyInput): Promise<Counterparty> => {
    const response = await api.post<Counterparty>('/api/v1/counterparties', data);
    return response.data;
  },

  // Обновить контрагента
  update: async (id: string, data: Partial<CreateCounterpartyInput>): Promise<Counterparty> => {
    const response = await api.patch<Counterparty>(`/api/v1/counterparties/${id}`, data);
    return response.data;
  },

  // Удалить контрагента
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/counterparties/${id}`);
  },

  // Добавить обособленное подразделение
  createBranch: async (counterpartyId: string, data: CreateBranchInput): Promise<Counterparty> => {
    const response = await api.post<Counterparty>(`/api/v1/counterparties/${counterpartyId}`, data);
    return response.data;
  },

  // Получить контактное лицо
  getContactPerson: async (id: string): Promise<ContactPerson> => {
    const response = await api.get<ContactPerson>(`/api/v1/counterparties/${id}/contact-person`);
    return response.data;
  },

  // Создать/обновить контактное лицо
  updateContactPerson: async (id: string, data: ContactPersonInput): Promise<ContactPerson> => {
    const response = await api.post<ContactPerson>(`/api/v1/counterparties/${id}/contact-persons`, data);
    return response.data;
  },

  // Получить клиентов контрагента
  getCustomers: async (id: string): Promise<CounterpartyCustomer[]> => {
    const response = await api.get<CounterpartyCustomer[]>(`/api/v1/counterparties/${id}/customers`);
    return response.data;
  },

  // Получить подразделения
  getBranches: async (id: string): Promise<Counterparty[]> => {
    const response = await api.get<PaginatedResponse<Counterparty>>('/api/v1/counterparties', {
      params: { parent_id: id, page: 1, size: 10 },
    });
    return response.data.items.filter(c => c.parent_id === id);
  },
  // Получить привязанные продукты контрагента
  getProducts: async (counterpartyId: string, page = 1, size = 10) => {
  const res = await api.get(`/api/v1/counterparties/${counterpartyId}/products`, {
    params: { page, size },
  });
  return res.data;
},

linkProduct: async (
  counterpartyId: string,
  data: { product_id: string; environment: string; is_primary: boolean }
) => {
  const res = await api.post(`/api/v1/counterparties/${counterpartyId}/products`, data);
  return res.data;
},
};

// ==== Invitations API ====
export const invitationsApi = {
  // Получить список приглашений (с пагинацией)
  getAll: async (page: number = 1, size: number = 10): Promise<PaginatedResponse<Invitation>> => {
    const response = await api.get<PaginatedResponse<Invitation>>('/api/v1/invitations', {
      params: { page, size },
    });
    return response.data;
  },

  // Получить приглашение по ID
  getById: async (id: string): Promise<Invitation> => {
    const response = await api.get<Invitation>(`/api/v1/invitations/${id}`);
    return response.data;
  },

  // Отправить приглашение (ВАЖНО: assigned_role, не role!)
  send: async (data: InvitationCreate): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/api/v1/invitations', data);
    return response.data;
  },

  // Отозвать приглашение
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/invitations/${id}`);
  },
};

// ==== Predict Response ====
interface PredictResponse {
  suggested_priority: TicketPriority;
  suggested_tags: { name: string; color: string }[];
  confidence: {
    priority: number;
    tags: number;
  };
}


// ==================== PROJECTS API ====================
export interface AddMemberRequest {
  user_id: string;
  project_role: 'owner' | 'manager' | 'member' | 'viewer' | 'customer' | 'customer_admin';
}

export interface AddMembersRequest {
  members: AddMemberRequest[];
}
export const projectsApi = {
  // Получить список проектов (с пагинацией)
  getAll: async (
    page: number = 1,
    size: number = 10,
    status?: ProjectStatus
  ): Promise<PaginatedResponse<Project>> => {
    const response = await api.get<PaginatedResponse<Project>>('/api/v1/projects', {
      params: { page, size, status },
    });
    return response.data;
  },

  // Получить проект по ID
  getById: async (id: string): Promise<Project> => {
    const response = await api.get<Project>(`/api/v1/projects/${id}`);
    return response.data;
  },

  // Создать проект
  create: async (data: CreateProjectInput): Promise<Project> => {
    const response = await api.post<Project>('/api/v1/projects', data);
    return response.data;
  },

  // Обновить проект
  update: async (id: string, data: UpdateProjectInput): Promise<Project> => {
    const response = await api.patch<Project>(`/api/v1/projects/${id}`, data);
    return response.data;
  },

  // Архивировать проект
  archive: async (id: string): Promise<Project> => {
    const response = await api.patch<Project>(`/api/v1/projects/${id}`, { status: 'archived' });
    return response.data;
  },

  // Получить проекты контрагента
  getByCounterparty: async (
    counterpartyId: string,
    page: number = 1,
    size: number = 10
  ): Promise<PaginatedResponse<Project>> => {
    const response = await api.get<PaginatedResponse<Project>>('/api/v1/projects', {
      params: { page, size, counterparty_id: counterpartyId },
    });
    return response.data;
  },



  // Добавить одного участника
  addMember: async (projectId: string, data: AddMemberRequest): Promise<Project> => {
    const response = await api.post<Project>(`/api/v1/projects/${projectId}/memberships`, {
      members: [data]
    });
    return response.data;
  },

  // Добавить нескольких участников
  addMembers: async (projectId: string, members: AddMemberRequest[]): Promise<Project> => {
    const response = await api.post<Project>(`/api/v1/projects/${projectId}/memberships`, {
      members
    });
    return response.data;
  },

  // Получить мои проекты (для customer)
  getMyProjects: async (
    role: 'all' | 'owner' | 'member' = 'all',
    page: number = 1,
    size: number = 10
  ): Promise<PaginatedResponse<Project>> => {
    const response = await api.get<PaginatedResponse<Project>>('/api/v1/projects/my', {
      params: { role, page, size },
    });
    return response.data;
  },



};

// projectsApi в client.ts




// ==== Tickets (Заявки) API ====
export const ticketsApi = {
  // AI-помощник: определение приоритета и тегов
  predict: async (title: string, description: string): Promise<PredictResponse> => {
    const response = await api.post<PredictResponse>('/api/v1/tickets/predict', {
      title,
      description,
    });
    return response.data;
  },

  // Получить мои заявки (основной метод)
  getMy: async (
    page: number = 1,
    size: number = 10,
    status?: TicketStatus,
    priority?: TicketPriority
  ): Promise<PaginatedResponse<TicketListItem>> => {
    const response = await api.get<PaginatedResponse<TicketListItem>>('/api/v1/tickets/me', {
      params: { page, size, status, priority },
    });
    return response.data;
  },

  // Получить все заявки (для support и выше)
  getAll: async (
    page: number = 1,
    size: number = 10,
    status?: TicketStatus,
    priority?: TicketPriority
  ): Promise<PaginatedResponse<TicketListItem>> => {
    const response = await api.get<PaginatedResponse<TicketListItem>>('/api/v1/tickets', {
      params: { page, size, status, priority },
    });
    return response.data;
  },

  // Получить заявку по ID
  getById: async (id: string): Promise<Ticket> => {
    const response = await api.get<Ticket>(`/api/v1/tickets/${id}`);
    return response.data;
  },

  // Создать заявку
  create: async (data: CreateTicketInput): Promise<Ticket> => {
    const response = await api.post<Ticket>('/api/v1/tickets', data);
    return response.data;
  },

  // Обновить заявку
  update: async (id: string, data: Partial<Ticket>): Promise<Ticket> => {
    const response = await api.patch<Ticket>(`/api/v1/tickets/${id}`, data);
    return response.data;
  },

  // Получить комментарий
  getComments: async (
    ticketId: string,
    params?: {
      include_internal?: boolean;
      page?: number;
      size?: number;
    }
  ): Promise<PaginatedResponse<Comment>> => {
    const response = await api.get<PaginatedResponse<Comment>>(
      `/api/v1/tickets/${ticketId}/comments`,
      {
        params: {
          include_internal: params?.include_internal || false,
          page: params?.page || 1,
          size: params?.size || 50
        }
      }
    );
    return response.data;
  },

  // Добавить комментарий - исправлен (возвращает комментарий, а не тикет)
  addComment: async (
    ticketId: string,
    text: string,
    type: 'public' | 'internal' | 'note' = 'public'
  ): Promise<Comment> => {
    const response = await api.post<Comment>(`/api/v1/tickets/${ticketId}/comments`, {
      text,
      type
    });
    return response.data;
  },

  // Редактировать комментарий (НОВЫЙ МЕТОД)
  updateComment: async (
    ticketId: string,
    commentId: string,
    text: string
  ): Promise<Comment> => {
    const response = await api.patch<Comment>(
      `/api/v1/tickets/${ticketId}/comments/${commentId}`,
      { text }
    );
    return response.data;
  },



  getAllWithFilters: async (
    page: number = 1,
    size: number = 10,
    filters?: {
      status?: TicketStatus;
      priority?: TicketPriority;
      counterparty_id?: string;
      project_id?: string;
      created_by?: string;
      reporter_id?: string;
      assigned_to?: string;
      search?: string;
      tags?: string[];
    }
  ): Promise<PaginatedResponse<TicketListItem>> => {
    const params: any = { page, size };

    if (filters?.status) params.status = filters.status;
    if (filters?.priority) params.priority = filters.priority;
    if (filters?.counterparty_id) params.counterparty_id = filters.counterparty_id;
    if (filters?.project_id) params.project_id = filters.project_id;
    if (filters?.created_by) params.created_by = filters.created_by;
    if (filters?.reporter_id) params.reporter_id = filters.reporter_id;
    if (filters?.assigned_to) params.assigned_to = filters.assigned_to;
    if (filters?.search) params.search = filters.search;
    if (filters?.tags && filters.tags.length > 0) params.tags = filters.tags.join(',');

    const response = await api.get<PaginatedResponse<TicketListItem>>('/api/v1/tickets', { params });
    return response.data;
  },

  // Найти тикет по номеру (если бэкенд поддерживает)
  getByNumber: async (number: string): Promise<Ticket | null> => {
    try {
      // Пробуем через фильтр search
      const response = await api.get<PaginatedResponse<TicketListItem>>('/api/v1/tickets', {
        params: { search: number, page: 1, size: 1 }
      });

      if (response.data.items.length > 0) {
        const found = response.data.items[0];
        if (found.number === number) {
          return await ticketsApi.getById(found.id);
        }
      }
      return null;
    } catch (error) {
      console.error('Failed to find ticket by number:', error);
      return null;
    }
  },


  // Добавить метод для получения сотрудников контрагента (для фильтра по инициатору)
  getCompanyUsers: async (counterpartyId: string): Promise<CounterpartyCustomer[]> => {
    const response = await api.get<PaginatedResponse<CounterpartyCustomer>>(
      `/api/v1/counterparties/${counterpartyId}/customers`,
      { params: { page: 1, size: 100 } }
    );
    return response.data.items;
  },
  // Назначить исполнителя
  assignTicket: async (ticketId: string, assigneeId: string): Promise<Ticket> => {
    const response = await api.post<Ticket>(`/api/v1/tickets/${ticketId}/assign`, {
      assignee_id: assigneeId
    });
    return response.data;
  },

  // Изменить статус тикета
  updateTicketStatus: async (ticketId: string, status: TicketStatus): Promise<Ticket> => {
    const response = await api.patch<Ticket>(`/api/v1/tickets/${ticketId}/status`, {
      status
    });
    return response.data;
  },

  // Получить ответы на комментарий
  getCommentReplies: async (
    commentId: string,
    params?: {
      include_internal?: boolean;
      page?: number;
      size?: number;
    }
  ): Promise<PaginatedResponse<Comment>> => {
    const response = await api.get<PaginatedResponse<Comment>>(
      `/api/v1/tickets/comments/${commentId}/replies`,
      {
        params: {
          include_internal: params?.include_internal || false,
          page: params?.page || 1,
          size: params?.size || 10
        }
      }
    );
    return response.data;
  },

  // Ответить на комментарий
  replyToComment: async (
    ticketId: string,
    commentId: string,
    text: string,
    type: 'public' | 'internal' | 'note' = 'public'
  ): Promise<Comment> => {
    const response = await api.post<Comment>(
      `/api/v1/tickets/${ticketId}/comments/${commentId}/replies`,
      { text, type }
    );
    return response.data;
  },

  // Редактировать комментарий (обновлённый путь)
  editComment: async (
    ticketId: string,
    commentId: string,
    text: string
  ): Promise<Comment> => {
    const response = await api.patch<Comment>(
      `/api/v1/tickets/${ticketId}/comments/${commentId}`,
      { text }
    );
    return response.data;
  },

  // Удалить комментарий (обновлённый путь)
  deleteComment: async (
    ticketId: string,
    commentId: string
  ): Promise<void> => {
    await api.delete(`/api/v1/tickets/${ticketId}/comments/${commentId}`);
  },
  // Получить реакции комментария
  getCommentReactions: async (commentId: string): Promise<{ reaction_counts: Record<string, number>; user_reactions: string[] }> => {
    const response = await api.get(`/api/v1/tickets/comments/${commentId}/reactions`);
    return response.data;
  },

  // Поставить/убрать реакцию
  toggleReaction: async (commentId: string, reactionType: string): Promise<void> => {
    await api.post(`/api/v1/tickets/comments/${commentId}/reactions`, {
      reaction_type: reactionType
    });
  },

archiveTicket: (ticketId: string) =>
  api.delete(`/api/v1/tickets/${ticketId}`).then(r => r.data),

};


// ==== Users API ====
export const usersApi = {
  // Получить клиентов (пользователей) контрагента
  getCustomers: async (
    counterpartyId: string,
    page: number = 1,
    size: number = 100
  ): Promise<PaginatedResponse<CounterpartyCustomer>> => {
    const response = await api.get<PaginatedResponse<CounterpartyCustomer>>(
      `/api/v1/counterparties/${counterpartyId}/customers`,
      { params: { page, size } }
    );
    return response.data;
  },
  getSupports: async (page: number = 1, size: number = 100): Promise<PaginatedResponse<SimpleUser>> => {
    const response = await api.get<PaginatedResponse<SimpleUser>>('/api/v1/users/supports', {
      params: { page, size }
    });
    return response.data;
  },
  // В usersApi добавьте:
  getAllUsers: async (page: number = 1, size: number = 100): Promise<PaginatedResponse<SimpleUser>> => {
    const response = await api.get<PaginatedResponse<SimpleUser>>('/api/v1/users', {
      params: { page, size }
    });
    return response.data;
  },

};

export default api;

// API для Коррекции текста
export const proofreadingApi = {
  spellCheck: async (text: string) => {
    const response = await api.post('/api/v1/proofreading/spell-check', { text });
    return response.data;
  }
};



//API Product
export const productsApi = {
  getProducts: async (params: {
    page?: number;
    size?: number;
    category?: string;
    status?: string;
    query?: string;
  }) => {
    const response = await api.get('/api/v1/products', { params });
    return response.data;
  },

  createProduct: async (payload: {
    name: string;
    vendor: string;
    category: string;
    description?: string;
    version?: string;
    status: string;
    attributes: Record<string, any>;
  }) => {
    const response = await api.post('/api/v1/products', payload);
    return response.data;
  },

  getCategorySchema: async (category: string) => {
    const response = await api.get(
      `/api/v1/products/categories/${encodeURIComponent(category)}/attributes-schema`
    );
    return response.data;
  },
};