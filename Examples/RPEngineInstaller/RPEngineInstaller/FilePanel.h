#pragma once
#include <wx/panel.h>

#include "EngineInfo.h"

class wxFilePickerCtrl;
class wxComboBox;
class wxStaticText;

class FilePanel : wxPanel
{
public:
	FilePanel(wxWindow* parent, const wxString customBuild, const wxString defaultBuild);
	FilePanel(wxWindow* parent, const EngineFile& file, const wxString customBuild, const wxString defaultBuild);
	~FilePanel();

	EngineFile getFileContext() const;

private:
	//Enum for types of errors.
	enum FileErrors : uint8_t { eError_None, eError_Empty, eError_CustRead, eError_CustInv, eError_DefRead, eError_DefInv, eError_Targ, eError_TargInv, eError_Hlp, eError_HlpInv, eError_HlpBad };

	void onButtonHelper(wxCommandEvent& event);

	void onButtonConfirm(wxCommandEvent& event);
	void onButtonCancel(wxCommandEvent& event);

	void onClearError(wxCommandEvent& event);

	void setError(FileErrors error);
	void clearError(const bool clearText);

	bool isHelperAvailable() const;

	wxFilePickerCtrl* mHelperFilePicker{ nullptr };
	wxButton* mHelperButton{ nullptr };

	wxFilePickerCtrl* mCustomFilePicker{ nullptr };
	wxFilePickerCtrl* mDefaultFilePicker{ nullptr };
	wxComboBox* mTargetPathCombo{ nullptr };

	wxButton* mConfirmButton{ nullptr };
	wxButton* mCancelButton{ nullptr };

	wxStaticText* mErrorText{ nullptr };

	FileErrors mCurrentError{ eError_None };

	wxString mCustomBuild{ wxEmptyString };
	wxString mDefaultBuild{ wxEmptyString };
};

