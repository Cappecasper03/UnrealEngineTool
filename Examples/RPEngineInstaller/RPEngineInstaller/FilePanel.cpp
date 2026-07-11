#include "FilePanel.h"

#include <wx/filepicker.h>
#include <wx/combobox.h>
#include <wx/sizer.h>
#include <wx/stattext.h>
#include <wx/statline.h>

#include <wx/log.h>
#include <wx/filefn.h> 
#include <wx/filename.h>

FilePanel::FilePanel(wxWindow* parent, const wxString customBuild, const wxString defaultBuild) : wxPanel(parent, -1, wxDefaultPosition, wxDefaultSize, wxNO_BORDER), mCustomBuild(customBuild), mDefaultBuild(defaultBuild)
{
	if (isHelperAvailable())
	{
		//Setup file picker for helper.
		mHelperFilePicker = new wxFilePickerCtrl(this, wxID_ANY, wxEmptyString, "Select Engine File", wxFileSelectorDefaultWildcardStr, wxDefaultPosition, wxDefaultSize);
		mHelperFilePicker->GetTextCtrl()->SetHint("Select a engine file.");
		mHelperFilePicker->SetToolTip("Select a engine file for autofill. Can be from either the custom or default engine build.");

		//Setup helper button.
		mHelperButton = new wxButton(this, wxID_ANY, "Autofill", wxDefaultPosition, wxDefaultSize);
		mHelperButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &FilePanel::onButtonHelper, this);
		mHelperButton->SetToolTip("Populate all the fields based on the engine file.");
	}

	//Setup file picker for custom engine file.
	mCustomFilePicker = new wxFilePickerCtrl(this, wxID_ANY, wxEmptyString, "Custom Engine File", wxFileSelectorDefaultWildcardStr, wxDefaultPosition, wxDefaultSize);
	mCustomFilePicker->GetTextCtrl()->SetHint("Select the custom engine file.");
	mCustomFilePicker->SetToolTip("Select the custom engine file.");

	//Setup file picker for default engine file.
	mDefaultFilePicker = new wxFilePickerCtrl(this, wxID_ANY, wxEmptyString, "Default Engine File", wxFileSelectorDefaultWildcardStr, wxDefaultPosition, wxDefaultSize);
	mDefaultFilePicker->GetTextCtrl()->SetHint("Select the default engine file.");
	mDefaultFilePicker->SetToolTip("Select the default engine file.");

	//Setup target path as combo box so we can add a few common paths in the dropdown.
	wxArrayString targetPathExamples;
	targetPathExamples.Add("\\Engine\\Binaries\\Win64\\");
	targetPathExamples.Add("\\Engine\\Source\\Runtime\\");
	targetPathExamples.Add("\\Engine\\Source\\Runtime\\Engine\\Private\\");
	targetPathExamples.Add("\\Engine\\Source\\Runtime\\Engine\\Public\\");
	targetPathExamples.Add("\\Engine\\Intermediate\\Build\\Win64\\UnrealEditor\\Inc\\Engine\\UHT\\");
	targetPathExamples.Add("\\Engine\\Intermediate\\Build\\Win64\\x64\\UnrealEditor\\Development\\Engine\\");
	mTargetPathCombo = new wxComboBox(this, wxID_ANY, targetPathExamples[0], wxDefaultPosition, wxDefaultSize, targetPathExamples);
	mTargetPathCombo->SetHint("Select the target location for the files.");
	mTargetPathCombo->SetToolTip("Set the relative path from the engine where this file belong. For example, the target path of Actor.cpp is \\Engine\\Source\\Runtime\\Engine\\Private\\Actor.cpp.");

	//Setup exit buttons.
	mConfirmButton = new wxButton(this, wxID_ANY, "Confirm", wxDefaultPosition, wxDefaultSize);
	mConfirmButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &FilePanel::onButtonConfirm, this);
	mConfirmButton->SetToolTip("Save file context and exit.");

	mCancelButton = new wxButton(this, wxID_ANY, "Cancel", wxDefaultPosition, wxDefaultSize);
	mCancelButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &FilePanel::onButtonCancel, this);
	mCancelButton->SetToolTip("Exit without saving.");

	//Setup error text.
	mErrorText = new wxStaticText(this, wxID_ANY, wxEmptyString, wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL);
	mErrorText->SetForegroundColour(wxColor(*wxRED));

	//Setup sizers.
	wxBoxSizer* mainBoxV = new wxBoxSizer(wxVERTICAL);
	wxBoxSizer* exitButtonsBoxH = new wxBoxSizer(wxHORIZONTAL);

	if (isHelperAvailable())
	{
		mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Engine File (Auto):", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
		mainBoxV->Add(mHelperFilePicker, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
		mainBoxV->Add(0, 5);
		mainBoxV->Add(mHelperButton, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
		mainBoxV->Add(new wxStaticLine(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLI_HORIZONTAL), 0, wxEXPAND | wxUP | wxLEFT | wxRIGHT, 5);
	}

	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Rock Pocket Engine File:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
	mainBoxV->Add(mCustomFilePicker, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);

	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Unreal Engine File:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxALL, 5);
	mainBoxV->Add(mDefaultFilePicker, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(new wxStaticLine(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLI_HORIZONTAL), 0, wxEXPAND | wxALL, 5);

	mainBoxV->Add(new wxStaticText(this, wxID_ANY, "Target Path:", wxDefaultPosition, wxDefaultSize, wxALIGN_CENTRE_HORIZONTAL), 0, wxEXPAND | wxLEFT | wxBOTTOM | wxRIGHT, 5);
	mainBoxV->Add(mTargetPathCombo, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(new wxStaticLine(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLI_HORIZONTAL), 0, wxEXPAND | wxALL, 5);

	mainBoxV->Add(mErrorText, 0, wxCENTRE | wxLEFT | wxBOTTOM | wxRIGHT, 5);
	exitButtonsBoxH->Add(mConfirmButton, 1, wxEXPAND);
	exitButtonsBoxH->Add(mCancelButton, 1, wxEXPAND | wxLEFT, 10);
	mainBoxV->Add(exitButtonsBoxH, 0, wxEXPAND | wxLEFT | wxRIGHT, 10);

	this->SetSizer(mainBoxV);
}

FilePanel::FilePanel(wxWindow* parent, const EngineFile& file, const wxString customBuild, const wxString defaultBuild) : FilePanel(parent, customBuild, defaultBuild)
{
	mCustomFilePicker->SetPath(file.pathCustom);
	mDefaultFilePicker->SetPath(file.pathDefault);
	mTargetPathCombo->SetValue(file.pathTarget);
}

FilePanel::~FilePanel()
{
}

EngineFile FilePanel::getFileContext() const
{
	EngineFile file;
	file.pathCustom = mCustomFilePicker->GetPath();
	file.pathDefault = mDefaultFilePicker->GetPath();
	file.pathTarget = mTargetPathCombo->GetValue();
	return file;
}

void FilePanel::onButtonHelper(wxCommandEvent& event)
{
	const wxString helperPath = mHelperFilePicker->GetPath();

	//Make sure the file is valid,
	if (helperPath.empty())
	{
		setError(eError_Hlp);
	}
	else if (wxFileExists(helperPath))
	{
		clearError(true);

		//Make sure the helper file is part of a build directory.
		if (helperPath.starts_with(mCustomBuild))
		{
			const wxString helperRelPath = helperPath.Mid(mCustomBuild.length());

			mCustomFilePicker->SetPath(mCustomBuild + helperRelPath);
			mDefaultFilePicker->SetPath(mDefaultBuild + helperRelPath);
			mTargetPathCombo->SetValue(helperRelPath);
		}
		else if (helperPath.starts_with(mDefaultBuild))
		{
			const wxString helperRelPath = helperPath.Mid(mDefaultBuild.length());

			mCustomFilePicker->SetPath(mCustomBuild + helperRelPath);
			mDefaultFilePicker->SetPath(mDefaultBuild + helperRelPath);
			mTargetPathCombo->SetValue(helperRelPath);
		}
		else
		{
			setError(eError_HlpBad);
		}
	}
	else
	{
		setError(eError_HlpInv);
	}
}

void FilePanel::onButtonConfirm(wxCommandEvent& event)
{
	wxLogNull errorSuppression;

	//Make sure the custom file is valid and can be read.
	const wxString customFilePath = mCustomFilePicker->GetPath();
	if (customFilePath.empty() == false)
	{
		if (wxFileExists(customFilePath))
		{
			if (wxIsReadable(customFilePath) == false)
			{
				setError(eError_CustRead);
				errorSuppression.~wxLogNull();
				return;
			}
		}
		else
		{
			setError(eError_CustInv);
			errorSuppression.~wxLogNull();
			return;
		}
	}

	//Make sure the default file is valid and can be read.
	const wxString defaultFilePath = mDefaultFilePicker->GetPath();
	if (defaultFilePath.empty() == false)
	{
		if (wxFileExists(defaultFilePath))
		{
			if (wxIsReadable(defaultFilePath) == false)
			{
				setError(eError_DefRead);
				errorSuppression.~wxLogNull();
				return;
			}
		}
		else
		{
			setError(eError_DefInv);
			errorSuppression.~wxLogNull();
			return;
		}
	}

	//Make sure the target path is valid.
	const wxString targetFilePath = mTargetPathCombo->GetValue();
	if (targetFilePath.empty())
	{
		setError(eError_Targ);
		errorSuppression.~wxLogNull();
		return;
	}
	else
	{
		wxFileName fileName("C:\\Program Files\\Epic Games\\UE_5.0" + targetFilePath);
		if (!fileName.IsOk() || !fileName.HasName())
		{
			setError(eError_TargInv);
			errorSuppression.~wxLogNull();
			return;
		}
	}

	errorSuppression.~wxLogNull();

	static_cast<wxDialog*>(GetParent())->EndModal(wxID_OK);
}

void FilePanel::onButtonCancel(wxCommandEvent& event)
{
	static_cast<wxDialog*>(GetParent())->EndModal(wxID_CANCEL);
}

void FilePanel::onClearError(wxCommandEvent& event)
{
	clearError(true);
}

void FilePanel::setError(FileErrors error)
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
		case eError_CustRead:
			mErrorText->SetLabel("Can't read file!");
			mCustomFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mCustomFilePicker->Refresh();
			mCustomFilePicker->GetTextCtrl()->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mCustomFilePicker->Bind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			Layout();
			break;
		case eError_CustInv:
			mErrorText->SetLabel("File does not exist!");
			mCustomFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mCustomFilePicker->Refresh();
			mCustomFilePicker->GetTextCtrl()->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mCustomFilePicker->Bind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			Layout();
			break;
		case eError_DefRead:
			mErrorText->SetLabel("Can't read file!");
			mDefaultFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mDefaultFilePicker->Refresh();
			mDefaultFilePicker->GetTextCtrl()->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mDefaultFilePicker->Bind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			Layout();
			break;
		case eError_DefInv:
			mErrorText->SetLabel("File does not exist!");
			mDefaultFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mDefaultFilePicker->Refresh();
			mDefaultFilePicker->GetTextCtrl()->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mDefaultFilePicker->Bind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			Layout();
			break;
		case eError_Targ:
			mErrorText->SetLabel("A target path is needed!");
			mTargetPathCombo->SetBackgroundColour(wxColour(255, 200, 200)); mTargetPathCombo->Refresh();
			mTargetPathCombo->Bind(wxEVT_COMBOBOX, &FilePanel::onClearError, this);
			mTargetPathCombo->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			Layout();
			break;
		case eError_TargInv:
			mErrorText->SetLabel("The target path is invalid!");
			mTargetPathCombo->SetBackgroundColour(wxColour(255, 200, 200)); mTargetPathCombo->Refresh();
			mTargetPathCombo->Bind(wxEVT_COMBOBOX, &FilePanel::onClearError, this);
			mTargetPathCombo->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			Layout();
			break;
		case eError_Hlp:
			mErrorText->SetLabel("No file selected!");
			mHelperFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mHelperFilePicker->Refresh();
			mHelperFilePicker->GetTextCtrl()->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mHelperFilePicker->Bind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			Layout();
			break;
		case eError_HlpInv:
			mErrorText->SetLabel("File does not exist!");
			mHelperFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mHelperFilePicker->Refresh();
			mHelperFilePicker->GetTextCtrl()->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mHelperFilePicker->Bind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			Layout();
			break;
		case eError_HlpBad:
			mErrorText->SetLabel("The file is not part of the build directories!");
			mHelperFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 200, 200)); mHelperFilePicker->Refresh();
			mHelperFilePicker->GetTextCtrl()->Bind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mHelperFilePicker->Bind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			Layout();
			break;
		}
	}
}

