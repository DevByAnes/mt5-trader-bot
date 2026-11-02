import fs from 'node:fs';
fs.mkdirSync('fixtures',{recursive:true});
const now='2026-11-02T10:00:00Z';
const values={executionMode:'PAPER',riskPerTrade:.5,dailyLossLimit:2,maxSpread:35,allowRemoteConfig:true,allowRealAccount:false};
const node={state:'healthy',heartbeat_utc:now,latency_ms:12};
const data={
 Status:{backend:node,ea:{...node,latency_ms:28},mt5:{...node,latency_ms:41},broker_offset_minutes:120},
 EaState:{mode:'PAPER',equity:10042.16,pnl_today:42.16,risk_active:true,risk_reason:null,session:'London / New York',trend_h1:'Bullish',trend_h4:'Neutral',h1_strength:72,h4_strength:48,atr:18.4,spread:21,trades_today:2,last_rejection:'SPREAD_LIMIT · 41 > 35',live_prerequisites:[{key:'demo',ok:true,reason:'Demo evidence reviewed'},{key:'forward',ok:true,reason:'Forward evidence reviewed'},{key:'real_account_opt_in',ok:false,reason:'MT5 permission disabled'}]},
 Positions:[{id:'XAU-1042',side:'BUY',entry:2688.4,sl:2679.1,tp:2707,lot:.12,r:.74,status:'OPEN',risk_free:false,time_exit_utc:null}],
 Signals:{items:[{id:'sig-31',time_utc:now,decision:'WAIT',reasons:['Spread above configured limit'],price:2691.2,reason_code:'SPREAD_LIMIT',actual:41,limit:35},{id:'sig-30',time_utc:now,decision:'BUY',reasons:['H1 trend confirmed'],price:2688.4,reason_code:null,actual:null,limit:null}],next_cursor:null},
 Chart:{candles:Array.from({length:48},(_,i)=>{const base=2680+Math.sin(i/8)*12+i*.16;return{time:1793613600+i*900,open:base,high:base+4,low:base-3,close:base+Math.sin(i)*2}}),overlays:[{label:'Entry',price:2688.4},{label:'SL',price:2679.1},{label:'TP',price:2707}]},
 DailyRisk:{state:'ACTIVE',reason:null,start_equity:10000,current_equity:10042.16,loss_limit_amount:200,loss_remaining:200,loss_remaining_percent:100,profit_target_amount:300,profit_remaining:257.84,profit_remaining_percent:86,trades_remaining:6,next_day_utc:'2026-11-03T00:00:00Z'},
 Telemetry:{equity:[10000,9992,10006,10002,10024,10015,10042.16],spread:[18,21,24,19,22,20,21],atr:[17,17.4,17.8,18.1,18.3,18.2,18.4]},
 SettingsData:{version:7,values,pending_next_day:false},
 Journal:{items:[{id:'1041',time_utc:now,side:'BUY',r:1.7,session:'London',result:'CLOSED'}],next_cursor:null},
 Validation:{items:[{id:'v1',test:'Walk-forward',status:'REVIEW',period:'2024–2026',evidence:'Simulated evidence only; backend report required'}],next_cursor:null},
 Logs:{items:[{id:'l1',time_utc:now,level:'INFO',source:'bridge',message:'Simulated heartbeat received'}],next_cursor:null},
 Audit:{items:[{id:'audit-7',time_utc:now,actor:'mock-operator',action:'SETTINGS_APPLIED',version:7,result:'APPLIED',previous_values:{...values,maxSpread:30}}],next_cursor:null},
 Diff:{base_version:7,values:{...values,maxSpread:30},diff:[{key:'maxSpread',old_value:35,new_value:30,apply:'HOT',risk_level:'MEDIUM',direction:'TIGHTER'}]},
 Ack:{request_id:'fixture-request',status:'APPLIED',reason:null,version:8,ea_ack_utc:now}
};
for(const [name,value] of Object.entries(data))fs.writeFileSync(`fixtures/${name}.json`,JSON.stringify({data:value,error:null,server_time_utc:now,api_version:'1.0.0'},null,2)+'\n');
fs.writeFileSync('fixtures/Error.json',JSON.stringify({data:null,error:{code:'VERSION_CONFLICT',message:'Reload current settings'},server_time_utc:now,api_version:'1.0.0'},null,2)+'\n');
