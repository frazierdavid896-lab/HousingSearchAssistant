# Build the Windows executable

This kit builds a **one-folder Windows application**, which is more reliable than a single-file executable for Streamlit and GIS libraries.

## Build

1. Extract this ZIP into your existing project folder or a separate build folder.
2. Open PowerShell in that folder.
3. Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build_exe.ps1
```

The first build may take several minutes.

## Finished application

The executable will be here:

```text
dist\HousingSearchAssistant\HousingSearchAssistant.exe
```

Keep the **entire** `dist\HousingSearchAssistant` folder together. The EXE depends on the files beside it.

When opened, the EXE starts a private local Streamlit server and opens the application in your default browser.

## Important

- The EXE is not digitally signed. Windows Smart App Control or Microsoft Defender may warn about an unknown publisher.
- Do not disable Smart App Control globally.
- A signed installer requires purchasing a code-signing certificate and signing the EXE.
- Build the Windows EXE on Windows. PyInstaller does not cross-compile Windows applications from another operating system.
