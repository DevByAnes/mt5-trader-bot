#property strict
#property script_show_inputs
#include "../Include/Aurum/V1/Execution.mqh"
// Explicitly authorized one-off Demo connectivity test. Never part of strategy selection.
input bool ConfirmOneDemoRoundTrip=false;
void OnStart() {
 for(int i=0;i<200&&!TerminalInfoInteger(TERMINAL_CONNECTED);i++)Sleep(100);
 if(!ConfirmOneDemoRoundTrip||AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO||
    AccountInfoInteger(ACCOUNT_LOGIN)!=10013438329||_Symbol!="XAUUSD"||
    !TerminalInfoInteger(TERMINAL_CONNECTED)) {Print("AURUM_DEMO_TEST: explicit designated Demo opt-in required");return;}
 V1Execution e;string root="AurumDemoAcceptance\\"+(string)GetMicrosecondCount();FolderCreate("AurumDemoAcceptance",FILE_COMMON);FolderCreate(root,FILE_COMMON);
 e.Init(root);e.mode=AUTO_EXECUTE;
 if(!e.Permissions()){V1Write("Aurum\\demo_execution_result.json","{\"demo\":true,\"sent\":false,\"reason\":\"TRADING_PERMISSION_DISABLED\"}");Print("AURUM_DEMO_TEST: Algo Trading or script trading permission is disabled");return;}
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),quantum=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 double distance=MathMax(500*point,3*SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point);
 V1Signal s;ZeroMemory(s);s.direction=1;s.entry=q.ask;s.sl=MathFloor((q.bid-distance)/quantum)*quantum;s.tp=MathCeil((q.ask+2*distance)/quantum)*quantum;s.volume=minimum;
 s.setup_id="DEMO_TRANSPORT_ACCEPTANCE:"+(string)GetMicrosecondCount();s.level_id="TEST_ONLY";
 if(!e.Reserve(s))return;
 bool sent=e.Send(s);Print("AURUM_DEMO_TEST send=",sent," result=",s.reason);
 ulong ticket=0;
 for(int retry=0;retry<20&&ticket==0;retry++) {
  for(int i=0;i<PositionsTotal();i++){ulong t=PositionGetTicket(i);if(t>0&&e.Own()&&PositionGetString(POSITION_COMMENT)=="A1:"+StringSubstr(V1HashText(s.setup_id),0,24)){ticket=t;break;}}
  if(ticket==0)Sleep(100);
 }
 bool protected_position=false,closed=false;
 if(ticket>0&&PositionSelectByTicket(ticket)) {
  protected_position=PositionGetDouble(POSITION_SL)>0&&PositionGetDouble(POSITION_TP)>0;
  e.Reconcile();closed=e.Close(ticket);
  // Close only the designated test ticket, never other positions. Broker SL stays attached.
  for(int i=0;i<3&&!closed;i++){Sleep(200);closed=!PositionSelectByTicket(ticket)||e.Close(ticket);}
 }
 string result="{\"demo\":true,\"test_only\":true,\"volume\":"+JNum(minimum)+",\"sent\":"+JBool(sent)+",\"protected\":"+JBool(protected_position)+",\"closed\":"+JBool(closed)+",\"ticket\":"+JQuote((string)ticket)+",\"reason\":"+JQuote(s.reason)+"}";
 V1Write("Aurum\\demo_execution_result.json",result);Print("AURUM_DEMO_TEST ",result);
}
