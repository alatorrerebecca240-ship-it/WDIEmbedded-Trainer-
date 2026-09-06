@echo off
where python >nul 2>nul
if not errorlevel 1 (
  python "%~dp0trainer.py" %*
) else (
  py -3 "%~dp0trainer.py" %*
)
