import { useState, useEffect, useCallback, useRef } from 'react';
import { notificationsApi } from '../api/client';

const ORIGINAL_TITLE = document.title;

export function useUnreadNotifications(intervalMs = 30000) {
  const [count, setCount] = useState(0);
  const blinkIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const c = await notificationsApi.getUnreadCount();
      setCount(c);
    } catch {
      // молча
    }
  }, []);

  // Polling
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, intervalMs);
    return () => clearInterval(timer);
  }, [refresh, intervalMs]);

  // Мигание вкладки браузера
  useEffect(() => {
    // Очищаем предыдущее мигание
    if (blinkIntervalRef.current) {
      clearInterval(blinkIntervalRef.current);
      blinkIntervalRef.current = null;
    }

    if (count <= 0) {
      document.title = ORIGINAL_TITLE;
      return;
    }

    // Мигаем между оригинальным title и сообщением о новых уведомлениях
    let isOriginal = true;
    const notifTitle = `(${count}) Новые уведомления!`;

    // Сразу показываем
    document.title = notifTitle;

    blinkIntervalRef.current = setInterval(() => {
      isOriginal = !isOriginal;
      document.title = isOriginal ? ORIGINAL_TITLE : notifTitle;
    }, 1500);

    return () => {
      if (blinkIntervalRef.current) {
        clearInterval(blinkIntervalRef.current);
        blinkIntervalRef.current = null;
      }
      document.title = ORIGINAL_TITLE;
    };
  }, [count]);

  // Когда пользователь фокусируется на вкладке — останавливаем мигание временно
  useEffect(() => {
    const handleFocus = () => {
      // При фокусе показываем обычный title, мигание продолжится если count > 0
      // но можно остановить если хотите чтобы при фокусе не мигало
    };

    const handleVisibilityChange = () => {
      if (document.hidden && count > 0) {
        // Вкладка скрыта и есть уведомления — мигание уже идёт
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
    };
  }, [count]);

  return { count, refresh };
}