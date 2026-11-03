import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { isTauri, invoke } from '@tauri-apps/api/core';
import { setSessionToken } from './shared/api/client';
import './shared/i18n';
import './styles.css';
import { App } from './App';
import { queryClient as client } from './shared/query';
async function bootstrap() { if (isTauri())
    setSessionToken(await invoke<string>('session_token'));
    else if (import.meta.env.DEV && import.meta.env.VITE_LOCAL_SESSION === 'true') {
        const response = await fetch('/__aurum/session', {method: 'POST', headers: {'X-Aurum-Session': '1'}, cache: 'no-store'});
        if (!response.ok) throw Error('Local session unavailable');
        const session: {token: string} = await response.json();
        setSessionToken(session.token);
    }
    if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS !== 'false') {
    const { worker } = await import('./mocks/browser');
    await worker.start({ onUnhandledFrame: 'bypass' });
} ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider></React.StrictMode>); }
void bootstrap().catch(() => { document.getElementById('root')!.textContent = 'Startup unavailable. Native session could not be initialized.'; });
