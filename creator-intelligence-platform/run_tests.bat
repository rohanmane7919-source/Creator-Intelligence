@echo off
cd backend
call venv\Scripts\activate
python -m pytest
pause
