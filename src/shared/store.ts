import { create } from 'zustand';
type UiState = { locale:'fa'|'en'; theme:'dark'|'light'; backendOnline:boolean; setLocale:(v:'fa'|'en')=>void; toggleTheme:()=>void; setBackendOnline:(v:boolean)=>void };
export const useUiStore = create<UiState>((set)=>({ locale:'fa', theme:'dark', backendOnline:true, setLocale:(locale)=>set({locale}), toggleTheme:()=>set(s=>({theme:s.theme==='dark'?'light':'dark'})), setBackendOnline:(backendOnline)=>set({backendOnline}) }));
