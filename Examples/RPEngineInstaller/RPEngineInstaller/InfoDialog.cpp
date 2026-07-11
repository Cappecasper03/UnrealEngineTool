#include "InfoDialog.h"
#include "InfoPanel.h"

InfoDialog::InfoDialog(wxWindow* parent) : wxDialog(parent, wxID_ANY, "Info", wxDefaultPosition, wxSize(600, 480), wxDEFAULT_DIALOG_STYLE)
{
	//Sets a dialog icon
	SetIcon(wxIcon("IDI_HELP1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));

	mPanel = new InfoPanel(this);
}

InfoDialog::~InfoDialog()
{
}