void FilePanel::clearError(const bool clearText)
{
	if (mCurrentError != eError_None)
	{
		if (clearText)
		{
			mErrorText->SetLabel(wxEmptyString);
		}

		switch (mCurrentError)
		{
		case eError_None:
			clearError(true);
			break;
		case eError_CustRead: case eError_CustInv:
			mCustomFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 255, 255)); mCustomFilePicker->Refresh();
			mCustomFilePicker->GetTextCtrl()->Unbind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mCustomFilePicker->Unbind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			break;
		case eError_DefRead: case eError_DefInv:
			mDefaultFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 255, 255)); mDefaultFilePicker->Refresh();
			mDefaultFilePicker->GetTextCtrl()->Unbind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mDefaultFilePicker->Unbind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			break;
		case eError_Targ: case eError_TargInv:
			mTargetPathCombo->SetBackgroundColour(wxColour(255, 255, 255)); mTargetPathCombo->Refresh();
			mTargetPathCombo->Unbind(wxEVT_COMBOBOX, &FilePanel::onClearError, this);
			mTargetPathCombo->Unbind(wxEVT_TEXT, &FilePanel::onClearError, this);
			break;
		case eError_Hlp: case eError_HlpInv: case eError_HlpBad:
			mHelperFilePicker->GetTextCtrl()->SetBackgroundColour(wxColour(255, 255, 255)); mHelperFilePicker->Refresh();
			mHelperFilePicker->GetTextCtrl()->Unbind(wxEVT_TEXT, &FilePanel::onClearError, this);
			mHelperFilePicker->Unbind(wxEVT_FILEPICKER_CHANGED, &FilePanel::onClearError, this);
			break;
		}

		mCurrentError = eError_None;
	}
}

bool FilePanel::isHelperAvailable() const
{
	if (mCustomBuild.empty() || mDefaultBuild.empty())
	{
		return false;
	}
	else
	{
		return true;
	}
}
