import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, LogIn, AlertCircle, Loader2 } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSent, setForgotSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Заполните все поля');
      return;
    }

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Ошибка входа');
    }
  };

  const handleForgotPassword = () => {
    if (!forgotEmail) return;
    // Мок отправки
    setTimeout(() => {
      setForgotSent(true);
    }, 1000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-[var(--bg-primary)]">
      </div>

      <div className="w-full max-w-3xl relative z-10">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center mb-6">
            <img
              src="http://80.93.62.177:8000/media/images/Logo_bez_fona_bez_teksta.width-80.height-80.png"
              alt="ДИО-Консалт"
              className="w-20 h-20 object-contain"
            />
          </div>
          <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">ДИО-Консалт</h1>
          <p className="text-lg text-[var(--text-primary)]/60">Система поддержки клиентов</p>
        </div>

        {/* Login Form */}
        <div className="glass-card p-8">
          <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Вход в систему</h2>
          <p className="text-[var(--text-primary)]/60 mb-8">Введите данные для входа</p>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)]/15 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-[var(--accent)] flex-shrink-0" />
              <p className="text-[var(--accent)]">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-[16px] text-[var(--text-primary)]/80 mb-3  font-medium">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="example@company.ru"
                className="input-field py-4 text-lg"
                autoComplete="email"
              />
            </div>

            <div>
              <label className="block text-[16px] text-[var(--text-primary)]/80 mb-3  font-medium">
                Пароль
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input-field py-4 text-lg pr-12"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--text-primary)]/50 hover:text-[var(--text-primary)] transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-end">
              <button
                type="button"
                onClick={() => setShowForgotModal(true)}
                className="text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors text-base"
              >
                Забыли пароль?
              </button>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-primary py-4 text-lg font-semibold"
            >
              {isLoading ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  Войти
                </>
              )}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-[var(--border-color)] text-center">
            <p className="text-[var(--text-primary)]/50">
              Нет аккаунта?{' '}
              <span className="text-[var(--text-primary)]/70">
                Обратитесь к администратору для получения приглашения
              </span>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-[var(--text-primary)]/30 mt-8 text-sm">
          © 2026 ДИО-Консалт. Все права защищены.
        </p>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => {
            setShowForgotModal(false);
            setForgotSent(false);
            setForgotEmail('');
          }} />
          <div className="glass-card p-8 w-full max-w-md relative z-10">
            {!forgotSent ? (
              <>
                <h3 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Восстановление пароля</h3>
                <p className="text-[var(--text-primary)]/60 mb-6">
                  Введите email, указанный при регистрации. Мы отправим инструкции по восстановлению.
                </p>
                <div className="mb-6">
                  <label className="block text-[var(--text-primary)]/80 mb-3 text-base font-medium">
                    Email
                  </label>
                  <input
                    type="email"
                    value={forgotEmail}
                    onChange={e => setForgotEmail(e.target.value)}
                    placeholder="example@company.ru"
                    className="input-field py-4 text-lg"
                  />
                </div>
                <div className="flex gap-4">
                  <button
                    onClick={() => {
                      setShowForgotModal(false);
                      setForgotEmail('');
                    }}
                    className="flex-1 py-4 px-6 rounded-xl bg-[var(--hover-1)] hover:bg-[var(--hover-2)] text-[var(--text-primary)] transition-colors text-base font-medium"
                  >
                    Отмена
                  </button>
                  <button
                    onClick={handleForgotPassword}
                    disabled={!forgotEmail}
                    className="flex-1 btn-primary py-4 text-base font-semibold"
                  >
                    Отправить
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-[var(--success)]/8 flex items-center justify-center">
                    <svg className="w-8 h-8 text-[var(--success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h3 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Письмо отправлено!</h3>
                  <p className="text-[var(--text-primary)]/60 mb-6">
                    Проверьте почту <span className="text-[var(--text-primary)]">{forgotEmail}</span> и следуйте инструкциям в письме.
                  </p>
                  <button
                    onClick={() => {
                      setShowForgotModal(false);
                      setForgotSent(false);
                      setForgotEmail('');
                    }}
                    className="btn-primary py-4 px-8 text-base font-semibold"
                  >
                    Понятно
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
