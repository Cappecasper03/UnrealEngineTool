To compile the engine installer you need the wxWidgets library.
To install the library follow these steps:
1: Download the source code from github: https://github.com/wxWidgets/wxWidgets
2: Open wx_vc17.sln found in the wxWidgets/build/msw folder.
3: Go to Build->Batch Build... and select everyting that is Release|x64 and Debug|x64 (not DLL) and click Build.
4: Add a enviroment variable to windows named WXWIN with the path to the wxWidgets folder as Value.
After that you should be able to compile the project.