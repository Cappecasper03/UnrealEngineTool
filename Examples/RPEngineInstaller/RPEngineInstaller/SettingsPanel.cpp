#include "SettingsPanel.h"
#include "EngineList.h"
#include "EngineDialog.h"

#include <wx/bmpbuttn.h>
#include <wx/sizer.h>
#include <wx/msgdlg.h>
#include <wx/menu.h>

SettingsPanel::SettingsPanel(wxWindow* parent, const wxVector<EngineInfo>& engines) : wxPanel(parent, -1, wxDefaultPosition, wxDefaultSize, wxNO_BORDER), mEngines(engines)
{
	//Setup list.
	mEngineList = new EngineList(this);
	mEngineList->Bind(wxEVT_LIST_KEY_DOWN, &SettingsPanel::onListKeyPressed, this);
	mEngineList->Bind(wxEVT_LIST_ITEM_RIGHT_CLICK, &SettingsPanel::onShowListContextMenu, this);
	mEngineList->Bind(EVT_CUSTOM_ENGINE_SELECTION, &SettingsPanel::onListSelection, this);
	mEngineList->initilizeItems(mEngines);

	//Setup list buttons.
	mAddButton = new wxBitmapButton(this, wxID_ANY, wxIcon("IDI_ADD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(32, 32));
	mAddButton->SetBitmapPressed(wxIcon("IDI_ADD2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mAddButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &SettingsPanel::onButtonAdd, this);
	mAddButton->SetToolTip("Add a new engine entry.");

	mEditButton = new wxBitmapButton(this, wxID_ANY, wxIcon("IDI_EDIT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(32, 32));
	mEditButton->SetBitmapPressed(wxIcon("IDI_EDIT2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mEditButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &SettingsPanel::onButtonEdit, this);
	mEditButton->SetToolTip("Edit the selected engine entry.");
	mEditButton->Disable();

	mRemoveButton = new wxBitmapButton(this, wxID_ANY, wxIcon("IDI_DEL1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(32, 32));
	mRemoveButton->SetBitmapPressed(wxIcon("IDI_DEL2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mRemoveButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &SettingsPanel::onButtonRemove, this);
	mRemoveButton->SetToolTip("Remove the selected engine entry.");
	mRemoveButton->Disable();

	//Setup exit buttons.
	mSaveButton = new wxButton(this, wxID_ANY, "Save", wxDefaultPosition, wxSize(80, 24));
	mSaveButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &SettingsPanel::onButtonSave, this);
	mSaveButton->SetToolTip("Save engine changes and exit.");

	mCancelButton = new wxButton(this, wxID_ANY, "Cancel", wxDefaultPosition, wxSize(80, 24));
	mCancelButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &SettingsPanel::onButtonCancel, this);
	mCancelButton->SetToolTip("Exit without saving.");

	//Setup sizers.
	wxBoxSizer* mainBoxV = new wxBoxSizer(wxVERTICAL);
	wxBoxSizer* listButtonsBoxH = new wxBoxSizer(wxHORIZONTAL);
	wxBoxSizer* exitButtonsBoxH = new wxBoxSizer(wxHORIZONTAL);

	mainBoxV->Add(mEngineList, 1, wxEXPAND | wxALL, 10);

	listButtonsBoxH->Add(mAddButton, 0);
	listButtonsBoxH->Add(mEditButton, 0, wxLEFT, 10);
	listButtonsBoxH->Add(mRemoveButton, 0, wxLEFT, 10);
	mainBoxV->Add(listButtonsBoxH, 0, wxCENTER | wxLEFT | wxRIGHT, 10);

	exitButtonsBoxH->Add(mSaveButton, 1);
	exitButtonsBoxH->Add(mCancelButton, 1, wxLEFT, 10);
	mainBoxV->Add(exitButtonsBoxH, 0, wxEXPAND | wxALL, 10);

	this->SetSizer(mainBoxV);
}

SettingsPanel::~SettingsPanel()
{
}

void SettingsPanel::onButtonAdd(wxCommandEvent& event)
{
	wxVector<EngineInfo> engines = mEngineList->getAllData();
	wxVector<wxString> otherVersions = wxVector<wxString>();
	for (uint32_t i{ 0 }; i < engines.size(); i++)
	{
		otherVersions.push_back(engines[i].engineVersion);
	}

	EngineDialog dialog(this, otherVersions);
	if (dialog.ShowModal() == wxID_OK)
	{
		EngineInfo addedEngine = dialog.getEngine();
		addedEngine.status = eEng_Add;
		mEngines.push_back(addedEngine);
		mEngineList->addItem(addedEngine);
	}
}

void SettingsPanel::onButtonEdit(wxCommandEvent& event)
{
	wxVector<EngineInfo> engines = mEngineList->getAllData();
	int32_t currentEngineIndex = mEngineList->getSelected();
	const EngineInfo targetEngine = engines[currentEngineIndex];
	wxVector<wxString> otherVersions = wxVector<wxString>();
	for (uint32_t i{ 0 }; i < engines.size(); i++)
	{
		if (i != currentEngineIndex)
		{
			otherVersions.push_back(engines[i].engineVersion);
		}
	}

	EngineDialog dialog(this, targetEngine, otherVersions);
	if (dialog.ShowModal() == wxID_OK)
	{
		EngineInfo modifiedEngine = dialog.getEngine();
		if (targetEngine.status == eEng_Add)
		{
			modifiedEngine.status = eEng_Add;
		}
		else
		{
			modifiedEngine.status = eEng_Modify;
		}
		mEngines[currentEngineIndex] = modifiedEngine;
		mEngineList->updateSelectedItem(modifiedEngine);
	}
}

void SettingsPanel::onButtonRemove(wxCommandEvent& event)
{
	wxMessageDialog message(this, "Are you sure you want to delete Rock Pocket Engine " + mEngineList->getSelectedEngineVersion() + "?", "Delete Item", wxYES_NO | wxNO_DEFAULT | wxICON_EXCLAMATION);
	message.SetYesNoLabels("Delete", "Cancel");
	if (message.ShowModal() == wxID_YES)
	{
		if (mEngines[mEngineList->getSelected()].status == eEng_Add)
		{
			mEngines.erase(mEngines.begin() + mEngineList->getSelected());
		}
		else
		{
			mEngines[mEngineList->getSelected()].status = eEng_Remove;
		}
		mEngineList->removeSelectedItem();
	}
}

void SettingsPanel::onButtonSave(wxCommandEvent& event)
{
	static_cast<wxDialog*>(GetParent())->EndModal(wxID_OK);
}

void SettingsPanel::onButtonCancel(wxCommandEvent& event)
{
	static_cast<wxDialog*>(GetParent())->EndModal(wxID_CANCEL);
}

void SettingsPanel::onListKeyPressed(wxListEvent& event)
{
	if (event.GetKeyCode() == WXK_DELETE && mRemoveButton->IsEnabled())
	{
		onButtonRemove(event);

		event.Skip();
	}
}

void SettingsPanel::onShowListContextMenu(wxListEvent& event)
{
	wxMenu menu;
	menu.Append(0, "Edit")->SetBitmap(wxIcon("IDI_EDIT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	menu.Append(1, "Delete")->SetBitmap(wxIcon("IDI_DEL1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	menu.Bind(wxEVT_COMMAND_MENU_SELECTED, &SettingsPanel::onListContextMenuSelected, this);
	PopupMenu(&menu);
}

void SettingsPanel::onListContextMenuSelected(wxCommandEvent& event)
{
	switch (event.GetId())
	{
	case 0:
		onButtonEdit(event);
		break;
	case 1:
		onButtonRemove(event);
		break;
	default:
		break;
	}
}

void SettingsPanel::onListSelection(wxCommandEvent& event)
{
	if (event.GetInt() == 0)
	{
		mEditButton->Disable();
		mRemoveButton->Disable();
	}
	else
	{
		mEditButton->Enable();
		mRemoveButton->Enable();
	}
}
