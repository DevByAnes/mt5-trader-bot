#ifndef AURUM_V1_BRIDGE
#define AURUM_V1_BRIDGE
#include "Execution.mqh"
// Key comes from the launcher's local-user-only Windows named pipe. No DLL import,
// plaintext file, input parameter, .set export or URL carries the secret.
class V1Bridge {
 private:
 uchar key[];long state_seq,ack_seq;string pending;datetime pending_after;long version;
 string Payload(string kind,string body,long seq,datetime utc,long ttl,string id="") {
  if(id=="")id=V1NewUuid();long now=(long)utc*1000;
  return "{\"kind\":"+JQuote(kind)+",\"sender\":\"EA\",\"message_id\":"+JQuote(id)+",\"ea_instance_id\":"+JQuote(instance)+",\"seq\":"+(string)seq+",\"issued_at_ms\":"+(string)now+",\"expires_at_ms\":"+(string)(now+ttl)+",\"body\":"+body+"}";
 }
 bool Persist(V1Execution &e) {
  string body="{\"version\":"+(string)version+",\"risk\":"+JNum(e.risk_pct)+",\"loss\":"+JNum(e.loss_pct)+",\"spread\":"+JNum(e.spread_max)+",\"mode\":"+JQuote(e.mode==AUTO_EXECUTE?"AUTO_EXECUTE":"SIGNAL_ONLY")+",\"killed\":"+JBool(e.killed)+"}";
  return V1Write(root+"\\native_config.json",V1Wire(body,BridgeKeyId,key));
 }
 bool Ack(string request,string status,string reason,datetime utc,long config_version=-1) {
  string body="{\"request_id\":"+JQuote(request)+",\"status\":"+JQuote(status)+",\"reason\":"+(reason==""?"null":JQuote(reason))+",\"version\":"+(config_version<0?"null":(string)config_version)+",\"ea_ack_utc\":"+JQuote(JTime(utc))+"}";
  string wire=V1Wire(Payload("ACK",body,++ack_seq,utc,86400000),BridgeKeyId,key);
  if(wire=="")return false;
  // Receipt is retained after Python consumes ack, so requests cannot repeat an effect.
  if(!V1Write(root+"\\receipt_"+request+".json",wire))return false;
  return V1Write(root+"\\ack_"+request+".json",wire);
 }
 bool Decode(string filename,V1Json &j,datetime utc,string &raw,string expected="") {
  string wire;if(!V1Read(root+"\\"+filename,wire)||!V1Unwire(wire,BridgeKeyId,key,raw)||!j.Parse(raw)||!j.Keys(0,"kind|sender|message_id|ea_instance_id|seq|issued_at_ms|expires_at_ms|body"))return false;
  double issued=j.Number(0,"issued_at_ms"),expires=j.Number(0,"expires_at_ms"),seq=j.Number(0,"seq"),now=(double)utc*1000;
  if(j.Get(0,"sender")!="PYTHON"||j.Get(0,"ea_instance_id")!=instance||!V1Uuid(j.Get(0,"message_id"))||seq<0||seq>9007199254740991||MathFloor(seq)!=seq||
   issued<0||issued>now+5000||expires<now||expires<=issued||expires-issued>86400000||expires>9007199254740991||MathFloor(issued)!=issued||MathFloor(expires)!=expires)return false;
  return expected==""||j.Get(0,"kind")==expected;
 }
 void Process(string name,V1Execution &e,datetime utc,bool boundary,double atr) {
  V1Json j;string raw;if(!Decode(name,j,utc,raw))return;
  int b=j.Field(0,"body");string kind=j.Get(0,"kind"),id=j.Get(b,"request_id");if(!V1Uuid(id)||id!=j.Get(0,"message_id"))return;
  if(kind!="COMMAND"&&kind!="CONFIG")return;
  string seen,path=root+"\\seen_"+id+".json";
  if(V1Read(path,seen)){if(seen!=raw)return;}
  else if(!V1Write(path,raw,false)){e.storage_ok=false;return;}
  string receipt;if(V1Read(root+"\\receipt_"+id+".json",receipt)){
   if(V1Write(root+"\\ack_"+id+".json",receipt))FileDelete(root+"\\"+name,FILE_COMMON);return;
  }
  if(FileIsExist(root+"\\intent_"+id+".json",FILE_COMMON)){Ack(id,"REJECTED","RECONCILIATION_REQUIRED_AFTER_AMBIGUOUS_EFFECT",utc);return;}
  if(kind=="CONFIG") {
   if(!j.Keys(b,"request_id|base_version|config_version|values|apply_at|confirmed_loosen"))return;
   int v=j.Field(b,"values");if(!j.Keys(v,"executionMode|riskPerTrade|dailyLossLimit|maxSpread|allowRemoteConfig|allowRealAccount"))return;
   double risk=j.Number(v,"riskPerTrade"),loss=j.Number(v,"dailyLossLimit"),spread=j.Number(v,"maxSpread");string mode=j.Get(v,"executionMode"),when=j.Get(b,"apply_at");
   string reason="";
   if(!AllowRemoteConfig)reason="MT5_ONLY";
   else if(j.Number(b,"base_version")!=version||j.Number(b,"config_version")!=version+1)reason="VERSION_CONFLICT";
   else if(risk<.1||risk>1||MathAbs(risk*10-MathRound(risk*10))>1e-6||loss<.5||loss>5||MathAbs(loss*10-MathRound(loss*10))>1e-6||spread<5||spread>100||MathFloor(spread)!=spread)reason="VALIDATION_ERROR";
   else if(j.Get(v,"allowRemoteConfig")!=JBool(AllowRemoteConfig)||j.Get(v,"allowRealAccount")!="false")reason="MT5_ONLY";
   else if((mode!="SIGNAL_ONLY"&&mode!="AUTO_EXECUTE")||(mode=="AUTO_EXECUTE"&&e.mode!=AUTO_EXECUTE))reason="AUTO_ENABLE_REQUIRES_NATIVE_CONFIGURATION";
   else if(risk>e.risk_pct||loss>e.loss_pct||spread>e.spread_max||j.Get(b,"confirmed_loosen")!="false")reason="RISK_LOOSENING_LOCKED";
   else if(when!="NEXT_M15"&&when!="NEXT_DAY")reason="INVALID_BOUNDARY";
   if(reason!=""){Ack(id,"REJECTED",reason,utc);return;}
   if(when=="NEXT_DAY") {
    if(pending!=id){if(pending!=""){Ack(id,"REJECTED","CONFIG_ALREADY_PENDING",utc);return;}pending=id;pending_after=e.next_day;}
    if(utc<pending_after)return;
   }else if(!boundary)return;
   if(!V1Write(root+"\\intent_"+id+".json",raw,false)){e.storage_ok=false;return;}
   double oldrisk=e.risk_pct,oldloss=e.loss_pct,oldspread=e.spread_max;V1Mode oldmode=e.mode;
   e.risk_pct=risk;e.loss_pct=loss;e.spread_max=spread;e.mode=mode=="SIGNAL_ONLY"?SIGNAL_ONLY:AUTO_EXECUTE;version++;
   if(!Persist(e)){version--;e.risk_pct=oldrisk;e.loss_pct=oldloss;e.spread_max=oldspread;e.mode=oldmode;e.storage_ok=false;return;}
   pending="";Ack(id,"APPLIED","",utc,version);return;
  }
  if(kind!="COMMAND"||!j.Keys(b,"request_id|command|position_id"))return;
  string command=j.Get(b,"command"),position=j.Get(b,"position_id"),reason="";bool ok=false;
  if(command!="kill-switch"&&command!="close-position"&&command!="risk-free-position"&&command!="risk-free-all")return;
  if(!V1Write(root+"\\intent_"+id+".json",raw,false)){e.storage_ok=false;return;}
  if(command=="kill-switch") {e.killed=true;ok=Persist(e);if(!ok)e.storage_ok=false;}
  else if(command=="risk-free-all") {
   ok=BreakEvenEnabled;if(!ok)reason="BREAK_EVEN_POLICY_DISABLED";
   for(int i=PositionsTotal()-1;i>=0&&ok;i--){ulong ticket=PositionGetTicket(i);if(ticket>0&&e.Own()&&!e.BreakEven(ticket,atr)){ok=false;reason="BROKER_REJECTED_BREAK_EVEN";}}
  }else {
   ulong ticket=(ulong)StringToInteger(position);
   if((string)ticket!=position||!PositionSelectByTicket(ticket)||!e.Own())reason="POSITION_UNAVAILABLE";
   else if(command=="close-position")ok=e.Close(ticket);
   else if(!BreakEvenEnabled)reason="BREAK_EVEN_POLICY_DISABLED";
   else ok=e.BreakEven(ticket,atr);
  }
  if(!ok&&reason=="")reason="EFFECT_NOT_CONFIRMED";
  Ack(id,ok?"APPLIED":"REJECTED",reason,utc);
 }
 public:
 string instance,root;bool active;
 V1Bridge(){active=false;state_seq=0;ack_seq=0;pending="";pending_after=0;version=1;}
 bool Init(string directory,V1Execution &e) {
  root=directory;instance=V1NewUuid();if(!BridgeEnabled)return true;
  string pipe="\\\\.\\pipe\\AurumControl-"+(string)AccountInfoInteger(ACCOUNT_LOGIN)+"-"+TradingSymbol+"-"+(string)Magic;
  int pipe_handle=FileOpen(pipe,FILE_READ|FILE_BIN);if(pipe_handle==INVALID_HANDLE){Print("AURUM KEY_HANDOFF_UNAVAILABLE: start backend launcher first");return false;}
  uchar buffer[];ArrayResize(buffer,64);uint n=FileReadArray(pipe_handle,buffer,0,64);FileClose(pipe_handle);
  if(n!=64)return false;string secret=CharArrayToString(buffer,0,64,CP_UTF8);bool valid=V1Unhex(secret,key);ArrayInitialize(buffer,0);secret="";if(!valid)return false;
  for(int i=0;i<StringLen(BridgeKeyId);i++)if(StringFind("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-",StringSubstr(BridgeKeyId,i,1))<0)return false;
  if(StringLen(BridgeKeyId)<1||StringLen(BridgeKeyId)>64)return false;
  string wire,text;if(V1Read(root+"\\native_config.json",wire)) {
   V1Json j;if(!V1Unwire(wire,BridgeKeyId,key,text)||!j.Parse(text)||!j.Keys(0,"version|risk|loss|spread|mode|killed"))return false;
   version=(long)j.Number(0,"version");if(version<1||j.Number(0,"risk")<.1||j.Number(0,"loss")<.5||j.Number(0,"spread")<0)return false;
   // Persisted remote tightening is retained across restart. Inputs cannot accidentally
   // undo a kill or restore a higher risk; explicit file reset is an operator action.
   e.risk_pct=MathMin(e.risk_pct,j.Number(0,"risk"));e.loss_pct=MathMin(e.loss_pct,j.Number(0,"loss"));e.spread_max=MathMin(e.spread_max,j.Number(0,"spread"));
   e.killed=e.killed||j.Get(0,"killed")=="true";if(j.Get(0,"mode")=="SIGNAL_ONLY")e.mode=SIGNAL_ONLY;
  }
  // Resolve a crash between durable intent and receipt conservatively. In particular,
  // an in-flight kill remains latched even if the config write was interrupted.
  string file;long f=FileFindFirst(root+"\\intent_*.json",file,FILE_COMMON);
  if(f!=INVALID_HANDLE){do {
   string id=StringSubstr(file,7,36);if(!V1Uuid(id)||FileIsExist(root+"\\receipt_"+id+".json",FILE_COMMON))continue;
   e.storage_ok=false;string raw;if(V1Read(root+"\\"+file,raw)){
    V1Json intent;if(intent.Parse(raw)&&intent.Get(intent.Field(0,"body"),"command")=="kill-switch"){e.killed=true;Persist(e);}
   }
  }while(FileFindNext(f,file));FileFindClose(f);}
  active=true;return true;
 }
 bool Heartbeat(datetime utc) {if(!active)return !RequirePythonHeartbeat;V1Json j;string raw;return Decode("python_heartbeat.json",j,utc,raw,"HEARTBEAT")&&j.Keys(j.Field(0,"body"),"api_version")&&j.Get(j.Field(0,"body"),"api_version")=="1.0.0";}
 void Poll(V1Execution &e,datetime utc,bool boundary,double atr) {
  if(!active)return;string file;long f=FileFindFirst(root+"\\command_*.json",file,FILE_COMMON);int count=0;
  if(f!=INVALID_HANDLE){do {Process(file,e,utc,boundary,atr);}while(++count<128&&FileFindNext(f,file));FileFindClose(f);}
  f=FileFindFirst(root+"\\config_*.json",file,FILE_COMMON);count=0;
  if(f!=INVALID_HANDLE){do {Process(file,e,utc,boundary,atr);}while(++count<128&&FileFindNext(f,file));FileFindClose(f);}
 }
 string Settings(V1Execution &e){
  // Legacy six-field UI cannot represent arbitrary research input steps. Report unavailable
  // instead of publishing a schema-invalid or rounded account configuration.
  if(e.spread_max<0||e.spread_max>100||MathFloor(e.spread_max)!=e.spread_max||e.risk_pct<.1||MathAbs(e.risk_pct*10-MathRound(e.risk_pct*10))>1e-6||e.loss_pct<.5||e.loss_pct>5||MathAbs(e.loss_pct*10-MathRound(e.loss_pct*10))>1e-6)return "null";
  return "{\"version\":"+(string)version+",\"values\":{\"executionMode\":"+JQuote(e.mode==AUTO_EXECUTE?"AUTO_EXECUTE":"SIGNAL_ONLY")+",\"riskPerTrade\":"+JNum(e.risk_pct)+",\"dailyLossLimit\":"+JNum(e.loss_pct)+",\"maxSpread\":"+JNum(e.spread_max)+",\"allowRemoteConfig\":"+JBool(AllowRemoteConfig)+",\"allowRealAccount\":false},\"pending_next_day\":"+JBool(pending!="")+"}";
 }
 bool State(string resources,datetime utc) {
  if(!active)return !BridgeEnabled;string body="{\"account_id\":"+JQuote((string)AccountInfoInteger(ACCOUNT_LOGIN))+",\"symbol\":"+JQuote(TradingSymbol)+",\"magic\":"+(string)Magic+",\"resources\":"+resources+"}";
  string wire=V1Wire(Payload("STATE",body,++state_seq,utc,30000),BridgeKeyId,key);return wire!=""&&V1Write(root+"\\state.json",wire);
 }
};
#endif
