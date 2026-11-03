#property strict
#property version "1.00"
#property description "Aurum V1 — closed-bar S1–S5; SIGNAL_ONLY default; explicit Demo-only AUTO_EXECUTE"
#include "../Include/Aurum/V1/Engine.mqh"
V1Engine engine;
int OnInit(){if(!engine.Init()){engine.Stop();return INIT_FAILED;}return INIT_SUCCEEDED;}
void OnDeinit(const int reason){engine.Stop();}
void OnTick(){engine.Pulse(false);}
void OnTimer(){engine.Pulse(true);}
