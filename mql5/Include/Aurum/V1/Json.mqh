#ifndef AURUM_V1_JSON
#define AURUM_V1_JSON
string JQuote(string s) {
 string out="\"";for(int i=0;i<StringLen(s);i++) {
  ushort c=StringGetCharacter(s,i);
  if(c==34)out+="\\\"";else if(c==92)out+="\\\\";else if(c<32)out+=StringFormat("\\u%04x",c);else out+=ShortToString(c);
 }return out+"\"";
}
string JNum(double v) {return MathIsValidNumber(v)&&v!=EMPTY_VALUE?DoubleToString(v,10):"null";}
string JBool(bool b){return b?"true":"false";}
// Casting datetime directly to string produces a date with colons, not Unix seconds.
// Use this for numeric JSON timestamps and filename components only.
string JEpoch(datetime t){return IntegerToString((long)t);}
string JTime(datetime t) {string s=TimeToString(t,TIME_DATE|TIME_SECONDS);StringReplace(s,".","-");StringReplace(s," ","T");return s+"Z";}
// Bounded strict JSON tokenizer. Duplicate object keys, malformed numbers and escapes fail closed.
struct JToken { string value; int kind,parent,end; }; // 1 object,2 array,3 string,4 number,5 literal
class V1Json {
 private:
 string raw;int pos;bool ok;
 void Space(){while(pos<StringLen(raw)&&StringFind(" \r\n\t",StringSubstr(raw,pos,1))>=0)pos++;}
 int Hex(ushort c){if(c>=48&&c<=57)return c-48;if(c>=65&&c<=70)return c-55;if(c>=97&&c<=102)return c-87;return -1;}
 string Str(){string out="";pos++;bool closed=false;
  while(pos<StringLen(raw)) {
   ushort c=StringGetCharacter(raw,pos++);if(c==34){closed=true;break;}if(c<32){ok=false;break;}
   if(c!=92){out+=ShortToString(c);continue;}if(pos>=StringLen(raw)){ok=false;break;}
   c=StringGetCharacter(raw,pos++);
   if(c==34||c==92||c==47)out+=ShortToString(c);else if(c==98)out+=ShortToString(8);else if(c==102)out+=ShortToString(12);
   else if(c==110)out+="\n";else if(c==114)out+="\r";else if(c==116)out+="\t";
   else if(c==117) {
    int n=0;for(int k=0;k<4;k++){if(pos>=StringLen(raw)){ok=false;break;}int h=Hex(StringGetCharacter(raw,pos++));if(h<0){ok=false;break;}n=n*16+h;}
    out+=ShortToString((ushort)n);
   }else {ok=false;break;}
  }if(!closed)ok=false;return out;
 }
 int Value(int parent,int depth){Space();if(depth>24||pos>=StringLen(raw)||ArraySize(t)>30000){ok=false;return -1;}
  int id=ArraySize(t);ArrayResize(t,id+1);t[id].parent=parent;t[id].value="";ushort c=StringGetCharacter(raw,pos);
  if(c==123||c==91) {
   bool object=c==123;t[id].kind=object?1:2;pos++;Space();ushort close=object?125:93;
   if(pos<StringLen(raw)&&StringGetCharacter(raw,pos)==close)pos++;
   else while(ok) {
    if(object) {
     Space();if(pos>=StringLen(raw)||StringGetCharacter(raw,pos)!=34){ok=false;break;}
     string key=Str();for(int k=id+1;k<ArraySize(t);k=t[k].end+1)if(t[k].parent==id&&t[k].value==key){ok=false;break;}
     int key_id=ArraySize(t);ArrayResize(t,key_id+1);t[key_id].kind=3;t[key_id].value=key;t[key_id].parent=id;t[key_id].end=key_id;
     Space();if(pos>=StringLen(raw)||StringGetCharacter(raw,pos++)!=58){ok=false;break;}
     Value(key_id,depth+1);t[key_id].end=ArraySize(t)-1;
    }else Value(id,depth+1);
    Space();if(pos>=StringLen(raw)){ok=false;break;}c=StringGetCharacter(raw,pos++);if(c==close)break;if(c!=44){ok=false;break;}
   }
  }else if(c==34){t[id].kind=3;t[id].value=Str();}
  else {
   int start=pos;while(pos<StringLen(raw)&&StringFind(" \t\r\n,]}",StringSubstr(raw,pos,1))<0)pos++;
   string v=StringSubstr(raw,start,pos-start);t[id].value=v;t[id].kind=5;
   if(v!="true"&&v!="false"&&v!="null") {
    t[id].kind=4;int q=0,len=StringLen(v);if(q<len&&StringGetCharacter(v,q)==45)q++;
    if(q>=len)ok=false;
    else if(StringGetCharacter(v,q)==48)q++;
    else {int begin=q;while(q<len&&StringGetCharacter(v,q)>=48&&StringGetCharacter(v,q)<=57)q++;if(begin==q)ok=false;}
    if(q<len&&StringGetCharacter(v,q)==46){q++;int begin=q;while(q<len&&StringGetCharacter(v,q)>=48&&StringGetCharacter(v,q)<=57)q++;if(q==begin)ok=false;}
    if(q<len&&(StringGetCharacter(v,q)==101||StringGetCharacter(v,q)==69)){q++;if(q<len&&(StringGetCharacter(v,q)==43||StringGetCharacter(v,q)==45))q++;int begin=q;while(q<len&&StringGetCharacter(v,q)>=48&&StringGetCharacter(v,q)<=57)q++;if(q==begin)ok=false;}
    if(q!=len||!MathIsValidNumber(StringToDouble(v)))ok=false;
   }
  }t[id].end=ArraySize(t)-1;return id;
 }
 public:
 JToken t[];
 bool Parse(string s){raw=s;pos=0;ok=true;ArrayResize(t,0);Value(-1,0);Space();return ok&&pos==StringLen(raw);}
 int Field(int object,string key){if(object<0||object>=ArraySize(t)||t[object].kind!=1)return -1;for(int k=object+1;k<=t[object].end;k=t[k].end+1)if(t[k].value==key)return k+1;return -1;}
 string Get(int object,string key){int k=Field(object,key);return k<0?"":t[k].value;}
 double Number(int object,string key){int k=Field(object,key);return k<0||t[k].kind!=4?EMPTY_VALUE:StringToDouble(t[k].value);}
 bool Keys(int object,string names){if(object<0||t[object].kind!=1)return false;int count=0;
  for(int k=object+1;k<=t[object].end;k=t[k].end+1){if(StringFind("|"+names+"|","|"+t[k].value+"|")<0)return false;count++;}
  int expected=1;for(int k=0;k<StringLen(names);k++)if(StringGetCharacter(names,k)==124)expected++;return count==expected;
 }
};
#endif
