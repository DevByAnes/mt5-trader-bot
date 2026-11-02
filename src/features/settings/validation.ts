import { z } from 'zod';
import schema from '../../../schema/settings.schema.json';
import type { SettingsValues } from '../../shared/api/client';
export const formSchema = z.custom<SettingsValues>((value) => validateValues(value).length === 0, 'Values must satisfy the settings contract');
export function validateValues(value: unknown): string[] { if (!value || typeof value !== 'object')
    return ['Missing settings']; const v = value as Record<string, unknown>; return Object.entries(schema.properties).flatMap(([key, m]) => { const x = v[key]; if (typeof x !== m.type)
    return [key]; if (m.enum && !m.enum.includes(x as never))
    return [key]; if (typeof x === 'number' && (!Number.isFinite(x) || m.min !== null && x < m.min || m.max !== null && x > m.max || m.step !== null && Math.abs(x / m.step - Math.round(x / m.step)) > 1e-8))
    return [key]; return []; }).concat(Object.keys(v).filter(k => !(k in schema.properties))); }
