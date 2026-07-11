#include "EnginePanel.h"
#include "FileList.h"
#include "FileDropTarget.h"
#include "FileDialog.h"
#include "App.h"

#include <wx/textctrl.h>
#include <wx/choice.h>
#include <wx/filepicker.h>
#include <wx/bmpbuttn.h>
#include <wx/sizer.h>
#include <wx/stattext.h>
#include <wx/statline.h>
#include <wx/msgdlg.h>
#include <wx/menu.h>

EnginePanel::EnginePanel(wxWindow* parent, const wxVector<wxString>& otherVersions) : wxPanel(parent, -1, wxDefaultPosition, wxDefaultSize, wxNO_BORDER), mOtherVersions(otherVersions)
{
	//Setup version names.
	mEngineVersionText = new wxTextCtrl(this, wxID_ANY, wxEmptyString, wxDefaultPosition, wxDefaultSize);
	mEngineVersionText->SetHint("Enter Rock Pocket Engine version.");
	mEngineVersionText->SetMaxLength(16);

	mUnrealVersionText = new wxTextCtrl(this, wxID_ANY, wxEmptyString, wxDefaultPosition, wxDefaultSize);
	mUnrealVersionText->SetHint("Enter Unreal Engine version.");
	mUnrealVersionText->SetMaxLength(16);

	//Setup parents picker.
	wxArrayString avaliableParents;
	avaliableParents.Add(mNoParent);
	for (uint32_t i{ 0 }; i < otherVersions.size(); i++)
	{
		avaliableParents.Add(otherVersions[i]);
	}
	mParentPicker = new wxChoice(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, avaliableParents);
	mParentPicker->SetSelection(0);
	mParentPicker->SetToolTip("Select a parent version. All file contexts from the parent will be inherited.");

	//Setup changelog.
	mChangelogText = new wxTextCtrl(this, wxID_ANY, wxEmptyString, wxDefaultPosition, wxSize(100, 75), wxTE_MULTILINE);
	mChangelogText->SetHint("Write down all the changes made to this version of the Rock Pocket Engine.");

	//Setup default unreal directory picker.
	mUnrealDir = new wxDirPickerCtrl(this, wxID_ANY, "C:\\Program Files\\Epic Games\\", "Unreal Engine Directory", wxDefaultPosition, wxDefaultSize);
	mUnrealDir->SetToolTip("Choose the default Unreal Engine directory matching the Unreal version.");

	//Setup file list.
	mFileList = new FileList(this);
	mFileList->Bind(wxEVT_LIST_KEY_DOWN, &EnginePanel::onListKeyPressed, this);
	mFileList->Bind(wxEVT_LIST_ITEM_RIGHT_CLICK, &EnginePanel::onShowListContextMenu, this);
	mFileList->Bind(EVT_CUSTOM_FILE_SELECTION, &EnginePanel::onListSelection, this);
	mFileList->Bind(EVT_CUSTOM_DROP_FAILED, &EnginePanel::onListDropFailed, this);

	//Setup file buttons.
	mAddFileButton = new wxBitmapButton(this, wxID_ANY, wxIcon("IDI_ADD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(32, 32));
	mAddFileButton->SetBitmapPressed(wxIcon("IDI_ADD2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mAddFileButton->SetToolTip("Add file context.");
	mAddFileButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &EnginePanel::onAddFileButton, this);

	mEditFileButton = new wxBitmapButton(this, wxID_ANY, wxIcon("IDI_EDIT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(32, 32));
	mEditFileButton->SetBitmapPressed(wxIcon("IDI_EDIT2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mEditFileButton->SetToolTip("Edit file context.");
	mEditFileButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &EnginePanel::onEditFileButton, this);
	mEditFileButton->Disable();

	mRemoveFileButton = new wxBitmapButton(this, wxID_ANY, wxIcon("IDI_DEL1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(32, 32));
	mRemoveFileButton->SetBitmapPressed(wxIcon("IDI_DEL2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mRemoveFileButton->SetToolTip("Remove file context.");
	mRemoveFileButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &EnginePanel::onRemoveFileButton, this);
	mRemoveFileButton->Disable();

	//Setup helper directory picker for the rock pocket engine build.
	mRockPocketBuildDir = new wxDirPickerCtrl(this, wxID_ANY, static_cast<App*>(wxApp::GetInstance())->getRockPocketHelperPath(), "Rock Pocket Build Directory", wxDefaultPosition, wxDefaultSize);
	mRockPocketBuildDir->GetTextCtrl()->SetHint("Rock Pocket Engine build directory.");
	mRockPocketBuildDir->SetToolTip("Locate the directory of the local Rock Pocket Engine build.");
	mRockPocketBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT_ENTER, &EnginePanel::onRockPocketBuildChanged, this);
	mRockPocketBuildDir->Bind(wxEVT_DIRPICKER_CHANGED, &EnginePanel::onRockPocketBuildChanged, this);

	//Setup helper directory picker for the unreal engine build.
	mUnrealBuildDir = new wxDirPickerCtrl(this, wxID_ANY, static_cast<App*>(wxApp::GetInstance())->getUnrealHelperPath(), "Unreal Build Directory", wxDefaultPosition, wxDefaultSize);
	mUnrealBuildDir->GetTextCtrl()->SetHint("Unreal Engine build directory.");
	mUnrealBuildDir->SetToolTip("Locate the directory of the local Unreal Engine build.");
	mUnrealBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT_ENTER, &EnginePanel::onUnrealBuildChanged, this);
	mUnrealBuildDir->Bind(wxEVT_DIRPICKER_CHANGED, &EnginePanel::onUnrealBuildChanged, this);

	//Setup exit buttons.
	mConfirmButton = new wxButton(this, wxID_ANY, "Confirm", wxDefaultPosition, wxDefaultSize);
	mConfirmButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &EnginePanel::onButtonConfirm, this);
	mConfirmButton->SetToolTip("Save engine and exit.");

	mCancelButton = new wxButton(this, wxID_ANY, "Cancel", wxDefaultPosition, wxDefaultSize);
	mCancelButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &EnginePanel::onButtonCancel, this);
	mCancelButton->SetToolTip("Exit without saving.");

	//Setup error text.
	mErrorText = new wxStaticText(this, wxID_ANY, wxEmptyString, wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL);
	mErrorText->SetForegroundColour(wxColor(*wxRED));

	//Setup list drop.
	mFileDrop = new FileDropTarget(mFileList);
	mFileDrop->setPaths(mRockPocketBuildDir->GetPath(), mUnrealBuildDir->GetPath());
	mFileList->SetDropTarget(mFileDrop);

	//Setup sizers.
	wxBoxSizer* mainBoxV = new wxBoxSizer(wxVERTICAL);
	wxBoxSizer* listButtonsBoxH = new wxBoxSizer(wxHORIZONTAL);
	wxBoxSizer* exitButtonsBoxH = new wxBoxSizer(wxHORIZONTAL);

	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Rock Pocket Engine Version:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
	mainBoxV->Add(mEngineVersionText, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Parent Version:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
	mainBoxV->Add(mParentPicker, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Unreal Engine Version:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
	mainBoxV->Add(mUnrealVersionText, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Changelog:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
	mainBoxV->Add(mChangelogText, 1, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Unreal Default Directory:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
	mainBoxV->Add(mUnrealDir, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);

	mainBoxV->Add(new wxStaticLine(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLI_HORIZONTAL), 0, wxEXPAND | wxUP, 5);
	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "File Context:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
	mainBoxV->Add(mFileList, 1, wxEXPAND | wxLEFT | wxRIGHT, 10);
	listButtonsBoxH->Add(mAddFileButton, 0);
	listButtonsBoxH->Add(mEditFileButton, 0, wxLEFT, 10);
	listButtonsBoxH->Add(mRemoveFileButton, 0, wxLEFT, 10);
	mainBoxV->Add(listButtonsBoxH, 0, wxCENTER | wxALL, 5);
	mainBoxV->Add(new wxStaticLine(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLI_HORIZONTAL), 0, wxEXPAND | wxBOTTOM, 5);

	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Build Directories (Optional):", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxBOTTOM, 5);
	mainBoxV->Add(mRockPocketBuildDir, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(0, 5);
	mainBoxV->Add(mUnrealBuildDir, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(new wxStaticLine(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLI_HORIZONTAL), 0, wxEXPAND | wxALL, 5);

	mainBoxV->Add(mErrorText, 0, wxCENTRE | wxBOTTOM, 5);
	exitButtonsBoxH->Add(mConfirmButton, 1, wxEXPAND);
	exitButtonsBoxH->Add(mCancelButton, 1, wxEXPAND | wxLEFT, 10);
	mainBoxV->Add(exitButtonsBoxH, 0, wxEXPAND | wxLEFT | wxBOTTOM | wxRIGHT, 10);

	this->SetSizer(mainBoxV);
}

EnginePanel::EnginePanel(wxWindow* parent, const EngineInfo& engine, const wxVector<wxString>& otherVersions) : EnginePanel(parent, otherVersions)
{
	mEngineVersionText->SetValue(engine.engineVersion);
	if (engine.parentVersion.empty() == false)
	{
		mParentPicker->SetStringSelection(engine.parentVersion);
	}
	mUnrealVersionText->SetValue(engine.unrealVersion);
	mChangelogText->SetValue(engine.changelog);
	mUnrealDir->SetPath(engine.unrealDir);
	mFileList->initilizeItems(engine.files);
}

EnginePanel::~EnginePanel()
{
	//delete mFileDrop;
}

EngineInfo EnginePanel::getEngine() const
{
	EngineInfo engine;
	engine.engineVersion = mEngineVersionText->GetValue();
	if (mParentPicker->GetSelection() > 0)
	{
		engine.parentVersion = mParentPicker->GetStringSelection();
	}
	engine.unrealVersion = mUnrealVersionText->GetValue();
	engine.changelog = mChangelogText->GetValue();
	engine.unrealDir = mUnrealDir->GetPath();
	engine.files = mFileList->getAllData();

	//Setup file names for copying.
	for (int i{ 0 }; i < engine.files.size(); i++)
	{
		wxFileName fileName(engine.files[i].pathTarget);
		unsigned int foundMatching{ 0 };

		for (int j{ i - 1 }; j >= 0; j--)
		{
			wxFileName otherName(engine.files[j].pathTarget);
			if ((fileName.GetName() + "." + fileName.GetExt()) == (otherName.GetName() + "." + otherName.GetExt()))
			{
				foundMatching++;
			}
		}

		//Append number to file name if there are several files of this name.
		if (foundMatching > 0)
		{
			engine.files[i].localName = fileName.GetName() + wxString::Format(wxT(" (%i)"), foundMatching) + "." + fileName.GetExt();
		}
		else
		{
			engine.files[i].localName = fileName.GetName() + "." + fileName.GetExt();
		}
	}

	return engine;
}

void EnginePanel::onAddFileButton(wxCommandEvent& event)
{
	if (checkBuildDirectories(true))
	{
		FileDialog dialog(this, mRockPocketBuildDir->GetPath(), mUnrealBuildDir->GetPath());
		if (dialog.ShowModal() == wxID_OK)
		{
			mFileList->addItem(dialog.getFileContext());
		}
	}
}

void EnginePanel::onEditFileButton(wxCommandEvent& event)
{
	if (checkBuildDirectories(true))
	{
		FileDialog dialog(this, mFileList->getSelectedData(), mRockPocketBuildDir->GetPath(), mUnrealBuildDir->GetPath());
		if (dialog.ShowModal() == wxID_OK)
		{
			mFileList->updateSelectedItem(dialog.getFileContext());
		}
	}
}

void EnginePanel::onRemoveFileButton(wxCommandEvent& event)
{
	wxMessageDialog message(this, "Are you sure you want to delete the file context for " + mFileList->getSelectedFileName() + "?", "Delete Item", wxYES_NO | wxNO_DEFAULT | wxICON_EXCLAMATION);
	message.SetYesNoLabels("Delete", "Cancel");
	if (message.ShowModal() == wxID_YES)
	{
		mFileList->removeSelectedItem();
	}
}

void EnginePanel::onButtonConfirm(wxCommandEvent& event)
{
	//Make sure the user has given a custom engine version, and that the version is not already in use.
	if (mEngineVersionText->GetValue().empty())
	{
		setError(eError_EngVer);
		return;
	}
	else
	{
		for (uint32_t i{ 0 }; i < mOtherVersions.size(); i++)
		{
			if (mEngineVersionText->GetValue().IsSameAs(mOtherVersions[i], false))
			{
				setError(eError_EngVerInv);
				return;
			}
		}
	}

	//Make sure the user has given a unreal version.
	if (mUnrealVersionText->GetValue().empty())
	{
		setError(eError_UnrVer);
		return;
	}

	//Make sure the user has written a changelog.
	if (mChangelogText->GetValue().empty())
	{
		setError(eError_ChgLog);
		return;
	}

	//Make sure there is at least one file for the engine.
	if (mFileList->IsEmpty())
	{
		setError(eError_File);
		return;
	}

	//Save build directories if valid.
	if (checkBuildDirectories(false))
	{
		static_cast<App*>(wxApp::GetInstance())->setHelperPaths(mRockPocketBuildDir->GetPath(), mUnrealBuildDir->GetPath());
	}

	static_cast<wxDialog*>(GetParent())->EndModal(wxID_OK);
}

void EnginePanel::onButtonCancel(wxCommandEvent& event)
{
	//Save build directories if valid.
	if (checkBuildDirectories(false))
	{
		static_cast<App*>(wxApp::GetInstance())->setHelperPaths(mRockPocketBuildDir->GetPath(), mUnrealBuildDir->GetPath());
	}

	static_cast<wxDialog*>(GetParent())->EndModal(wxID_CANCEL);
}

void EnginePanel::onListKeyPressed(wxListEvent& event)
{
	if (event.GetKeyCode() == WXK_DELETE && mRemoveFileButton->IsEnabled())
	{
		onRemoveFileButton(event);

		event.Skip();
	}
}

void EnginePanel::onShowListContextMenu(wxListEvent& event)
{
	wxMenu menu;
	menu.Append(0, "Edit")->SetBitmap(wxIcon("IDI_EDIT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	menu.Append(1, "Delete")->SetBitmap(wxIcon("IDI_DEL1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	menu.Bind(wxEVT_COMMAND_MENU_SELECTED, &EnginePanel::onListContextMenuSelected, this);
	PopupMenu(&menu);
}

void EnginePanel::onListContextMenuSelected(wxCommandEvent& event)
{
	switch (event.GetId())
	{
	case 0:
		onEditFileButton(event);
		break;
	case 1:
		onRemoveFileButton(event);
		break;
	default:
		break;
	}
}

void EnginePanel::onListSelection(wxCommandEvent& event)
{
	if (event.GetInt() == 0)
	{
		mEditFileButton->Disable();
		mRemoveFileButton->Disable();
	}
	else
	{
		mEditFileButton->Enable();
		mRemoveFileButton->Enable();
	}
}

void EnginePanel::onListDropFailed(wxCommandEvent& event)
{
	if (mRockPocketBuildDir->GetPath().IsEmpty() && mUnrealBuildDir->GetPath().IsEmpty())
	{
		setError(eError_NoBuild);
	}
	else
	{
		checkBuildDirectories(true);
	}
}

void EnginePanel::onRockPocketBuildChanged(wxCommandEvent& event)
{
	mFileDrop->setCustomPath(mRockPocketBuildDir->GetPath());

	//Also clear error if related to rock pocket build directory.
	switch (mCurrentError)
	{
	case eError_RBuild: case eError_RBuildInv: case eError_SameBuild: case eError_NoBuild:
		clearError(true);
		break;
	default:
		break;
	}
}

void EnginePanel::onUnrealBuildChanged(wxCommandEvent& event)
{
	mFileDrop->setDefaultPath(mUnrealBuildDir->GetPath());

	//Also clear error if related to rock unreal build directory.
	switch (mCurrentError)
	{
	case eError_UBuild: case eError_UBuildInv: case eError_SameBuild: case eError_NoBuild:
		clearError(true);
		break;
	default:
		break;
	}
}

void EnginePanel::onClearError(wxCommandEvent& event)
{
	clearError(true);
}

bool EnginePanel::checkBuildDirectories(const bool displayError)
{
	const wxString rockPocketBuildPath = mRockPocketBuildDir->GetPath();
	const wxString unrealBuildPath = mUnrealBuildDir->GetPath();

	if (rockPocketBuildPath.IsEmpty() == false)
	{
		if (unrealBuildPath.IsEmpty() == false)
		{
			//Make sure the rock pocket build directory is valid.
			if (wxDirExists(rockPocketBuildPath) && wxFileExists(rockPocketBuildPath + mBuildTestPath))
			{
				//Make sure the unreal build directory is valid.
				if (wxDirExists(unrealBuildPath) && wxFileExists(unrealBuildPath + mBuildTestPath))
				{
					//Make sure the builds are different.
					if (rockPocketBuildPath == unrealBuildPath)
					{
						if (displayError)
						{
							setError(eError_SameBuild);
						}
						return false;
					}
					return true;
				}
				else
				{
					if (displayError)
					{
						setError(eError_UBuildInv);
					}
					return false;
				}
			}
			else
			{
				if (displayError)
				{
					setError(eError_RBuildInv);
				}
				return false;
			}
		}
		else
		{
			if (displayError)
			{
				setError(eError_UBuild);
			}
			return false;
		}
	}
	else if (unrealBuildPath.IsEmpty() == false)
	{
		if (displayError)
		{
			setError(eError_RBuild);
		}
		return false;
	}
	else
	{
		return true;
	}
}

void EnginePanel::setError(EngineErrors error)
{
	if (mCurrentError != error)
	{
		if (mCurrentError != eError_None)
		{
			clearError(false);
		}

		mCurrentError = error;

		switch (mCurrentError)
		{
		case eError_None:
			clearError(true);
			break;
		case eError_EngVer:
			mErrorText->SetLabel("A custom engine version is needed!");
			mEngineVersionText->SetBackgroundColour(wxColour(255, 200, 200)); mEngineVersionText->Refresh();
			mEngineVersionText->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_EngVerInv:
			mErrorText->SetLabel("The version number " + mEngineVersionText->GetValue() + " is already in use!");
			mEngineVersionText->SetBackgroundColour(wxColour(255, 200, 200)); mEngineVersionText->Refresh();
			mEngineVersionText->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_UnrVer:
			mErrorText->SetLabel("A Unreal Engine version is needed!");
			mUnrealVersionText->SetBackgroundColour(wxColour(255, 200, 200)); mUnrealVersionText->Refresh();
			mUnrealVersionText->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_ChgLog:
			mErrorText->SetLabel("Please write down the changes made for this version!");
			mChangelogText->SetBackgroundColour(wxColour(255, 200, 200)); mChangelogText->Refresh();
			mChangelogText->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_File:
			mErrorText->SetLabel("At least one file context is needed!");
			mFileList->SetBackgroundColour(wxColour(255, 200, 200)); mFileList->Refresh();
			mFileList->Bind(EVT_CUSTOM_FILE_ADD, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_RBuild:
			mErrorText->SetLabel("To use the file context helper, both builds needs to be located!");
			mRockPocketBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mRockPocketBuildDir->Refresh();
			mRockPocketBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_RBuildInv:
			mErrorText->SetLabel("The Rock Pocket build directory is invalid!");
			mRockPocketBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mRockPocketBuildDir->Refresh();
			mRockPocketBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_UBuild:
			mErrorText->SetLabel("To use the file context helper, both builds needs to be located!");
			mUnrealBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mUnrealBuildDir->Refresh();
			mUnrealBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_UBuildInv:
			mErrorText->SetLabel("The Unreal build directory is invalid!");
			mUnrealBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mUnrealBuildDir->Refresh();
			mUnrealBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_SameBuild:
			mErrorText->SetLabel("Build directories need to be different!");
			mRockPocketBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mRockPocketBuildDir->Refresh();
			mUnrealBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mUnrealBuildDir->Refresh();
			mRockPocketBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			mUnrealBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		case eError_NoBuild:
			mErrorText->SetLabel("No build directories are selected!");
			mRockPocketBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mRockPocketBuildDir->Refresh();
			mUnrealBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mUnrealBuildDir->Refresh();
			mRockPocketBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			mUnrealBuildDir->GetTextCtrl()->Bind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			Layout();
			break;
		}
	}
}

void EnginePanel::clearError(const bool clearText)
{
	if (mCurrentError != eError_None)
	{
		if (clearText)
		{
			mErrorText->SetLabel(wxEmptyString);
		}

		switch (mCurrentError)
		{
		case eError_EngVer: case eError_EngVerInv:
			mEngineVersionText->SetBackgroundColour(wxColour(255, 255, 255)); mEngineVersionText->Refresh();
			mEngineVersionText->Unbind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			break;
		case eError_UnrVer:
			mUnrealVersionText->SetBackgroundColour(wxColour(255, 255, 255)); mUnrealVersionText->Refresh();
			mUnrealVersionText->Unbind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			break;
		case eError_ChgLog:
			mChangelogText->SetBackgroundColour(wxColour(255, 255, 255)); mChangelogText->Refresh();
			mChangelogText->Unbind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			break;
		case eError_File:
			mFileList->SetBackgroundColour(wxColour(255, 255, 255)); mFileList->Refresh();
			mFileList->Unbind(EVT_CUSTOM_FILE_ADD, &EnginePanel::onClearError, this);
			break;
		case eError_RBuild: case eError_RBuildInv:
			mRockPocketBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 255, 255)); mRockPocketBuildDir->Refresh();
			mRockPocketBuildDir->GetTextCtrl()->Unbind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			break;
		case eError_UBuild: case eError_UBuildInv:
			mUnrealBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 255, 255)); mUnrealBuildDir->Refresh();
			mUnrealBuildDir->GetTextCtrl()->Unbind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			break;
		case eError_SameBuild: case eError_NoBuild:
			mRockPocketBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 255, 255)); mRockPocketBuildDir->Refresh();
			mUnrealBuildDir->GetTextCtrl()->SetBackgroundColour(wxColour(255, 255, 255)); mUnrealBuildDir->Refresh();
			mRockPocketBuildDir->GetTextCtrl()->Unbind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			mUnrealBuildDir->GetTextCtrl()->Unbind(wxEVT_TEXT, &EnginePanel::onClearError, this);
			break;
		}

		mCurrentError = eError_None;
	}
}
