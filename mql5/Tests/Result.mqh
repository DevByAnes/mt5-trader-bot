#ifndef AURUM_TEST_RESULT_MQH
#define AURUM_TEST_RESULT_MQH

// Test-only result in this terminal's private file sandbox, not FILE_COMMON.
bool AurumWriteTestResult(const string name,const string json)
{
   ResetLastError();
   int handle=FileOpen(name,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
   if(handle==INVALID_HANDLE)
   {
      PrintFormat("AURUM_TEST_RESULT_WRITE_FAILED code=%d",GetLastError());
      return false;
   }
   uint written=FileWriteString(handle,json);
   FileFlush(handle);
   int failure=GetLastError();
   FileClose(handle);
   if(written==0 || failure!=0)
   {
      PrintFormat("AURUM_TEST_RESULT_WRITE_FAILED code=%d",failure);
      return false;
   }
   return true;
}
#endif
