#ifndef AURUM_V1_INPUTS
#define AURUM_V1_INPUTS
#include "Types.mqh"
enum V1Mode { SIGNAL_ONLY=0,AUTO_EXECUTE=1 };
input group "Aurum V1 — execution (Demo only)"
input V1Mode Mode=SIGNAL_ONLY;
input bool ConfirmDemoAutoExecute=false;
input string TradingSymbol="XAUUSD";
input long Magic=260110;
input double RiskPercent=.5;
input double DailyLossPercent=2;
input double DailyProfitPercent=0; // Optional; zero disables profit cap.
input int MaxOpen=1;
input int MaxTradesPerDay=8;
input double MinimumMarginLevel=300;
input int MaxDeviationPoints=20;
input int MaxEntryDelaySeconds=10;
input int MaxQuoteAgeSeconds=30;
input int CooldownBars=8;
input int MaxHoldingHours=24;
input int WeekendCloseMinutes=180;
input int WeekendCloseNYMinute=17*60;
input bool KillSwitch=false;
input bool AllowRemoteConfig=false;
input group "Data, time and training-derived thresholds — fail closed until configured"
input string BrokerClockCsv="Aurum\\broker_clock.csv";
input string NewsCsv="Aurum\\news.csv";
input bool NativeNewsEnabled=true; // Live USD calendar; tester uses the exported CSV.
input int NewsBeforeMinutes=30;
input int NewsAfterMinutes=30;
input bool SessionFilterEnabled=true;
input bool LondonEnabled=true;
input int LondonStartMinute=8*60;
input int LondonEndMinute=17*60;
input bool NewYorkEnabled=true;
input int NewYorkStartMinute=8*60;
input int NewYorkEndMinute=17*60;
input int AsiaStartMinute=9*60;
input int AsiaEndMinute=15*60;
input string TradingDayCity="New_York";
input int TradingDayStartMinute=17*60;
input int HistoryBars=5000;
input int DemoRolloverGapMinutes=0; // UNVERIFIED Demo-only exception after server midnight; 0=strict.
input int H1HistoryBars=500;
input double MaxSpreadPoints=0; // Training P90, not an invented default.
input double AtrRatioLow=0; // Training P10.
input double AtrRatioHigh=0; // Training P95.
input bool CostsKnown=false;
input double CommissionRoundTripPerLot=0;
input double SlippagePoints=0;
input group "V1 feature parameters"
input int SwingN=3;
input int AtrPeriod=14;
input int AtrMedianBars=100;
input double BosAtr=.10;
input double ZoneAtr=.15;
input double SweepMinAtr=.05;
input double SweepMaxAtr=1;
input int SweepConfirmBars=3;
input bool SoftSweeps=false;
input double DisplacementBodyAtr=.8;
input double DisplacementBodyRatio=.6;
input double DisplacementClosePosition=.7;
input double MultiDisplacementAtr=1.2;
input int RetestMinBars=3;
input int RetestMaxBars=10;
input int TouchGapBars=4;
input int MinTouches=2;
input int PullbackBars=3;
input double StopBufferAtr=.2;
input double MinStopAtr=.5;
input double MinimumRR=1.5;
input double MaximumCostRatio=.15;
input bool RoundLevelsEnabled=false;
input double RoundLevelStep=50;
input int RoundLevelCount=4;
input group "Independent strategies and ranking (NOT win probabilities)"
input bool EnableS1=true;
input bool EnableS2=true;
input bool EnableS3=true;
input bool EnableS4=true;
input bool EnableS5=false;
input double StrictBaseScore=50;
input double SoftBaseScore=40;
input double S2BaseScore=50; // Document leaves S2–S5 bases unspecified; explicit research inputs.
input double S3BaseScore=50;
input double S4BaseScore=50;
input double S5BaseScore=50;
input double HighScore=70;
input double MidScore=55;
input double ConflictMargin=15;
input double MergeBonus=5;
input double TargetSpaceAtr=2.5;
input double AlignmentBonus=10;
input double DisplacementBonus=10;
input double MajorLevelBonus=5;
input double SessionBonus=5;
input double TargetSpaceBonus=5;
input double ThirdTouchBonus=5;
input double NormalVolatilityBonus=5;
input bool ExperimentalPatternBonus=false;
input double PatternBonus=5;
input double S5SweepBonus=15;
input group "Bridge and experimental management"
input bool BridgeEnabled=true;
input string BridgeKeyId="local-v1";
input bool RequirePythonHeartbeat=true;
input int HeartbeatSeconds=2;
input bool BreakEvenEnabled=false;
input double BreakEvenTriggerR=1;
input double BreakEvenBufferAtr=0;
input bool PartialCloseEnabled=false;
input double PartialCloseTriggerR=1.5;
input double PartialClosePercent=50;
void V1ReadParams(V1Params &p) {
 V1Defaults(p);p.swing=SwingN;p.atr_period=AtrPeriod;p.atr_median=AtrMedianBars;
 p.bos=BosAtr;p.zone=ZoneAtr;p.sweep_min=SweepMinAtr;p.sweep_max=SweepMaxAtr;p.confirm=SweepConfirmBars;p.soft=SoftSweeps;
 p.body_atr=DisplacementBodyAtr;p.body_ratio=DisplacementBodyRatio;p.close_pos=DisplacementClosePosition;p.multi_atr=MultiDisplacementAtr;
 p.retest_min=RetestMinBars;p.retest_max=RetestMaxBars;p.touch_gap=TouchGapBars;p.min_touch=MinTouches;p.pullback=PullbackBars;
 p.sl_buffer=StopBufferAtr;p.sl_min=MinStopAtr;p.rr=MinimumRR;p.cost_max=MaximumCostRatio;
 p.s1=EnableS1;p.s2=EnableS2;p.s3=EnableS3;p.s4=EnableS4;p.s5=EnableS5;p.patterns=ExperimentalPatternBonus;
 p.base_strict=StrictBaseScore;p.base_soft=SoftBaseScore;p.base_s2=S2BaseScore;p.base_s3=S3BaseScore;p.base_s4=S4BaseScore;p.base_s5=S5BaseScore;
 p.high=HighScore;p.mid=MidScore;p.conflict=ConflictMargin;p.merge=MergeBonus;p.space=TargetSpaceAtr;
 p.bonus_align=AlignmentBonus;p.bonus_displacement=DisplacementBonus;p.bonus_level=MajorLevelBonus;p.bonus_session=SessionBonus;p.bonus_space=TargetSpaceBonus;
 p.bonus_touch=ThirdTouchBonus;p.bonus_vol=NormalVolatilityBonus;p.bonus_pattern=PatternBonus;p.bonus_sweep=S5SweepBonus;
}
bool V1ValidateInputs() {
 if(TradingSymbol==""||Magic<=0||RiskPercent<=0||RiskPercent>1||DailyLossPercent<=0||DailyProfitPercent<0||MaxOpen<1||MaxTradesPerDay<1||MinimumMarginLevel<=0||
 MaxDeviationPoints<0||MaxEntryDelaySeconds<1||MaxQuoteAgeSeconds<1||CooldownBars<0||MaxHoldingHours<1||MaxHoldingHours>24||WeekendCloseMinutes<0||WeekendCloseMinutes>1440||
 SwingN<1||SwingN>20||AtrPeriod<2||AtrMedianBars<2||HistoryBars<2000||HistoryBars>30000||H1HistoryBars<100||H1HistoryBars>5000||DemoRolloverGapMinutes<0||DemoRolloverGapMinutes>120||
 BosAtr<0||ZoneAtr<=0||SweepMinAtr<0||SweepMaxAtr<=SweepMinAtr||SweepConfirmBars<1||SweepConfirmBars>3||
 DisplacementBodyAtr<=0||DisplacementBodyRatio<=0||DisplacementBodyRatio>1||DisplacementClosePosition<=0||DisplacementClosePosition>1||MultiDisplacementAtr<=0||
 RetestMinBars<1||RetestMaxBars<RetestMinBars||RetestMaxBars>100||TouchGapBars<1||MinTouches<1||PullbackBars<1||PullbackBars>50||
 StopBufferAtr<0||MinStopAtr<=0||MinimumRR<2||MaximumCostRatio<=0||MaximumCostRatio>=1||
 MidScore<0||HighScore<MidScore||HighScore>100||ConflictMargin<0||MergeBonus<0||TargetSpaceAtr<0||
 MaxSpreadPoints<0||AtrRatioLow<0||AtrRatioHigh<0||CommissionRoundTripPerLot<0||SlippagePoints<0||HeartbeatSeconds<1||HeartbeatSeconds>5||
 BreakEvenTriggerR<=0||BreakEvenBufferAtr<0||PartialCloseTriggerR<=0||PartialClosePercent<=0||PartialClosePercent>=100||
 NewsBeforeMinutes<0||NewsAfterMinutes<0||NewsBeforeMinutes>1440||NewsAfterMinutes>1440||RoundLevelStep<=0||RoundLevelCount<1||RoundLevelCount>20)return false;
 int minutes[]={LondonStartMinute,LondonEndMinute,NewYorkStartMinute,NewYorkEndMinute,AsiaStartMinute,AsiaEndMinute,TradingDayStartMinute,WeekendCloseNYMinute};
 for(int i=0;i<ArraySize(minutes);i++)if(minutes[i]<0||minutes[i]>=1440)return false;
 double weights[]={StrictBaseScore,SoftBaseScore,S2BaseScore,S3BaseScore,S4BaseScore,S5BaseScore,AlignmentBonus,DisplacementBonus,MajorLevelBonus,SessionBonus,TargetSpaceBonus,ThirdTouchBonus,NormalVolatilityBonus,PatternBonus,S5SweepBonus};
 for(int i=0;i<ArraySize(weights);i++)if(!MathIsValidNumber(weights[i])||weights[i]<0||weights[i]>100)return false;
 return (Mode==SIGNAL_ONLY||Mode==AUTO_EXECUTE)&&LondonStartMinute!=LondonEndMinute&&NewYorkStartMinute!=NewYorkEndMinute&&AsiaStartMinute!=AsiaEndMinute&&
 (TradingDayCity=="New_York"||TradingDayCity=="London"||TradingDayCity=="Tokyo");
}
#endif
