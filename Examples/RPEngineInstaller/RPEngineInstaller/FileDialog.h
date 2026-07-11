#pragma once
#include <wx/Dialog.h>

#include "EngineInfo.h"

class FilePanel;

class FileDialog : public wxDialog
{
public:
	FileDialog(wxWindow* parent, const wxString customBuild, const wxString defaultBuild);
	FileDialog(wxWindow* parent, const EngineFile& file, const wxString customBuild, const wxString defaultBuild);
	~FileDialog();

	EngineFile getFileContext() const;

private:
	FilePanel* mPanel{ nullptr };
};

