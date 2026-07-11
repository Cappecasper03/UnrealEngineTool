#pragma once
#include <wx/statbmp.h>

class wxTimerEvent;
class wxTimer;

class StatusImage : public wxStaticBitmap
{
public:
	StatusImage(wxWindow* parent);
	~StatusImage();

	void setFrameTarget(uint8_t target);

private:
	void onImageTick(wxTimerEvent& event);
	void onIdleTick(wxTimerEvent& event);

	wxTimer* imageTimer{ nullptr };
	wxTimer* idleTimer{ nullptr };

	uint8_t currentFrame{ 4 };
	uint8_t targetFrame{ 4 };

	uint8_t currentIdle{ 1 };

	const uint32_t updateSpeed{ 80 };
};