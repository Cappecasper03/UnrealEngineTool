#include "App.h"
#include "MainFrame.h"

wxIMPLEMENT_APP(App);

App::App()
{
}

App::~App()
{

}

bool App::OnInit()
{
	mMain = new MainFrame();
	mMain->Show();
	return true;
}

void App::setRockPocketHelperPath(const wxString rockPocketHelperPath)
{
	mRockPocketHelperPath = rockPocketHelperPath;
}

void App::setUnrealHelperPath(const wxString unrealHelperPath)
{
	mUnrealHelperPath = unrealHelperPath;
}

void App::setHelperPaths(const wxString rockPocketHelperPath, const wxString unrealHelperPath)
{
	mRockPocketHelperPath = rockPocketHelperPath;
	mUnrealHelperPath = unrealHelperPath;
}
