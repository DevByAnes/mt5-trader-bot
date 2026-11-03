#ifndef AURUM_V1_CRYPTO
#define AURUM_V1_CRYPTO
#include "Json.mqh"
void V1Bytes(string text,uchar &out[]){int n=StringToCharArray(text,out,0,WHOLE_ARRAY,CP_UTF8);if(n>0)ArrayResize(out,n-1);}
string V1Hex(const uchar &a[]){string s="";for(int i=0;i<ArraySize(a);i++)s+=StringFormat("%02x",a[i]);return s;}
string V1Hash(const uchar &a[]){uchar empty[],out[];if(CryptEncode(CRYPT_HASH_SHA256,a,empty,out)!=32)return "";return V1Hex(out);}
string V1HashText(string s){uchar a[];V1Bytes(s,a);return V1Hash(a);}
bool V1Unhex(string s,uchar &out[]){int n=StringLen(s);if(n<64||n>256||n%2!=0)return false;ArrayResize(out,n/2);
 string digits="0123456789abcdef";StringToLower(s);for(int i=0;i<n;i+=2){int h=StringFind(digits,StringSubstr(s,i,1)),l=StringFind(digits,StringSubstr(s,i+1,1));if(h<0||l<0)return false;out[i/2]=(uchar)(h*16+l);}return true;}
string V1Hmac(const uchar &key[],string text) {
 uchar k[],inner[],outer[],data[],empty[],digest[];ArrayCopy(k,key);
 if(ArraySize(k)>64){if(CryptEncode(CRYPT_HASH_SHA256,k,empty,digest)!=32)return "";ArrayCopy(k,digest);ArrayResize(k,32);}
 ArrayResize(inner,64);ArrayResize(outer,96);
 for(int i=0;i<64;i++){uchar v=i<ArraySize(k)?k[i]:0;inner[i]=(uchar)(v^0x36);outer[i]=(uchar)(v^0x5c);}
 V1Bytes(text,data);ArrayCopy(inner,data,64);if(CryptEncode(CRYPT_HASH_SHA256,inner,empty,digest)!=32)return "";
 ArrayCopy(outer,digest,64);if(CryptEncode(CRYPT_HASH_SHA256,outer,empty,digest)!=32)return "";return V1Hex(digest);
}
bool V1Equal(string a,string b){int diff=StringLen(a)^StringLen(b);for(int i=0;i<MathMin(StringLen(a),StringLen(b));i++)diff|=StringGetCharacter(a,i)^StringGetCharacter(b,i);return diff==0;}
string V1Base64(string s){uchar a[],empty[],out[];V1Bytes(s,a);if(CryptEncode(CRYPT_BASE64,a,empty,out)<=0)return "";return CharArrayToString(out,0,WHOLE_ARRAY,CP_UTF8);}
bool V1Decode64(string s,string &decoded){uchar a[],empty[],out[];V1Bytes(s,a);if(CryptDecode(CRYPT_BASE64,a,empty,out)<=0)return false;
 decoded=CharArrayToString(out,0,WHOLE_ARRAY,CP_UTF8);return V1Base64(decoded)==s;}
string V1Wire(string payload,string key_id,const uchar &key[]){string hash=V1HashText(payload),mac=V1Hmac(key,"AURUM-FILE-V1\n"+key_id+"\n"+payload);
 if(hash==""||mac=="")return "";return "{\"protocol_version\":\"1.0.0\",\"key_id\":"+JQuote(key_id)+",\"payload_b64\":"+JQuote(V1Base64(payload))+",\"sha256\":"+JQuote(hash)+",\"hmac_sha256\":"+JQuote(mac)+"}";}
bool V1Unwire(string wire,string key_id,const uchar &key[],string &payload) {
 V1Json j;if(StringLen(wire)>2200000||!j.Parse(wire)||!j.Keys(0,"protocol_version|key_id|payload_b64|sha256|hmac_sha256")||j.Get(0,"protocol_version")!="1.0.0"||j.Get(0,"key_id")!=key_id)return false;
 if(!V1Decode64(j.Get(0,"payload_b64"),payload)||StringLen(payload)>1500000)return false;
 return V1Equal(V1HashText(payload),j.Get(0,"sha256"))&&V1Equal(V1Hmac(key,"AURUM-FILE-V1\n"+key_id+"\n"+payload),j.Get(0,"hmac_sha256"));
}
#endif
