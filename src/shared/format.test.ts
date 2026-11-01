import { describe,expect,it } from 'vitest'; import { numberValue,unavailable } from './format';
describe('safe formatting',()=>{it('does not turn missing data into zero',()=>{expect(numberValue(null)).toBe(unavailable);expect(numberValue(undefined)).toBe(unavailable);expect(numberValue(0)).not.toBe(unavailable)})});
