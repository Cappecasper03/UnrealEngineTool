#pragma once
#include <wx/dnd.h>

class FileList;

class FileDropTarget : public wxFileDropTarget
{
public:
	FileDropTarget(FileList* list);

	virtual bool OnDrop(wxCoord x, wxCoord y) override;
	virtual bool OnDropFiles(wxCoord x, wxCoord y, const wxArrayString& filenames) override;

	void setPaths(const wxString& customPath, const wxString& defaultPath);
	void setCustomPath(const wxString& path, const bool refresh = true);
	void setDefaultPath(const wxString& path, const bool refresh = true);

private:
	void checkPaths();

	FileList* mList{ nullptr };

	//Path to the custom build directory.
	wxString mCustomPath{ wxEmptyString };
	//Path to the default build directory.
	wxString mDefaultPath{ wxEmptyString };

	//Only allow dropping if true.
	bool bEnabled{ false };

	//Path to test if the build paths are valid.
	const wxString mBuildTestPath{ "\\Engine\\Binaries\\Win64\\UnrealEditor-Engine.dll" };
};

