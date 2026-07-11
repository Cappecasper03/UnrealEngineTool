#pragma once
#include <wx/panel.h>

#include "EngineInfo.h"

class wxTextCtrl;
class wxChoice;
class wxDirPickerCtrl;
class wxBitmapButton;
class wxListEvent;
class wxStaticText;

class FileList;
class FileDropTarget;

class EnginePanel : public wxPanel
{
public:
	EnginePanel(wxWindow* parent, const wxVector<wxString>& otherVersions);
	EnginePanel(wxWindow* parent, const EngineInfo& engine, const wxVector<wxString>& otherVersions);
	~EnginePanel();

	EngineInfo getEngine() const;

private:
	//Enum for types of errors.
	enum EngineErrors : uint8_t { eError_None, eError_EngVer, eError_EngVerInv, eError_UnrVer, eError_ChgLog, eError_File, eError_RBuild, eError_RBuildInv, eError_UBuild, eError_UBuildInv, eError_SameBuild,  eError_NoBuild };

	void onAddFileButton(wxCommandEvent& event);
	void onEditFileButton(wxCommandEvent& event);
	void onRemoveFileButton(wxCommandEvent& event);

	void onButtonConfirm(wxCommandEvent& event);
	void onButtonCancel(wxCommandEvent& event);

	void onListKeyPressed(wxListEvent& event);
	void onShowListContextMenu(wxListEvent& event);
	void onListContextMenuSelected(wxCommandEvent& event);
	void onListSelection(wxCommandEvent& event);
	void onListDropFailed(wxCommandEvent& event);

	void onRockPocketBuildChanged(wxCommandEvent& event);
	void onUnrealBuildChanged(wxCommandEvent& event);

	void onClearError(wxCommandEvent& event);

	bool checkBuildDirectories(const bool displayError);

	void setError(EngineErrors error);
	void clearError(const bool clearText);

	wxTextCtrl* mEngineVersionText{ nullptr };
	wxChoice* mParentPicker{ nullptr };
	wxTextCtrl* mUnrealVersionText{ nullptr };
	wxTextCtrl* mChangelogText{ nullptr };

	wxDirPickerCtrl* mUnrealDir{ nullptr };

	FileList* mFileList{ nullptr };
	FileDropTarget* mFileDrop{ nullptr };

	wxBitmapButton* mAddFileButton{ nullptr };
	wxBitmapButton* mEditFileButton{ nullptr };
	wxBitmapButton* mRemoveFileButton{ nullptr };

	wxDirPickerCtrl* mRockPocketBuildDir{ nullptr };
	wxDirPickerCtrl* mUnrealBuildDir{ nullptr };

	wxButton* mConfirmButton{ nullptr };
	wxButton* mCancelButton{ nullptr };

	wxStaticText* mErrorText{ nullptr };

	EngineErrors mCurrentError{ eError_None };

	wxVector<wxString> mOtherVersions;

	//What to show for no parent engine.
	const wxString mNoParent{ "None" };
	//Path to test if the build location is valid.
	const wxString mBuildTestPath{ "\\Engine\\Binaries\\Win64\\UnrealEditor-Engine.dll" };
};

