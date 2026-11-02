#property strict
#property script_show_inputs
#include "../Include/Aurum/GeneratedInputs.mqh"

void OnStart()
{
   string reason;
   bool valid=AurumValidateInputs(reason);
   Print("Aurum input validation: ",valid?"PASS":"FAIL", " ",reason);
   // This JSON contains no credentials. Compare it with schema/settings.v2.schema.json.
   if(valid) Print(AurumSettingsV2Json());
}
