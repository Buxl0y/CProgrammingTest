@echo off
set ROOT=%~dp0
where WinRAR >nul 2>&1
if %ERRORLEVEL%==0 (
  if exist "%ROOT%CProgrammingTest.rar" del /q "%ROOT%CProgrammingTest.rar"
  WinRAR a -r "%ROOT%CProgrammingTest.rar" "%ROOT%*"
  echo Created CProgrammingTest.rar
  pause
  exit /b 0
)

echo WinRAR was not found on PATH.
echo Install WinRAR, then run this script again.
echo A CProgrammingTest.zip is included with the project as a portable archive.
pause
