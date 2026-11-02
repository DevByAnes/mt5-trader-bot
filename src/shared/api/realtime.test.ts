import { afterEach,beforeEach,describe,expect,it,vi } from 'vitest';
import { connectRealtime } from './realtime';
class Socket {
 static OPEN=1;static instances:Socket[]=[];readyState=1;
 onopen?:()=>void;onclose?:()=>void;onerror?:()=>void;onmessage?:(event:{data:string})=>void;
 constructor(){Socket.instances.push(this);}
 close(){this.readyState=3;this.onclose?.();}
 message(seq:number){this.onmessage?.({data:JSON.stringify({type:'position',seq,server_time_utc:new Date().toISOString(),payload:[]})});}
}
beforeEach(()=>{vi.useFakeTimers();Socket.instances=[];vi.stubGlobal('WebSocket',Socket);});
afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals();});
describe('realtime recovery',()=>{
 it.each(['backend','ea','mt5'] as const)('keeps commands disabled when %s is offline and recovers on a healthy heartbeat',component=>{
  const state=vi.fn();
  const stop=connectRealtime(vi.fn(),state,vi.fn());
  const socket=Socket.instances[0]!;socket.onopen?.();
  const node={state:'healthy',heartbeat_utc:new Date().toISOString(),latency_ms:null};
  const payload={backend:{...node},ea:{...node},mt5:{...node},broker_offset_minutes:null};
  payload[component]={state:'offline',heartbeat_utc:new Date().toISOString(),latency_ms:null};
  socket.onmessage?.({data:JSON.stringify({type:'heartbeat',seq:1,server_time_utc:new Date().toISOString(),payload})});
  expect(state).toHaveBeenLastCalledWith(expect.objectContaining({status:'stale'}));
  payload[component]={...node};
  socket.onmessage?.({data:JSON.stringify({type:'heartbeat',seq:2,server_time_utc:new Date().toISOString(),payload})});
  expect(state).toHaveBeenLastCalledWith(expect.objectContaining({status:'online'}));
  stop();
 });
 it('refreshes snapshots after open, gaps and malformed frames, ignoring duplicates',()=>{const event=vi.fn(),state=vi.fn(),snapshot=vi.fn();const stop=connectRealtime(event,state,snapshot);const socket=Socket.instances[0]!;socket.onopen?.();socket.message(1);socket.message(1);socket.message(4);socket.onmessage?.({data:'bad JSON'});expect(event).toHaveBeenCalledTimes(2);expect(snapshot).toHaveBeenCalledTimes(3);stop();});
 it('marks missing heartbeat stale and reconnects with bounded backoff',()=>{const state=vi.fn();const stop=connectRealtime(vi.fn(),state,vi.fn());Socket.instances[0]!.onopen?.();vi.advanceTimersByTime(7000);expect(state).toHaveBeenLastCalledWith(expect.objectContaining({status:'stale'}));vi.advanceTimersByTime(9000);expect(state).toHaveBeenLastCalledWith(expect.objectContaining({status:'offline',attempt:1}));vi.advanceTimersByTime(1400);expect(Socket.instances).toHaveLength(2);stop();const count=Socket.instances.length;vi.advanceTimersByTime(60000);expect(Socket.instances).toHaveLength(count);});
});
