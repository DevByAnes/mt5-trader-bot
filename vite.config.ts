import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import type { Plugin } from 'vite';

// Explicit local development launcher only. Secrets never enter client bundles or URLs.
function localSession(): Plugin {
    return {
        name: 'aurum-local-session', apply: 'serve',
        configureServer(server) {
            if (process.env.AURUM_LOCAL_DEV !== '1') return;
            const token = process.env.AURUM_SESSION_TOKEN;
            if (!token || !/^[\x21-\x7e]{32,4096}$/.test(token)) throw Error('Local session unavailable');
            server.middlewares.use('/__aurum/session', (req, res) => {
                const hosts = ['127.0.0.1:1420', 'localhost:1420'];
                const peers = ['127.0.0.1', '::1', '::ffff:127.0.0.1'];
                if (req.method !== 'POST' || !hosts.includes(req.headers.host ?? '') ||
                    !peers.includes(req.socket.remoteAddress ?? '') ||
                    req.headers.origin !== `http://${req.headers.host}` ||
                    req.headers['sec-fetch-site'] !== 'same-origin' ||
                    req.headers['x-aurum-session'] !== '1') {
                    res.statusCode = 403; res.end(); return;
                }
                res.setHeader('Cache-Control', 'no-store');
                res.setHeader('Content-Type', 'application/json');
                res.end(JSON.stringify({token}));
            });
        },
    };
}
export default defineConfig({ plugins: [react(), localSession()], server: { host: '127.0.0.1', port: 1420, strictPort: true, watch: { ignored: ['**/backend/.evidence/**', '**/releases/**'] } }, clearScreen: false });
