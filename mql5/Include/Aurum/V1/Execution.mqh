#ifndef AURUM_V1_EXECUTION
#define AURUM_V1_EXECUTION
#include <Trade/Trade.mqh>
#include "../Economics.mqh"
#include "Inputs.mqh"
#include "Storage.mqh"
#include "Clock.mqh"
class V1Execution {
 public:
 string root;bool killed,storage_ok;double risk_pct,loss_pct,spread_max,start_equity,pnl,losses;int entries;datetime day_start,next_day;V1Mode mode;
 CTrade trade;
 V1Execution(){killed=false;storage_ok=true;start_equity=0;pnl=0;losses=0;entries=0;day_start=0;next_day=0;}
 bool Own(){return PositionGetString(POSITION_SYMBOL)==TradingSymbol&&PositionGetInteger(POSITION_MAGIC)==Magic;}
 int OpenCount(){int count=0;for(int i=0;i<PositionsTotal();i++)if(PositionGetTicket(i)>0&&Own())count++;for(int i=0;i<OrdersTotal();i++)if(OrderGetTicket(i)>0&&OrderGetString(ORDER_SYMBOL)==TradingSymbol&&OrderGetInteger(ORDER_MAGIC)==Magic)count++;return count;}
 bool Demo(){return AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO;}
 bool Permissions(){return Demo()&&ConfirmDemoAutoExecute&&TerminalInfoInteger(TERMINAL_CONNECTED)&&TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)&&MQLInfoInteger(MQL_TRADE_ALLOWED)&&AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)&&AccountInfoInteger(ACCOUNT_TRADE_EXPERT);}
 bool Init(string directory) {
  root=directory;killed=KillSwitch;risk_pct=RiskPercent;loss_pct=DailyLossPercent;spread_max=MaxSpreadPoints;mode=Mode;
  trade.SetExpertMagicNumber((ulong)Magic);trade.SetDeviationInPoints(MaxDeviationPoints);trade.SetAsyncMode(false);return trade.SetTypeFillingBySymbol(TradingSymbol);
 }
 bool Daily(datetime utc,int offset) {
  datetime start=V1DayStart(utc,TradingDayCity,TradingDayStartMinute);next_day=V1NextDay(utc,TradingDayCity,TradingDayStartMinute);
  if(start<=0||!HistorySelect(start-86400+offset*60,utc+offset*60))return false;
  pnl=0;losses=0;entries=0;double cashflows=0;ulong ids[];int total=HistoryDealsTotal();
  for(int i=0;i<total;i++) {
   ulong deal=HistoryDealGetTicket(i);if(deal==0)return false;datetime time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME)-offset*60;
   if(time<start)continue;
   ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   double result=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_FEE);
   if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL){cashflows+=result;continue;}
   // Account-wide realized loss includes other EAs/manual trades; never hide account losses.
   pnl+=result;if(result<0)losses-=result;
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=TradingSymbol||HistoryDealGetInteger(deal,DEAL_MAGIC)!=Magic)continue;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry==DEAL_ENTRY_IN||entry==DEAL_ENTRY_INOUT) {
    ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);bool seen=false;for(int j=0;j<ArraySize(ids);j++)if(ids[j]==order)seen=true;
    if(!seen){int n=ArraySize(ids);ArrayResize(ids,n+1);ids[n]=order;entries++;}
   }
  }
  if(day_start!=start) {
   string path=root+"\\day_"+JEpoch(start)+".json",text;double baseline=0;
   if(V1Read(path,text)){V1Json j;if(!j.Parse(text)||j.Number(0,"equity")<=0)return false;baseline=j.Number(0,"equity");}
   else {
    // Exact midnight equity is unavailable on a late first attachment. Conservative restart
    // baseline: current equity excluding today's realized P&L/cashflows, including floating P&L.
    baseline=AccountInfoDouble(ACCOUNT_EQUITY)-pnl-cashflows;
    if(baseline<=0||!V1Write(path,"{\"equity\":"+JNum(baseline)+"}",false))return false;
   }start_equity=baseline;day_start=start;
  }return start_equity>0&&MathIsValidNumber(pnl);
 }
 bool DailyBlocked(){return start_equity<=0||losses>=start_equity*loss_pct/100||(DailyProfitPercent>0&&pnl>=start_equity*DailyProfitPercent/100);}
 bool Quote(MqlTick &q,datetime utc,int offset) {
  if(!SymbolInfoTick(TradingSymbol,q)||q.bid<=0||q.ask<q.bid||q.time<=0)return false;
  long age=(long)utc-((long)q.time-offset*60);return age>=-5&&age<=MaxQuoteAgeSeconds;
 }
 bool Economics(V1Signal &s,double atr,string &reason) {
  double point=SymbolInfoDouble(TradingSymbol,SYMBOL_POINT),tick=SymbolInfoDouble(TradingSymbol,SYMBOL_TRADE_TICK_SIZE);
  if(!CostsKnown||point<=0||tick<=0){reason="NO_SIGNAL_DATA_QUALITY";return false;}
  int digits=(int)SymbolInfoInteger(TradingSymbol,SYMBOL_DIGITS);
  // Round protection outward, targets toward entry; then recalculate actual broker economics.
  s.sl=NormalizeDouble((s.direction>0?MathFloor(s.sl/tick):MathCeil(s.sl/tick))*tick,digits);
  s.tp=NormalizeDouble((s.direction>0?MathFloor(s.tp/tick):MathCeil(s.tp/tick))*tick,digits);
  if(s.direction*(s.entry-s.sl)<MinStopAtr*atr||s.direction*(s.tp-s.entry)<=0){reason="INVALID_PROTECTION";return false;}
  ENUM_ORDER_TYPE side=s.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
  double extra=0;if(!OrderCalcProfit(side,TradingSymbol,1,s.entry,s.entry-s.direction*SlippagePoints*point,extra)){reason="COST_UNAVAILABLE";return false;}
  double fees=CommissionRoundTripPerLot+2*MathAbs(extra);
  if(!AurumVolumeForRisk(TradingSymbol,side,s.entry,s.sl,AccountInfoDouble(ACCOUNT_EQUITY)*risk_pct/100,fees,s.volume,reason))return false;
  double loss=0,reward=0;if(!OrderCalcProfit(side,TradingSymbol,s.volume,s.entry,s.sl,loss)||!OrderCalcProfit(side,TradingSymbol,s.volume,s.entry,s.tp,reward)||loss>=0||reward<=0){reason="ECONOMICS_UNAVAILABLE";return false;}
  // Entry uses actual ask/bid, so spread is already in stop/reward. Include it only in the
  // separate friction ratio; fees/slippage are additionally charged in net RR/risk budget.
  MqlTick q;if(!SymbolInfoTick(TradingSymbol,q)){reason="SPREAD_UNKNOWN";return false;}
  double spread_cost=0;if(!OrderCalcProfit(side,TradingSymbol,s.volume,s.entry,s.entry-s.direction*(q.ask-q.bid),spread_cost)){reason="COST_UNAVAILABLE";return false;}
  double cost=fees*s.volume;s.cost=cost+MathAbs(spread_cost);s.rr=(reward-cost)/(-loss+cost);
  if(s.rr<MinimumRR){reason="NET_RR_TOO_LOW";return false;}
  if(s.cost/reward>MaximumCostRatio){reason="COST_TOO_HIGH";return false;}
  long stops=SymbolInfoInteger(TradingSymbol,SYMBOL_TRADE_STOPS_LEVEL);double market=s.direction>0?q.bid:q.ask;
  if(s.direction*(market-s.sl)<stops*point||s.direction*(s.tp-market)<stops*point){reason="BROKER_STOPS_LEVEL";return false;}
  return AurumMarginAllowed(TradingSymbol,side,s.volume,s.entry,MinimumMarginLevel,reason);
 }
 bool Duplicate(V1Signal &s){return FileIsExist(root+"\\setup_"+V1HashText(s.setup_id)+".json",FILE_COMMON);}
 bool Cooldown(V1Signal &s,datetime utc,int offset) {
  if(CooldownBars==0)return false;
  if(!HistorySelect(utc+offset*60-CooldownBars*900,utc+offset*60))return true;
  for(int i=0;i<HistoryDealsTotal();i++) {
   ulong deal=HistoryDealGetTicket(i);if(HistoryDealGetInteger(deal,DEAL_REASON)!=DEAL_REASON_SL||HistoryDealGetString(deal,DEAL_SYMBOL)!=TradingSymbol||HistoryDealGetInteger(deal,DEAL_MAGIC)!=Magic)continue;
   ulong position=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);string text;V1Json j;
   if(!V1Read(root+"\\position_"+(string)position+".json",text)||!j.Parse(text))return true;
   if(j.Get(0,"level_id")==s.level_id&&(int)j.Number(0,"direction")==s.direction)return true;
  }return false;
 }
 bool Reserve(V1Signal &s) {
  string path=root+"\\setup_"+V1HashText(s.setup_id)+".json";
  // Write-ahead consumed intent. Never retry an ambiguous OrderSend, even after restart.
  bool ok=V1Write(path,"{\"setup_id\":"+JQuote(s.setup_id)+",\"level_id\":"+JQuote(s.level_id)+",\"direction\":"+(string)s.direction+",\"sl\":"+JNum(s.sl)+",\"entry\":"+JNum(s.entry)+",\"volume\":"+JNum(s.volume)+"}",false);
  if(!ok)storage_ok=false;return ok;
 }
 bool Send(V1Signal &s) {
  if(mode!=AUTO_EXECUTE||!Permissions()||killed||!storage_ok){s.reason="AUTO_EXECUTE_LOCKED";return false;}
  // Netting accounts cannot isolate manual/other-EA positions sharing the symbol.
  if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING&&PositionSelect(TradingSymbol)){s.reason="NETTING_SYMBOL_OCCUPIED";return false;}
  MqlTradeRequest req={};MqlTradeCheckResult check={};MqlTradeResult result={};
  req.action=TRADE_ACTION_DEAL;req.symbol=TradingSymbol;req.magic=(ulong)Magic;req.volume=s.volume;
  req.type=s.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;req.price=s.entry;req.sl=s.sl;req.tp=s.tp;req.deviation=MaxDeviationPoints;
  long filling=SymbolInfoInteger(TradingSymbol,SYMBOL_FILLING_MODE);
  req.type_filling=(filling&SYMBOL_FILLING_FOK)!=0?ORDER_FILLING_FOK:((filling&SYMBOL_FILLING_IOC)!=0?ORDER_FILLING_IOC:ORDER_FILLING_RETURN);
  req.comment="A1:"+StringSubstr(V1HashText(s.setup_id),0,24);
  if(!OrderCheck(req,check)||(check.retcode!=0&&check.retcode!=TRADE_RETCODE_DONE)){s.reason="ORDER_CHECK:"+(string)check.retcode;return false;}
  if(!OrderSend(req,result)){s.reason="ORDER_SEND_UNKNOWN:"+(string)result.retcode;return false;}
  if(result.retcode!=TRADE_RETCODE_DONE&&result.retcode!=TRADE_RETCODE_DONE_PARTIAL){s.reason="ORDER_OUTCOME:"+(string)result.retcode;return false;}
  s.reason="ORDER_FILLED:"+(string)result.deal;return true;
 }
 void Reconcile() {
  for(int i=0;i<PositionsTotal();i++) {
   if(PositionGetTicket(i)==0||!Own())continue;ulong id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   string path=root+"\\position_"+(string)id+".json";if(FileIsExist(path,FILE_COMMON))continue;
   // Locate immutable setup intent via the order comment (survives a crash after fill).
   string comment=PositionGetString(POSITION_COMMENT),file;long find=FileFindFirst(root+"\\setup_*.json",file,FILE_COMMON);
   bool found=false;if(find!=INVALID_HANDLE) {
    do {string text;V1Json j;if(V1Read(root+"\\"+file,text)&&j.Parse(text)&&comment=="A1:"+StringSubstr(V1HashText(j.Get(0,"setup_id")),0,24)) {
     found=V1Write(path,text,false);break;
    }}while(FileFindNext(find,file));FileFindClose(find);
   }
   if(!found)storage_ok=false;
  }
 }
 bool ResultOK(){uint ret=trade.ResultRetcode();return ret==TRADE_RETCODE_DONE||ret==TRADE_RETCODE_DONE_PARTIAL;}
 bool Close(ulong ticket) {
  if(!PositionSelectByTicket(ticket)||!Own()||!Demo())return false;
  bool ok=trade.PositionClose(ticket,MaxDeviationPoints)&&ResultOK();
  V1Append(root+"\\execution.jsonl","{\"action\":\"CLOSE\",\"ticket\":"+JQuote((string)ticket)+",\"retcode\":"+(string)trade.ResultRetcode()+",\"ok\":"+JBool(ok)+"}");return ok;
 }
 bool BreakEven(ulong ticket,double atr) {
  if(!PositionSelectByTicket(ticket)||!Own()||!Demo())return false;
  int d=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;double entry=PositionGetDouble(POSITION_PRICE_OPEN),old=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
  double tick=SymbolInfoDouble(TradingSymbol,SYMBOL_TRADE_TICK_SIZE);if(tick<=0)return false;
  double stop=entry+d*BreakEvenBufferAtr*atr;stop=(d>0?MathCeil(stop/tick):MathFloor(stop/tick))*tick;
  MqlTick q;if(!SymbolInfoTick(TradingSymbol,q))return false;double current=d>0?q.bid:q.ask;
  double gap=MathMax(SymbolInfoInteger(TradingSymbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(TradingSymbol,SYMBOL_TRADE_FREEZE_LEVEL))*SymbolInfoDouble(TradingSymbol,SYMBOL_POINT);
  if(old>0&&d*(old-stop)>=0)return true;if(d*(current-stop)<=gap)return false;
  bool ok=trade.PositionModify(ticket,stop,tp)&&ResultOK();V1Append(root+"\\execution.jsonl","{\"action\":\"BREAK_EVEN\",\"ticket\":"+JQuote((string)ticket)+",\"retcode\":"+(string)trade.ResultRetcode()+",\"ok\":"+JBool(ok)+"}");return ok;
 }
 void Manage(datetime utc,int offset,double atr,bool in_session) {
  Reconcile();MqlDateTime ny;TimeToStruct(utc+V1ZoneOffset(utc,"New_York")*60,ny);
  bool weekend=ny.day_of_week==6||ny.day_of_week==0||(ny.day_of_week==5&&ny.hour*60+ny.min>=WeekendCloseNYMinute-WeekendCloseMinutes);
  for(int i=PositionsTotal()-1;i>=0;i--) {
   ulong ticket=PositionGetTicket(i);if(ticket==0||!Own())continue;
   if(PositionGetDouble(POSITION_SL)<=0||PositionGetDouble(POSITION_TP)<=0){Close(ticket);continue;}
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME)-offset*60;
   if(weekend||utc-opened>=MaxHoldingHours*3600||(SessionFilterEnabled&&!in_session)){Close(ticket);continue;}
   if(atr<=0||atr==EMPTY_VALUE)continue;string text;V1Json j;ulong id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   if(!V1Read(root+"\\position_"+(string)id+".json",text)||!j.Parse(text))continue;
   double initial_risk=MathAbs(j.Number(0,"entry")-j.Number(0,"sl"));if(initial_risk<=0||initial_risk==EMPTY_VALUE)continue;
   int d=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;double r=d*(PositionGetDouble(POSITION_PRICE_CURRENT)-PositionGetDouble(POSITION_PRICE_OPEN))/initial_risk;
   if(BreakEvenEnabled&&r>=BreakEvenTriggerR)BreakEven(ticket,atr);
   string marker=root+"\\partial_"+(string)id+".json";
   if(PartialCloseEnabled&&r>=PartialCloseTriggerR&&!FileIsExist(marker,FILE_COMMON)) {
    double step=SymbolInfoDouble(TradingSymbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(TradingSymbol,SYMBOL_VOLUME_MIN),volume=PositionGetDouble(POSITION_VOLUME);
    if(step<=0)continue;double part=MathFloor(volume*PartialClosePercent/100/step)*step;
    if(part<minimum||volume-part<minimum)continue;
    // Intent before effect: an unknown partial outcome is never repeated.
    if(!V1Write(marker,"{}",false)){storage_ok=false;continue;}
    bool ok=false;
    if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)ok=trade.PositionClosePartial(ticket,part,MaxDeviationPoints)&&ResultOK();
    V1Append(root+"\\execution.jsonl","{\"action\":\"PARTIAL_CLOSE\",\"ticket\":"+JQuote((string)ticket)+",\"ok\":"+JBool(ok)+",\"retcode\":"+(string)trade.ResultRetcode()+"}");
   }
  }
 }
};
#endif
