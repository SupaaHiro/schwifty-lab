@echo off
setlocal

REM Load environment variables from .env file if it exists
if exist .env (
  for /F "delims== tokens=1,* eol=#" %%i in (.env) do set %%i=%%~j
  echo Environment variables loaded from .env
)

REM Start the WEB bundle
if "%1" == "web" (  
  call bundle exec jekyll serve --livereload  --config _config.yml,_config.local.yml
  
  goto :EOF
)

echo "Usage: start.bat [web]"