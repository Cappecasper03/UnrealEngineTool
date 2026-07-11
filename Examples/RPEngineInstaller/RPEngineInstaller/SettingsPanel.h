#pragma once
#include <wx/panel.h>

#include "EngineInfo.h"

class EngineList;
class wxBitmapButton;
class wxListEvent;

class SettingsPanel : wxPanel
{
public:
	SettingsPanel(wxWindow* parent, const wxVector<EngineInfo>& engines);
	~SettingsPanel();

	wxVector<EngineInfo>& getEngines() const { return mEngines; }

private:
	void onButtonAdd(wxCommandEvent& event);
	void onButtonEdit(wxCommandEvent& event);
	void onButtonRemove(wxCommandEvent& event);

	void onButtonSave(wxCommandEvent& event);
	void onButtonCancel(wxCommandEvent& event);

	void onListKeyPressed(wxListEvent& event);
	void onShowListContextMenu(wxListEvent& event);
	void onListContextMenuSelected(wxCommandEvent& event);
	void onListSelection(wxCommandEvent& event);

	EngineList* mEngineList{ nullptr };

	wxBitmapButton* mAddButton{ nullptr };
	wxBitmapButton* mEditButton{ nullptr };
	wxBitmapButton* mRemoveButton{ nullptr };

	wxButton* mSaveButton{ nullptr };
	wxButton* mCancelButton{ nullptr };

	mutable wxVector<EngineInfo> mEngines;
};

