import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { User, Lock, UserCircle, AlertCircle, CheckCircle } from 'lucide-react';
import { authApi } from '../api/client';

const registerSchema = z.object({
  username: z.string().min(3, 'Минимум 3 символа').regex(/^[a-z0-9_]+$/, 'Только латинские буквы, цифры и _'),
  full_name: z.string().min(2, 'Введите ФИО'),
  password: z.string().min(6, 'Минимум 6 символов'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Пароли не совпадают',
  path: ['confirmPassword'],
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function InviteAcceptPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    if (!token) {
      setError('Токен приглашения не найден');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await authApi.register(token, {
        username: data.username,
        full_name: data.full_name,
        password: data.password,
      });

      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Ошибка регистрации. Возможно, приглашение недействительно.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-neutral-900/80 backdrop-blur-sm border border-neutral-800 rounded-2xl p-8 text-center">
            <AlertCircle className="w-16 h-16 text-[var(--accent)] mx-auto mb-4" />
            <h2 className="text-[16px] font-semibold text-white mb-2">Ссылка недействительна</h2>
            <p className="text-[var(--text-muted)] mb-6">
              Токен приглашения не найден. Убедитесь, что вы перешли по правильной ссылке из письма.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="px-6 py-3 bg-neutral-800 hover:bg-neutral-700 text-white rounded-xl transition-colors"
            >
              Перейти на страницу входа
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-neutral-900/80 backdrop-blur-sm border border-neutral-800 rounded-2xl p-8 text-center">
            <div className="w-16 h-16 bg-[var(--success)]/8 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-[var(--success)]" />
            </div>
            <h2 className="text-[16px] font-semibold text-white mb-2">Регистрация успешна!</h2>
            <p className="text-[var(--text-muted)] mb-6">
              Ваш аккаунт создан. Сейчас вы будете перенаправлены на страницу входа...
            </p>
            <div className="w-8 h-8 border-2 border-neutral-600 border-t-red-500 rounded-full animate-spin mx-auto" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
      {/* Фоновые эффекты */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[var(--accent-soft)] rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[var(--accent-soft)] rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Логотип */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[var(--accent)] mb-4">
            <span className="text-2xl font-bold text-white">ДК</span>
          </div>
          <h1 className="text-2xl font-bold text-white">ДИО-Консалт</h1>
          <p className="text-neutral-500 mt-1">Регистрация по приглашению</p>
        </div>

        {/* Форма */}
        <div className="bg-neutral-900/80 backdrop-blur-sm border border-neutral-800 rounded-2xl p-8">
          <h2 className="text-[16px] font-semibold text-white mb-2">Создание аккаунта</h2>
          <p className="text-neutral-500 mb-6">Заполните данные для завершения регистрации</p>

          {error && (
            <div className="mb-6 p-4 bg-[var(--accent-soft)] border border-[var(--accent)]/15 rounded-xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-[var(--accent)] flex-shrink-0 mt-0.5" />
              <p className="text-sm text-[var(--accent)]">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Имя пользователя (логин)
              </label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-500" />
                <input
                  type="text"
                  {...register('username')}
                  className="w-full pl-12 pr-4 py-3 bg-neutral-800/50 border border-neutral-700 rounded-xl text-white placeholder-neutral-500 focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-red-500 transition-colors"
                  placeholder="ivan_ivanov"
                />
              </div>
              {errors.username && (
                <p className="text-[var(--accent)] text-sm mt-2">{errors.username.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                ФИО
              </label>
              <div className="relative">
                <UserCircle className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-500" />
                <input
                  type="text"
                  {...register('full_name')}
                  className="w-full pl-12 pr-4 py-3 bg-neutral-800/50 border border-neutral-700 rounded-xl text-white placeholder-neutral-500 focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-red-500 transition-colors"
                  placeholder="Иванов Иван Иванович"
                />
              </div>
              {errors.full_name && (
                <p className="text-[var(--accent)] text-sm mt-2">{errors.full_name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Пароль
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-500" />
                <input
                  type="password"
                  {...register('password')}
                  className="w-full pl-12 pr-4 py-3 bg-neutral-800/50 border border-neutral-700 rounded-xl text-white placeholder-neutral-500 focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-red-500 transition-colors"
                  placeholder="••••••••"
                />
              </div>
              {errors.password && (
                <p className="text-[var(--accent)] text-sm mt-2">{errors.password.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Подтверждение пароля
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-500" />
                <input
                  type="password"
                  {...register('confirmPassword')}
                  className="w-full pl-12 pr-4 py-3 bg-neutral-800/50 border border-neutral-700 rounded-xl text-white placeholder-neutral-500 focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-red-500 transition-colors"
                  placeholder="••••••••"
                />
              </div>
              {errors.confirmPassword && (
                <p className="text-[var(--accent)] text-sm mt-2">{errors.confirmPassword.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-[var(--accent)] hover:from-red-600 hover:to-red-700 text-white font-medium rounded-xl transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Регистрация...
                </>
              ) : (
                'Зарегистрироваться'
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-neutral-600 text-sm mt-6">
          © 2024 ДИО-Консалт. Все права защищены.
        </p>
      </div>
    </div>
  );
}
