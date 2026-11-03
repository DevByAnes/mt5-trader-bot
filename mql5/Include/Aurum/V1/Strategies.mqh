#ifndef AURUM_V1_STRATEGIES
#define AURUM_V1_STRATEGIES
#include "Features.mqh"
void V1Candidate(V1Signal &out[],string strategy,int d,string level_id,string level_type,string event_id,datetime event_time,double sl,double score,bool soft,string core,string bonus) {
 int n=ArraySize(out);ArrayResize(out,n+1);ZeroMemory(out[n]);out[n].strategy=strategy;out[n].direction=d;
 out[n].level_id=level_id;out[n].level_type=level_type;out[n].event_id=event_id;out[n].event_time=event_time;
 out[n].setup_id=strategy+":"+event_id+":"+(string)d;out[n].sl=sl;out[n].score=score;out[n].soft=soft;
 out[n].core=core;out[n].bonus=bonus;out[n].status="CANDIDATE";
}
double V1Bonus(int d,int trend,bool disp,bool session,bool major,const V1Params &p,string &hits) {
 double v=0;hits="";
 if(d==trend){v+=p.bonus_align;hits+="H1_ALIGN;";}
 if(disp){v+=p.bonus_displacement;hits+="DISPLACEMENT;";}
 if(major){v+=p.bonus_level;hits+="MAJOR_LEVEL;";}
 if(session){v+=p.bonus_session;hits+="SESSION;";}return v;
}
void V1Evaluate(const MqlRates &r[],const double &a[],const V1Swing &s[],const V1Swing &h[],const V1Level &levels[],const V1Break &breaks[],const V1Sweep &sweeps[],const V1Params &p,bool session,bool normal_vol,V1Signal &out[]) {
 ArrayResize(out,0);int at=ArraySize(r)-1,dummy=0;if(at<4)return;
 int ht=V1Trend(h,ArraySize(h)>0?2147483647:dummy),mt=V1Trend(s,at);
 double atr=a[at];string hits;
 if(p.s1)for(int k=0;k<ArraySize(sweeps);k++) {
  V1Sweep w=sweeps[k];if(w.state!=1||w.confirmed!=at)continue;
  double score=(w.soft?p.base_soft:p.base_strict)+V1Bonus(w.direction,ht,V1Displacement(r,a,at,w.direction,p),session,w.major,p,hits);
  V1Candidate(out,"S1",w.direction,w.level_id,w.level_type,w.level_id+":"+(string)r[w.index].time,r[w.index].time,w.extreme-w.direction*p.sl_buffer*atr,score,w.soft,"VALID_LEVEL;CONFIRMED_SWEEP",hits);
 }
 for(int k=0;k<ArraySize(breaks);k++) {
  V1Break b=breaks[k];if((b.choch?!p.s5:!p.s2)||!V1Retest(r,a,b,at,p))continue;
  int d=b.direction;double candle=d>0?r[at].low:r[at].high;
  double stop=d>0?MathMax(candle,b.level):MathMin(candle,b.level);stop-=d*p.sl_buffer*atr;
  // S2 permits the nearer structural stop, but never less than SL_MIN_ATR.
  if(d*(r[at].close-stop)<p.sl_min*atr)stop=r[at].close-d*p.sl_min*atr;
  double score=b.choch?p.base_s5:p.base_s2;
  if(!b.choch)score+=V1Bonus(d,ht,b.displacement,session,false,p,hits);
  else {
   hits="";if(b.displacement){score+=p.bonus_displacement;hits+="CHOCH_DISPLACEMENT;";}
   for(int l=0;l<ArraySize(levels);l++)if(!levels[l].invalidated&&levels[l].h1&&MathAbs(levels[l].price-b.level)<=p.zone*atr){score+=p.bonus_level;hits+="H1_LEVEL;";break;}
   for(int w=0;w<ArraySize(sweeps);w++)if(sweeps[w].direction==d&&sweeps[w].index<b.index&&MathAbs(sweeps[w].level-b.level)<=p.zone*atr){score+=p.bonus_sweep;hits+="PRIOR_SWEEP;";break;}
  }
  V1Candidate(out,b.choch?"S5":"S2",d,b.level_id,"SWING_M15",b.event_id,r[b.index].time,stop,score,false,"STRUCTURE_BREAK;RETEST;DIRECTIONAL_CLOSE",hits);
 }
 if(p.s3)for(int k=0;k<ArraySize(levels);k++) {
  V1Level l=levels[k];if(l.invalidated||l.touches<p.min_touch||l.created>=at)continue;
  int d=-l.side;double extreme=d>0?r[at].low:r[at].high,range=r[at].high-r[at].low;
  double pos=d>0?r[at].close-r[at].low:r[at].high-r[at].close;
  if(range<=0||MathAbs(extreme-l.price)>p.zone*atr||pos/range<.5||d*(r[at].close-l.price)<=0)continue;
  double stop=l.price-d*(p.zone+p.sl_buffer)*atr;if(d*(r[at].close-stop)<p.sl_min*atr)continue;
  double score=p.base_s3+V1Bonus(d,ht,false,false,l.major||l.h1,p,hits);
  if(l.touches>=3){score+=p.bonus_touch;hits+="TOUCH_3;";}
  if(normal_vol){score+=p.bonus_vol;hits+="NORMAL_VOL;";}
  if(p.patterns&&V1Pattern(r,at,d)){score+=p.bonus_pattern;hits+="CANDLE_PATTERN;";}
  V1Candidate(out,"S3",d,l.id,l.type,l.id+":"+(string)r[at].time,r[at].time,stop,score,false,"MULTIPLE_TOUCH;REJECTION;STRUCTURAL_STOP",hits);
 }
 if(p.s4&&ht!=0) {
  int k=V1LastSwing(s,-ht,at);if(k<0)return;
  // Pullback may precede the trigger; preserve the visit over the trigger lookback.
  double trigger=ht>0?r[at-1].high:r[at-1].low,extreme=ht>0?r[at].low:r[at].high;bool touch=false,invalid=false;
  for(int j=at-p.pullback;j<=at;j++) {
   if(j<0)continue;
   if(j<at)trigger=ht>0?MathMax(trigger,r[j].high):MathMin(trigger,r[j].low);
   double e=ht>0?r[j].low:r[j].high;extreme=ht>0?MathMin(extreme,e):MathMax(extreme,e);
   if(j>=s[k].confirmed&&MathAbs(e-s[k].price)<=p.zone*a[j])touch=true;
   if(ht*(r[j].close-s[k].price)<0)invalid=true;
   for(int b=0;b<ArraySize(breaks);b++)if(breaks[b].choch&&breaks[b].direction==-ht&&breaks[b].index==j)invalid=true;
  }
  if(touch&&!invalid&&ht*(r[at].close-trigger)>0) {
   double score=p.base_s4+V1Bonus(ht,mt,V1Displacement(r,a,at,ht,p),session,false,p,hits);
   string id="M15:"+(string)s[k].time+":"+(string)(-ht);
   V1Candidate(out,"S4",ht,id,"SWING_M15",id+":"+(string)r[at].time,r[at].time,extreme-ht*p.sl_buffer*atr,score,false,"H1_TREND;PULLBACK_VISIT;MINOR_BREAK",hits);
  }
 }
}
// Target selection is a real opposing level; never synthesize an RR multiple as a target.
bool V1Target(V1Signal &s,const V1Level &levels[],double atr,const V1Params &p) {
 double risk=s.direction*(s.entry-s.sl),best=DBL_MAX;if(risk<p.sl_min*atr||risk<=0){s.reason="SL_TOO_SMALL";return false;}
 for(int k=0;k<ArraySize(levels);k++) {
  if(levels[k].invalidated||levels[k].side!=s.direction)continue;
  double distance=s.direction*(levels[k].price-s.entry);
  if(distance/risk>=p.rr&&distance<best){best=distance;s.tp=levels[k].price;}
 }
 if(best==DBL_MAX){s.reason="NO_ECONOMIC_TARGET";return false;}
 s.rr=best/risk;
 if((s.strategy=="S1"||s.strategy=="S2"||s.strategy=="S4")&&best/atr>p.space){s.score+=p.bonus_space;s.bonus+="TARGET_SPACE;";}
 s.score=MathMin(100,s.score);return true;
}
int V1Resolve(V1Signal &c[],const V1Params &p,string &reason) {
 int buy=-1,sell=-1;
 for(int i=0;i<ArraySize(c);i++)if(c[i].status=="ELIGIBLE"&&c[i].score>=p.mid) {
  if(c[i].direction>0){if(buy<0||c[i].score>c[buy].score)buy=i;}
  else if(sell<0||c[i].score>c[sell].score)sell=i;
 }
 // Merge each direction before comparing the resulting directional scores.
 for(int d=-1;d<=1;d+=2) {
  int best=d>0?buy:sell;if(best<0)continue;
  for(int j=0;j<ArraySize(c);j++)if(j!=best&&c[j].status=="ELIGIBLE"&&c[j].direction==d&&c[j].score>=p.mid&&c[j].event_id!=c[best].event_id&&c[j].level_id!=c[best].level_id){c[best].score=MathMin(100,c[best].score+p.merge);c[best].bonus+="INDEPENDENT_MERGE;";break;}
 }
 if(buy>=0&&sell>=0&&MathAbs(c[buy].score-c[sell].score)<p.conflict){reason="DIRECTION_CONFLICT";return -1;}
 int selected=buy<0?sell:(sell<0?buy:(c[buy].score>=c[sell].score?buy:sell));
 if(selected<0){reason="BELOW_T_MID";return -1;}c[selected].strong=c[selected].score>=p.high;reason="";return selected;
}
#endif
