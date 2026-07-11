#include "SettingsDialog.h"
#include "SettingsPanel.h"

SettingsDialog::SettingsDialog(wxWindow* parent, const wxVector<EngineInfo>& engines) : wxDialog(parent, wxID_ANY, "Settings", wxDefaultPosition, wxSize(250, 297), wxDEFAULT_DIALOG_STYLE)
{
	//Sets a dialog icon
	SetIcon(wxIcon("IDI_SETTING1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));

	mPanel = new SettingsPanel(this, engines);
}

SettingsDialog::~SettingsDialog()
{
}

wxVector<EngineInfo>& SettingsDialog::getEngines() const
{
	return mPanel->getEngines();
}
