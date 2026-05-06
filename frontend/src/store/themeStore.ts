import { create } from "zustand";

// Только тёмная тема
interface ThemeState {
  theme: "dark";
}

export const useThemeStore = create<ThemeState>(() => ({
  theme: "dark",
}));
