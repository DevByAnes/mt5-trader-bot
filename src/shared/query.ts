import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => count < 1 && !('retryAfterMs' in error && error.retryAfterMs),
      staleTime: 5000,
      refetchInterval: 5000,
    },
    mutations: { retry: false },
  },
});

export type TransportMetadata = { mode: 'fixture' | 'file' | 'unknown' };
