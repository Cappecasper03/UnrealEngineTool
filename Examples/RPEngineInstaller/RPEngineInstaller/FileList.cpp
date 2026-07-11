#include "FileList.h"
#include <wx/filename.h>

wxDEFINE_EVENT(EVT_CUSTOM_FILE_SELECTION, wxCommandEvent);
wxDEFINE_EVENT(EVT_CUSTOM_FILE_ADD, wxCommandEvent);
wxDEFINE_EVENT(EVT_CUSTOM_DROP_FAILED, wxCommandEvent);

FileList::FileList(wxWindow* parent) : wxListCtrl(parent, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLC_REPORT | wxLC_VIRTUAL | wxLC_SINGLE_SEL)
{
	SetItemCount(0);

	//Setup columns.
	InsertColumn(0, "File", 0, 132);
	InsertColumn(1, "Custom", 0, 90);
	InsertColumn(2, "Default", 0, 90);

	//Setup bindings.
	this->Bind(wxEVT_LIST_ITEM_SELECTED, &FileList::onItemSelected, this);
	this->Bind(wxEVT_LIST_ITEM_DESELECTED, &FileList::onItemDeselected, this);
}

FileList::~FileList()
{
}

void FileList::initilizeItems(const wxVector<EngineFile>& items)
{
	if (mListData.size() > 0)
	{
		mListData.clear();
	}

	mListData = items;
	//Make sure initilized target paths are absolute.
	for (uint32_t i{ 0 }; i < mListData.size(); i++)
	{
		if (mListData[i].pathCustom.empty() == false)
		{
			mListData[i].pathCustom = wxGetCwd() + mListData[i].pathCustom;
		}
		if (mListData[i].pathDefault.empty() == false)
		{
			mListData[i].pathDefault = wxGetCwd() + mListData[i].pathDefault;
		}
	}
	SetItemCount(mListData.size());
	RefreshItems(0, mListData.size());
}

void FileList::addItem(const EngineFile& item)
{
	mListData.push_back(item);
	SetItemCount(mListData.size());
	RefreshItems(mListData.size() - 1, mListData.size());

	wxCommandEvent event(EVT_CUSTOM_FILE_ADD, GetId());
	ProcessWindowEvent(event);
}

void FileList::removeSelectedItem()
{
	mListData.erase(mListData.begin() + mSelectedItem);
	SetItemState(mSelectedItem, 0, wxLIST_STATE_SELECTED);
	SetItemCount(mListData.size());
	RefreshItems(mSelectedItem, mListData.size());
}

void FileList::updateSelectedItem(const EngineFile& item)
{
	mListData[mSelectedItem] = item;
	RefreshItems(mSelectedItem, mSelectedItem);
}

wxString FileList::getSelectedFileName() const
{
	return getFileName(mListData[mSelectedItem].pathTarget);
}

EngineFile FileList::getSelectedData() const
{
	return mListData[mSelectedItem];
}

wxString FileList::OnGetItemText(long item, long column) const
{
	switch (column)
	{
	case 0:
		return getFileName(mListData[item].pathTarget);
	case 1:
		return mListData[item].pathCustom.empty() ? "No" : "Yes";
	case 2:
		return mListData[item].pathDefault.empty() ? "No" : "Yes";
	default:
		return "ERROR";
	}
}

void FileList::onItemSelected(wxListEvent& event)
{
	//Send an event if there previously was no selection.
	if (mSelectedItem == mNoSelectionIndex)
	{
		wxCommandEvent event(EVT_CUSTOM_FILE_SELECTION, GetId());
		event.SetEventObject(this);
		event.SetInt(1);
		ProcessWindowEvent(event);
	}

	mSelectedItem = event.GetIndex();
}

void FileList::onItemDeselected(wxListEvent& event)
{
	//Send an event if there previously was a selection.
	if (GetSelectedItemCount() == 0 && mSelectedItem != mNoSelectionIndex)
	{
		wxCommandEvent event(EVT_CUSTOM_FILE_SELECTION, GetId());
		event.SetEventObject(this);
		event.SetInt(0);
		ProcessWindowEvent(event);

		mSelectedItem = mNoSelectionIndex;
	}
}

wxString FileList::getFileName(const wxString& filePath) const
{
	wxFileName fileName(filePath);
	return fileName.GetName() + "." + fileName.GetExt();
}
