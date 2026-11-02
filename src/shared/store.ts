import { create } from 'zustand';
type UiState={theme:'dark'|'light';backendOnline:boolean;toggleTheme:()=>void;setBackendOnline:(v:boolean)=>void};
export const useUiStore=create<UiState>((set)=>({theme:'dark',backendOnline:true,toggleTheme:()=>set(s=>({theme:s.theme==='dark'?'light':'dark'})),setBackendOnline:(backendOnline)=>set({backendOnline})}));
