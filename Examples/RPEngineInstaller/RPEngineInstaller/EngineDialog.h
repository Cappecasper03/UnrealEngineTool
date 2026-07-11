#pragma once
#include <wx/Dialog.h>

#include "EngineInfo.h"

class EnginePanel;

class EngineDialog : public wxDialog
{
public:
	EngineDialog(wxWindow* parent, const wxVector<wxString>& otherVersions);
	EngineDialog(wxWindow* parent, const EngineInfo& engine, const wxVector<wxString>& otherVersions);
	~EngineDialog();

	EngineInfo getEngine() const;

private:
	EnginePanel* mPanel{ nullptr };
};

