#include "EngineDialog.h"
#include "EnginePanel.h"

EngineDialog::EngineDialog(wxWindow* parent, const wxVector<wxString>& otherVersions) : wxDialog(parent, wxID_ANY, "Add Engine", wxDefaultPosition, wxSize(400, 650), wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)
{
	//Sets a dialog icon
	SetIcon(wxIcon("IDI_ADD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	SetMinSize(wxSize(400, 600));

	mPanel = new EnginePanel(this, otherVersions);
}

EngineDialog::EngineDialog(wxWindow* parent, const EngineInfo& engine, const wxVector<wxString>& otherVersions) : wxDialog(parent, wxID_ANY, "Edit Engine", wxDefaultPosition, wxSize(400, 650), wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)
{
	//Sets a dialog icon
	SetIcon(wxIcon("IDI_EDIT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	SetMinSize(wxSize(400, 600));

	mPanel = new EnginePanel(this, engine, otherVersions);
}

EngineDialog::~EngineDialog()
{
}

EngineInfo EngineDialog::getEngine() const
{
	return mPanel->getEngine();
}
