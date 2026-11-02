// Generated from schema/settings.v2.schema.json. Do not edit.
#ifndef AURUM_GENERATED_INPUTS_MQH
#define AURUM_GENERATED_INPUTS_MQH

input group "execution"
enum ENUM_AU_InpExecutionMode { ENUM_AU_InpExecutionMode_SIGNAL_ONLY, ENUM_AU_InpExecutionMode_PAPER, ENUM_AU_InpExecutionMode_LIVE };
input ENUM_AU_InpExecutionMode InpExecutionMode=ENUM_AU_InpExecutionMode_SIGNAL_ONLY;
input bool InpConfirmLive=false;
input bool InpAllowRealAccount=false;
input bool InpAllowRemoteConfig=false;
input bool InpAllowLiveFromConfig=false;
input string InpSymbol="XAUUSD";
input int InpMagic=260110;
input int InpDeviationPoints=20;
input bool InpKillSwitch=false;
input group "risk"
enum ENUM_AU_InpCapitalBasis { ENUM_AU_InpCapitalBasis_EQUITY, ENUM_AU_InpCapitalBasis_BALANCE };
input ENUM_AU_InpCapitalBasis InpCapitalBasis=ENUM_AU_InpCapitalBasis_EQUITY;
enum ENUM_AU_InpRiskProfile { ENUM_AU_InpRiskProfile_CONSERVATIVE, ENUM_AU_InpRiskProfile_MODERATE, ENUM_AU_InpRiskProfile_AGGRESSIVE, ENUM_AU_InpRiskProfile_CUSTOM };
input ENUM_AU_InpRiskProfile InpRiskProfile=ENUM_AU_InpRiskProfile_CONSERVATIVE;
input double InpRiskPerTrade=0.5;
input int InpMaxTradesPerDay=8;
input int InpMaxSimultaneous=1;
input int InpMinMarginLevel=300;
input group "daily"
input double InpDailyLossLimit=2.0;
input double InpDailyProfitTarget=3.0;
input bool InpForceCloseDailyLoss=false;
input int InpTradingDayStartUtcHour=0;
input group "management"
input bool InpBreakEvenEnabled=true;
input double InpBreakEvenTriggerR=1.0;
input double InpBreakEvenBufferAtr=0.05;
input bool InpPartialCloseEnabled=false;
input double InpPartialCloseAtR=1.5;
input int InpPartialClosePercent=50;
input bool InpTrailingEnabled=false;
input double InpTrailingAtr=1.5;
input int InpMaxHoldingHours=24;
enum ENUM_AU_InpPreNewsAction { ENUM_AU_InpPreNewsAction_NONE, ENUM_AU_InpPreNewsAction_BREAK_EVEN, ENUM_AU_InpPreNewsAction_CLOSE };
input ENUM_AU_InpPreNewsAction InpPreNewsAction=ENUM_AU_InpPreNewsAction_BREAK_EVEN;
enum ENUM_AU_InpPreWeekendAction { ENUM_AU_InpPreWeekendAction_NONE, ENUM_AU_InpPreWeekendAction_BREAK_EVEN, ENUM_AU_InpPreWeekendAction_CLOSE };
input ENUM_AU_InpPreWeekendAction InpPreWeekendAction=ENUM_AU_InpPreWeekendAction_BREAK_EVEN;
enum ENUM_AU_InpAbnormalAction { ENUM_AU_InpAbnormalAction_NONE, ENUM_AU_InpAbnormalAction_ALERT, ENUM_AU_InpAbnormalAction_BREAK_EVEN };
input ENUM_AU_InpAbnormalAction InpAbnormalAction=ENUM_AU_InpAbnormalAction_ALERT;
input group "sessions"
input bool InpLondonEnabled=true;
input bool InpOverlapEnabled=true;
input bool InpNewYorkEnabled=true;
input int InpLondonStartMinute=480;
input int InpLondonEndMinute=660;
input int InpOverlapStartMinute=780;
input int InpOverlapEndMinute=1020;
input int InpNewYorkStartMinute=480;
input int InpNewYorkEndMinute=690;
input int InpEndOfDayEntryBufferMinutes=30;
input int InpWeekendEntryBufferMinutes=120;
enum ENUM_AU_InpBrokerOffsetMode { ENUM_AU_InpBrokerOffsetMode_AUTO, ENUM_AU_InpBrokerOffsetMode_MANUAL };
input ENUM_AU_InpBrokerOffsetMode InpBrokerOffsetMode=ENUM_AU_InpBrokerOffsetMode_AUTO;
input int InpBrokerUtcOffsetMinutes=120;
input group "filters"
input bool InpNewsFilterEnabled=true;
input int InpNewsBeforeMinutes=30;
input int InpNewsAfterMinutes=30;
input string InpTesterNewsCsv="aurum_news_test.csv";
input int InpMaxSpreadPoints=35;
input double InpMaxSpreadAtr=0.1;
input double InpMaxSpreadStopRatio=0.1;
input group "costs"
input bool InpCostsKnown=false;
input double InpCommissionRoundTripPerLot=0.0;
input int InpSlippagePoints=10;
input double InpMinNetRR=2.0;
input group "signals"
input int InpAtrPeriod=14;
input int InpEmaPeriod=200;
input int InpRsiPeriod=14;
input int InpRsiUpper=75;
input int InpRsiLower=25;
input int InpAdxMin=20;
input int InpSwingLeft=2;
input int InpSwingRight=2;
input group "setups"
input bool InpReversalEnabled=true;
input bool InpContinuationEnabled=true;
input double InpSweepAtr=0.15;
input int InpSweepConfirmBars=3;
input double InpDisplacementAtr=0.8;
input double InpBodyRatio=0.6;
input int InpRetestMinBars=3;
input int InpRetestMaxBars=10;
input double InpZoneWidthAtr=0.2;
input int InpMaxLevelTouches=3;
input int InpMaxLevelAgeBars=96;
input double InpStopBufferAtr=0.1;
input double InpMinStopAtr=0.3;
input double InpMaxStopAtr=3.0;
input double InpMaxSignalRangeAtr=2.5;
input double InpMaxAdrFraction=0.8;
input int InpCooldownAfterSlBars=4;
input group "experimental"
input bool InpLogFvg=false;
input bool InpLogOrderBlock=false;
input bool InpLogCandlePatterns=false;
input bool InpUseDxyFeature=false;
input group "bridge"
enum ENUM_AU_InpBridgeMode { ENUM_AU_InpBridgeMode_OFF, ENUM_AU_InpBridgeMode_FILE, ENUM_AU_InpBridgeMode_HTTP_LOCAL };
input ENUM_AU_InpBridgeMode InpBridgeMode=ENUM_AU_InpBridgeMode_FILE;
enum ENUM_AU_InpBridgeFailPolicy { ENUM_AU_InpBridgeFailPolicy_CONTINUE_WITHOUT, ENUM_AU_InpBridgeFailPolicy_BLOCK_NEW_ENTRIES };
input ENUM_AU_InpBridgeFailPolicy InpBridgeFailPolicy=ENUM_AU_InpBridgeFailPolicy_CONTINUE_WITHOUT;
enum ENUM_AU_InpConfigSource { ENUM_AU_InpConfigSource_INPUTS, ENUM_AU_InpConfigSource_FILE };
input ENUM_AU_InpConfigSource InpConfigSource=ENUM_AU_InpConfigSource_INPUTS;
input int InpTimerSeconds=2;
input group "notifications"
input bool InpAlertEnabled=true;
input bool InpPushEnabled=false;
input bool InpEmailEnabled=false;
input bool InpTelegramEnabled=false;
input group "experimental"
input bool InpDebugDeterminism=false;
input bool InpMlEnabled=false;

