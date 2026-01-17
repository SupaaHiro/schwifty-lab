@echo off
setlocal

REM Load environment variables from .env file if it exists
if exist .env (
  for /F "delims== tokens=1,* eol=#" %%i in (.env) do set "%%i=%%~j"
  echo Environment variables loaded from .env
)

REM Start the client (dotnet solution)
if /I "%1" == "client" (
  echo Running client...

  if exist "ApiResilience.Client\ApiResilience.Client.csproj" (
    cd ApiResilience.Client
    call dotnet watch --project "ApiResilience.Client.csproj" run
    goto :EOF
  )

  echo Unable to start the client. Ensure you are in the correct directory.
  exit /b 1
)

REM Start the server (dotnet solution)
if /I "%1" == "server" (
  echo Running server...

  if exist "ApiResilience.Server\ApiResilience.Server.csproj" (
    cd ApiResilience.Server
    call dotnet watch --project "ApiResilience.Server.csproj" run
    goto :EOF
  )

  echo Unable to start the server. Ensure you are in the correct directory.
  exit /b 1
)

echo Usage: start.bat [client^|server]
