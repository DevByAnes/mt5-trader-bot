#property strict
#include "../Include/Aurum/V1/Clock.mqh"
#include "../Include/Aurum/V1/Storage.mqh"
void Status(string message){V1Write("Aurum\\calendar_export_result.json","{\"status\":"+JQuote(message)+"}");Print("CALENDAR_EXPORT: ",message);}
void OnStart() {
 Status("STARTED");
 for(int i=0;i<200&&!TerminalInfoInteger(TERMINAL_CONNECTED);i++)Sleep(100);
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO||!TerminalInfoInteger(TERMINAL_CONNECTED)){Status("DEMO_CONNECTION_REQUIRED");return;}
 V1BrokerClock clock;if(!clock.Load("Aurum\\broker_clock.csv")){Status("CLOCK_UNAVAILABLE");return;}
 datetime from=TimeTradeServer()-180*86400,to=TimeTradeServer()+7*86400;MqlCalendarValue values[];
 ResetLastError();int count=CalendarValueHistory(values,from,to,NULL,"USD");int err=GetLastError();
 if(count<0||err!=0){Status("API_ERROR:"+(string)err);return;}
 datetime first,last;if(!clock.Convert(from,first)||!clock.Convert(to,last)){Status("CLOCK_COVERAGE_REQUIRED");return;}
 string csv="AURUM_NEWS_V1,UTC,"+JTime(first)+","+JTime(last)+"\nevent_id,time_utc,currency,impact,title\n";int emitted=0;
 for(int i=0;i<count;i++) {
  MqlCalendarEvent event;if(!CalendarEventById(values[i].event_id,event)){Status("METADATA_UNAVAILABLE");return;}
  if(event.importance!=CALENDAR_IMPORTANCE_HIGH)continue;
  datetime utc;if(!clock.Convert(values[i].time,utc)){Print("CALENDAR_EXPORT clock gap");return;}
  string name=event.name;StringReplace(name,","," ");StringReplace(name,"\"","");StringReplace(name,"\n"," ");StringReplace(name,"\r"," ");
  if(event.time_mode!=CALENDAR_TIMEMODE_DATETIME){Status("IMPRECISE_HIGH_EVENT:"+event.name);return;}
  csv+=(string)values[i].id+","+JTime(utc)+",USD,HIGH,"+name+"\n";emitted++;
 }
 if(V1Write("Aurum\\news.csv",csv))Status("EXPORTED:"+(string)emitted);else Status("WRITE_FAILED");
}
