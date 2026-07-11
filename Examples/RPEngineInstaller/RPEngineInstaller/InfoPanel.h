#pragma once
#include <wx/panel.h>
#include <wx/richtext/richtextbuffer.h>

class wxButton;
class wxRichTextCtrl;
class wxStaticBitmap;
class wxStaticText;
class wxTimer;

class wxTimerEvent;

class InfoPanel : wxPanel
{
public:
	InfoPanel(wxWindow* parent);
	~InfoPanel();

private:
	void onButtonInstall(wxCommandEvent& event);
	void onButtonSettings(wxCommandEvent& event);
	void onButtonCoding(wxCommandEvent& event);

	void onTextURL(wxTextUrlEvent& event);

	//0 = installation, 1 = settings, 2 = coding.
	void setCategory(uint8_t category);

	void showClipboardMessage();
	void hideClipboardMessage(wxTimerEvent& event);

	wxButton* mInstallButton{ nullptr };
	wxButton* mSettingsButton{ nullptr };
	wxButton* mCodingButton{ nullptr };

	wxStaticText* mCopyText{ nullptr };
	wxStaticBitmap* mCopyImage{ nullptr };

	wxRichTextCtrl* mInfoText{ nullptr };

	//Timer for how long we are going to show the clipboard.
	wxTimer* mCopyTimer{ nullptr };

	wxRichTextAttr mNormalAttr;
	wxRichTextAttr mHeaderAttr;
	wxRichTextAttr mHighlightAttr;
	wxRichTextAttr mCaptionAttr;
	wxRichTextAttr mLinkAttr;
	wxRichTextAttr mCodeAttr;

	//0 = installation, 1 = settings, 2 = coding.
	uint8_t mCurrentCategory{ 0 };
};