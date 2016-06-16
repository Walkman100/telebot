@echo off
python2 main.py
echo.
echo If output says "ImportError: No module named PIL" then press enter...
pause
python2 -u "%ProgramFiles%\Google\AppEngine\appcfg.py" --oauth2_credential_file="%UserProfile%\.appcfg_oauth2_tokens" update "%~dp0"
