#ifndef AURUM_V1_ENGINE
#define AURUM_V1_ENGINE
#include "Strategies.mqh"
#include "Clock.mqh"
#include "Bridge.mqh"
class V1Engine {
 private:
 V1Params p;MqlRates bars[],h1[];double atr[];V1Swing swings[],hourly[];V1Level levels[];V1Break breaks[];V1Sweep sweeps[];
 datetime last_bar,now_utc;double last_atr,atr_ratio,day_range_ratio;int offset,lock_handle;bool data_ok,daily_ok;
 string last_reason,session,signal_items[],log_items[];double eq_history[],spread_history[],atr_history[];
 V1BrokerClock clock;V1News news;
 bool InSession(datetime utc) {return (LondonEnabled&&V1InSession(utc,"London",LondonStartMinute,LondonEndMinute))||(NewYorkEnabled&&V1InSession(utc,"New_York",NewYorkStartMinute,NewYorkEndMinute));}
 string SessionName(datetime utc){string result="";if(V1InSession(utc,"Tokyo",AsiaStartMinute,AsiaEndMinute))result="Tokyo";
  if(LondonEnabled&&V1InSession(utc,"London",LondonStartMinute,LondonEndMinute))result+=(result==""?"":" / ")+"London";
  if(NewYorkEnabled&&V1InSession(utc,"New_York",NewYorkStartMinute,NewYorkEndMinute))result+=(result==""?"":" / ")+"New York";return result==""?"Outside sessions":result;}
 void Ring(string &items[],string item,int maximum=100){int n=ArraySize(items);if(n>=maximum){for(int i=1;i<n;i++)items[i-1]=items[i];n--;ArrayResize(items,n);}ArrayResize(items,n+1);items[n]=item;}
 void Sample(double &items[],double value){int n=ArraySize(items);if(n>=120){for(int i=1;i<n;i++)items[i-1]=items[i];n--;ArrayResize(items,n);}ArrayResize(items,n+1);items[n]=value;}
 string Join(const string &items[]){string result="[";for(int i=ArraySize(items)-1;i>=0;i--){if(i<ArraySize(items)-1)result+=",";result+=items[i];}return result+"]";}
 string Numbers(const double &items[]){string result="[";for(int i=0;i<ArraySize(items);i++){if(i)result+=",";result+=JNum(items[i]);}return result+"]";}
 void Log(string level,string message) {
  string item="{\"id\":"+JQuote(V1NewUuid())+",\"time_utc\":"+JQuote(JTime(now_utc))+",\"level\":"+JQuote(level)+",\"source\":\"MT5-EA\",\"message\":"+JQuote(message)+"}";
  Ring(log_items,item);if(!V1Append(exec.root+"\\events_"+JEpoch(V1DayStart(now_utc,TradingDayCity,TradingDayStartMinute))+".jsonl",item))exec.storage_ok=false;
  Print("AURUM ",level," ",message);
 }
 void SignalLog(V1Signal &s,string status,string reason) {
  string features="{\"atr\":"+JNum(last_atr)+",\"atr_ratio\":"+JNum(atr_ratio)+",\"day_range_ratio\":"+JNum(day_range_ratio)+",\"signal_range_atr\":"+(data_ok?JNum((bars[ArraySize(bars)-1].high-bars[ArraySize(bars)-1].low)/last_atr):"null")+",\"h1_structure\":"+JQuote(V1Structure(V1Trend(hourly,2147483647)))+",\"m15_structure\":"+JQuote(V1Structure(V1Trend(swings,ArraySize(bars)-1)))+",\"session\":"+JQuote(session)+",\"level_type\":"+JQuote(s.level_type)+",\"spread\":"+Spread()+",\"fvg\":"+FVG()+",\"order_block\":"+OrderBlock()+"}";
  string record="{\"time\":"+JQuote(JTime(now_utc))+",\"strategy\":"+JQuote(s.strategy)+",\"direction\":"+JQuote(V1Direction(s.direction))+",\"setup_id\":"+JQuote(s.setup_id)+",\"core_passed\":"+JQuote(s.core)+",\"bonus_hit\":"+JQuote(s.bonus)+",\"ranking_score\":"+JNum(s.score)+",\"historical_win_probability\":null,\"mode_strict_or_soft\":"+JQuote(s.soft?"SOFT":"STRICT")+",\"entry\":"+JNum(s.entry)+",\"sl\":"+JNum(s.sl)+",\"tp\":"+JNum(s.tp)+",\"rr\":"+JNum(s.rr)+",\"cost_estimate\":"+JNum(s.cost)+",\"status\":"+JQuote(status)+",\"reject_reason\":"+JQuote(reason)+",\"features\":"+features+"}";
  if(!V1Append(exec.root+"\\signals_"+JEpoch(V1DayStart(now_utc,TradingDayCity,TradingDayStartMinute))+".jsonl",record))exec.storage_ok=false;
  string decision=status=="ISSUED"?V1Direction(s.direction):(status=="NO_SIGNAL"?"NO_SIGNAL":"WAIT");
  string item="{\"id\":"+JQuote(s.setup_id==""?V1NewUuid():s.setup_id)+",\"time_utc\":"+JQuote(JTime(now_utc))+",\"decision\":"+JQuote(decision)+",\"reasons\":["+JQuote(s.strategy+" "+status+" "+reason+" rank="+DoubleToString(s.score,1)+" (uncalibrated)")+"],\"price\":"+(s.entry>0?JNum(s.entry):"null")+",\"reason_code\":"+(reason==""?"null":JQuote(reason))+",\"actual\":null,\"limit\":null}";
  Ring(signal_items,item);
 }
 string FVG(){int n=ArraySize(bars);if(!data_ok||n<3)return "null";int i=n-1,d=bars[i].low>bars[i-2].high?1:(bars[i].high<bars[i-2].low?-1:0);
  if(d==0)return "null";return "{\"direction\":"+JQuote(V1Direction(d))+",\"size_atr\":"+JNum(d>0?(bars[i].low-bars[i-2].high)/last_atr:(bars[i-2].low-bars[i].high)/last_atr)+",\"formed_at\":"+JQuote(JTime(bars[i].time+900))+",\"filled_at\":null}";}
 string OrderBlock(){if(!data_ok)return "null";int at=ArraySize(bars)-1;for(int k=ArraySize(breaks)-1;k>=0;k--)if(breaks[k].index==at&&!breaks[k].choch){int d=breaks[k].direction;for(int j=at-1;j>=0;j--)if(d*(bars[j].close-bars[j].open)<0)return "{\"time\":"+JQuote(JTime(bars[j].time))+",\"low\":"+JNum(bars[j].low)+",\"high\":"+JNum(bars[j].high)+"}";}return "null";}
 bool SessionOpenAt(datetime server) {
  MqlDateTime d;TimeToStruct(server,d);datetime from,to;int second=d.hour*3600+d.min*60+d.sec;
  for(uint k=0;k<20;k++) {
   if(!SymbolInfoSessionTrade(TradingSymbol,(ENUM_DAY_OF_WEEK)d.day_of_week,k,from,to))break;
   long first=(long)from,last=(long)to;if(first==last)return true;
   if(last>first?(second>=first&&second<last):(second>=first||second<last))return true;
  }return false;
 }
 bool Load(MqlRates &out[],ENUM_TIMEFRAMES tf,int count) {
  MqlRates source[];if(CopyRates(TradingSymbol,tf,1,count,source)!=count)return false;
  int seconds=PeriodSeconds(tf);ArrayResize(out,count);
  for(int i=0;i<count;i++) {
   out[i]=source[i];datetime utc;if(!clock.Convert(source[i].time,utc))return false;out[i].time=utc;
   if(utc+seconds>now_utc)return false;
   if(i>0)for(datetime missing=source[i-1].time+seconds;missing<source[i].time;missing+=seconds)if(SessionOpenAt(missing))return false;
  }return V1ValidBars(out,seconds);
 }
 datetime WeekStart(datetime utc) {
  int off=V1ZoneOffset(utc,"New_York");MqlDateTime d;TimeToStruct(utc+off*60,d);datetime civil=V1Date(d.year,d.mon,d.day)-d.day_of_week*86400+WeekendCloseNYMinute*60;
  datetime result=civil-off*60;for(int i=0;i<3;i++)result=civil-V1ZoneOffset(result,"New_York")*60;if(result>utc){civil-=7*86400;for(int i=0;i<3;i++)result=civil-V1ZoneOffset(result,"New_York")*60;}return result;
 }
 bool Range(datetime first,datetime last,double &hi,double &lo,int &created) {
  hi=-DBL_MAX;lo=DBL_MAX;created=-1;bool begins=false;
  for(int i=0;i<ArraySize(bars);i++) {
   if(bars[i].time<first)begins=true;
   if(bars[i].time>=first&&bars[i].time+900<=last){hi=MathMax(hi,bars[i].high);lo=MathMin(lo,bars[i].low);}
   if(created<0&&bars[i].time>=last)created=i;
  }return begins&&hi>lo&&created>=0;
 }
 void PeriodLevel(datetime first,datetime last,string prefix) {
  double hi,lo;int created;if(!Range(first,last,hi,lo,created))return;
  V1AddLevel(levels,prefix+"H:"+(string)last,prefix+"H",1,hi,created-1,last,true);
  V1AddLevel(levels,prefix+"L:"+(string)last,prefix+"L",-1,lo,created-1,last,true);
 }
 void Levels() {
  ArrayResize(levels,0);V1SwingLevels(swings,"M15",levels,bars,900);V1SwingLevels(hourly,"H1",levels,bars,3600);
  datetime today=V1DayStart(now_utc,TradingDayCity,TradingDayStartMinute),previous=V1DayStart(today-1,TradingDayCity,TradingDayStartMinute);
  PeriodLevel(previous,today,"PD");datetime week=WeekStart(now_utc);PeriodLevel(WeekStart(week-1),week,"PW");
  // Most recent fully completed Tokyo session; never use an unfinished Asia range.
  MqlDateTime tokyo;TimeToStruct(now_utc+9*3600,tokyo);datetime asia=V1Date(tokyo.year,tokyo.mon,tokyo.day)+AsiaEndMinute*60-9*3600;
  if(asia>now_utc)asia-=86400;datetime start=asia-(AsiaEndMinute>AsiaStartMinute?AsiaEndMinute-AsiaStartMinute:1440-AsiaStartMinute+AsiaEndMinute)*60;
  PeriodLevel(start,asia,"ASIA_");
  if(RoundLevelsEnabled){double center=MathFloor(bars[ArraySize(bars)-1].close/RoundLevelStep)*RoundLevelStep;for(int k=-RoundLevelCount;k<=RoundLevelCount;k++){double price=center+k*RoundLevelStep;int side=price>=bars[ArraySize(bars)-1].close?1:-1;V1AddLevel(levels,"ROUND:"+JNum(price),"ROUND",side,price,MathMax(0,ArraySize(bars)-100),bars[MathMax(0,ArraySize(bars)-100)].time);}}
  V1LevelHistory(levels,bars,atr,ArraySize(bars)-2,p);
  double ranges[];datetime end=today;
  for(int d=0;d<35&&ArraySize(ranges)<20;d++){datetime begin=V1DayStart(end-1,TradingDayCity,TradingDayStartMinute);double hi,lo;int created;if(Range(begin,end,hi,lo,created)){int z=ArraySize(ranges);ArrayResize(ranges,z+1);ranges[z]=hi-lo;}end=begin;}
  double high=-DBL_MAX,low=DBL_MAX;for(int i=0;i<ArraySize(bars);i++)if(bars[i].time>=today){high=MathMax(high,bars[i].high);low=MathMin(low,bars[i].low);}
  double median=V1Median(ranges,ArraySize(ranges)-1,20);day_range_ratio=median==EMPTY_VALUE||high<low?EMPTY_VALUE:(high-low)/median;
 }
 string Spread(){MqlTick q;if(!SymbolInfoTick(TradingSymbol,q)||SymbolInfoDouble(TradingSymbol,SYMBOL_POINT)<=0)return "null";return JNum((q.ask-q.bid)/SymbolInfoDouble(TradingSymbol,SYMBOL_POINT));}
 string Gate() {
  if(!data_ok||!daily_ok||!exec.storage_ok||!CostsKnown||exec.spread_max<=0||AtrRatioLow<=0||AtrRatioHigh<=AtrRatioLow)return "NO_SIGNAL_DATA_QUALITY";
  if(exec.killed)return "KILL_SWITCH";
  if(RequirePythonHeartbeat&&!bridge.Heartbeat(now_utc))return "BRIDGE_OFFLINE";
  MqlTick q;if(!TerminalInfoInteger(TERMINAL_CONNECTED)||!exec.Quote(q,now_utc,offset))return "NO_SIGNAL_DATA_QUALITY";
  if((q.ask-q.bid)/SymbolInfoDouble(TradingSymbol,SYMBOL_POINT)>exec.spread_max)return "SPREAD_HIGH";
  int ng=news.Gate(now_utc,NewsBeforeMinutes,NewsAfterMinutes);if(ng<0)return "NO_SIGNAL_DATA_QUALITY:NEWS_CALENDAR_COVERAGE";if(ng>0)return "NEWS_WINDOW";
  if(SessionFilterEnabled&&!InSession(now_utc))return "SESSION_BLOCKED";
  if(atr_ratio<AtrRatioLow||atr_ratio>AtrRatioHigh)return "VOLATILITY_OUT";
  if(exec.DailyBlocked())return "DAILY_LIMIT";
  if(exec.OpenCount()>=MaxOpen||exec.entries>=MaxTradesPerDay)return "MAX_TRADES";
  MqlDateTime ny;TimeToStruct(now_utc+V1ZoneOffset(now_utc,"New_York")*60,ny);
  if(ny.day_of_week==0||ny.day_of_week==6||(ny.day_of_week==5&&ny.hour*60+ny.min>=WeekendCloseNYMinute-WeekendCloseMinutes))return "WEEKEND_EXIT_WINDOW";
  return "";
 }
 void Evaluate() {
  last_reason=Gate();if(last_reason!=""){V1Signal empty;ZeroMemory(empty);SignalLog(empty,"NO_SIGNAL",last_reason);return;}
  int at=ArraySize(bars)-1;V1Signal candidates[];
  V1Evaluate(bars,atr,swings,hourly,levels,breaks,sweeps,p,InSession(now_utc),true,candidates);
  string strategies[]={"S1","S2","S3","S4","S5"};bool enabled[]={p.s1,p.s2,p.s3,p.s4,p.s5};
  for(int k=0;k<5;k++)if(enabled[k]){bool found=false;for(int i=0;i<ArraySize(candidates);i++)if(candidates[i].strategy==strategies[k])found=true;if(!found){V1Signal empty;ZeroMemory(empty);empty.strategy=strategies[k];SignalLog(empty,"NO_SIGNAL","CORE_NOT_MET");}}
  MqlTick quote;if(!exec.Quote(quote,now_utc,offset))return;
  for(int i=0;i<ArraySize(candidates);i++) {
   candidates[i].entry=candidates[i].direction>0?quote.ask:quote.bid;
   string reason="";
   if(exec.Duplicate(candidates[i]))reason="DUPLICATE_SETUP";
   else if(exec.Cooldown(candidates[i],now_utc,offset))reason="COOLDOWN";
   else if(!V1Target(candidates[i],levels,last_atr,p))reason=candidates[i].reason;
   else {
    // Try opposing levels in price order until one satisfies broker net economics.
    double base_score=candidates[i].score;string base_bonus=candidates[i].bonus;bool valid=false;
    double lower=0;
    for(int attempt=0;attempt<ArraySize(levels);attempt++) {
     double best=DBL_MAX,target=0;
     for(int k=0;k<ArraySize(levels);k++)if(!levels[k].invalidated&&levels[k].side==candidates[i].direction){double dist=candidates[i].direction*(levels[k].price-candidates[i].entry);if(dist>lower&&dist<best&&dist/(candidates[i].direction*(candidates[i].entry-candidates[i].sl))>=p.rr){best=dist;target=levels[k].price;}}
     if(target==0)break;candidates[i].tp=target;lower=best;
     if(exec.Economics(candidates[i],last_atr,reason)){valid=true;break;}
     if(reason!="NET_RR_TOO_LOW"&&reason!="COST_TOO_HIGH"&&reason!="BROKER_STOPS_LEVEL")break;
    }
    candidates[i].score=base_score;candidates[i].bonus=base_bonus;
    if(valid)reason="";else if(reason=="")reason="NO_ECONOMIC_TARGET";
   }
   if(reason!=""){candidates[i].status="REJECTED";SignalLog(candidates[i],"REJECTED",reason);}
   else {candidates[i].status="ELIGIBLE";SignalLog(candidates[i],"WAIT","CANDIDATE_RANKED");}
  }
  int selected=V1Resolve(candidates,p,last_reason);
  if(selected<0){V1Signal empty;ZeroMemory(empty);SignalLog(empty,"WAIT",last_reason);return;}
  V1Signal chosen=candidates[selected];
  // Medium scores notify only; automatic order placement requires T_HIGH.
  if(exec.mode==AUTO_EXECUTE&&!chosen.strong){SignalLog(chosen,"WAIT","MEDIUM_SCORE_NOTIFICATION_ONLY");return;}
  if(now_utc-(bars[at].time+900)>MaxEntryDelaySeconds){SignalLog(chosen,"REJECTED","ENTRY_WINDOW_EXPIRED");return;}
  string gate=Gate();MqlTick current;
  if(gate!=""||!exec.Quote(current,now_utc,offset)){SignalLog(chosen,"REJECTED",gate==""?"NO_SIGNAL_DATA_QUALITY":gate);return;}
  double entry=chosen.direction>0?current.ask:current.bid,point=SymbolInfoDouble(TradingSymbol,SYMBOL_POINT);
  // Compare with next bar's actual opening bid, adjusted for the side's spread.
  double opening=iOpen(TradingSymbol,PERIOD_M15,0)+(chosen.direction>0?current.ask-current.bid:0);
  if(opening<=0||MathAbs(entry-opening)>MaxDeviationPoints*point||MathAbs(entry-chosen.entry)>MaxDeviationPoints*point){SignalLog(chosen,"REJECTED","ENTRY_DEVIATION");return;}
  chosen.entry=entry;if(!exec.Economics(chosen,last_atr,last_reason)){SignalLog(chosen,"REJECTED",last_reason);return;}
  if(!exec.Reserve(chosen)){SignalLog(chosen,"REJECTED","INTENT_STORAGE_FAILED");return;}
  if(exec.mode==SIGNAL_ONLY){SignalLog(chosen,"ISSUED","SIGNAL_ONLY");Log("INFO",chosen.strategy+" "+V1Direction(chosen.direction)+" "+chosen.setup_id);}
  else if(exec.Send(chosen)){exec.Reconcile();SignalLog(chosen,"ISSUED",chosen.reason);Log("INFO",chosen.reason);}
  else {SignalLog(chosen,"REJECTED",chosen.reason);Log("ERROR",chosen.reason);}
 }
 string Positions() {
  string result="[";int count=0;
  for(int i=0;i<PositionsTotal();i++){ulong ticket=PositionGetTicket(i);if(ticket==0||!exec.Own())continue;
   int d=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;double entry=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);string text,r="null";V1Json j;
   if(V1Read(exec.root+"\\position_"+(string)PositionGetInteger(POSITION_IDENTIFIER)+".json",text)&&j.Parse(text)){double risk=MathAbs(j.Number(0,"entry")-j.Number(0,"sl"));if(risk>0&&risk<DBL_MAX)r=JNum(d*(PositionGetDouble(POSITION_PRICE_CURRENT)-entry)/risk);}
   if(count++>0)result+=",";result+="{\"id\":"+JQuote((string)ticket)+",\"side\":"+JQuote(V1Direction(d))+",\"entry\":"+JNum(entry)+",\"sl\":"+(sl>0?JNum(sl):"null")+",\"tp\":"+(tp>0?JNum(tp):"null")+",\"lot\":"+JNum(PositionGetDouble(POSITION_VOLUME))+",\"r\":"+r+",\"status\":\"OPEN\",\"risk_free\":"+JBool(sl>0&&d*(sl-entry)>=0)+",\"time_exit_utc\":"+JQuote(JTime((datetime)PositionGetInteger(POSITION_TIME)-offset*60+MaxHoldingHours*3600))+"}";
  }return result+"]";
 }
 string Chart(){
  MqlRates view[];string basis="UTC";
  if(data_ok)ArrayCopy(view,bars,0,MathMax(0,ArraySize(bars)-200));
  else {
   // Monitoring is independent of strategy readiness. Preserve broker-local time
   // explicitly; never apply today's unknown offset to historical candles.
   basis="BROKER";if(CopyRates(TradingSymbol,PERIOD_M15,1,200,view)<=0||!V1ValidBars(view,900))return "null";
  }
  string text="{\"time_basis\":"+JQuote(basis)+",\"candles\":[";
  for(int i=0;i<ArraySize(view);i++){
   if(i>0)text+=",";text+="{\"time\":"+JEpoch(view[i].time)+",\"open\":"+JNum(view[i].open)+",\"high\":"+JNum(view[i].high)+",\"low\":"+JNum(view[i].low)+",\"close\":"+JNum(view[i].close)+"}";
  }return text+"],\"overlays\":[]}";
 }
 string Journal(){if(offset==100000||!HistorySelect(now_utc+offset*60-35*86400,now_utc+offset*60))return "null";string result="{\"items\":[";int count=0;
  for(int i=HistoryDealsTotal()-1;i>=0&&count<200;i--){ulong ticket=HistoryDealGetTicket(i);if(HistoryDealGetInteger(ticket,DEAL_MAGIC)!=Magic||HistoryDealGetString(ticket,DEAL_SYMBOL)!=TradingSymbol)continue;
   ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(ticket,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
   if(count++>0)result+=",";datetime at=(datetime)HistoryDealGetInteger(ticket,DEAL_TIME)-offset*60;result+="{\"id\":"+JQuote((string)ticket)+",\"time_utc\":"+JQuote(JTime(at))+",\"side\":"+JQuote(type==DEAL_TYPE_BUY?"BUY":"SELL")+",\"r\":null,\"session\":"+JQuote(SessionName(at))+",\"result\":"+JQuote("MT5 DEAL profit="+JNum(HistoryDealGetDouble(ticket,DEAL_PROFIT))+" commission="+JNum(HistoryDealGetDouble(ticket,DEAL_COMMISSION))+" entry="+(string)HistoryDealGetInteger(ticket,DEAL_ENTRY))+"}";
  }return result+"],\"next_cursor\":null}";}
 void Publish() {
  string health="{\"state\":\"healthy\",\"heartbeat_utc\":"+JQuote(JTime(now_utc))+",\"latency_ms\":null}",unknown="{\"state\":\"offline\",\"heartbeat_utc\":null,\"latency_ms\":null}";
  string status="{\"backend\":"+unknown+",\"ea\":"+health+",\"mt5\":"+(TerminalInfoInteger(TERMINAL_CONNECTED)?health:unknown)+",\"broker_offset_minutes\":"+(offset==100000?"null":(string)offset)+"}";
  string state="{\"mode\":"+JQuote(exec.mode==AUTO_EXECUTE?"AUTO_EXECUTE":"SIGNAL_ONLY")+",\"equity\":"+JNum(AccountInfoDouble(ACCOUNT_EQUITY))+",\"pnl_today\":"+(daily_ok?JNum(exec.pnl):"null")+",\"risk_active\":"+JBool(!exec.killed&&daily_ok&&!exec.DailyBlocked())+",\"risk_reason\":"+JQuote(last_reason)+",\"session\":"+JQuote(session)+",\"trend_h1\":"+(data_ok?JQuote(V1Structure(V1Trend(hourly,2147483647))):"null")+",\"trend_h4\":null,\"h1_strength\":null,\"h4_strength\":null,\"atr\":"+JNum(last_atr)+",\"spread\":"+Spread()+",\"trades_today\":"+(daily_ok?(string)exec.entries:"null")+",\"last_rejection\":"+JQuote(last_reason)+",\"live_prerequisites\":[{\"key\":\"demo_only\",\"ok\":false,\"reason\":\"Real-account LIVE disabled; AUTO_EXECUTE requires native Demo opt-in\"}]}";
  double amount=exec.start_equity*exec.loss_pct/100,remaining=MathMax(0,amount-exec.losses),profit=exec.start_equity*DailyProfitPercent/100;
  string risk=daily_ok?"{\"state\":"+JQuote(exec.killed||exec.DailyBlocked()?"STOPPED":"ACTIVE")+",\"reason\":"+(last_reason==""?"null":JQuote(last_reason))+",\"start_equity\":"+JNum(exec.start_equity)+",\"current_equity\":"+JNum(AccountInfoDouble(ACCOUNT_EQUITY))+",\"loss_limit_amount\":"+JNum(amount)+",\"loss_remaining\":"+JNum(remaining)+",\"loss_remaining_percent\":"+JNum(amount>0?remaining/amount*100:0)+",\"profit_target_amount\":"+(profit>0?JNum(profit):"null")+",\"profit_remaining\":"+(profit>0?JNum(MathMax(0,profit-exec.pnl)):"null")+",\"profit_remaining_percent\":"+(profit>0?JNum(MathMax(0,profit-exec.pnl)/profit*100):"null")+",\"trades_remaining\":"+(string)MathMax(0,MaxTradesPerDay-exec.entries)+",\"next_day_utc\":"+JQuote(JTime(exec.next_day))+"}":"null";
  state=StringSubstr(state,0,StringLen(state)-1)+",\"account_currency\":"+JQuote(AccountInfoString(ACCOUNT_CURRENCY))+"}";
  if(!daily_ok)risk="{\"state\":\"STOPPED\",\"reason\":"+JQuote(last_reason)+",\"start_equity\":null,\"current_equity\":"+JNum(AccountInfoDouble(ACCOUNT_EQUITY))+",\"loss_limit_amount\":null,\"loss_remaining\":null,\"loss_remaining_percent\":null,\"profit_target_amount\":null,\"profit_remaining\":null,\"profit_remaining_percent\":null,\"trades_remaining\":null,\"next_day_utc\":"+JQuote(JTime(V1NextDay(now_utc,TradingDayCity,TradingDayStartMinute)))+"}";
  string resources="{\"Status\":"+status+",\"EaState\":"+state+",\"Positions\":"+Positions()+",\"DailyRisk\":"+risk+",\"SettingsData\":"+bridge.Settings(exec)+",\"Signals\":{\"items\":"+Join(signal_items)+",\"next_cursor\":null,\"rejection_counts\":[]},\"Chart\":"+Chart()+",\"Telemetry\":{\"equity\":"+Numbers(eq_history)+",\"spread\":"+Numbers(spread_history)+",\"atr\":"+Numbers(atr_history)+"},\"Journal\":"+Journal()+",\"Validation\":null,\"Logs\":{\"items\":"+Join(log_items)+",\"next_cursor\":null}}";
  if(!bridge.State(resources,now_utc)){exec.storage_ok=false;Print("AURUM STATE_WRITE_FAILED");}
 }
 public:
 V1Execution exec;V1Bridge bridge;
 V1Engine(){last_bar=0;last_atr=EMPTY_VALUE;atr_ratio=EMPTY_VALUE;day_range_ratio=EMPTY_VALUE;data_ok=false;daily_ok=false;lock_handle=INVALID_HANDLE;offset=100000;}
 bool Init() {
  if(!V1ValidateInputs()||!SymbolSelect(TradingSymbol,true))return false;
  if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO){Print("AURUM DEMO_ACCOUNT_REQUIRED");return false;}
  if(Mode==AUTO_EXECUTE&&!ConfirmDemoAutoExecute){Print("AURUM EXPLICIT_DEMO_CONFIRMATION_REQUIRED");return false;}
  MathSrand((int)(GetTickCount()^(uint)TimeLocal()));V1ReadParams(p);
  string root="Aurum\\"+(string)AccountInfoInteger(ACCOUNT_LOGIN)+"-"+TradingSymbol+"-"+(string)Magic;
  if(StringFind(TradingSymbol,"\\")>=0||StringFind(TradingSymbol,"/")>=0||StringFind(TradingSymbol,"..")>=0)return false;
  FolderCreate("Aurum",FILE_COMMON);FolderCreate(root,FILE_COMMON);
  lock_handle=FileOpen(root+"\\ea.lock",FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);if(lock_handle==INVALID_HANDLE){Print("AURUM DUPLICATE_INSTANCE_OR_STORAGE_ERROR");return false;}
  if(!exec.Init(root)||!bridge.Init(root,exec))return false;
  now_utc=TimeGMT();
  if(!clock.Load(BrokerClockCsv))Log("WARN","BROKER_CLOCK_MISSING_OR_INVALID: "+BrokerClockCsv+"; retrying automatically every heartbeat");
  if(!news.Load(NewsCsv))Log("WARN","NEWS_CALENDAR_MISSING_OR_INVALID: "+NewsCsv+"; entries blocked until valid coverage is supplied");
  Log("INFO","Aurum V1 initialized; ranking scores are uncalibrated; Demo only");
  return EventSetTimer(HeartbeatSeconds);
 }
 void Stop(){EventKillTimer();if(lock_handle!=INVALID_HANDLE){FileClose(lock_handle);lock_handle=INVALID_HANDLE;}}
 void Pulse(bool timer) {
  // Retry before the fail-closed return; a missing file at startup must not latch
  // the engine offline forever. Historical broker offsets are never guessed.
  if(timer){clock.Load(BrokerClockCsv);news.Load(NewsCsv);}
  datetime server=TimeTradeServer();offset=clock.Offset(server);
  if(offset==100000){
   now_utc=TimeGMT();session=SessionName(now_utc);data_ok=false;daily_ok=false;
   last_atr=EMPTY_VALUE;atr_ratio=EMPTY_VALUE;day_range_ratio=EMPTY_VALUE;
   string reason="NO_SIGNAL_DATA_QUALITY:BROKER_CLOCK_COVERAGE";
   if(last_reason!=reason)Log("WARN",reason+"; supply "+BrokerClockCsv+" in Terminal/Common/Files; auto-retry enabled");
   last_reason=reason;bridge.Poll(exec,now_utc,false,EMPTY_VALUE);
   if(timer){Sample(eq_history,AccountInfoDouble(ACCOUNT_EQUITY));Sample(spread_history,Spread()=="null"?EMPTY_VALUE:StringToDouble(Spread()));Sample(atr_history,EMPTY_VALUE);Publish();}
   return;
  }
  if(last_reason=="NO_SIGNAL_DATA_QUALITY:BROKER_CLOCK_COVERAGE"){
   last_bar=0;last_reason="";Log("INFO","BROKER_CLOCK_RECOVERED; reloading closed-bar history");
  }
  now_utc=server-offset*60;session=SessionName(now_utc);
  daily_ok=exec.Daily(now_utc,offset);
  // Independent position management runs even when news, history or Python are unavailable.
  exec.Manage(now_utc,offset,last_atr,InSession(now_utc));
  datetime closed=iTime(TradingSymbol,PERIOD_M15,1);bool boundary=closed>0&&closed!=last_bar;
  if(boundary) {
   last_bar=closed;
   data_ok=Load(bars,PERIOD_M15,HistoryBars)&&Load(h1,PERIOD_H1,H1HistoryBars)&&V1ATR(bars,p.atr_period,atr);
   if(data_ok) {
    int at=ArraySize(bars)-1;last_atr=atr[at];double median=V1Median(atr,at-1,p.atr_median);data_ok=median!=EMPTY_VALUE;
    if(data_ok){atr_ratio=last_atr/median;V1Swings(bars,p.swing,900,swings);V1Swings(h1,p.swing,3600,hourly);V1Breaks(bars,atr,swings,p,breaks);Levels();V1Sweeps(bars,atr,levels,breaks,p,sweeps);}
   }
   if(!data_ok){last_atr=EMPTY_VALUE;atr_ratio=EMPTY_VALUE;day_range_ratio=EMPTY_VALUE;}
  }
  bridge.Poll(exec,now_utc,boundary,last_atr);
  if(boundary)Evaluate();
  if(timer){Sample(eq_history,AccountInfoDouble(ACCOUNT_EQUITY));Sample(spread_history,Spread()=="null"?EMPTY_VALUE:StringToDouble(Spread()));Sample(atr_history,last_atr);Publish();}
 }
};
#endif
