import fs from 'node:fs';
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n');
const str={type:'string'}, num={type:['number','null']}, integer={type:'integer'}, bool={type:'boolean'}, time={type:'string',format:'date-time'};
const en=(...v)=>({type:'string',enum:v}); const arr=items=>({type:'array',items});
const obj=(properties,required=Object.keys(properties))=>({type:'object',additionalProperties:false,properties,required});
const ref=n=>({$ref:'#/components/schemas/'+n});
const settings=JSON.parse(fs.readFileSync('schema/settings.schema.json','utf8'));
settings.properties.executionMode.enum=['SIGNAL_ONLY','PAPER','LIVE'];settings.properties.executionMode.default='SIGNAL_ONLY';
for(const [key,m] of Object.entries(settings.properties)){m.key=key;m.min=m.minimum??null;m.max=m.maximum??null;m.step=m.multipleOf??null;m.enum??=null;}
write('schema/settings.schema.json',settings);
const draft=obj(Object.fromEntries(Object.entries(settings.properties).map(([k,m])=>[k,{type:m.type,...(m.enum?{enum:m.enum}:{}),...(m.minimum!==undefined?{minimum:m.minimum,maximum:m.maximum,multipleOf:m.multipleOf}:{})}])));
const S={
 Error:obj({code:en('VALIDATION_ERROR','VERSION_CONFLICT','MT5_ONLY','LIVE_LOCKED','EA_OFFLINE','UNAUTHORIZED','NOT_FOUND','IDEMPOTENCY_CONFLICT','UNAVAILABLE'),message:str,field:str},['code','message']),
 HealthNode:obj({state:en('healthy','stale','offline'),heartbeat_utc:{anyOf:[time,{type:'null'}]},latency_ms:num}),
 Status:obj({backend:ref('HealthNode'),ea:ref('HealthNode'),mt5:ref('HealthNode'),broker_offset_minutes:{type:['integer','null']}}),
 EaState:obj({mode:en('SIGNAL_ONLY','PAPER','LIVE'),equity:num,pnl_today:num,risk_active:{type:['boolean','null']},risk_reason:{type:['string','null']},session:str,trend_h1:{type:['string','null']},trend_h4:{type:['string','null']},h1_strength:num,h4_strength:num,atr:num,spread:num,trades_today:{type:['integer','null']},last_rejection:{type:['string','null']},live_prerequisites:arr(obj({key:str,ok:bool,reason:str}))}),
 Position:obj({id:str,side:en('BUY','SELL'),entry:num,sl:num,tp:num,lot:num,r:num,status:str,risk_free:{type:['boolean','null']},time_exit_utc:{anyOf:[time,{type:'null'}]}}),
 Signal:obj({id:str,time_utc:time,decision:en('BUY','SELL','WAIT','NO_SIGNAL'),reasons:arr(str),price:num,reason_code:{type:['string','null']},actual:num,limit:num}),
 Candle:obj({time:integer,open:{type:'number'},high:{type:'number'},low:{type:'number'},close:{type:'number'}}),
 Chart:obj({candles:arr(ref('Candle')),overlays:arr(obj({label:str,price:{type:'number'}}))}),
 DailyRisk:obj({state:en('ACTIVE','STOPPED'),reason:{type:['string','null']},start_equity:num,current_equity:num,loss_limit_amount:num,loss_remaining:num,loss_remaining_percent:num,profit_target_amount:num,profit_remaining:num,profit_remaining_percent:num,trades_remaining:{type:['integer','null']},next_day_utc:time}),
 Telemetry:obj({equity:arr(num),spread:arr(num),atr:arr(num)}),
 SettingsDraft:draft,
 SettingsData:obj({version:integer,values:ref('SettingsDraft'),pending_next_day:bool}),
 DiffItem:obj({key:str,old_value:{type:['string','number','boolean']},new_value:{type:['string','number','boolean']},apply:en('HOT','COLD'),risk_level:en('LOW','MEDIUM','HIGH'),direction:en('TIGHTER','LOOSER','NEUTRAL')}),
 Diff:obj({base_version:integer,diff:arr(ref('DiffItem')),values:ref('SettingsDraft')}),
 ApplyRequest:obj({base_version:integer,values:ref('SettingsDraft')}),
 Ack:obj({request_id:str,status:en('PENDING','APPLIED','REJECTED','TIMEOUT'),reason:{type:['string','null']},version:{type:['integer','null']},ea_ack_utc:{anyOf:[time,{type:'null'}]}}),
 CommandRequest:obj({position_id:str},[]),
 JournalRecord:obj({id:str,time_utc:time,side:en('BUY','SELL'),r:num,session:str,result:str}),
 ValidationRecord:obj({id:str,test:str,status:en('PASS','REVIEW','FAIL'),period:str,evidence:str}),
 LogRecord:obj({id:str,time_utc:time,level:en('INFO','WARN','ERROR'),source:str,message:str}),
 AuditRecord:obj({id:str,time_utc:time,actor:str,action:str,version:integer,result:str,previous_values:ref('SettingsDraft')})
};
const list=entity=>obj({items:arr(ref(entity)),next_cursor:{type:['string','null']}});
S.Signals=list('Signal');for(const [name,entity] of Object.entries({Journal:'JournalRecord',Validation:'ValidationRecord',Logs:'LogRecord',Audit:'AuditRecord'}))S[name]=list(entity);
S.Positions=arr(ref('Position'));
for(const name of [...Object.keys(S)].filter(n=>!['Error','HealthNode','SettingsDraft','ApplyRequest','CommandRequest'].includes(n)))S[name+'Envelope']=obj({data:ref(name),error:{anyOf:[ref('Error'),{type:'null'}]},server_time_utc:time,api_version:{type:'string',const:'1.0.0'}});
S.ErrorEnvelope=obj({data:{type:'null'},error:ref('Error'),server_time_utc:time,api_version:{type:'string',const:'1.0.0'}});
const response=(name,description='OK')=>({description,content:{'application/json':{schema:ref(name+'Envelope')}}});
const errors=Object.fromEntries([400,401,403,404,409,422,503].map(n=>[n,response('Error','See Error.code; request was not applied')]));
const paths={};
const endpoints={'/status':'Status','/ea/state':'EaState','/positions':'Positions','/signals':'Signals','/chart':'Chart','/risk/daily':'DailyRisk','/telemetry':'Telemetry','/settings':'SettingsData','/journal':'Journal','/validation':'Validation','/logs':'Logs','/audit':'Audit','/requests/{id}':'Ack'};
for(const [path,name] of Object.entries(endpoints)){const parameters=[];if(['Signals','Journal','Validation','Logs','Audit'].includes(name))parameters.push({name:'cursor',in:'query',schema:str},{name:'limit',in:'query',schema:{type:'integer',minimum:1,maximum:100,default:50}});if(path.includes('{id}'))parameters.push({name:'id',in:'path',required:true,schema:str});paths[path]={get:{operationId:'get'+name,parameters,responses:{200:response(name),...errors}}};}
const post=(path,input,output,idempotent=false,params=[])=>{paths[path]={post:{operationId:path.replace(/[^a-z]/gi,''),parameters:[...params,...(idempotent?[{$ref:'#/components/parameters/IdempotencyKey'}]:[])],...(input?{requestBody:{required:true,content:{'application/json':{schema:ref(input)}}}}:{}),responses:{[output==='Ack'?202:200]:response(output),...errors}}};};
post('/settings/validate','ApplyRequest','Diff');post('/settings/apply','ApplyRequest','Ack',true);
post('/commands/{command}','CommandRequest','Ack',true,[{name:'command',in:'path',required:true,schema:en('kill-switch','risk-free-all','risk-free-position','close-position')}]);
post('/audit/{id}/rollback',null,'Diff',false,[{name:'id',in:'path',required:true,schema:str}]);
write('schema/openapi.yaml',{openapi:'3.1.0',info:{title:'Aurum Control Python Bridge',version:'1.0.0'},servers:[{url:'http://127.0.0.1:8765/api/v1'}],security:[{session:[]}],paths,components:{securitySchemes:{session:{type:'http',scheme:'bearer'}},parameters:{IdempotencyKey:{name:'Idempotency-Key',in:'header',required:true,schema:{type:'string',format:'uuid'}}},schemas:S}});
const events={ea_state:'EaState',position:'Positions',signal:'Signal',risk_mode:'DailyRisk',log:'LogRecord',command_ack:'Ack',config_ack:'Ack',heartbeat:'Status'};
write('schema/events.json',{$schema:'https://json-schema.org/draft/2020-12/schema',$id:'https://aurum.local/events/1.0.0',title:'Bridge event',oneOf:Object.entries(events).map(([type,payload])=>obj({type:{const:type},seq:{type:'integer',minimum:1},server_time_utc:time,payload:{$ref:`openapi.yaml#/components/schemas/${payload}`}})), 'x-protocol':{version:'1.0.0',heartbeat_ms:2000,stale_ms:6000,offline_ms:15000,snapshot:'GET every active query after open or seq gap. Ignore duplicates and old seq. HTTP snapshot is authoritative; events invalidate caches. New socket resets seq baseline.',ack:'Correlate request_id; poll /requests/{id}. Only APPLIED with ea_ack_utc proves EA acknowledgement. TIMEOUT is unknown; do not resubmit automatically.'}});
