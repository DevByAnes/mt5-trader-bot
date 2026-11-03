#ifndef AURUM_V1_STORAGE
#define AURUM_V1_STORAGE
#include "Crypto.mqh"
bool V1Write(string path,string data,bool replace=true) {
 string temp=path+".tmp";uchar bytes[];V1Bytes(data,bytes);ResetLastError();
 int f=FileOpen(temp,FILE_WRITE|FILE_BIN|FILE_COMMON);if(f==INVALID_HANDLE)return false;
 uint written=FileWriteArray(f,bytes);FileFlush(f);int err=GetLastError();FileClose(f);
 if(written!=(uint)ArraySize(bytes)||err!=0){FileDelete(temp,FILE_COMMON);return false;}
 if(!FileMove(temp,FILE_COMMON,path,FILE_COMMON|(replace?FILE_REWRITE:0))){FileDelete(temp,FILE_COMMON);return false;}return true;
}
bool V1Read(string path,string &data) {
 int f=FileOpen(path,FILE_READ|FILE_BIN|FILE_COMMON|FILE_SHARE_READ);if(f==INVALID_HANDLE)return false;
 ulong size=FileSize(f);if(size==0||size>2200000){FileClose(f);return false;}uchar bytes[];ArrayResize(bytes,(int)size);
 uint got=FileReadArray(f,bytes);FileClose(f);if(got!=size)return false;data=CharArrayToString(bytes,0,WHOLE_ARRAY,CP_UTF8);return true;
}
bool V1Append(string path,string data) {
 ResetLastError();int f=FileOpen(path,FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,0,CP_UTF8);if(f==INVALID_HANDLE)return false;
 FileSeek(f,0,SEEK_END);uint written=FileWriteString(f,data+"\n");FileFlush(f);int err=GetLastError();FileClose(f);return written>0&&err==0;
}
bool V1Uuid(string id) {if(StringLen(id)!=36)return false;for(int i=0;i<36;i++){string c=StringSubstr(id,i,1);if(i==8||i==13||i==18||i==23){if(c!="-")return false;}else if(StringFind("0123456789abcdef",c)<0)return false;}return true;}
string V1NewUuid(){string h="";for(int i=0;i<32;i++)h+=StringSubstr("0123456789abcdef",MathRand()%16,1);return StringSubstr(h,0,8)+"-"+StringSubstr(h,8,4)+"-4"+StringSubstr(h,13,3)+"-a"+StringSubstr(h,17,3)+"-"+StringSubstr(h,20,12);}
#endif
