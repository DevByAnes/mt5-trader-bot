import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5000, refetchInterval: 5000 },
    mutations: { retry: false },
  },
});

export type TransportMetadata = { mode: 'fixture' | 'file' | 'unknown' };
