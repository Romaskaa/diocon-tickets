import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff, Loader2, CheckCircle } from 'lucide-react';
import { authApi } from '../api/client';
import { useToast } from '../components/ui/use-toast';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const { toast } = useToast();
  
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!token) {
      toast({ title: 'Ошибка', description: 'Недействительная ссылка приглашения', variant: 'destructive' });
      return;
    }

    if (password !== confirmPassword) {
      toast({ title: 'Ошибка', description: 'Пароли не совпадают', variant: 'destructive' });
      return;
    }

    if (password.length < 6) {
      toast({ title: 'Ошибка', description: 'Пароль должен быть не менее 6 символов', variant: 'destructive' });
      return;
    }

    setLoading(true);
    try {
      await authApi.register(token, { username, full_name: fullName, password });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        title: 'Ошибка регистрации',
        description: err.response?.data?.detail || 'Не удалось зарегистрироваться',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-[#0a0a0a]">
        <div className="glass-card-static p-8 max-w-md w-full text-center">
          <h2 className="text-[16px] font-semibold text-white mb-4">Недействительная ссылка</h2>
          <p className="text-white/50 mb-6">Ссылка приглашения недействительна или истекла.</p>
          <button onClick={() => navigate('/login')} className="btn-primary">
            Перейти к входу
          </button>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-[#0a0a0a]">
        <div className="glass-card-static p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-[16px] font-semibold text-white mb-2">Регистрация завершена!</h2>
          <p className="text-white/50">Переход на страницу входа...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#0a0a0a]">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-1/4 w-1/2 h-1/2 bg-red-900/20 rounded-full blur-[100px]" />
        <div className="absolute bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-red-800/10 rounded-full blur-[100px]" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-800 to-red-900 flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl font-bold text-white">ДК</span>
          </div>
          <h1 className="text-2xl font-bold text-white">ДИО-Консалт</h1>
          <p className="text-white/50 mt-1">Создание аккаунта</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="glass-card-static p-8">
          <h2 className="text-[16px] font-semibold text-white mb-6 text-center">Регистрация</h2>
          
          <div className="space-y-5">
            <div>
              <label className="label">Имя пользователя</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="ivan_ivanov"
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="label">Полное имя</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Иванов Иван Иванович"
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="label">Пароль</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Минимум 6 символов"
                  className="input-field pr-12"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div>
              <label className="label">Подтверждение пароля</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Повторите пароль"
                className="input-field"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading || !username || !fullName || !password || !confirmPassword}
              className="btn-primary w-full py-4"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'Создать аккаунт'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
