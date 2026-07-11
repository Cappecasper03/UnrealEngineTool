#include "InfoPanel.h"

#include <wx/button.h>
#include <wx/richtext/richtextctrl.h>
#include <wx/statline.h>
#include <wx/sizer.h>
#include <wx/stattext.h>
#include <wx/statbmp.h>

#include <wx/timer.h>
#include <wx/icon.h>
#include <wx/clipbrd.h>

InfoPanel::InfoPanel(wxWindow* parent) : wxPanel(parent, -1, wxDefaultPosition, wxDefaultSize, wxNO_BORDER)
{
	//Setup category buttons.
	mInstallButton = new wxButton(this, wxID_ANY, "Engine Installation", wxDefaultPosition, wxSize(130, 24));
	mInstallButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &InfoPanel::onButtonInstall, this);
	mInstallButton->SetBitmap(wxIcon("IDI_LIGHT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mInstallButton->SetBitmapPressed(wxIcon("IDI_LIGHT2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mInstallButton->SetBitmapDisabled(wxIcon("IDI_LIGHT2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));

	mSettingsButton = new wxButton(this, wxID_ANY, "Engine Settings", wxDefaultPosition, wxSize(130, 24));
	mSettingsButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &InfoPanel::onButtonSettings, this);
	mSettingsButton->SetBitmap(wxIcon("IDI_LIGHT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mSettingsButton->SetBitmapPressed(wxIcon("IDI_LIGHT2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mSettingsButton->SetBitmapDisabled(wxIcon("IDI_LIGHT2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));

	mCodingButton = new wxButton(this, wxID_ANY, "Engine Coding", wxDefaultPosition, wxSize(130, 24));
	mCodingButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, &InfoPanel::onButtonCoding, this);
	mCodingButton->SetBitmap(wxIcon("IDI_LIGHT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mCodingButton->SetBitmapPressed(wxIcon("IDI_LIGHT2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mCodingButton->SetBitmapDisabled(wxIcon("IDI_LIGHT2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));

	mCopyImage = new wxStaticBitmap(this, wxID_ANY, wxIcon("IDI_CLIP1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(16, 16));
	mCopyImage->Show(false);
	mCopyText = new wxStaticText(this, wxID_ANY, "Copied to Clipboard", wxDefaultPosition, wxDefaultSize);
	mCopyText->Show(false);
	mCopyTimer = new wxTimer(this, wxID_ANY);
	Connect(wxEVT_TIMER, wxTimerEventHandler(InfoPanel::hideClipboardMessage));

	//Setup text and text styles.
	mInfoText = new wxRichTextCtrl(this, wxID_ANY, wxEmptyString, wxDefaultPosition, wxDefaultSize, wxRE_MULTILINE | wxRE_READONLY);
	mInfoText->SetEditable(false);
	mInfoText->Bind(wxEVT_TEXT_URL, &InfoPanel::onTextURL, this);

	mNormalAttr.SetTextColour(*wxBLACK);
	mNormalAttr.SetFont(*wxNORMAL_FONT);
	mNormalAttr.SetLineSpacing(6);
	mHeaderAttr.SetTextColour(*wxBLACK);
	mHeaderAttr.SetFont(wxSWISS_FONT->Bold());
	mHeaderAttr.SetLineSpacing(6);
	mHighlightAttr.SetTextColour(*wxBLUE);
	mHighlightAttr.SetFont(*wxNORMAL_FONT);
	mHighlightAttr.SetLineSpacing(6);
	mCaptionAttr.SetTextColour(*wxLIGHT_GREY);
	mCaptionAttr.SetFont(*wxSMALL_FONT);
	mCaptionAttr.SetLineSpacing(6);
	mLinkAttr.SetTextColour(*wxBLUE);
	mLinkAttr.SetFont(*wxNORMAL_FONT);
	mLinkAttr.SetFontUnderlined(true);
	mLinkAttr.SetLineSpacing(6);
	mCodeAttr.SetTextColour(wxColour(0,150,0));
	mCodeAttr.SetFont(*wxNORMAL_FONT);
	mCodeAttr.SetLineSpacing(6);

	//Setup Sizers
	wxBoxSizer* mainBoxV = new wxBoxSizer(wxVERTICAL);
	wxBoxSizer* buttonsBoxH = new wxBoxSizer(wxHORIZONTAL);

	buttonsBoxH->Add(mInstallButton, 0);
	buttonsBoxH->Add(mSettingsButton, 0, wxLEFT, 5);
	buttonsBoxH->Add(mCodingButton, 0, wxLEFT, 5);
	buttonsBoxH->AddStretchSpacer(1);
	buttonsBoxH->Add(mCopyImage, 0, wxLEFT | wxCENTRE, 5);
	buttonsBoxH->Add(mCopyText, 0, wxCENTRE);
	mainBoxV->Add(buttonsBoxH, 0, wxEXPAND | wxLEFT | wxRIGHT | wxUP, 10);

	mainBoxV->Add(0, 2);
	mainBoxV->Add(new wxStaticLine(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLI_HORIZONTAL), 0, wxEXPAND | wxLEFT | wxRIGHT, 10);
	mainBoxV->Add(0, 2);

	mainBoxV->Add(mInfoText, 1, wxEXPAND | wxLEFT | wxRIGHT | wxDOWN, 10);

	this->SetSizer(mainBoxV);

	//Set installation as default.
	setCategory(0);
}

InfoPanel::~InfoPanel()
{
	if (mCopyTimer->IsRunning())
	{
		mCopyTimer->Stop();
	}
}

void InfoPanel::onButtonInstall(wxCommandEvent& event)
{
	setCategory(0);
}

void InfoPanel::onButtonSettings(wxCommandEvent& event)
{
	setCategory(1);
}

void InfoPanel::onButtonCoding(wxCommandEvent& event)
{
	setCategory(2);
}

void InfoPanel::onTextURL(wxTextUrlEvent& event)
{
	wxString text = event.GetString();
	//Open link in browser.
	if (text.starts_with("LNK:"))
	{
		wxLaunchDefaultBrowser(text.Mid(4));
	}
	//Copy text to clipboard.
	else if (text.starts_with("CPY:"))
	{
		wxTheClipboard->Open();
		wxTheClipboard->Clear();
		wxTheClipboard->SetData(new wxTextDataObject(text.Mid(4)));
		wxTheClipboard->Flush();
		wxTheClipboard->Close();

		showClipboardMessage();
	}
}

void InfoPanel::setCategory(uint8_t category)
{
	switch (mCurrentCategory)
	{
	case 0:
		mInstallButton->Enable(true);
		break;
	case 1:
		mSettingsButton->Enable(true);
		break;
	case 2:
		mCodingButton->Enable(true);
		break;
	default:
		break;
	}

	mCurrentCategory = category;
	mInfoText->SelectNone();
	mInfoText->Clear();
	mInfoText->SetDefaultStyle(mNormalAttr);

	switch (mCurrentCategory)
	{
	case 0:
		mInstallButton->Enable(false);

		mInfoText->BeginStyle(mHeaderAttr);
		mInfoText->WriteText("Apply custom engine\n");
		mInfoText->EndStyle();
		mInfoText->WriteText("To apply the Rock Pocket Engine build, select the desired engine ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("version");
		mInfoText->EndStyle();
		mInfoText->WriteText(" in the dropdown box.\n");
		mInfoText->WriteText("You will need to have Unreal Engine ");
		mInfoText->BeginURL("LNK:https://www.unrealengine.com/en-US/download");
		mInfoText->BeginStyle(mLinkAttr);
		mInfoText->WriteText("installed");
		mInfoText->EndStyle();
		mInfoText->EndURL();
		mInfoText->WriteText(" on your PC.\n");
		mInfoText->WriteText("Check the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("changelog");
		mInfoText->EndStyle();
		mInfoText->WriteText(" to find what version of Unreal Engine is needed.\n");
		mInfoText->WriteText("Then locate the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Unreal Engine directory");
		mInfoText->EndStyle();
		mInfoText->WriteText(" on your PC\nand press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Rock Pocket Engine button");
		mInfoText->EndStyle();
		mInfoText->WriteText(" to start the installation.\n");
		mInfoText->WriteText("Once done, you will get ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("feedback");
		mInfoText->EndStyle();
		mInfoText->WriteText(" regarding success or failure.\n");
		mInfoText->WriteText("Note that this will replace the installed Unreal Engine build with the Rock Pocket Engine build.\n");

		mInfoText->BeginStyle(mHeaderAttr);
		mInfoText->WriteText("\nApply default engine\n");
		mInfoText->EndStyle();
		mInfoText->WriteText("Reverting back to the default build of Unreal Engine can be done by\nselecting the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("version");
		mInfoText->EndStyle();
		mInfoText->WriteText(" of Rock Pocket Engine that is installed in the dropdown box.\n");
		mInfoText->WriteText("Then locate the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Unreal Engine directory");
		mInfoText->EndStyle();
		mInfoText->WriteText(" you have applied the custom engine to.\n");
		mInfoText->WriteText("Finally press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Default Unreal Engine button");
		mInfoText->EndStyle();
		mInfoText->WriteText(" to revert unreal engine back to default.\n");
		mInfoText->WriteText("Once done, you will get ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("feedback");
		mInfoText->EndStyle();
		mInfoText->WriteText(" regarding success or failure.\n");

		mInfoText->WriteText("\n");
		mInfoText->WriteImage(wxBitmap("IDI_IMGREF1", wxBITMAP_TYPE_PNG_RESOURCE));
		mInfoText->BeginStyle(mCaptionAttr);
		mInfoText->WriteText("\n                              Installation controls.");
		mInfoText->EndStyle();
		break;
	case 1:
		mSettingsButton->Enable(false);

		mInfoText->SetLineHeight(10);
		mInfoText->BeginStyle(mHeaderAttr);
		mInfoText->WriteText("Adding custom engines\n");
		mInfoText->EndStyle();
		mInfoText->WriteText("Press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("settings button ");
		mInfoText->EndStyle();
		mInfoText->WriteImage(wxIcon("IDI_SETTING1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		mInfoText->WriteText(" to show all custom engine entries.\n");
		mInfoText->WriteText("You can press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("add button ");
		mInfoText->EndStyle();
		mInfoText->WriteImage(wxIcon("IDI_ADD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		mInfoText->WriteText(" to create a new entry.\n");
		mInfoText->WriteText("You will need to have a copy of all the engine files that has been added/modified,\nas well as the original unaltered files located on your PC.\n");
		mInfoText->WriteText("Fill in the boxes as told.\n");
		mInfoText->WriteText("If you set a ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("parent version");
		mInfoText->EndStyle();
		mInfoText->WriteText(", this version will inherit all the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("file contexts");
		mInfoText->EndStyle();
		mInfoText->WriteText(" from the parent.\n");
		mInfoText->WriteText("If the parent and child share a file, the child file will always be prioritized.\n");
		mInfoText->WriteText("This works recursively, meaning a parent's parent is also inherited.\n");
		mInfoText->WriteText("Add entries into the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("file context");
		mInfoText->EndStyle();
		mInfoText->WriteText(" by pressing the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("add button ");
		mInfoText->EndStyle();
		mInfoText->WriteImage(wxIcon("IDI_ADD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		mInfoText->WriteText(" under the file context section.\n");
		mInfoText->WriteText("For the file entry you need to locate the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Rock Pocket Engine");
		mInfoText->EndStyle();
		mInfoText->WriteText(" and ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Unreal Engine");
		mInfoText->EndStyle();
		mInfoText->WriteText(" version of the file.\n");
		mInfoText->WriteText("If the file location is only filled in for one of the engines,\nit will mean that the file is exclusive to that engine.\n");
		mInfoText->WriteText("And the file will be removed or added depending on what engine you apply.\n");
		mInfoText->WriteText("The ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("target path");
		mInfoText->EndStyle();
		mInfoText->WriteText(" should be relative to the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("engine directory");
		mInfoText->EndStyle();
		mInfoText->WriteText(" and include the file name and extension.\n");
		mInfoText->WriteText("You will need a file entry for each file you want to apply to the custom engine.\n");
		mInfoText->WriteText("If you have a full build installed for the custom and default engine,\nyou can fill in the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("build directories");
		mInfoText->EndStyle();
		mInfoText->WriteText(" to allow auto populating file entries from one given file.\n");
		mInfoText->WriteText("To do this locate an ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("engine file");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (can be either custom or default), and press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("autofill button");
		mInfoText->EndStyle();
		mInfoText->WriteText(".\n");
		mInfoText->WriteText("With the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("build directories");
		mInfoText->EndStyle();
		mInfoText->WriteText(" selected you can also drag and drop files directly into the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("file context");
		mInfoText->EndStyle();
		mInfoText->WriteText(" list.\n");

		mInfoText->BeginStyle(mHeaderAttr);
		mInfoText->WriteText("\nEditing custom engines\n");
		mInfoText->EndStyle();
		mInfoText->WriteText("Press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("settings button ");
		mInfoText->EndStyle();
		mInfoText->WriteImage(wxIcon("IDI_SETTING1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		mInfoText->WriteText(" to show all custom engine entries.\n");
		mInfoText->WriteText("Select the engine and press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("edit button ");
		mInfoText->EndStyle();
		mInfoText->WriteImage(wxIcon("IDI_EDIT1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		mInfoText->WriteText(" to edit the entry.\n");
		mInfoText->WriteText("Once you are done editing, press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("confirm button");
		mInfoText->EndStyle();
		mInfoText->WriteText(" to apply the changes,\nor ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("cancel");
		mInfoText->EndStyle();
		mInfoText->WriteText(" to discard any changes.\n");
		mInfoText->WriteText("To remove a custom engine, select the engine entry and press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("delete button ");
		mInfoText->EndStyle();
		mInfoText->WriteImage(wxIcon("IDI_DEL1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		mInfoText->WriteText(".\nOnce you are done press the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("save button");
		mInfoText->EndStyle();
		mInfoText->WriteText(" to save the entries, or ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("cancel");
		mInfoText->EndStyle();
		mInfoText->WriteText(" to discard any changes.");
		break;
	case 2:
		mCodingButton->Enable(false);

		mInfoText->BeginStyle(mHeaderAttr);
		mInfoText->WriteText("Setting up a custom engine\n");
		mInfoText->EndStyle();
		mInfoText->WriteText("To create a new custom engine, you first need to\ndownload the Unreal Engine source code from ");
		mInfoText->BeginURL("LNK:https://github.com/EpicGames/UnrealEngine/");
		mInfoText->BeginStyle(mLinkAttr);
		mInfoText->WriteText("github");
		mInfoText->EndStyle();
		mInfoText->EndURL();
		mInfoText->WriteText(".\nSelect the github branch matching the engine version you want to edit.\n");
		mInfoText->WriteText("Once the source code is downloaded, run Setup.bat to install all prerequisites\nfollowed by GenerateProjectFiles.bat to generate the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("project file");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (.sln).\n");
		mInfoText->WriteText("Open the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("project file");
		mInfoText->EndStyle();
		mInfoText->WriteText(" and start coding.\n");
		mInfoText->WriteText("In the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("game target file");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (UnrealGame.Target.cs) you want to add the line ");
		mInfoText->BeginURL("CPY:bUsePCHFiles = false;");
		mInfoText->BeginStyle(mCodeAttr);
		mInfoText->WriteText("bUsePCHFiles = false;");
		mInfoText->EndStyle();
		mInfoText->EndURL();
		mInfoText->WriteText(".\n");
		mInfoText->WriteText("If you want to continue work on an existing engine version on a new build,\nyou can run the installer on the engine source folder too.\n");
		mInfoText->WriteText("To only apply the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("source files");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (.h/.cpp), double right click on the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("status image");
		mInfoText->EndStyle();
		mInfoText->WriteText("\nand select ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Install to Source ");
		mInfoText->EndStyle();
		mInfoText->WriteImage(wxIcon("IDI_CD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		mInfoText->WriteText(".\nRepeat the process with ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Install to Engine ");
		mInfoText->EndStyle();
		mInfoText->WriteImage(wxIcon("IDI_CD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		mInfoText->WriteText(" to go back to default.\n");
		mInfoText->WriteText("You can test the project by compiling and running it from ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("UE5");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("Development Editor");
		mInfoText->EndStyle();
		mInfoText->WriteText(").\n");
		mInfoText->WriteText("Once you've finished editing the code, open the command prompt from the root directory and enter\n");
		mInfoText->BeginURL("CPY:Engine\\Build\\BatchFiles\\RunUAT.bat BuildGraph -target=\"Make Installed Build Win64\" -script=Engine/Build/InstalledEngineBuild.xml -clean -set:HostPlatformOnly=true -set:WithDDC=false");
		mInfoText->BeginStyle(mCodeAttr);
		mInfoText->WriteText("Engine\\Build\\BatchFiles\\RunUAT.bat BuildGraph -target=\"Make Installed Build Win64\" \n-script=Engine/Build/InstalledEngineBuild.xml -clean -set:HostPlatformOnly=true \n-set:WithDDC=false\n");
		mInfoText->EndStyle();
		mInfoText->EndURL();
		mInfoText->WriteText("to create an engine build to distribute.\n");
		mInfoText->WriteText("Once done you will find the engine build in the LocalBuilds folder.\n");

		mInfoText->BeginStyle(mHeaderAttr);
		mInfoText->WriteText("\nCoding standard\n");
		mInfoText->EndStyle();
		mInfoText->WriteText("Any additions or changes to the default code should be encompassed with\n");
		mInfoText->BeginURL("CPY://----------RPG START----------//");
		mInfoText->BeginStyle(mCodeAttr);
		mInfoText->WriteText("//----------RPG START----------//");
		mInfoText->EndStyle();
		mInfoText->EndURL();
		mInfoText->WriteText(" above the edited code, and\n");
		mInfoText->BeginURL("CPY://-----------RPG END-----------//");
		mInfoText->BeginStyle(mCodeAttr);
		mInfoText->WriteText("//-----------RPG END-----------//");
		mInfoText->EndStyle();
		mInfoText->EndURL();
		mInfoText->WriteText(" beneath it.\n");
		mInfoText->WriteText("If code was replaced, you should add a comment describing what was replaced.\n");
		mInfoText->WriteText("You might also write the original code in its entirety as a comment.\n");

		mInfoText->BeginStyle(mHeaderAttr);
		mInfoText->WriteText("\nEngine files\n");
		mInfoText->EndStyle();
		mInfoText->WriteText("The engine files you will need to include for the custom engine is:\n");
		mInfoText->WriteText("Any ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("source files");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (.h/.cpp) that were added or modified.\n");
		mInfoText->WriteText("Any ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("unreal assets");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (.uasset) that were added or modified.\n");
		mInfoText->WriteText("If the header file includes a ");
		mInfoText->BeginURL("CPY:GENERATED_BODY()");
		mInfoText->BeginStyle(mCodeAttr);
		mInfoText->WriteText("GENERATED_BODY()");
		mInfoText->EndStyle();
		mInfoText->EndURL();
		mInfoText->WriteText(" you will also need the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("generated file");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (.generated.h).\n");
		mInfoText->WriteText("There will be two versions of the generated files,\none for ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("UnrealEditor Development");
		mInfoText->EndStyle();
		mInfoText->WriteText(", and the other for ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("UnrealEditor DebugGame");
		mInfoText->EndStyle();
		mInfoText->WriteText(".\n");
		mInfoText->WriteText("For any modules that were added or modified, you need the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("binary files ");
		mInfoText->EndStyle();
		mInfoText->WriteText("(.dll/.pdb/.lib).\n");
		mInfoText->WriteText("You will also need the ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("precompiled files");
		mInfoText->EndStyle();
		mInfoText->WriteText(" (.cpp.obj/.h.obj/.precompiled) in order to package projects.\n");
		mInfoText->WriteText("There will be two sets of the precompiled files,\none for ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("UnrealGame Development");
		mInfoText->EndStyle();
		mInfoText->WriteText(", and the other for ");
		mInfoText->BeginStyle(mHighlightAttr);
		mInfoText->WriteText("UnrealGame Shipping");
		mInfoText->EndStyle();
		mInfoText->WriteText(".");
		break;
	default:
		break;
	}
}

void InfoPanel::showClipboardMessage()
{
	mCopyImage->Show(true);
	mCopyText->Show(true);
	Layout();

	mCopyTimer->Start(5000, true);
}

void InfoPanel::hideClipboardMessage(wxTimerEvent& event)
{
	mCopyImage->Show(false);
	mCopyText->Show(false);
	Layout();
}
