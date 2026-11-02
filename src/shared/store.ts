import { create } from 'zustand';
type UiState = {
    theme: 'dark' | 'light';
    locale: 'en' | 'fa';
    digits: 'latn' | 'arabext';
    backendOnline: boolean;
    toggleTheme: () => void;
    setLocale: (v: 'en' | 'fa') => void;
    setDigits: (v: 'latn' | 'arabext') => void;
    setBackendOnline: (v: boolean) => void;
};
export const useUiStore = create<UiState>(set => ({ theme: 'dark', locale: 'en', digits: 'latn', backendOnline: false, toggleTheme: () => set(s => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })), setLocale: locale => set({ locale }), setDigits: digits => set({ digits }), setBackendOnline: backendOnline => set({ backendOnline }) }));
