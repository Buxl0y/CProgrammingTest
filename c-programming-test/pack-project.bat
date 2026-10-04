@echo off
if exist dist rmdir /s /q dist
if not exist dist mkdir dist
if exist CProgrammingTest.zip del /q CProgrammingTest.zip
powershell -NoProfile -Command "Compress-Archive -Path * -DestinationPath CProgrammingTest.zip -Force"
echo Created CProgrammingTest.zip
