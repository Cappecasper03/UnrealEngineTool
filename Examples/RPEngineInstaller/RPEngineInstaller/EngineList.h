#pragma once
#include <wx/listctrl.h>

#include "EngineInfo.h"

wxDECLARE_EVENT(EVT_CUSTOM_ENGINE_SELECTION, wxCommandEvent);

class EngineList : public wxListCtrl
{
public:
	EngineList(wxWindow* parent);
	~EngineList();

	void initilizeItems(const wxVector<EngineInfo>& items);
	void addItem(const EngineInfo& item);
	void removeSelectedItem();
	void updateSelectedItem(const EngineInfo& item);

	int32_t getSelected() const { return mSelectedItem; }
	wxString getSelectedEngineVersion() const;
	EngineInfo getSelectedData() const;
	wxVector<EngineInfo> getAllData() const { return mListData; }

protected:
	virtual wxString OnGetItemText(long item, long column) const override;

private:
	void onItemSelected(wxListEvent& event);
	void onItemDeselected(wxListEvent& event);

	wxVector<EngineInfo> mListData = wxVector<EngineInfo>();

	const int32_t mNoSelectionIndex{ -1 };
	int32_t mSelectedItem{ mNoSelectionIndex };
};

