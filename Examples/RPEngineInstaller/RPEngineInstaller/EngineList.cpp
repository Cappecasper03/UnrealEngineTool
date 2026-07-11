#include "EngineList.h"

wxDEFINE_EVENT(EVT_CUSTOM_ENGINE_SELECTION, wxCommandEvent);

EngineList::EngineList(wxWindow* parent) : wxListCtrl(parent, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLC_REPORT | wxLC_VIRTUAL | wxLC_SINGLE_SEL)
{
	SetItemCount(0);

	//Setup columns.
	InsertColumn(0, "Version", 0, 70);
	InsertColumn(1, "Unreal", 0, 70);
	InsertColumn(2, "Files", 0, 70);

	//Setup bindings.
	this->Bind(wxEVT_LIST_ITEM_SELECTED, &EngineList::onItemSelected, this);
	this->Bind(wxEVT_LIST_ITEM_DESELECTED, &EngineList::onItemDeselected, this);
}

EngineList::~EngineList()
{
}

void EngineList::initilizeItems(const wxVector<EngineInfo>& items)
{
	if (mListData.size() > 0)
	{
		mListData.clear();
	}
	
	mListData = items;
	SetItemCount(mListData.size());
	RefreshItems(0, mListData.size());
}

void EngineList::addItem(const EngineInfo& item)
{
	mListData.push_back(item);
	SetItemCount(mListData.size());
	RefreshItems(mListData.size() - 1, mListData.size());
}

void EngineList::removeSelectedItem()
{
	mListData.erase(mListData.begin() + mSelectedItem);
	SetItemState(mSelectedItem, 0, wxLIST_STATE_SELECTED);
	SetItemCount(mListData.size());
	RefreshItems(mSelectedItem, mListData.size());
}

void EngineList::updateSelectedItem(const EngineInfo& item)
{
	mListData[mSelectedItem] = item;
	RefreshItems(mSelectedItem, mSelectedItem);
}

wxString EngineList::getSelectedEngineVersion() const
{
	return mListData[mSelectedItem].engineVersion;
}

EngineInfo EngineList::getSelectedData() const
{
	return mListData[mSelectedItem];
}

wxString EngineList::OnGetItemText(long item, long column) const
{
	switch (column)
	{
	case 0:
		return mListData[item].engineVersion;
	case 1:
		return mListData[item].unrealVersion;
	case 2:
		return wxString::Format(wxT("%i"), mListData[item].files.size());
	default:
		return "ERROR";
	}
}

void EngineList::onItemSelected(wxListEvent& event)
{
	//Send an event if there previously was no selection.
	if (mSelectedItem == mNoSelectionIndex)
	{
		wxCommandEvent event(EVT_CUSTOM_ENGINE_SELECTION, GetId());
		event.SetEventObject(this);
		event.SetInt(1);
		ProcessWindowEvent(event);
	}

	mSelectedItem = event.GetIndex();
}

void EngineList::onItemDeselected(wxListEvent& event)
{
	//Send an event if there previously was a selection.
	if (GetSelectedItemCount() == 0 && mSelectedItem != mNoSelectionIndex)
	{
		wxCommandEvent event(EVT_CUSTOM_ENGINE_SELECTION, GetId());
		event.SetEventObject(this);
		event.SetInt(0);
		ProcessWindowEvent(event);

		mSelectedItem = mNoSelectionIndex;
	}
}
