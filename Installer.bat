python -m PyInstaller --onefile --windowed main.py

move dist\* .
pause
rmdir /s /q dist
rmdir /s /q build
del main.spec
pause
