@echo off
REM Daily Research Job - runs after market close
REM Schedule via Windows Task Scheduler at 5:30 PM ET
REM
REM Logs output to data/reports/run_YYYY-MM-DD.log

cd /d C:\Users\Yaming\family-quant-ai
call venv\Scripts\activate.bat

REM Create log filename with today's date
for /f "tokens=1-3 delims=/ " %%a in ('echo %date%') do set TODAY=%%c-%%a-%%b

REM Run the research pipeline (dry run - no orders submitted)
python daily_research.py > "data\reports\run_%TODAY%.log" 2>&1

REM To enable live order execution, change the line above to:
REM python daily_research.py --execute > "data\reports\run_%TODAY%.log" 2>&1

echo Done. Check data\reports\run_%TODAY%.log for results.
