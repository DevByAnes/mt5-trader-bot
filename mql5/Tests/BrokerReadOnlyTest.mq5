#property strict
#include "../Include/Aurum/Economics.mqh"
#include "../Include/Aurum/GeneratedInputs.mqh"
#include "Result.mqh"

// Explicit read/calculation diagnostic. No entry, modification, close or trading permission changes.
void OnStart()
{
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO)
   {
      Print("AURUM_BROKER_TEST: Demo account required; no action taken");
      return;
   }
   if(StringFind(_Symbol,"XAUUSD")<0 || !TerminalInfoInteger(TERMINAL_CONNECTED))
   {
      Print("AURUM_BROKER_TEST: connected XAUUSD chart required");
      return;
   }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0 || tick.bid<=0)
   {
      Print("AURUM_BROKER_TEST: quote unavailable");
      return;
   }
   datetime utc=TimeGMT();
   datetime server=TimeTradeServer();
   long offset=(long)server-(long)utc;
   double volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double quantum=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(volume<=0 || quantum<=0) {Print("AURUM_BROKER_TEST: invalid symbol rules");return;}
   int failures=0;
   string estimates="[";
   for(int i=0;i<2;i++)
   {
      ENUM_ORDER_TYPE side=i==0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
      int direction=i==0?1:-1;
      double entry=i==0?tick.ask:tick.bid;
      double stop=entry-direction*100*quantum;
      double win=0,loss=0,margin=0;
      bool available=OrderCalcProfit(side,_Symbol,volume,entry,entry+direction*100*quantum,win)
         && OrderCalcProfit(side,_Symbol,volume,entry,stop,loss)
         && OrderCalcMargin(side,_Symbol,volume,entry,margin);
      bool valid=available && MathIsValidNumber(win) && MathIsValidNumber(loss)
         && MathIsValidNumber(margin) && win>0 && loss<0 && margin>0;
      if(!valid) failures++;
      // Zero fees here are an explicit test vector; actual commission/slippage remain unknown.
      double target=0;
      string reason;
      bool target_ok=valid && AurumCostAdjustedTarget(_Symbol,side,volume,entry,stop,
         0,0,2,1000*quantum,target,reason);
      double sized=0;
      bool size_ok=valid && AurumVolumeForRisk(_Symbol,side,entry,stop,-loss*1.5,0,sized,reason)
         && sized>=volume && sized<=volume*1.5+1e-8;
      double actual_reward=0;
      bool rr_ok=target_ok && OrderCalcProfit(side,_Symbol,volume,entry,target,actual_reward)
         && MathIsValidNumber(actual_reward) && actual_reward/(-loss)>=2-1e-9;
      if(!size_ok) failures++;
      if(!rr_ok) failures++;
      if(i>0) estimates+=",";
      estimates+="{\"side\":"+AurumJsonQuote(i==0?"BUY":"SELL")+
         ",\"estimates_valid\":"+(valid?"true":"false")+
         ",\"volume_test_pass\":"+(size_ok?"true":"false")+
         ",\"target_test_pass\":"+(rr_ok?"true":"false")+"}";
   }
   estimates+="]";
   string report="{\"suite\":\"broker_read_only\",\"account_type\":\"DEMO\",\"build\":"+
      IntegerToString((int)TerminalInfoInteger(TERMINAL_BUILD))+
      ",\"symbol\":"+AurumJsonQuote(_Symbol)+
      ",\"utc_epoch\":"+IntegerToString((long)utc)+
      ",\"server_epoch\":"+IntegerToString((long)server)+
      ",\"broker_minus_utc_seconds\":"+IntegerToString(offset)+
      ",\"tick_age_server_seconds\":"+IntegerToString((long)server-(long)tick.time)+
      ",\"sdk_timestamp_is_server_clock\":"+(MathAbs(offset)>5?"true":"false")+
      ",\"checks\":6,\"failures\":"+IntegerToString(failures)+
      ",\"costs_test_only\":true,\"orders_submitted\":false,\"results\":"+estimates+"}";
   AurumWriteTestResult("aurum_broker_readonly_test.json",report);
   PrintFormat("AURUM_BROKER_TEST: %d failures; broker minus UTC = %d seconds",failures,offset);
}
