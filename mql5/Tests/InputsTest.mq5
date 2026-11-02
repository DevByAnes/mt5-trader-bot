#property strict
#include "../Include/Aurum/GeneratedInputs.mqh"
#include "Result.mqh"

void OnStart()
{
   string reason;
   bool valid=AurumValidateInputs(reason);
   Print("Aurum input validation: ",valid?"PASS":"FAIL", " ",reason);
   // This JSON contains no credentials. Compare it with schema/settings.v2.schema.json.
   if(valid) Print(AurumSettingsV2Json());
   string sample="quote=\" slash=\\\r\n\t"+ShortToString(1)+" فارسی";
   string report="{\"suite\":\"inputs\",\"build\":"+
      IntegerToString((int)TerminalInfoInteger(TERMINAL_BUILD))+
      ",\"valid\":"+(valid?"true":"false")+",\"reason\":"+AurumJsonQuote(reason)+
      ",\"escape_sample\":"+AurumJsonQuote(sample)+
      ",\"settings\":"+AurumSettingsV2Json()+"}";
   AurumWriteTestResult("aurum_inputs_test.json",report);
}
