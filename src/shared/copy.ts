import i18n from './i18n';
import fa from './fa-copy.json';
export function copy(value: string): string { return i18n.language === 'fa' ? (fa[value as keyof typeof fa] ?? value) : value; }
