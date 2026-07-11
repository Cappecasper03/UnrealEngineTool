#include "MainFrame.h"
#include "MainPanel.h"

MainFrame::MainFrame() : wxFrame(nullptr, wxID_ANY, "Rock Pocket Engine Installer", wxDefaultPosition, wxSize(550, 355), wxMINIMIZE_BOX | wxCLOSE_BOX | wxCAPTION | wxCLIP_CHILDREN)
{
	Centre();
	SetMinSize(wxSize(550, 355));
	SetMaxSize(wxSize(550, 355));

	//Sets a program icon
	wxIconBundle iconBundle;
	iconBundle.AddIcon(wxIcon("IDA_ICON", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	iconBundle.AddIcon(wxIcon("IDA_ICON", wxBITMAP_TYPE_ICO_RESOURCE, 32, 32));
	SetIcons(iconBundle);

	mPanel = new MainPanel(this);
}

MainFrame::~MainFrame()
{
}