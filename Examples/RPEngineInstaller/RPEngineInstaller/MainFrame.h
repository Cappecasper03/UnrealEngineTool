#pragma once
#include <wx/frame.h>

class MainPanel;

class MainFrame : public wxFrame
{
public:
	MainFrame();
	~MainFrame();

private:
	MainPanel* mPanel{ nullptr };
};
