#pragma once
#include <wx/Dialog.h>

class InfoPanel;

class InfoDialog : public wxDialog
{
public:
	InfoDialog(wxWindow* parent);
	~InfoDialog();

private:
	InfoPanel* mPanel{ nullptr };
};

