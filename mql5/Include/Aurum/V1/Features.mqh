#ifndef AURUM_V1_FEATURES
#define AURUM_V1_FEATURES
#include "Types.mqh"
bool V1ValidBars(const MqlRates &r[],int period) {
 int n=ArraySize(r);if(n<2)return false;
 for(int i=0;i<n;i++) {
  if(!MathIsValidNumber(r[i].open)||!MathIsValidNumber(r[i].high)||!MathIsValidNumber(r[i].low)||!MathIsValidNumber(r[i].close)||
     r[i].low<=0||r[i].high<MathMax(r[i].open,r[i].close)||r[i].low>MathMin(r[i].open,r[i].close)||r[i].high<r[i].low||
     (i>0&&(r[i].time<=r[i-1].time||(r[i].time-r[i-1].time)%period!=0)))return false;
 }return true;
}
bool V1ATR(const MqlRates &r[],int period,double &a[]) {
 int n=ArraySize(r);ArrayResize(a,n);ArrayInitialize(a,EMPTY_VALUE);if(period<1||n<=period)return false;
 double sum=0;
 for(int i=1;i<n;i++) {
  double tr=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-r[i-1].close),MathAbs(r[i].low-r[i-1].close)));
  if(i<=period)sum+=tr;
  if(i==period)a[i]=sum/period;
  if(i>period)a[i]=(a[i-1]*(period-1)+tr)/period;
 }return a[n-1]>0&&a[n-1]!=EMPTY_VALUE;
}
double V1Median(const double &a[],int end,int count) {
 if(end-count+1<0||count<1)return EMPTY_VALUE;double v[];ArrayResize(v,count);
 for(int i=0;i<count;i++){v[i]=a[end-i];if(v[i]==EMPTY_VALUE||!MathIsValidNumber(v[i])||v[i]<=0)return EMPTY_VALUE;}
 ArraySort(v);return count%2!=0?v[count/2]:(v[count/2-1]+v[count/2])/2;
}
bool V1IsSwing(const MqlRates &r[],int i,int n,int side) {
 if(i<n||i+n>=ArraySize(r))return false;double p=side>0?r[i].high:r[i].low;
 for(int k=1;k<=n;k++) {
  double before=side>0?r[i-k].high:r[i-k].low,after=side>0?r[i+k].high:r[i+k].low;
  if(side>0?(p<=before||p<after):(p>=before||p>after))return false;
 }return true;
}
void V1Swings(const MqlRates &r[],int n,int period,V1Swing &out[]) {
 ArrayResize(out,0);
 for(int i=n;i+n<ArraySize(r);i++)for(int side=-1;side<=1;side+=2)if(V1IsSwing(r,i,n,side)) {
  int z=ArraySize(out);ArrayResize(out,z+1);out[z].side=side;out[z].index=i;out[z].confirmed=i+n;
  out[z].price=side>0?r[i].high:r[i].low;out[z].time=r[i].time;out[z].confirmed_at=r[i+n].time+period;out[z].broken=false;
 }
}
int V1LastSwing(const V1Swing &s[],int side,int at,int skip=0) {
 for(int i=ArraySize(s)-1;i>=0;i--)if(s[i].side==side&&s[i].confirmed<=at){if(skip--==0)return i;}return -1;
}
int V1Trend(const V1Swing &s[],int at) {
 int h=V1LastSwing(s,1,at),h0=V1LastSwing(s,1,at,1),l=V1LastSwing(s,-1,at),l0=V1LastSwing(s,-1,at,1);
 if(h<0||h0<0||l<0||l0<0)return 0;
 if(s[h].price>s[h0].price&&s[l].price>s[l0].price)return 1;
 if(s[h].price<s[h0].price&&s[l].price<s[l0].price)return -1;return 0;
}
bool V1Displacement(const MqlRates &r[],const double &a[],int i,int d,const V1Params &p) {
 if(i<0||a[i]==EMPTY_VALUE||a[i]<=0)return false;
 double range=r[i].high-r[i].low,body=d*(r[i].close-r[i].open);
 double pos=d>0?r[i].close-r[i].low:r[i].high-r[i].close;
 if(range>0&&body/a[i]>=p.body_atr&&body/range>=p.body_ratio&&pos/range>=p.close_pos)return true;
 for(int count=2;count<=3;count++) {
  if(i-count+1<0)continue;bool same=true;
  for(int j=i-count+1;j<=i;j++)if(d*(r[j].close-r[j].open)<=0)same=false;
  if(same&&d*(r[i].close-r[i-count+1].open)>=p.multi_atr*a[i])return true;
 }return false;
}
void V1Breaks(const MqlRates &r[],const double &a[],V1Swing &s[],const V1Params &p,V1Break &b[]) {
 ArrayResize(b,0);
 for(int i=1;i<ArraySize(r);i++) {
  if(a[i]==EMPTY_VALUE||a[i]<=0)continue;int trend=V1Trend(s,i);if(trend==0)continue;
  for(int d=-1;d<=1;d+=2) {
   int k=V1LastSwing(s,d,i);if(k<0||s[k].broken||d*(r[i].close-s[k].price)<=p.bos*a[i])continue;
   s[k].broken=true;int z=ArraySize(b);ArrayResize(b,z+1);
   b[z].direction=d;b[z].index=i;b[z].level=s[k].price;b[z].structure=trend;b[z].choch=d!=trend;
   b[z].level_id="M15:"+(string)s[k].time+":"+(string)d;b[z].event_id=b[z].level_id+":"+(string)r[i].time;
   b[z].displacement=V1Displacement(r,a,i,d,p);
  }
 }
}
bool V1Retest(const MqlRates &r[],const double &a[],const V1Break &b,int at,const V1Params &p) {
 int age=at-b.index;if(age<p.retest_min||age>p.retest_max)return false;
 for(int j=b.index+1;j<=at;j++) {
  if(b.direction*(r[j].close-b.level)<-p.zone*a[j])return false;
  // First eligible retest consumes this event: it cannot reissue every later candle.
  bool hit=b.direction>0?r[j].low<=b.level+p.zone*a[j]:r[j].high>=b.level-p.zone*a[j];
  if(j-b.index>=p.retest_min&&hit&&b.direction*(r[j].close-b.level)>0)return j==at;
 }return false;
}
void V1AddLevel(V1Level &levels[],string id,string type,int side,double price,int created,datetime time,bool major=false,bool h1=false) {
 if(price<=0||!MathIsValidNumber(price))return;
 for(int i=0;i<ArraySize(levels);i++)if(levels[i].id==id)return;
 int z=ArraySize(levels);ArrayResize(levels,z+1);levels[z].id=id;levels[z].type=type;levels[z].side=side;levels[z].price=price;
 levels[z].created=created;levels[z].time=time;levels[z].touches=0;levels[z].breaks=0;levels[z].last_touch=-100000;
 levels[z].invalidated=false;levels[z].invalidated_at=-1;levels[z].major=major;levels[z].h1=h1;
}
void V1SwingLevels(const V1Swing &s[],string tf,V1Level &levels[],const MqlRates &m[],int period) {
 for(int k=0;k<ArraySize(s);k++) {
  int created=0;while(created<ArraySize(m)&&m[created].time+900<s[k].confirmed_at)created++;
  V1AddLevel(levels,tf+":"+(string)s[k].time+":"+(string)s[k].side,"SWING_"+tf,s[k].side,s[k].price,created,s[k].confirmed_at,false,period==3600);
 }
}
void V1LevelHistory(V1Level &l[],const MqlRates &r[],const double &a[],int through,const V1Params &p) {
 for(int k=0;k<ArraySize(l);k++)for(int j=l[k].created+1;j<=through;j++) {
  if(a[j]==EMPTY_VALUE||a[j]<=0||l[k].invalidated)continue;
  double z=p.zone*a[j],extreme=l[k].side>0?r[j].high:r[j].low;
  if(l[k].side*(r[j].close-l[k].price)>z){l[k].invalidated=true;l[k].invalidated_at=j;l[k].breaks++;continue;}
  if(MathAbs(extreme-l[k].price)<=z&&j-l[k].last_touch>=p.touch_gap){l[k].touches++;l[k].last_touch=j;}
 }
}
void V1Sweeps(const MqlRates &r[],const double &a[],const V1Level &levels[],const V1Break &breaks[],const V1Params &p,V1Sweep &out[]) {
 ArrayResize(out,0);int at=ArraySize(r)-1;
 for(int k=0;k<ArraySize(levels);k++) {
  V1Level l=levels[k];int d=-l.side;
  for(int i=MathMax(l.created+1,at-p.confirm);i<at;i++) {
   if(a[i]==EMPTY_VALUE||a[i]<=0||(l.invalidated&&l.invalidated_at<i))continue;
   double extreme=d>0?r[i].low:r[i].high,depth=d*(l.price-extreme)/a[i];
   if(depth<=p.sweep_min||depth>p.sweep_max)continue;
   bool strict=d*(r[i].close-l.price)>0,soft=!strict&&p.soft&&d*(r[i+1].close-l.price)>0;
   if(!strict&&!soft)continue;
   int confirmed=-1,state=0;
   for(int j=i+1;j<=MathMin(at,i+p.confirm);j++) {
    if(d*(r[j].close-extreme)<0){state=-1;break;}
    bool small=false;for(int b=0;b<ArraySize(breaks);b++)if(!breaks[b].choch&&breaks[b].index==j&&breaks[b].direction==d)small=true;
    double trigger=d>0?r[i].high:r[i].low;
    if((d*(r[j].close-trigger)>0||small)&&(!soft||j>=i+1)){confirmed=j;state=1;break;}
   }
   if(confirmed<0&&at>=i+p.confirm)state=-1;
   int z=ArraySize(out);ArrayResize(out,z+1);out[z].direction=d;out[z].index=i;out[z].confirmed=confirmed;
   out[z].state=state;out[z].level=l.price;out[z].extreme=extreme;out[z].high=r[i].high;out[z].low=r[i].low;
   out[z].depth=depth;out[z].strength=d*(r[at].close-extreme)/a[i];out[z].level_id=l.id;out[z].level_type=l.type;out[z].soft=soft;out[z].major=l.major;
  }
 }
}
bool V1Pattern(const MqlRates &r[],int i,int d) {
 if(i<1)return false;double body=MathAbs(r[i].close-r[i].open),range=r[i].high-r[i].low;
 if(range<=0)return false;double wick=d>0?MathMin(r[i].open,r[i].close)-r[i].low:r[i].high-MathMax(r[i].open,r[i].close);
 bool pin=wick>=2*body&&wick/range>=.6;
 bool engulf=d*(r[i].close-r[i].open)>0&&d*(r[i-1].close-r[i-1].open)<0&&
  MathMax(r[i].open,r[i].close)>=MathMax(r[i-1].open,r[i-1].close)&&MathMin(r[i].open,r[i].close)<=MathMin(r[i-1].open,r[i-1].close);
 return pin||engulf;
}
#endif
