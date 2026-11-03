#property strict
#property script_show_inputs
#include "../Include/Aurum/V1/Bridge.mqh"
#include "Result.mqh"
input string TestDirectory="";
int checks=0,failures=0;
void Check(bool ok,string name){checks++;if(!ok){failures++;Print("FAIL ",name);}}
void OnStart(){
 // Dedicated public-vector test namespace. Never use an operational account directory.
 if(StringFind(TestDirectory,"AurumNativeTests\\")!=0||StringFind(TestDirectory,"..")>=0)return;
 V1Execution e;e.root=TestDirectory;e.risk_pct=.5;e.loss_pct=2;e.spread_max=35;e.mode=SIGNAL_ONLY;e.killed=false;
 V1Bridge b;Check(b.Init(TestDirectory,e),"initialize inherited test key");if(!b.active)return;
 b.instance="22345678-1234-4234-a234-123456789abc";
 datetime utc=TimeGMT();Check(b.Heartbeat(utc),"verify Python heartbeat");
 b.Poll(e,utc,false,2);Check(e.killed,"authenticated kill effect");
 string kill="",config="";Check(V1Read(TestDirectory+"\\ack_32345678-1234-4234-a234-123456789abc.json",kill),"durable kill acknowledgement");
 Check(!FileIsExist(TestDirectory+"\\ack_42345678-1234-4234-a234-123456789abc.json",FILE_COMMON),"config waits for closed M15 boundary");
 b.Poll(e,utc,true,2);Check(e.risk_pct==.4&&e.spread_max==30,"atomic tightening applied");
 Check(V1Read(TestDirectory+"\\ack_42345678-1234-4234-a234-123456789abc.json",config),"durable config acknowledgement");
 Check(!FileIsExist(TestDirectory+"\\receipt_52345678-1234-4234-a234-123456789abc.json",FILE_COMMON),"tampered request has no effect or acknowledgement");
 b.Poll(e,utc,true,2);Check(e.risk_pct==.4&&e.killed,"redelivery cannot repeat config");
 V1Execution restarted;restarted.root=TestDirectory;restarted.risk_pct=.5;restarted.loss_pct=2;restarted.spread_max=35;restarted.mode=SIGNAL_ONLY;restarted.killed=false;
 V1Bridge after;Check(after.Init(TestDirectory,restarted)&&restarted.killed&&restarted.risk_pct==.4&&restarted.spread_max==30,"restart retains authenticated kill and tightening");
 string resources="{\"Status\":null,\"EaState\":null,\"Positions\":null,\"DailyRisk\":null,\"SettingsData\":"+b.Settings(e)+",\"Signals\":null,\"Chart\":null,\"Telemetry\":null,\"Journal\":null,\"Validation\":null,\"Logs\":null}";
 Check(b.State(resources,utc),"native signed atomic state");string state="";Check(V1Read(TestDirectory+"\\state.json",state),"native snapshot readable");
 string result="{\"checks\":"+(string)checks+",\"failures\":"+(string)failures+",\"kill\":"+(kill==""?"null":kill)+",\"config\":"+(config==""?"null":config)+",\"state\":"+(state==""?"null":state)+"}";
 AurumWriteTestResult("aurum_v1_bridge_test.json",result);
}
