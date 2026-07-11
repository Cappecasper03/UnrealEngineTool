#pragma once
#include <wx/listctrl.h>

#include "EngineInfo.h"

wxDECLARE_EVENT(EVT_CUSTOM_FILE_SELECTION, wxCommandEvent);
wxDECLARE_EVENT(EVT_CUSTOM_FILE_ADD, wxCommandEvent);
wxDECLARE_EVENT(EVT_CUSTOM_DROP_FAILED, wxCommandEvent);

class FileList : public wxListCtrl
{
public:
	FileList(wxWindow* parent);
	~FileList();

	void initilizeItems(const wxVector<EngineFile>& items);
	void addItem(const EngineFile& item);
	void removeSelectedItem();
	void updateSelectedItem(const EngineFile& item);

	int32_t getSelected() const { return mSelectedItem; }
	wxString getSelectedFileName() const;
	EngineFile getSelectedData() const;
	wxVector<EngineFile> getAllData() const { return mListData; }

protected:
	virtual wxString OnGetItemText(long item, long column) const override;

private:
	void onItemSelected(wxListEvent& event);
	void onItemDeselected(wxListEvent& event);

	wxString getFileName(const wxString& filePath) const;

	wxVector<EngineFile> mListData = wxVector<EngineFile>();

	const int32_t mNoSelectionIndex{ -1 };
	int32_t mSelectedItem{ mNoSelectionIndex };
};

