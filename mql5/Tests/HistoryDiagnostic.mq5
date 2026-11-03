#property strict
#include "../Include/Aurum/V1/Storage.mqh"
void OnStart(){
 for(int i=0;i<200&&!TerminalInfoInteger(TERMINAL_CONNECTED);i++)Sleep(100);
 string report="";datetime first,last;
 for(int day=0;day<7;day++)for(uint n=0;n<20;n++){
  bool q=SymbolInfoSessionQuote("XAUUSD",(ENUM_DAY_OF_WEEK)day,n,first,last);
  if(q)report+="QUOTE day="+(string)day+" from="+(string)(long)first+" to="+(string)(long)last+"\n";
  bool t=SymbolInfoSessionTrade("XAUUSD",(ENUM_DAY_OF_WEEK)day,n,first,last);
  if(t)report+="TRADE day="+(string)day+" from="+(string)(long)first+" to="+(string)(long)last+"\n";
  if(!q&&!t)break;
 }
 V1Write("Aurum\\history_diagnostic.txt",report);Print(report);
}
