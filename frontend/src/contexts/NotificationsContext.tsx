import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import { notificationsApi } from '../api/client';

interface NotificationsContextType {
  unreadCount: number;
  refresh: () => Promise<void>;
}

const NotificationsContext = createContext<NotificationsContextType>({
  unreadCount: 0,
  refresh: async () => {},
});

export function useNotifications() {
  return useContext(NotificationsContext);
}

const ORIGINAL_TITLE = document.title || 'ДИО Деск';

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [unreadCount, setUnreadCount] = useState(0);
  const blinkRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const count = await notificationsApi.getUnreadCount();
      setUnreadCount(count);
    } catch {
      // молча
    }
  }, []);

  // Polling каждые 30 сек
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 30000);
    return () => clearInterval(timer);
  }, [refresh]);

  // Мигание title
  useEffect(() => {
    if (blinkRef.current) {
      clearInterval(blinkRef.current);
      blinkRef.current = null;
    }

    if (unreadCount <= 0) {
      document.title = ORIGINAL_TITLE;
      return;
    }

    let isOriginal = true;
    const notifTitle = `(${unreadCount}) Новые уведомления!`;
    document.title = notifTitle;

    blinkRef.current = setInterval(() => {
      isOriginal = !isOriginal;
      document.title = isOriginal ? ORIGINAL_TITLE : notifTitle;
    }, 1500);

    return () => {
      if (blinkRef.current) {
        clearInterval(blinkRef.current);
        blinkRef.current = null;
      }
      document.title = ORIGINAL_TITLE;
    };
  }, [unreadCount]);

  return (
    <NotificationsContext.Provider value={{ unreadCount, refresh }}>
      {children}
    </NotificationsContext.Provider>
  );
}