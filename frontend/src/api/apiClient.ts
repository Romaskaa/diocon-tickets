import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = '/api/v1';

// Создаём axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Accept': 'application/json',
  },
});

// Хелперы для работы с токенами
export const tokenStorage = {
  getAccessToken: (): string | null => {
    return localStorage.getItem('access_token') || getCookie('access_token');
  },
  
  getRefreshToken: (): string | null => {
    return localStorage.getItem('refresh_token') || getCookie('refresh_token');
  },
  
  setTokens: (accessToken: string, refreshToken: string, expiresAt: number) => {
    // Сохраняем в localStorage
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    localStorage.setItem('token_expires_at', expiresAt.toString());
    
    // Сохраняем в cookies
    const accessExpires = new Date(expiresAt * 1000);
    const refreshExpires = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000); // 30 дней
    
    setCookie('access_token', accessToken, accessExpires);
    setCookie('refresh_token', refreshToken, refreshExpires);
  },
  
  clearTokens: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_expires_at');
    
    deleteCookie('access_token');
    deleteCookie('refresh_token');
  },
  
  isTokenExpired: (): boolean => {
    const expiresAt = localStorage.getItem('token_expires_at');
    if (!expiresAt) return true;
    return Date.now() >= parseInt(expiresAt) * 1000;
  }
};

// Cookie helpers
function setCookie(name: string, value: string, expires: Date) {
  document.cookie = `${name}=${value}; expires=${expires.toUTCString()}; path=/; SameSite=Strict`;
}

function getCookie(name: string): string | null {
  const matches = document.cookie.match(new RegExp(
    '(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)'
  ));
  return matches ? decodeURIComponent(matches[1]) : null;
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

// Request interceptor - добавляем Authorization header
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - обработка ошибок
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Токен истёк - очищаем и редиректим на логин
      tokenStorage.clearTokens();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: number;
}

export interface UserResponse {
  user_id: string;
  username: string;
  full_name: string | null;
  email: string;
  role: string;
}

export const authApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const formData = new URLSearchParams();
    formData.append('grant_type', 'password');
    formData.append('username', email);
    formData.append('password', password);
    formData.append('scope', '');
    formData.append('client_id', 'string');
    formData.append('client_secret', 'string');

    const response = await apiClient.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    return response.data;
  },

  getMe: async (): Promise<UserResponse> => {
    const response = await apiClient.post<UserResponse>('/users/me', '');
    return response.data;
  },

  logout: () => {
    tokenStorage.clearTokens();
  },
};

export default apiClient;
