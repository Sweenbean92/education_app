@echo off
echo ============================================================
echo Ollama Model Setup Script
echo ============================================================
echo.
echo This script will set up the required Ollama models:
echo   - smollm2:360m (base model)
echo   - smollfinetuned (from bundled GGUF file)
echo.
echo Make sure Ollama is installed and running.
echo.
pause

python setup_models.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Setup completed successfully!
    echo You can now run the application with: python app.py
) else (
    echo.
    echo Setup encountered errors. Please check the output above.
)

python app.py
pause
