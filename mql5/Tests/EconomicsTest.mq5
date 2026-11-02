#property strict
#include "../Include/Aurum/Economics.mqh"
#include "Result.mqh"

void OnStart()
{
   int failures=0;
   double required=AurumRequiredReward(100,10,10,2);
   if(MathAbs(required-230)>1e-9) failures++;
   if(MathAbs((required-10)/(100+10)-2)>1e-9) failures++;
   if(AurumRequiredReward(100,0,0,2)!=200) failures++;
   if(AurumRequiredReward(0,0,0,2)!=-1) failures++;
   if(AurumRequiredReward(100,-1,0,2)!=-1) failures++;
   if(AurumRequiredReward(100,0,0,1.9)!=-1) failures++;
   if(AurumRequiredReward(DBL_MAX,DBL_MAX,0,2)!=-1) failures++;
   double volume=999;
   string reason;
   if(AurumVolumeForRisk("",ORDER_TYPE_BUY,10,9,0,0,volume,reason) || volume!=0)
      failures++;
   double target=999;
   if(AurumCostAdjustedTarget("",ORDER_TYPE_BUY,0,10,9,0,0,2,10,target,reason) || target!=0)
      failures++;
   PrintFormat("Aurum economics tests: %d failures",failures);
   AurumWriteTestResult("aurum_economics_test.json",
      "{\"suite\":\"economics\",\"checks\":9,\"failures\":"+
      IntegerToString(failures)+",\"build\":"+
      IntegerToString((int)TerminalInfoInteger(TERMINAL_BUILD))+"}");
}
