#pragma once
#include <wx/Dialog.h>

#include "EngineInfo.h"

class SettingsPanel;

class SettingsDialog : public wxDialog
{
public:
	SettingsDialog(wxWindow* parent, const wxVector<EngineInfo>& engines);
	~SettingsDialog();

	wxVector<EngineInfo>& getEngines() const;

private:

	SettingsPanel* mPanel{ nullptr };
};

