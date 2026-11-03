#property strict
#property script_show_inputs
#include "../Include/Aurum/V1/Strategies.mqh"
#include "../Include/Aurum/V1/Clock.mqh"
#include "../Include/Aurum/V1/Crypto.mqh"
#include "../Include/Aurum/V1/Storage.mqh"
#include "../Include/Aurum/V1/Bridge.mqh"
#include "Result.mqh"
int checks=0,failures=0;string failed="";
void Check(bool value,string name){checks++;if(!value){failures++;failed+=name+";";Print("FAIL ",name);}}
void Bar(MqlRates &r,datetime time,double o,double h,double l,double c){ZeroMemory(r);r.time=time;r.open=o;r.high=h;r.low=l;r.close=c;}
void OnStart(){
 V1Execution settings_exec;settings_exec.risk_pct=.5;settings_exec.loss_pct=2;settings_exec.spread_max=4;settings_exec.mode=SIGNAL_ONLY;V1Bridge settings_bridge;V1Json settings_json;
 Check(settings_json.Parse(settings_bridge.Settings(settings_exec))&&settings_json.Number(settings_json.Field(0,"values"),"maxSpread")==4,"actual training spread below legacy UI minimum is reported");
 Check(V1DemoRolloverGap(D'2026.11.02 22:45',D'2026.11.03 01:00',D'2026.11.03 00:15',60,true),"explicit Demo midnight exception");
 Check(!V1DemoRolloverGap(D'2026.11.02 22:45',D'2026.11.03 01:00',D'2026.11.03 00:15',60,false),"rollover exception forbidden on real account");
 Check(!V1DemoRolloverGap(D'2026.11.02 22:45',D'2026.11.03 01:00',D'2026.11.03 00:15',0,true),"strict default rejects rollover exception");
 Check(!V1DemoRolloverGap(D'2026.11.03 10:00',D'2026.11.03 11:00',D'2026.11.03 10:15',60,true),"intraday missing candle blocked");
 Check(!V1DemoRolloverGap(D'2026.11.02 22:45',D'2026.11.03 02:00',D'2026.11.03 01:00',60,true),"midnight exception has bounded end");
 Check(!V1SessionContains(3600,0,0),"zero duration session is closed");
 Check(V1SessionContains(3600,0,86400),"explicit full day session");
 Check(V1SessionContains(3600,0,82800)&&!V1SessionContains(82800,0,82800),"session close exclusive");
 Check(V1SessionContains(3600,79200,7200)&&!V1SessionContains(43200,79200,7200),"overnight session");
 V1Params p;V1Defaults(p);MqlRates r[];ArrayResize(r,12);
 for(int i=0;i<12;i++)Bar(r[i],D'2026.01.05 00:00'+i*900,10,11,9,10);
 Check(V1ValidBars(r,900),"valid bars");r[1].close=12;Check(!V1ValidBars(r,900),"invalid OHLC");r[1].close=10;
 r[1].time=r[0].time;Check(!V1ValidBars(r,900),"duplicate time");r[1].time=r[0].time+900;
 double a[];Check(V1ATR(r,3,a)&&a[3]==2&&a[11]==2,"Wilder seed and recurrence");
 Check(V1Median(a,11,5)==2,"median");Check(V1Median(a,3,5)==EMPTY_VALUE,"missing median is unavailable");
 r[4].high=15;r[5].high=15;
 Check(V1IsSwing(r,4,2,1),"first equal high wins");Check(!V1IsSwing(r,5,2,1),"later equal high loses");
 V1Swing s[];V1Swings(r,2,900,s);Check(ArraySize(s)==1&&s[0].confirmed==6&&s[0].confirmed_at==r[6].time+900,"confirmation close time");
 Check(V1LastSwing(s,1,5)==-1&&V1LastSwing(s,1,6)==0,"no lookahead swing");
 ArrayResize(s,4);for(int i=0;i<4;i++){s[i].side=i%2==0?1:-1;s[i].confirmed=i;s[i].index=i;s[i].broken=false;s[i].time=r[i].time;}
 s[0].price=12;s[1].price=8;s[2].price=14;s[3].price=9;
 Check(V1Trend(s,3)==1,"HH HL bull");s[3].price=7;Check(V1Trend(s,3)==0,"mixed neutral");s[2].price=11;Check(V1Trend(s,3)==-1,"LH LL bear");
 s[2].price=14;s[3].price=9;V1Break b[];
 for(int i=0;i<12;i++)Bar(r[i],D'2026.01.05'+i*900,10,11,9.5,10);
 r[4].high=16;r[4].close=15;r[5].high=16;r[5].close=15;
 V1Breaks(r,a,s,p,b);Check(ArraySize(b)==1&&b[0].direction==1&&!b[0].choch,"BOS once per swing");
 Check(s[2].broken,"broken flag");s[2].broken=false;s[3].broken=false;r[4].close=8;r[4].low=7;r[5].close=10;
 V1Breaks(r,a,s,p,b);Check(ArraySize(b)==1&&b[0].choch&&b[0].direction==-1,"canonical bearish CHoCH");
 Bar(r[11],r[11].time,10,12,10,11.8);Check(V1Displacement(r,a,11,1,p),"bull displacement");Check(!V1Displacement(r,a,11,-1,p),"directional displacement");
 Bar(r[11],r[11].time,10,14,9,11);Check(!V1Displacement(r,a,11,1,p),"large wick not displacement");
 ArrayResize(b,1);b[0].direction=1;b[0].index=5;b[0].level=10;b[0].choch=false;b[0].event_id="break";b[0].level_id="level";b[0].displacement=false;
 for(int i=6;i<12;i++)Bar(r[i],r[i].time,12,13,11,12);
 Bar(r[8],r[8].time,10.2,12,10.1,11);
 Check(V1Retest(r,a,b[0],8,p),"first retest at age3");Check(!V1Retest(r,a,b[0],9,p),"retest consumed once");
 r[7].close=9;r[7].low=8;Check(!V1Retest(r,a,b[0],8,p),"retest invalidation");r[7].close=12;r[7].low=11;
 Check(!V1Retest(r,a,b[0],6,p),"early retest rejected");
 V1Level levels[];V1AddLevel(levels,"L","PDL",-1,10,0,r[0].time,true);
 for(int i=0;i<12;i++)Bar(r[i],r[i].time,11,12,10.5,11);
 Bar(r[9],r[9].time,10.5,11,9.5,10.5);Bar(r[10],r[10].time,10.5,12,10,11.5);
 V1Sweep w[];ArrayResize(b,0);V1Sweeps(r,a,levels,b,p,w);
 Check(ArraySize(w)==1&&w[0].confirmed==10&&w[0].state==1&&!w[0].soft,"strict sweep confirmation");
 r[9].low=7;V1Sweeps(r,a,levels,b,p,w);Check(ArraySize(w)==0,"deep sweep rejected");r[9].low=9.5;r[9].close=9.8;
 V1Sweeps(r,a,levels,b,p,w);Check(ArraySize(w)==0,"soft off by default");p.soft=true;V1Sweeps(r,a,levels,b,p,w);Check(ArraySize(w)==1&&w[0].soft,"soft one bar return");
 r[10].close=9;r[10].low=8;V1Sweeps(r,a,levels,b,p,w);Check(ArraySize(w)==0||w[0].state!=1,"sweep invalidation");
 // Independent strategy vectors on the same closed-bar context.
 p.soft=false;ArrayResize(s,0);V1Swing h[];V1Signal c[];
 ArrayResize(w,1);ZeroMemory(w[0]);w[0].direction=1;w[0].state=1;w[0].index=9;w[0].confirmed=11;w[0].extreme=9.5;w[0].level_id="L";w[0].level_type="PDL";w[0].major=true;
 V1Evaluate(r,a,s,h,levels,b,w,p,true,true,c);Check(ArraySize(c)>0&&c[0].strategy=="S1"&&c[0].sl==9.1,"S1 core and sweep stop");
 ArrayResize(w,0);ArrayResize(b,1);b[0].direction=1;b[0].index=8;b[0].level=10;b[0].choch=false;b[0].event_id="B";b[0].level_id="L";b[0].displacement=true;
 for(int i=9;i<12;i++)Bar(r[i],r[i].time,11,13,10.5,12);Bar(r[11],r[11].time,10.2,12,10.1,11);
 V1Evaluate(r,a,s,h,levels,b,w,p,true,true,c);Check(ArraySize(c)==1&&c[0].strategy=="S2","S2 independent core");
 b[0].choch=true;V1Evaluate(r,a,s,h,levels,b,w,p,true,true,c);Check(ArraySize(c)==0,"S5 disabled");p.s5=true;V1Evaluate(r,a,s,h,levels,b,w,p,true,true,c);Check(ArraySize(c)==1&&c[0].strategy=="S5","S5 CHoCH retest");p.s5=false;
 ArrayResize(b,0);levels[0].touches=2;r[11].close=11.2;V1Evaluate(r,a,s,h,levels,b,w,p,true,true,c);Check(ArraySize(c)==1&&c[0].strategy=="S3","S3 touch rejection structural stop");
 levels[0].touches=1;V1Evaluate(r,a,s,h,levels,b,w,p,true,true,c);Check(ArraySize(c)==0,"S3 requires touches");
 ArrayResize(h,4);for(int i=0;i<4;i++){h[i].side=i%2==0?1:-1;h[i].confirmed=i;h[i].price=(i%2==0?14:9)+i;}
 ArrayResize(s,1);s[0].side=-1;s[0].confirmed=5;s[0].time=r[2].time;s[0].price=10;
 for(int i=8;i<12;i++)Bar(r[i],r[i].time,11,12,10.5,11);
 Bar(r[9],r[9].time,10.5,12,10.1,11);Bar(r[11],r[11].time,11,14,11,13);
 V1Evaluate(r,a,s,h,levels,b,w,p,true,true,c);Check(ArraySize(c)==1&&c[0].strategy=="S4","S4 prior pullback then trigger");
 V1Signal target;ZeroMemory(target);target.direction=1;target.entry=10;target.sl=8;target.strategy="S1";
 V1AddLevel(levels,"H","PDH",1,14,0,r[0].time,true);Check(V1Target(target,levels,2,p)&&target.tp==14&&target.rr==2,"opposing level target");
 levels[1].invalidated=true;Check(!V1Target(target,levels,2,p),"no invented target");
 ArrayResize(c,2);for(int i=0;i<2;i++){ZeroMemory(c[i]);c[i].status="ELIGIBLE";c[i].score=70;c[i].direction=i==0?1:-1;c[i].event_id=(string)i;c[i].level_id=(string)i;}
 string reason;Check(V1Resolve(c,p,reason)==-1&&reason=="DIRECTION_CONFLICT","conflict WAIT");c[0].score=90;Check(V1Resolve(c,p,reason)==0,"dominant direction");
 c[0].score=70;c[1].direction=1;c[1].score=65;Check(V1Resolve(c,p,reason)==0&&c[0].score==75,"independent merge once");
 c[0].score=70;c[1].event_id=c[0].event_id;Check(V1Resolve(c,p,reason)==0&&c[0].score==70,"same event no double count");
 c[0].score=40;c[1].score=40;Check(V1Resolve(c,p,reason)==-1,"below threshold WAIT");
 Check(V1ZoneOffset(D'2026.03.08 06:59',"New_York")==-300&&V1ZoneOffset(D'2026.03.08 07:00',"New_York")==-240,"NY DST spring");
 Check(V1ZoneOffset(D'2026.11.01 05:59',"New_York")==-240&&V1ZoneOffset(D'2026.11.01 06:00',"New_York")==-300,"NY DST fall");
 Check(V1ZoneOffset(D'2026.03.29 00:59',"London")==0&&V1ZoneOffset(D'2026.03.29 01:00',"London")==60,"London DST");
 Check(V1DayStart(D'2026.11.03 20:00',"New_York",1020)==D'2026.11.02 22:00',"NY trading day");
 Check(V1NextDay(D'2026.11.03 20:00',"New_York",1020)==D'2026.11.03 22:00',"next day UTC");
 V1Json j;Check(j.Parse("{\"x\":1,\"y\":[true,null,\"a\"]}")&&j.Number(0,"x")==1,"JSON nested");
 Check(!j.Parse("{\"x\":1,\"x\":2}"),"JSON duplicate");Check(!j.Parse("{\"x\":01}"),"JSON leading zero");Check(!j.Parse("{\"x\":NaN}"),"JSON nonfinite");Check(!j.Parse("[1,]"),"JSON trailing comma");
 Check(V1HashText("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","SHA256 vector");
 uchar key[];ArrayResize(key,32);for(int i=0;i<32;i++)key[i]=(uchar)i;
 Check(V1Hmac(key,"abc")=="f0133729c4163dede81e21cd47839256da58171238c8a0d874397c73b14e1e47","HMAC cross-language vector");
 string decoded,encoded=V1Base64("quote=\" فارسی");Check(V1Decode64(encoded,decoded)&&decoded=="quote=\" فارسی","UTF8 base64");
 string payload="{\"kind\":\"ACK\",\"sender\":\"EA\",\"message_id\":\"12345678-1234-4234-a234-123456789abc\",\"ea_instance_id\":\"22345678-1234-4234-a234-123456789abc\",\"seq\":1,\"issued_at_ms\":1793613600000,\"expires_at_ms\":1793613630000,\"body\":{\"request_id\":\"32345678-1234-4234-a234-123456789abc\",\"status\":\"APPLIED\",\"reason\":null,\"version\":null,\"ea_ack_utc\":\"2026-11-02T10:00:00Z\"}}";
 string wire=V1Wire(payload,"local-v1",key);Check(V1Unwire(wire,"local-v1",key,decoded)&&decoded==payload,"signed wire roundtrip");
 Check(!V1Unwire(wire,"wrong-key-id",key,decoded),"wrong key id");
 string result="{\"checks\":"+(string)checks+",\"failures\":"+(string)failures+",\"failed\":"+JQuote(failed)+",\"wire\":"+wire+"}";
 // Focused regressions: Windows-safe filenames, numeric chart timestamps and clock recovery.
 string epoch=JEpoch(D'2026.11.02 10:00');
 Check(epoch=="1793613600"&&j.Parse("{\"time\":"+epoch+"}")&&j.Number(0,"time")==1793613600,"numeric datetime JSON");
 string path="AurumNativeTests\\clock-recovery-"+(string)GetMicrosecondCount()+".csv";
 V1BrokerClock clock;datetime converted;
 Check(!clock.Load(path)&&!clock.Convert(D'2026.11.03 12:00',converted),"missing clock blocks");
 string csv="server_start,server_end,offset_minutes\r\n2026.11.01 00:00:00,2026.12.01 00:00:00,120\r\n";
 Check(V1Write(path,csv)&&clock.Load(path)&&clock.Convert(D'2026.11.03 12:00',converted)&&converted==D'2026.11.03 10:00',"clock recovers when supplied");
 Check(V1Write(path,csv+"invalid,row,120\r\n")&&!clock.Load(path)&&!clock.Convert(D'2026.11.03 12:00',converted),"partial invalid clock is discarded");
 Check(V1Write(path,csv)&&clock.Load(path),"clock recovers after correction");
 FileDelete(path,FILE_COMMON);
 path="AurumNativeTests\\day_"+epoch+".json";
 Check(V1Write(path,"{\"equity\":100000}"),"daily filename is writable on Windows");FileDelete(path,FILE_COMMON);
 result="{\"checks\":"+(string)checks+",\"failures\":"+(string)failures+",\"failed\":"+JQuote(failed)+",\"wire\":"+wire+"}";
 AurumWriteTestResult("aurum_v1_test.json",result);
 Print("AURUM_V1 ",checks," checks / ",failures," failures");
}
