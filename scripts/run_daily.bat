@echo off
REM Family Quant AI - Autonomous Daily Market Close Runner
cd /d "C:\Users\Yaming\family-quant-ai"
"C:\Users\Yaming\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\Users\Yaming\family-quant-ai\scripts\run_daily_cycle.py" >> "C:\Users\Yaming\family-quant-ai\data\reports\scheduler.log" 2>&1
