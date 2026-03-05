@echo off
setlocal

REM ============================================================
REM  code-sign.cmd
REM  Generates a code-signing certificate signed by a local CA
REM  and exports the result as a PFX bundle.
REM
REM  Prerequisites:
REM    - OpenSSL on PATH
REM    - ca.crt and ca.key present in this directory (or adjust
REM      CA_CRT / CA_KEY below to point to your CA files)
REM    - code-sign.conf present in this directory
REM
REM  Output files:
REM    code-sign.key  private key (keep secret, never commit)
REM    code-sign.csr  certificate signing request
REM    code-sign.crt  signed certificate
REM    code-sign.pfx  PFX bundle  <-- use this with Invoke-ScriptSigning.ps1
REM ============================================================

set BASENAME=code-sign
set CA_CRT=ca.crt
set CA_KEY=ca.key
set DAYS=1825

REM ── Sanity checks ────────────────────────────────────────────

if not exist "%CA_CRT%" (
    echo ERROR: CA certificate not found: %CA_CRT%
    echo        Place your CA certificate in this directory or update CA_CRT.
    exit /b 1
)
if not exist "%CA_KEY%" (
    echo ERROR: CA private key not found: %CA_KEY%
    echo        Place your CA private key in this directory or update CA_KEY.
    exit /b 1
)
if not exist "%BASENAME%.conf" (
    echo ERROR: OpenSSL config not found: %BASENAME%.conf
    exit /b 1
)

REM ── Step 1: Generate private key ─────────────────────────────

echo [1/4] Generating private key: %BASENAME%.key
openssl genrsa -out %BASENAME%.key 4096
if errorlevel 1 goto :error

REM ── Step 2: Create CSR ───────────────────────────────────────

echo [2/4] Creating certificate signing request: %BASENAME%.csr
openssl req -new -key %BASENAME%.key -out %BASENAME%.csr -config %BASENAME%.conf
if errorlevel 1 goto :error

REM ── Step 3: Sign CSR with local CA ───────────────────────────

echo [3/4] Signing CSR with local CA: %BASENAME%.crt
openssl x509 -req ^
    -days %DAYS% ^
    -in %BASENAME%.csr ^
    -sha256 ^
    -CA %CA_CRT% ^
    -CAkey %CA_KEY% ^
    -CAcreateserial ^
    -extfile %BASENAME%.conf ^
    -extensions v3_req ^
    -out %BASENAME%.crt
if errorlevel 1 goto :error

REM ── Step 4: Export PFX bundle ─────────────────────────────────

echo [4/4] Exporting PFX bundle: %BASENAME%.pfx
echo       (you will be prompted to set a password for the PFX)
openssl pkcs12 -export ^
    -out %BASENAME%.pfx ^
    -inkey %BASENAME%.key ^
    -in %BASENAME%.crt ^
    -certfile %CA_CRT%
if errorlevel 1 goto :error

REM ── Done ──────────────────────────────────────────────────────

echo.
echo Done!  Generated files:
echo   %BASENAME%.key  -- private key     (KEEP SECRET)
echo   %BASENAME%.csr  -- signing request (can be discarded)
echo   %BASENAME%.crt  -- signed certificate
echo   %BASENAME%.pfx  -- PFX bundle      (use with Invoke-ScriptSigning.ps1)
echo.
echo REMINDER: do NOT commit .key or .pfx files to source control.
goto :eof

:error
echo.
echo ERROR: a step failed.  Review the OpenSSL output above.
exit /b 1
