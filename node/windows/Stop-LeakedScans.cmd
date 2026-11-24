@echo off
rem OWNER STEP (NODE, task desks-3-6). Lists find.exe scans a session left running from / or a drive root.
rem Double-click: it only LISTS, then waits. To stop what it lists, run it from a terminal with -Apply:
rem     Stop-LeakedScans.cmd -Apply
rem Why a .cmd: on this PC `powershell -File x.ps1` is refused ("running scripts is disabled"), and the
rem fix is this one-process bypass. It changes no setting and no policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Stop-LeakedScans.ps1" %*
pause
