// launcher_english.cpp
#include <windows.h>
#include <fstream>
#include <string>

bool FileExists(const char* filename) {
    return GetFileAttributesA(filename) != INVALID_FILE_ATTRIBUTES;
}

bool CreateRunBat() {
    std::ofstream bat("run_gui.bat");
    if (!bat.is_open()) return false;
    
    // 写入UTF-8 BOM
    char bom[] = {(char)0xEF, (char)0xBB, (char)0xBF};
    bat.write(bom, 3);
    
    bat << "@echo off\r\n";
    bat << "chcp 65001 > nul\r\n";
    bat << "title DACreator GUI\r\n";
    bat << "echo ========================================\r\n";
    bat << "echo Starting DACreator GUI...\r\n";
    bat << "echo ========================================\r\n";
    bat << "echo.\r\n";
    bat << "\r\n";
    bat << ":: Check virtual environment\r\n";
    bat << "if exist venv\\Scripts\\activate.bat (\r\n";
    bat << "    echo Activating virtual environment...\r\n";
    bat << "    call venv\\Scripts\\activate.bat\r\n";
    bat << ") else (\r\n";
    bat << "    echo First run, creating virtual environment...\r\n";
    bat << ")\r\n";
    bat << "\r\n";
    bat << ":: Run GUI\r\n";
    bat << "python dacreator_gui.py\r\n";
    bat << "\r\n";
    bat << "if errorlevel 1 (\r\n";
    bat << "    echo.\r\n";
    bat << "    echo Error running program, check Python installation\r\n";
    bat << "    pause\r\n";
    bat << ")\r\n";
    bat << "\r\n";
    bat << "pause\r\n";
    
    bat.close();
    return true;
}

void ShowMessage(const char* title, const char* message) {
    MessageBoxA(NULL, message, title, MB_OK | MB_ICONINFORMATION);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE p, LPSTR c, int s) {
    if (!FileExists("run_gui.bat")) {
        ShowMessage("DACreator First Run", 
                   "Initializing environment...\n\n"
                   "1. Virtual environment will be created\n"
                   "2. Please wait for the command window\n"
                   "3. Run this program again after installation\n\n"
                   "Click OK to continue.");
        
        if (!CreateRunBat()) {
            ShowMessage("Error", "Cannot create startup script.");
            return 1;
        }
        
        STARTUPINFOA si = {sizeof(si)};
        PROCESS_INFORMATION pi;
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_SHOW;
        
        CreateProcessA(NULL, (LPSTR)"python dacreator_gui.py",
                      NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi);
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        
        ShowMessage("Installation Complete", 
                   "Environment is ready!\n\n"
                   "Please run this program again to start GUI.");
    } else {
        STARTUPINFOA si = {sizeof(si)};
        PROCESS_INFORMATION pi;
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_SHOW;
        
        CreateProcessA(NULL, (LPSTR)"run_gui.bat",
                      NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi);
    }
    
    return 0;
}