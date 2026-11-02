#ifndef AURUM_ECONOMICS_MQH
#define AURUM_ECONOMICS_MQH

// Account-currency estimates only. Live fills may differ. This header never sends an entry.
double AurumRequiredReward(const double loss,const double stop_cost,const double target_cost,
                          const double minimum_net_rr)
{
   if(!MathIsValidNumber(loss) || !MathIsValidNumber(stop_cost) ||
      !MathIsValidNumber(target_cost) || loss<=0 || stop_cost<0 || target_cost<0 ||
      minimum_net_rr<2 || !MathIsValidNumber(minimum_net_rr)) return -1;
   double reward=minimum_net_rr*(loss+stop_cost)+target_cost;
   return MathIsValidNumber(reward)?reward:-1;
}

bool AurumVolumeForRisk(const string symbol,const ENUM_ORDER_TYPE side,const double entry,
                       const double stop,const double budget,const double fees_per_lot,
                       double &volume,string &reason)
{
   volume=0;
   if(!MathIsValidNumber(budget) || !MathIsValidNumber(fees_per_lot) ||
      !MathIsValidNumber(entry) || !MathIsValidNumber(stop) ||
      budget<=0 || fees_per_lot<0 || entry<=0 || stop<=0 ||
      (side!=ORDER_TYPE_BUY && side!=ORDER_TYPE_SELL))
      {reason="INVALID_RISK_INPUT";return false;}
   double loss=0;
   if(!OrderCalcProfit(side,symbol,1.0,entry,stop,loss) || !MathIsValidNumber(loss) || loss>=0)
      {reason="LOSS_ESTIMATE_UNAVAILABLE";return false;}
   double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   double minimum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   if(!MathIsValidNumber(step) || !MathIsValidNumber(minimum) || !MathIsValidNumber(maximum) ||
      step<=0 || minimum<=0 || maximum<minimum)
      {reason="VOLUME_RULES_UNAVAILABLE";return false;}
   double unit_loss=-loss+fees_per_lot;
   volume=MathFloor(MathMin(maximum,budget/unit_loss)/step+1e-10)*step;
   if(volume<minimum || volume*unit_loss>budget+1e-8)
      {volume=0;reason="MINIMUM_VOLUME_EXCEEDS_RISK";return false;}
   volume=NormalizeDouble(volume,8);
   reason="";return true;
}

bool AurumCostAdjustedTarget(const string symbol,const ENUM_ORDER_TYPE side,const double volume,
                             const double entry,const double stop,const double stop_cost,
                             const double target_cost,const double minimum_net_rr,
                             const double maximum_distance,double &target,string &reason)
{
   target=0;
   if(!MathIsValidNumber(volume) || !MathIsValidNumber(maximum_distance) ||
      !MathIsValidNumber(entry) || !MathIsValidNumber(stop) || entry<=0 || stop<=0 ||
      volume<=0 || maximum_distance<=0 || (side!=ORDER_TYPE_BUY && side!=ORDER_TYPE_SELL))
      {reason="INVALID_TARGET_INPUT";return false;}
   double loss=0;
   if(!OrderCalcProfit(side,symbol,volume,entry,stop,loss) || !MathIsValidNumber(loss) || loss>=0)
      {reason="LOSS_ESTIMATE_UNAVAILABLE";return false;}
   double required=AurumRequiredReward(-loss,stop_cost,target_cost,minimum_net_rr);
   if(required<=0) {reason="COST_ESTIMATE_UNAVAILABLE";return false;}
   double tick=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   if(!MathIsValidNumber(tick) || tick<=0) {reason="TICK_RULES_UNAVAILABLE";return false;}
   int direction=side==ORDER_TYPE_BUY?1:-1;
   double low=0,high=maximum_distance,profit=0;
   double far_price=entry+direction*high;
   if(far_price<=0 || !OrderCalcProfit(side,symbol,volume,entry,far_price,profit) ||
      !MathIsValidNumber(profit) || profit<required)
      {reason="NET_RR_TARGET_UNAVAILABLE";return false;}
   for(int i=0;i<64;i++)
   {
      double middle=(low+high)/2;
      if(!OrderCalcProfit(side,symbol,volume,entry,entry+direction*middle,profit) ||
         !MathIsValidNumber(profit))
         {reason="TARGET_ESTIMATE_UNAVAILABLE";return false;}
      if(profit>=required) high=middle; else low=middle;
   }
   double raw=entry+direction*high;
   target=direction>0?MathCeil(raw/tick-1e-10)*tick:MathFloor(raw/tick+1e-10)*tick;
   target=NormalizeDouble(target,digits);
   if(target<=0 || MathAbs(target-entry)>maximum_distance+tick*1e-6 ||
      !OrderCalcProfit(side,symbol,volume,entry,target,profit) ||
      !MathIsValidNumber(profit) ||
      (profit-target_cost)/(-loss+stop_cost)<minimum_net_rr-1e-9)
      {target=0;reason="NET_RR_AFTER_NORMALIZATION";return false;}
   reason="";return true;
}

bool AurumMarginAllowed(const string symbol,const ENUM_ORDER_TYPE side,const double volume,
                         const double entry,const double minimum_level,string &reason)
{
   double margin=0;
   if(!MathIsValidNumber(minimum_level) || minimum_level<=0 ||
      !OrderCalcMargin(side,symbol,volume,entry,margin) || !MathIsValidNumber(margin) || margin<0)
      {reason="MARGIN_UNAVAILABLE";return false;}
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double total=AccountInfoDouble(ACCOUNT_MARGIN)+margin;
   if(!MathIsValidNumber(equity) || !MathIsValidNumber(total) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE) || equity<=0 ||
      (total>0 && equity/total*100<minimum_level))
      {reason="MARGIN_LIMIT";return false;}
   reason="";return true;
}
#endif
