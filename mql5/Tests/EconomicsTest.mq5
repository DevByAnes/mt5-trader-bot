#property strict
#property script_show_inputs
#include "../Include/Aurum/Economics.mqh"

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
   PrintFormat("Aurum economics tests: %d failures",failures);
}
