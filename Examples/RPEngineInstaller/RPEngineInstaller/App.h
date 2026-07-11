#pragma once
#include <wx/App.h>

class MainFrame;

class App : public wxApp
{
public:
	App();
	~App();

	virtual bool OnInit();

	void setRockPocketHelperPath(const wxString rockPocketHelperPath);
	void setUnrealHelperPath(const wxString unrealHelperPath);
	void setHelperPaths(const wxString rockPocketHelperPath, const wxString unrealHelperPath);

	wxString getRockPocketHelperPath() const { return mRockPocketHelperPath; }
	wxString getUnrealHelperPath() const { return mUnrealHelperPath; }

private:
	MainFrame* mMain;

	//Helper path used to ease adding engine files.
	wxString mRockPocketHelperPath{ wxEmptyString };
	//Helper path used to ease adding engine files.
	wxString mUnrealHelperPath{ wxEmptyString };
};

