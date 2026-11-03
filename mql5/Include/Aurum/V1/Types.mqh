#ifndef AURUM_V1_TYPES
#define AURUM_V1_TYPES
// Internal arrays are chronological: index 0 is oldest, never the forming bar.
struct V1Params {
 int swing,atr_period,atr_median,confirm,retest_min,retest_max,touch_gap,min_touch,pullback;
 double bos,zone,sweep_min,sweep_max,body_atr,body_ratio,close_pos,multi_atr;
 double sl_buffer,sl_min,rr,cost_max,mid,high,conflict,merge;
 double base_strict,base_soft,base_s2,base_s3,base_s4,base_s5,space;
 double bonus_align,bonus_displacement,bonus_level,bonus_session,bonus_space,bonus_touch,bonus_vol,bonus_pattern,bonus_sweep;
 bool s1,s2,s3,s4,s5,soft,patterns;
};
void V1Defaults(V1Params &p) {
 p.swing=3;p.atr_period=14;p.atr_median=100;p.confirm=3;p.retest_min=3;p.retest_max=10;
 p.touch_gap=4;p.min_touch=2;p.pullback=3;p.bos=.10;p.zone=.15;p.sweep_min=.05;p.sweep_max=1;
 p.body_atr=.8;p.body_ratio=.6;p.close_pos=.7;p.multi_atr=1.2;
 p.sl_buffer=.2;p.sl_min=.5;p.rr=1.5;p.cost_max=.15;p.mid=55;p.high=70;p.conflict=15;p.merge=5;
 p.base_strict=50;p.base_soft=40;p.base_s2=50;p.base_s3=50;p.base_s4=50;p.base_s5=50;p.space=2.5;
 p.bonus_align=10;p.bonus_displacement=10;p.bonus_level=5;p.bonus_session=5;p.bonus_space=5;
 p.bonus_touch=5;p.bonus_vol=5;p.bonus_pattern=5;p.bonus_sweep=15;
 p.s1=true;p.s2=true;p.s3=true;p.s4=true;p.s5=false;p.soft=false;p.patterns=false;
}
struct V1Swing { int side,index,confirmed; double price; datetime time,confirmed_at; bool broken; };
struct V1Level {
 string id,type; int side,touches,breaks,last_touch,created,invalidated_at; double price;
 datetime time; bool invalidated,major,h1;
};
struct V1Break { int direction,index,structure; double level; string event_id,level_id; bool choch,displacement; };
struct V1Sweep {
 int direction,index,confirmed,state; double level,extreme,high,low,depth,strength; string level_id,level_type;
 bool soft,major;
};
struct V1Signal {
 string strategy,setup_id,event_id,level_id,level_type,core,bonus,reason,status;
 int direction; double score,entry,sl,tp,rr,cost,volume; datetime event_time;
 bool soft,strong;
};
string V1Direction(int d) { return d>0?"BUY":(d<0?"SELL":"WAIT"); }
string V1Structure(int d) { return d>0?"Bullish":(d<0?"Bearish":"Neutral"); }
#endif
