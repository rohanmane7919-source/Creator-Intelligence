@echo off
cd backend
python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo DONE. Now open backend\.env and put your PostgreSQL password in DB_PASSWORD.
pause
