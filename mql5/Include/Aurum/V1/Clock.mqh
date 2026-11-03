#ifndef AURUM_V1_CLOCK
#define AURUM_V1_CLOCK
#include "Json.mqh"
datetime V1Date(int year,int month,int day,int hour=0) {MqlDateTime d={};d.year=year;d.mon=month;d.day=day;d.hour=hour;return StructToTime(d);}
int V1Sunday(int y,int m,int nth) {MqlDateTime d;TimeToStruct(V1Date(y,m,1),d);return 1+(7-d.day_of_week)%7+7*(nth-1);}
int V1LastSunday(int y,int m){datetime next=m==12?V1Date(y+1,1,1):V1Date(y,m+1,1);MqlDateTime d;TimeToStruct(next-86400,d);return d.day-d.day_of_week;}
int V1ZoneOffset(datetime utc,string city) {
 MqlDateTime d;TimeToStruct(utc,d);if(d.year<2007)return 100000;
 if(city=="Tokyo")return 540;
 if(city=="London")return utc>=V1Date(d.year,3,V1LastSunday(d.year,3),1)&&utc<V1Date(d.year,10,V1LastSunday(d.year,10),1)?60:0;
 if(city=="New_York")return utc>=V1Date(d.year,3,V1Sunday(d.year,3,2),7)&&utc<V1Date(d.year,11,V1Sunday(d.year,11,1),6)?-240:-300;
 return 100000;
}
bool V1InSession(datetime utc,string city,int start,int end) {
 int offset=V1ZoneOffset(utc,city);if(offset==100000)return false;MqlDateTime d;TimeToStruct(utc+offset*60,d);
 int minute=d.hour*60+d.min;if(d.day_of_week==0||d.day_of_week==6)return false;
 return start<end?(minute>=start&&minute<end):(minute>=start||minute<end);
}
datetime V1DayStart(datetime utc,string city,int minute) {
 int offset=V1ZoneOffset(utc,city);if(offset==100000)return 0;
 datetime local=utc+offset*60;MqlDateTime d;TimeToStruct(local,d);datetime civil=V1Date(d.year,d.mon,d.day)+minute*60;
 if(civil>local)civil-=86400;
 // Iterate offset at the boundary itself (not the current date across a DST boundary).
 datetime result=civil-offset*60;for(int i=0;i<3;i++)result=civil-V1ZoneOffset(result,city)*60;return result;
}
datetime V1NextDay(datetime utc,string city,int minute){datetime start=V1DayStart(utc,city,minute);return V1DayStart(start+36*3600,city,minute);}
// Broker offsets are explicit, with declared coverage. This prevents today's offset being
// silently reused on historical bars across broker DST changes. Schedule uses SERVER times.
class V1BrokerClock {
 private: datetime starts[],ends[];int offsets[];
 public:
 bool Load(string filename) {
  ArrayResize(starts,0);ArrayResize(ends,0);ArrayResize(offsets,0);
  int f=FileOpen(filename,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',',CP_UTF8);if(f==INVALID_HANDLE)return false;
  bool ok=FileReadString(f)=="server_start"&&FileReadString(f)=="server_end"&&FileReadString(f)=="offset_minutes";
  while(ok&&!FileIsEnding(f)) {
   string first=FileReadString(f);if(first==""&&FileIsEnding(f))break;
   string last=FileReadString(f),off=FileReadString(f);datetime a=StringToTime(first),b=StringToTime(last);int v=(int)StringToInteger(off),n=ArraySize(starts);
   if(a<=0||a>=b||MathAbs(v)>840||(n>0&&a!=ends[n-1])||n>=1000){ok=false;break;}
   ArrayResize(starts,n+1);ArrayResize(ends,n+1);ArrayResize(offsets,n+1);starts[n]=a;ends[n]=b;offsets[n]=v;
  }FileClose(f);
  if(!ok||ArraySize(starts)==0){ArrayResize(starts,0);ArrayResize(ends,0);ArrayResize(offsets,0);return false;}
  return true;
 }
 bool Convert(datetime server,datetime &utc) {for(int i=0;i<ArraySize(starts);i++)if(server>=starts[i]&&server<ends[i]){utc=server-offsets[i]*60;return true;}return false;}
 int Offset(datetime server){datetime utc;if(!Convert(server,utc))return 100000;return (int)((server-utc)/60);}
};
class V1News {
 private: datetime start,finish,events[];bool valid;
 datetime ParseUTC(string s){if(StringLen(s)!=20||StringSubstr(s,19)!="Z")return 0;StringReplace(s,"T"," ");StringReplace(s,"Z","");StringReplace(s,"-",".");return StringToTime(s);}
 public:
 V1News(){valid=false;start=0;finish=0;}
 bool Load(string filename) {
  valid=false;ArrayResize(events,0);int f=FileOpen(filename,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',',CP_UTF8);if(f==INVALID_HANDLE)return false;
  bool ok=FileReadString(f)=="AURUM_NEWS_V1"&&FileReadString(f)=="UTC";start=ParseUTC(FileReadString(f));finish=ParseUTC(FileReadString(f));
  ok=ok&&start>0&&finish>start&&FileReadString(f)=="event_id"&&FileReadString(f)=="time_utc"&&FileReadString(f)=="currency"&&FileReadString(f)=="impact"&&FileReadString(f)=="title";
  string ids[];
  while(ok&&!FileIsEnding(f)) {
   string id=FileReadString(f);if(id==""&&FileIsEnding(f))break;
   datetime at=ParseUTC(FileReadString(f));string currency=FileReadString(f),impact=FileReadString(f),title=FileReadString(f);
   if(id==""||title==""||at<start||at>=finish||StringLen(currency)!=3||(impact!="LOW"&&impact!="MEDIUM"&&impact!="HIGH")){ok=false;break;}
   for(int i=0;i<ArraySize(ids);i++)if(ids[i]==id)ok=false;
   int n=ArraySize(ids);if(n>=20000){ok=false;break;}ArrayResize(ids,n+1);ids[n]=id;
   if(currency=="USD"&&impact=="HIGH"){n=ArraySize(events);ArrayResize(events,n+1);events[n]=at;}
  }FileClose(f);valid=ok;return valid;
 }
 int Gate(datetime utc,int before,int after){if(!valid||utc-after*60<start||utc+before*60>=finish)return -1;for(int i=0;i<ArraySize(events);i++)if(events[i]>=utc-after*60&&events[i]<=utc+before*60)return 1;return 0;}
};
#endif