string AurumJsonQuote(string value)
{
   string result="\"";
   for(int i=0;i<StringLen(value);i++)
   {
      ushort code=StringGetCharacter(value,i);
      if(code==34) result+="\\\"";
      else if(code==92) result+="\\\\";
      else if(code<32) result+=StringFormat("\\u%04x",(uint)code);
      else result+=ShortToString(code);
   }
   return result+"\"";
}

bool AurumValidateInputs(string &reason)
{
   if((int)InpExecutionMode<0 || (int)InpExecutionMode>=3) {reason="InpExecutionMode: invalid enum"; return false;}
   if(StringLen(InpSymbol)<1 || StringLen(InpSymbol)>128) {reason="InpSymbol: length";return false;}
   if(!MathIsValidNumber((double)InpMagic) || InpMagic<1 || MathAbs(InpMagic/1.0-MathRound(InpMagic/1.0))>1e-7) {reason="InpMagic: range or step";return false;}
   if(!MathIsValidNumber((double)InpDeviationPoints) || InpDeviationPoints<0 || InpDeviationPoints>100 || MathAbs(InpDeviationPoints/1.0-MathRound(InpDeviationPoints/1.0))>1e-7) {reason="InpDeviationPoints: range or step";return false;}
   if((int)InpCapitalBasis<0 || (int)InpCapitalBasis>=2) {reason="InpCapitalBasis: invalid enum"; return false;}
   if((int)InpRiskProfile<0 || (int)InpRiskProfile>=4) {reason="InpRiskProfile: invalid enum"; return false;}
   if(!MathIsValidNumber((double)InpRiskPerTrade) || InpRiskPerTrade<0.1 || InpRiskPerTrade>2 || MathAbs(InpRiskPerTrade/0.1-MathRound(InpRiskPerTrade/0.1))>1e-7) {reason="InpRiskPerTrade: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxTradesPerDay) || InpMaxTradesPerDay<1 || InpMaxTradesPerDay>20 || MathAbs(InpMaxTradesPerDay/1.0-MathRound(InpMaxTradesPerDay/1.0))>1e-7) {reason="InpMaxTradesPerDay: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxSimultaneous) || InpMaxSimultaneous<1 || InpMaxSimultaneous>3 || MathAbs(InpMaxSimultaneous/1.0-MathRound(InpMaxSimultaneous/1.0))>1e-7) {reason="InpMaxSimultaneous: range or step";return false;}
   if(!MathIsValidNumber((double)InpMinMarginLevel) || InpMinMarginLevel<100 || InpMinMarginLevel>2000 || MathAbs(InpMinMarginLevel/10.0-MathRound(InpMinMarginLevel/10.0))>1e-7) {reason="InpMinMarginLevel: range or step";return false;}
   if(!MathIsValidNumber((double)InpDailyLossLimit) || InpDailyLossLimit<0.5 || InpDailyLossLimit>5 || MathAbs(InpDailyLossLimit/0.1-MathRound(InpDailyLossLimit/0.1))>1e-7) {reason="InpDailyLossLimit: range or step";return false;}
   if(!MathIsValidNumber((double)InpDailyProfitTarget) || InpDailyProfitTarget<0.5 || InpDailyProfitTarget>10 || MathAbs(InpDailyProfitTarget/0.1-MathRound(InpDailyProfitTarget/0.1))>1e-7) {reason="InpDailyProfitTarget: range or step";return false;}
   if(!MathIsValidNumber((double)InpTradingDayStartUtcHour) || InpTradingDayStartUtcHour<0 || InpTradingDayStartUtcHour>23 || MathAbs(InpTradingDayStartUtcHour/1.0-MathRound(InpTradingDayStartUtcHour/1.0))>1e-7) {reason="InpTradingDayStartUtcHour: range or step";return false;}
   if(!MathIsValidNumber((double)InpBreakEvenTriggerR) || InpBreakEvenTriggerR<0.5 || InpBreakEvenTriggerR>2 || MathAbs(InpBreakEvenTriggerR/0.1-MathRound(InpBreakEvenTriggerR/0.1))>1e-7) {reason="InpBreakEvenTriggerR: range or step";return false;}
   if(!MathIsValidNumber((double)InpBreakEvenBufferAtr) || InpBreakEvenBufferAtr<0 || InpBreakEvenBufferAtr>0.3 || MathAbs(InpBreakEvenBufferAtr/0.01-MathRound(InpBreakEvenBufferAtr/0.01))>1e-7) {reason="InpBreakEvenBufferAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpPartialCloseAtR) || InpPartialCloseAtR<0.5 || InpPartialCloseAtR>3 || MathAbs(InpPartialCloseAtR/0.1-MathRound(InpPartialCloseAtR/0.1))>1e-7) {reason="InpPartialCloseAtR: range or step";return false;}
   if(!MathIsValidNumber((double)InpPartialClosePercent) || InpPartialClosePercent<10 || InpPartialClosePercent>80 || MathAbs(InpPartialClosePercent/10.0-MathRound(InpPartialClosePercent/10.0))>1e-7) {reason="InpPartialClosePercent: range or step";return false;}
   if(!MathIsValidNumber((double)InpTrailingAtr) || InpTrailingAtr<0.5 || InpTrailingAtr>4 || MathAbs(InpTrailingAtr/0.1-MathRound(InpTrailingAtr/0.1))>1e-7) {reason="InpTrailingAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxHoldingHours) || InpMaxHoldingHours<1 || InpMaxHoldingHours>24 || MathAbs(InpMaxHoldingHours/1.0-MathRound(InpMaxHoldingHours/1.0))>1e-7) {reason="InpMaxHoldingHours: range or step";return false;}
   if((int)InpPreNewsAction<0 || (int)InpPreNewsAction>=3) {reason="InpPreNewsAction: invalid enum"; return false;}
   if((int)InpPreWeekendAction<0 || (int)InpPreWeekendAction>=3) {reason="InpPreWeekendAction: invalid enum"; return false;}
   if((int)InpAbnormalAction<0 || (int)InpAbnormalAction>=3) {reason="InpAbnormalAction: invalid enum"; return false;}
   if(!MathIsValidNumber((double)InpLondonStartMinute) || InpLondonStartMinute<0 || InpLondonStartMinute>1435 || MathAbs(InpLondonStartMinute/5.0-MathRound(InpLondonStartMinute/5.0))>1e-7) {reason="InpLondonStartMinute: range or step";return false;}
   if(!MathIsValidNumber((double)InpLondonEndMinute) || InpLondonEndMinute<0 || InpLondonEndMinute>1435 || MathAbs(InpLondonEndMinute/5.0-MathRound(InpLondonEndMinute/5.0))>1e-7) {reason="InpLondonEndMinute: range or step";return false;}
   if(!MathIsValidNumber((double)InpOverlapStartMinute) || InpOverlapStartMinute<0 || InpOverlapStartMinute>1435 || MathAbs(InpOverlapStartMinute/5.0-MathRound(InpOverlapStartMinute/5.0))>1e-7) {reason="InpOverlapStartMinute: range or step";return false;}
   if(!MathIsValidNumber((double)InpOverlapEndMinute) || InpOverlapEndMinute<0 || InpOverlapEndMinute>1435 || MathAbs(InpOverlapEndMinute/5.0-MathRound(InpOverlapEndMinute/5.0))>1e-7) {reason="InpOverlapEndMinute: range or step";return false;}
   if(!MathIsValidNumber((double)InpNewYorkStartMinute) || InpNewYorkStartMinute<0 || InpNewYorkStartMinute>1435 || MathAbs(InpNewYorkStartMinute/5.0-MathRound(InpNewYorkStartMinute/5.0))>1e-7) {reason="InpNewYorkStartMinute: range or step";return false;}
   if(!MathIsValidNumber((double)InpNewYorkEndMinute) || InpNewYorkEndMinute<0 || InpNewYorkEndMinute>1435 || MathAbs(InpNewYorkEndMinute/5.0-MathRound(InpNewYorkEndMinute/5.0))>1e-7) {reason="InpNewYorkEndMinute: range or step";return false;}
   if(!MathIsValidNumber((double)InpEndOfDayEntryBufferMinutes) || InpEndOfDayEntryBufferMinutes<5 || InpEndOfDayEntryBufferMinutes>120 || MathAbs(InpEndOfDayEntryBufferMinutes/5.0-MathRound(InpEndOfDayEntryBufferMinutes/5.0))>1e-7) {reason="InpEndOfDayEntryBufferMinutes: range or step";return false;}
   if(!MathIsValidNumber((double)InpWeekendEntryBufferMinutes) || InpWeekendEntryBufferMinutes<30 || InpWeekendEntryBufferMinutes>360 || MathAbs(InpWeekendEntryBufferMinutes/15.0-MathRound(InpWeekendEntryBufferMinutes/15.0))>1e-7) {reason="InpWeekendEntryBufferMinutes: range or step";return false;}
   if((int)InpBrokerOffsetMode<0 || (int)InpBrokerOffsetMode>=2) {reason="InpBrokerOffsetMode: invalid enum"; return false;}
   if(!MathIsValidNumber((double)InpBrokerUtcOffsetMinutes) || InpBrokerUtcOffsetMinutes<-720 || InpBrokerUtcOffsetMinutes>840 || MathAbs(InpBrokerUtcOffsetMinutes/15.0-MathRound(InpBrokerUtcOffsetMinutes/15.0))>1e-7) {reason="InpBrokerUtcOffsetMinutes: range or step";return false;}
   if(!MathIsValidNumber((double)InpNewsBeforeMinutes) || InpNewsBeforeMinutes<5 || InpNewsBeforeMinutes>120 || MathAbs(InpNewsBeforeMinutes/5.0-MathRound(InpNewsBeforeMinutes/5.0))>1e-7) {reason="InpNewsBeforeMinutes: range or step";return false;}
   if(!MathIsValidNumber((double)InpNewsAfterMinutes) || InpNewsAfterMinutes<5 || InpNewsAfterMinutes>120 || MathAbs(InpNewsAfterMinutes/5.0-MathRound(InpNewsAfterMinutes/5.0))>1e-7) {reason="InpNewsAfterMinutes: range or step";return false;}
   if(StringLen(InpTesterNewsCsv)<1 || StringLen(InpTesterNewsCsv)>128) {reason="InpTesterNewsCsv: length";return false;}
   if(!MathIsValidNumber((double)InpMaxSpreadPoints) || InpMaxSpreadPoints<5 || InpMaxSpreadPoints>100 || MathAbs(InpMaxSpreadPoints/1.0-MathRound(InpMaxSpreadPoints/1.0))>1e-7) {reason="InpMaxSpreadPoints: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxSpreadAtr) || InpMaxSpreadAtr<0.01 || InpMaxSpreadAtr>0.5 || MathAbs(InpMaxSpreadAtr/0.01-MathRound(InpMaxSpreadAtr/0.01))>1e-7) {reason="InpMaxSpreadAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxSpreadStopRatio) || InpMaxSpreadStopRatio<0.01 || InpMaxSpreadStopRatio>0.3 || MathAbs(InpMaxSpreadStopRatio/0.01-MathRound(InpMaxSpreadStopRatio/0.01))>1e-7) {reason="InpMaxSpreadStopRatio: range or step";return false;}
   if(!MathIsValidNumber((double)InpCommissionRoundTripPerLot) || InpCommissionRoundTripPerLot<0 || InpCommissionRoundTripPerLot>100 || MathAbs(InpCommissionRoundTripPerLot/0.1-MathRound(InpCommissionRoundTripPerLot/0.1))>1e-7) {reason="InpCommissionRoundTripPerLot: range or step";return false;}
   if(!MathIsValidNumber((double)InpSlippagePoints) || InpSlippagePoints<0 || InpSlippagePoints>100 || MathAbs(InpSlippagePoints/1.0-MathRound(InpSlippagePoints/1.0))>1e-7) {reason="InpSlippagePoints: range or step";return false;}
   if(!MathIsValidNumber((double)InpMinNetRR) || InpMinNetRR<2 || InpMinNetRR>3 || MathAbs(InpMinNetRR/0.1-MathRound(InpMinNetRR/0.1))>1e-7) {reason="InpMinNetRR: range or step";return false;}
   if(!MathIsValidNumber((double)InpAtrPeriod) || InpAtrPeriod<5 || InpAtrPeriod>50 || MathAbs(InpAtrPeriod/1.0-MathRound(InpAtrPeriod/1.0))>1e-7) {reason="InpAtrPeriod: range or step";return false;}
   if(!MathIsValidNumber((double)InpEmaPeriod) || InpEmaPeriod<50 || InpEmaPeriod>400 || MathAbs(InpEmaPeriod/10.0-MathRound(InpEmaPeriod/10.0))>1e-7) {reason="InpEmaPeriod: range or step";return false;}
   if(!MathIsValidNumber((double)InpRsiPeriod) || InpRsiPeriod<5 || InpRsiPeriod>30 || MathAbs(InpRsiPeriod/1.0-MathRound(InpRsiPeriod/1.0))>1e-7) {reason="InpRsiPeriod: range or step";return false;}
   if(!MathIsValidNumber((double)InpRsiUpper) || InpRsiUpper<55 || InpRsiUpper>90 || MathAbs(InpRsiUpper/1.0-MathRound(InpRsiUpper/1.0))>1e-7) {reason="InpRsiUpper: range or step";return false;}
   if(!MathIsValidNumber((double)InpRsiLower) || InpRsiLower<10 || InpRsiLower>45 || MathAbs(InpRsiLower/1.0-MathRound(InpRsiLower/1.0))>1e-7) {reason="InpRsiLower: range or step";return false;}
   if(!MathIsValidNumber((double)InpAdxMin) || InpAdxMin<10 || InpAdxMin>40 || MathAbs(InpAdxMin/1.0-MathRound(InpAdxMin/1.0))>1e-7) {reason="InpAdxMin: range or step";return false;}
   if(!MathIsValidNumber((double)InpSwingLeft) || InpSwingLeft<1 || InpSwingLeft>10 || MathAbs(InpSwingLeft/1.0-MathRound(InpSwingLeft/1.0))>1e-7) {reason="InpSwingLeft: range or step";return false;}
   if(!MathIsValidNumber((double)InpSwingRight) || InpSwingRight<1 || InpSwingRight>10 || MathAbs(InpSwingRight/1.0-MathRound(InpSwingRight/1.0))>1e-7) {reason="InpSwingRight: range or step";return false;}
   if(!MathIsValidNumber((double)InpSweepAtr) || InpSweepAtr<0.05 || InpSweepAtr>1 || MathAbs(InpSweepAtr/0.05-MathRound(InpSweepAtr/0.05))>1e-7) {reason="InpSweepAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpSweepConfirmBars) || InpSweepConfirmBars<1 || InpSweepConfirmBars>3 || MathAbs(InpSweepConfirmBars/1.0-MathRound(InpSweepConfirmBars/1.0))>1e-7) {reason="InpSweepConfirmBars: range or step";return false;}
   if(!MathIsValidNumber((double)InpDisplacementAtr) || InpDisplacementAtr<0.5 || InpDisplacementAtr>2 || MathAbs(InpDisplacementAtr/0.1-MathRound(InpDisplacementAtr/0.1))>1e-7) {reason="InpDisplacementAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpBodyRatio) || InpBodyRatio<0.5 || InpBodyRatio>0.9 || MathAbs(InpBodyRatio/0.05-MathRound(InpBodyRatio/0.05))>1e-7) {reason="InpBodyRatio: range or step";return false;}
   if(!MathIsValidNumber((double)InpRetestMinBars) || InpRetestMinBars<1 || InpRetestMinBars>5 || MathAbs(InpRetestMinBars/1.0-MathRound(InpRetestMinBars/1.0))>1e-7) {reason="InpRetestMinBars: range or step";return false;}
   if(!MathIsValidNumber((double)InpRetestMaxBars) || InpRetestMaxBars<5 || InpRetestMaxBars>20 || MathAbs(InpRetestMaxBars/1.0-MathRound(InpRetestMaxBars/1.0))>1e-7) {reason="InpRetestMaxBars: range or step";return false;}
   if(!MathIsValidNumber((double)InpZoneWidthAtr) || InpZoneWidthAtr<0.1 || InpZoneWidthAtr>0.3 || MathAbs(InpZoneWidthAtr/0.05-MathRound(InpZoneWidthAtr/0.05))>1e-7) {reason="InpZoneWidthAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxLevelTouches) || InpMaxLevelTouches<1 || InpMaxLevelTouches>10 || MathAbs(InpMaxLevelTouches/1.0-MathRound(InpMaxLevelTouches/1.0))>1e-7) {reason="InpMaxLevelTouches: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxLevelAgeBars) || InpMaxLevelAgeBars<4 || InpMaxLevelAgeBars>480 || MathAbs(InpMaxLevelAgeBars/1.0-MathRound(InpMaxLevelAgeBars/1.0))>1e-7) {reason="InpMaxLevelAgeBars: range or step";return false;}
   if(!MathIsValidNumber((double)InpStopBufferAtr) || InpStopBufferAtr<0.05 || InpStopBufferAtr>0.5 || MathAbs(InpStopBufferAtr/0.05-MathRound(InpStopBufferAtr/0.05))>1e-7) {reason="InpStopBufferAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpMinStopAtr) || InpMinStopAtr<0.1 || InpMinStopAtr>1 || MathAbs(InpMinStopAtr/0.1-MathRound(InpMinStopAtr/0.1))>1e-7) {reason="InpMinStopAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxStopAtr) || InpMaxStopAtr<1 || InpMaxStopAtr>5 || MathAbs(InpMaxStopAtr/0.1-MathRound(InpMaxStopAtr/0.1))>1e-7) {reason="InpMaxStopAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxSignalRangeAtr) || InpMaxSignalRangeAtr<1 || InpMaxSignalRangeAtr>4 || MathAbs(InpMaxSignalRangeAtr/0.1-MathRound(InpMaxSignalRangeAtr/0.1))>1e-7) {reason="InpMaxSignalRangeAtr: range or step";return false;}
   if(!MathIsValidNumber((double)InpMaxAdrFraction) || InpMaxAdrFraction<0.3 || InpMaxAdrFraction>1 || MathAbs(InpMaxAdrFraction/0.05-MathRound(InpMaxAdrFraction/0.05))>1e-7) {reason="InpMaxAdrFraction: range or step";return false;}
   if(!MathIsValidNumber((double)InpCooldownAfterSlBars) || InpCooldownAfterSlBars<1 || InpCooldownAfterSlBars>24 || MathAbs(InpCooldownAfterSlBars/1.0-MathRound(InpCooldownAfterSlBars/1.0))>1e-7) {reason="InpCooldownAfterSlBars: range or step";return false;}
   if((int)InpBridgeMode<0 || (int)InpBridgeMode>=3) {reason="InpBridgeMode: invalid enum"; return false;}
   if((int)InpBridgeFailPolicy<0 || (int)InpBridgeFailPolicy>=2) {reason="InpBridgeFailPolicy: invalid enum"; return false;}
   if((int)InpConfigSource<0 || (int)InpConfigSource>=2) {reason="InpConfigSource: invalid enum"; return false;}
   if(!MathIsValidNumber((double)InpTimerSeconds) || InpTimerSeconds<1 || InpTimerSeconds>10 || MathAbs(InpTimerSeconds/1.0-MathRound(InpTimerSeconds/1.0))>1e-7) {reason="InpTimerSeconds: range or step";return false;}
   if(InpRetestMinBars>InpRetestMaxBars || InpMinStopAtr>InpMaxStopAtr) {reason="Inconsistent dependent ranges";return false;}
   reason="";return true;
}

string AurumSettingsV2Json()
{
   string result="{";
   result+="\"InpExecutionMode\":"+(InpExecutionMode==ENUM_AU_InpExecutionMode_SIGNAL_ONLY ? "\"SIGNAL_ONLY\"" : InpExecutionMode==ENUM_AU_InpExecutionMode_PAPER ? "\"PAPER\"" : "\"LIVE\"")+",";
   result+="\"InpConfirmLive\":"+(InpConfirmLive?"true":"false")+",";
   result+="\"InpAllowRealAccount\":"+(InpAllowRealAccount?"true":"false")+",";
   result+="\"InpAllowRemoteConfig\":"+(InpAllowRemoteConfig?"true":"false")+",";
   result+="\"InpAllowLiveFromConfig\":"+(InpAllowLiveFromConfig?"true":"false")+",";
   result+="\"InpSymbol\":"+AurumJsonQuote(InpSymbol)+",";
   result+="\"InpMagic\":"+IntegerToString(InpMagic)+",";
   result+="\"InpDeviationPoints\":"+IntegerToString(InpDeviationPoints)+",";
   result+="\"InpKillSwitch\":"+(InpKillSwitch?"true":"false")+",";
   result+="\"InpCapitalBasis\":"+(InpCapitalBasis==ENUM_AU_InpCapitalBasis_EQUITY ? "\"EQUITY\"" : "\"BALANCE\"")+",";
   result+="\"InpRiskProfile\":"+(InpRiskProfile==ENUM_AU_InpRiskProfile_CONSERVATIVE ? "\"CONSERVATIVE\"" : InpRiskProfile==ENUM_AU_InpRiskProfile_MODERATE ? "\"MODERATE\"" : InpRiskProfile==ENUM_AU_InpRiskProfile_AGGRESSIVE ? "\"AGGRESSIVE\"" : "\"CUSTOM\"")+",";
   result+="\"InpRiskPerTrade\":"+DoubleToString(InpRiskPerTrade,8)+",";
   result+="\"InpMaxTradesPerDay\":"+IntegerToString(InpMaxTradesPerDay)+",";
   result+="\"InpMaxSimultaneous\":"+IntegerToString(InpMaxSimultaneous)+",";
   result+="\"InpMinMarginLevel\":"+IntegerToString(InpMinMarginLevel)+",";
   result+="\"InpDailyLossLimit\":"+DoubleToString(InpDailyLossLimit,8)+",";
   result+="\"InpDailyProfitTarget\":"+DoubleToString(InpDailyProfitTarget,8)+",";
   result+="\"InpForceCloseDailyLoss\":"+(InpForceCloseDailyLoss?"true":"false")+",";
   result+="\"InpTradingDayStartUtcHour\":"+IntegerToString(InpTradingDayStartUtcHour)+",";
   result+="\"InpBreakEvenEnabled\":"+(InpBreakEvenEnabled?"true":"false")+",";
   result+="\"InpBreakEvenTriggerR\":"+DoubleToString(InpBreakEvenTriggerR,8)+",";
   result+="\"InpBreakEvenBufferAtr\":"+DoubleToString(InpBreakEvenBufferAtr,8)+",";
   result+="\"InpPartialCloseEnabled\":"+(InpPartialCloseEnabled?"true":"false")+",";
   result+="\"InpPartialCloseAtR\":"+DoubleToString(InpPartialCloseAtR,8)+",";
   result+="\"InpPartialClosePercent\":"+IntegerToString(InpPartialClosePercent)+",";
   result+="\"InpTrailingEnabled\":"+(InpTrailingEnabled?"true":"false")+",";
   result+="\"InpTrailingAtr\":"+DoubleToString(InpTrailingAtr,8)+",";
   result+="\"InpMaxHoldingHours\":"+IntegerToString(InpMaxHoldingHours)+",";
   result+="\"InpPreNewsAction\":"+(InpPreNewsAction==ENUM_AU_InpPreNewsAction_NONE ? "\"NONE\"" : InpPreNewsAction==ENUM_AU_InpPreNewsAction_BREAK_EVEN ? "\"BREAK_EVEN\"" : "\"CLOSE\"")+",";
   result+="\"InpPreWeekendAction\":"+(InpPreWeekendAction==ENUM_AU_InpPreWeekendAction_NONE ? "\"NONE\"" : InpPreWeekendAction==ENUM_AU_InpPreWeekendAction_BREAK_EVEN ? "\"BREAK_EVEN\"" : "\"CLOSE\"")+",";
   result+="\"InpAbnormalAction\":"+(InpAbnormalAction==ENUM_AU_InpAbnormalAction_NONE ? "\"NONE\"" : InpAbnormalAction==ENUM_AU_InpAbnormalAction_ALERT ? "\"ALERT\"" : "\"BREAK_EVEN\"")+",";
   result+="\"InpLondonEnabled\":"+(InpLondonEnabled?"true":"false")+",";
   result+="\"InpOverlapEnabled\":"+(InpOverlapEnabled?"true":"false")+",";
   result+="\"InpNewYorkEnabled\":"+(InpNewYorkEnabled?"true":"false")+",";
   result+="\"InpLondonStartMinute\":"+IntegerToString(InpLondonStartMinute)+",";
   result+="\"InpLondonEndMinute\":"+IntegerToString(InpLondonEndMinute)+",";
   result+="\"InpOverlapStartMinute\":"+IntegerToString(InpOverlapStartMinute)+",";
   result+="\"InpOverlapEndMinute\":"+IntegerToString(InpOverlapEndMinute)+",";
   result+="\"InpNewYorkStartMinute\":"+IntegerToString(InpNewYorkStartMinute)+",";
   result+="\"InpNewYorkEndMinute\":"+IntegerToString(InpNewYorkEndMinute)+",";
   result+="\"InpEndOfDayEntryBufferMinutes\":"+IntegerToString(InpEndOfDayEntryBufferMinutes)+",";
   result+="\"InpWeekendEntryBufferMinutes\":"+IntegerToString(InpWeekendEntryBufferMinutes)+",";
   result+="\"InpBrokerOffsetMode\":"+(InpBrokerOffsetMode==ENUM_AU_InpBrokerOffsetMode_AUTO ? "\"AUTO\"" : "\"MANUAL\"")+",";
   result+="\"InpBrokerUtcOffsetMinutes\":"+IntegerToString(InpBrokerUtcOffsetMinutes)+",";
   result+="\"InpNewsFilterEnabled\":"+(InpNewsFilterEnabled?"true":"false")+",";
   result+="\"InpNewsBeforeMinutes\":"+IntegerToString(InpNewsBeforeMinutes)+",";
   result+="\"InpNewsAfterMinutes\":"+IntegerToString(InpNewsAfterMinutes)+",";
   result+="\"InpTesterNewsCsv\":"+AurumJsonQuote(InpTesterNewsCsv)+",";
   result+="\"InpMaxSpreadPoints\":"+IntegerToString(InpMaxSpreadPoints)+",";
   result+="\"InpMaxSpreadAtr\":"+DoubleToString(InpMaxSpreadAtr,8)+",";
   result+="\"InpMaxSpreadStopRatio\":"+DoubleToString(InpMaxSpreadStopRatio,8)+",";
   result+="\"InpCostsKnown\":"+(InpCostsKnown?"true":"false")+",";
   result+="\"InpCommissionRoundTripPerLot\":"+DoubleToString(InpCommissionRoundTripPerLot,8)+",";
   result+="\"InpSlippagePoints\":"+IntegerToString(InpSlippagePoints)+",";
   result+="\"InpMinNetRR\":"+DoubleToString(InpMinNetRR,8)+",";
   result+="\"InpAtrPeriod\":"+IntegerToString(InpAtrPeriod)+",";
   result+="\"InpEmaPeriod\":"+IntegerToString(InpEmaPeriod)+",";
   result+="\"InpRsiPeriod\":"+IntegerToString(InpRsiPeriod)+",";
   result+="\"InpRsiUpper\":"+IntegerToString(InpRsiUpper)+",";
   result+="\"InpRsiLower\":"+IntegerToString(InpRsiLower)+",";
   result+="\"InpAdxMin\":"+IntegerToString(InpAdxMin)+",";
   result+="\"InpSwingLeft\":"+IntegerToString(InpSwingLeft)+",";
   result+="\"InpSwingRight\":"+IntegerToString(InpSwingRight)+",";
   result+="\"InpReversalEnabled\":"+(InpReversalEnabled?"true":"false")+",";
   result+="\"InpContinuationEnabled\":"+(InpContinuationEnabled?"true":"false")+",";
   result+="\"InpSweepAtr\":"+DoubleToString(InpSweepAtr,8)+",";
   result+="\"InpSweepConfirmBars\":"+IntegerToString(InpSweepConfirmBars)+",";
   result+="\"InpDisplacementAtr\":"+DoubleToString(InpDisplacementAtr,8)+",";
   result+="\"InpBodyRatio\":"+DoubleToString(InpBodyRatio,8)+",";
   result+="\"InpRetestMinBars\":"+IntegerToString(InpRetestMinBars)+",";
   result+="\"InpRetestMaxBars\":"+IntegerToString(InpRetestMaxBars)+",";
   result+="\"InpZoneWidthAtr\":"+DoubleToString(InpZoneWidthAtr,8)+",";
   result+="\"InpMaxLevelTouches\":"+IntegerToString(InpMaxLevelTouches)+",";
   result+="\"InpMaxLevelAgeBars\":"+IntegerToString(InpMaxLevelAgeBars)+",";
   result+="\"InpStopBufferAtr\":"+DoubleToString(InpStopBufferAtr,8)+",";
   result+="\"InpMinStopAtr\":"+DoubleToString(InpMinStopAtr,8)+",";
   result+="\"InpMaxStopAtr\":"+DoubleToString(InpMaxStopAtr,8)+",";
   result+="\"InpMaxSignalRangeAtr\":"+DoubleToString(InpMaxSignalRangeAtr,8)+",";
   result+="\"InpMaxAdrFraction\":"+DoubleToString(InpMaxAdrFraction,8)+",";
   result+="\"InpCooldownAfterSlBars\":"+IntegerToString(InpCooldownAfterSlBars)+",";
   result+="\"InpLogFvg\":"+(InpLogFvg?"true":"false")+",";
   result+="\"InpLogOrderBlock\":"+(InpLogOrderBlock?"true":"false")+",";
   result+="\"InpLogCandlePatterns\":"+(InpLogCandlePatterns?"true":"false")+",";
   result+="\"InpUseDxyFeature\":"+(InpUseDxyFeature?"true":"false")+",";
   result+="\"InpBridgeMode\":"+(InpBridgeMode==ENUM_AU_InpBridgeMode_OFF ? "\"OFF\"" : InpBridgeMode==ENUM_AU_InpBridgeMode_FILE ? "\"FILE\"" : "\"HTTP_LOCAL\"")+",";
   result+="\"InpBridgeFailPolicy\":"+(InpBridgeFailPolicy==ENUM_AU_InpBridgeFailPolicy_CONTINUE_WITHOUT ? "\"CONTINUE_WITHOUT\"" : "\"BLOCK_NEW_ENTRIES\"")+",";
   result+="\"InpConfigSource\":"+(InpConfigSource==ENUM_AU_InpConfigSource_INPUTS ? "\"INPUTS\"" : "\"FILE\"")+",";
   result+="\"InpTimerSeconds\":"+IntegerToString(InpTimerSeconds)+",";
   result+="\"InpAlertEnabled\":"+(InpAlertEnabled?"true":"false")+",";
   result+="\"InpPushEnabled\":"+(InpPushEnabled?"true":"false")+",";
   result+="\"InpEmailEnabled\":"+(InpEmailEnabled?"true":"false")+",";
   result+="\"InpTelegramEnabled\":"+(InpTelegramEnabled?"true":"false")+",";
   result+="\"InpDebugDeterminism\":"+(InpDebugDeterminism?"true":"false")+",";
   result+="\"InpMlEnabled\":"+(InpMlEnabled?"true":"false")+",";
   return StringSubstr(result,0,StringLen(result)-1)+"}";
}
#endif
