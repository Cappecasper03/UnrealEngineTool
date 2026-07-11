#include "FileDialog.h"
#include "FilePanel.h"

FileDialog::FileDialog(wxWindow* parent, const wxString customBuild, const wxString defaultBuild) : wxDialog(parent, wxID_ANY, "Add File Context", wxDefaultPosition, customBuild.IsEmpty() || defaultBuild.IsEmpty() ? wxSize(300, 259) : wxSize(300, 343), wxDEFAULT_DIALOG_STYLE)
{
	//Sets a dialog icon
	SetIcon(wxIcon("IDI_ADD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));

	mPanel = new FilePanel(this, customBuild, defaultBuild);
}

FileDialog::FileDialog(wxWindow* parent, const EngineFile& file, const wxString customBuild, const wxString defaultBuild) : wxDialog(parent, wxID_ANY, "Edit File Context", wxDefaultPosition, customBuild.IsEmpty() || defaultBuild.IsEmpty() ? wxSize(300, 259) : wxSize(300, 343), wxDEFAULT_DIALOG_STYLE)
{
	//Sets a dialog icon
	SetIcon(wxIcon("IDI_EDIT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));

	mPanel = new FilePanel(this, file, customBuild, defaultBuild);
}

FileDialog::~FileDialog()
{
}

EngineFile FileDialog::getFileContext() const
{
	return mPanel->getFileContext();
}
