#include "StatusImage.h"

#include <wx/timer.h>

StatusImage::StatusImage(wxWindow* parent) : wxStaticBitmap(parent, wxID_ANY, wxIcon("IDI_ANIM4", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48), wxDefaultPosition, wxSize(48, 48))
{
	int32_t imageTimerId = wxNewId();
	int32_t idleTimerId = wxNewId();

	imageTimer = new wxTimer(this, imageTimerId);
	Connect(imageTimerId, wxEVT_TIMER, wxTimerEventHandler(StatusImage::onImageTick));

	idleTimer = new wxTimer(this, idleTimerId);
	Connect(idleTimerId, wxEVT_TIMER, wxTimerEventHandler(StatusImage::onIdleTick));
	idleTimer->Start(updateSpeed);
}

StatusImage::~StatusImage()
{
	if (imageTimer->IsRunning())
	{
		imageTimer->Stop();
	}

	if (idleTimer->IsRunning())
	{
		idleTimer->Stop();
	}
}

void StatusImage::setFrameTarget(uint8_t target)
{
	if (targetFrame != target && currentFrame != target)
	{
		targetFrame = target;
		if (imageTimer->IsRunning() == false)
		{
			currentIdle = 1;
			idleTimer->Stop();
			imageTimer->Start(updateSpeed);
		}
	}
}

void StatusImage::onImageTick(wxTimerEvent& event)
{
	if (currentFrame != targetFrame)
	{
		if (currentFrame < targetFrame)
		{
			currentFrame++;
		}
		else
		{
			currentFrame--;
		}

		switch (currentFrame)
		{
		case 0:
			SetBitmap(wxIcon("IDI_ANIM0", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 1:
			SetBitmap(wxIcon("IDI_ANIM1", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 2:
			SetBitmap(wxIcon("IDI_ANIM2", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 3:
			SetBitmap(wxIcon("IDI_ANIM3", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 4:
			SetBitmap(wxIcon("IDI_ANIM4", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 5:
			SetBitmap(wxIcon("IDI_ANIM5", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 6:
			SetBitmap(wxIcon("IDI_ANIM6", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 7:
			SetBitmap(wxIcon("IDI_ANIM7", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 8:
			SetBitmap(wxIcon("IDI_ANIM8", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		default:
			break;
		}

		if (currentFrame == targetFrame)
		{
			imageTimer->Stop();
			idleTimer->Start(updateSpeed);
		}
	}
	else
	{
		imageTimer->Stop();
		idleTimer->Start(updateSpeed);
	}
}

void StatusImage::onIdleTick(wxTimerEvent& event)
{
	switch (targetFrame)
	{
	case 0:
		switch (currentIdle)
		{
		case 0:
			SetBitmap(wxIcon("IDI_ANIM0", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 21: case 23:
			SetBitmap(wxIcon("IDI_ANIM9", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 22:
			SetBitmap(wxIcon("IDI_ANIM10", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		}
		break;
	case 4:
		switch (currentIdle)
		{
		case 0:
			SetBitmap(wxIcon("IDI_ANIM4", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 21: case 23:
			SetBitmap(wxIcon("IDI_ANIM11", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 22:
			SetBitmap(wxIcon("IDI_ANIM12", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		}
		break;
	case 8:
		switch (currentIdle)
		{
		case 0:
			SetBitmap(wxIcon("IDI_ANIM8", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 21: case 23:
			SetBitmap(wxIcon("IDI_ANIM13", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		case 22:
			SetBitmap(wxIcon("IDI_ANIM14", wxBITMAP_TYPE_ICO_RESOURCE, 48, 48));
			break;
		}
		break;
	}

	if (currentIdle >= 23)
	{
		currentIdle = 0;
	}
	else
	{
		currentIdle++;
	}
}
