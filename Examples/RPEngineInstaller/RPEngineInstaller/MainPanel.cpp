#include "MainPanel.h"

#include <wx/filepicker.h>
#include <wx/button.h>
#include <wx/bmpbuttn.h>
#include <wx/choice.h>
#include <wx/textctrl.h>
#include <wx/stattext.h>
#include <wx/sizer.h>
#include <wx/menu.h>

#include <wx/file.h>
#include <wx/dir.h>
#include <wx/log.h>
#include <wx/filename.h>

#include <fileapi.h>

#include "MainFrame.h"
#include "StatusImage.h"
#include "SettingsDialog.h"
#include "InfoDialog.h"

MainPanel::MainPanel(wxWindow* parent) : wxPanel(parent, -1, wxDefaultPosition, wxDefaultSize, wxNO_BORDER)
{
	wxImage::AddHandler(new wxPNGHandler());

	//Setup unreal directory picker.
	mEngineDir = new wxDirPickerCtrl(this, wxID_ANY, wxEmptyString, "Unreal Engine Directory", wxDefaultPosition, wxSize(300, 32));
	mEngineDir->SetToolTip("Choose the Unreal Engine directory matching the selected version.");
	mEngineDir->GetTextCtrl()->SetHint("Select the Unreal Engine directory.");

	//Setup unreal version picker.
	SetupVersions();
	mVersionPicker = new wxChoice(this, wxID_ANY, wxDefaultPosition, wxSize(80, 32), mVersionStrings);
	mVersionPicker->SetToolTip("Select the version you want to install (or revert from).");
	mVersionPicker->Bind(wxEVT_CHOICE, wxCommandEventFunction(&MainPanel::onVersionSelected), this);

	mSettingsButton = new wxBitmapButton(this, wxID_ANY, wxIcon("IDI_SETTING1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(24, 24));
	mSettingsButton->SetBitmapPressed(wxIcon("IDI_SETTING2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mSettingsButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, wxCommandEventFunction(&MainPanel::onButtonSettings), this);
	mSettingsButton->SetToolTip("Open settings.");

	mInfoButton = new wxBitmapButton(this, wxID_ANY, wxIcon("IDI_HELP1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16), wxDefaultPosition, wxSize(24, 24));
	mInfoButton->SetBitmapPressed(wxIcon("IDI_HELP2", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	mInfoButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, wxCommandEventFunction(&MainPanel::onButtonInfo), this);
	mInfoButton->SetToolTip("View info.");
	
	//Setup changelog.
	mChangelogText = new wxTextCtrl(this, wxID_ANY, wxEmptyString, wxDefaultPosition, wxSize(300, 150), wxTE_MULTILINE | wxTE_READONLY | wxTE_RICH2 | wxTE_LEFT | wxTE_BESTWRAP);

	//Setup engine button.
	mCustomButton = new wxButton(this, wxID_ANY, "Rock Pocket Engine", wxDefaultPosition, wxSize(100, 32));
	mCustomButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, wxCommandEventFunction(&MainPanel::onButtonCustom), this);
	mCustomButton->SetToolTip("Apply custom engine files.");

	mDefaultButton = new wxButton(this, wxID_ANY, "Default Unreal Engine", wxDefaultPosition, wxSize(100, 32));
	mDefaultButton->Bind(wxEVT_COMMAND_BUTTON_CLICKED, wxCommandEventFunction(&MainPanel::onButtonDefault), this);
	mDefaultButton->SetToolTip("Apply default engine files.");

	//Add the status image and text.
	mStatusImage = new StatusImage(this);
	mStatusImage->Bind(wxEVT_RIGHT_DCLICK, wxMouseEventFunction(&MainPanel::onShowStatusContextMenu), this);
	mStatusText = new wxStaticText(this, wxID_ANY, wxEmptyString, wxDefaultPosition, wxDefaultSize);

	//Setup Sizers
	wxBoxSizer* mainBoxV = new wxBoxSizer(wxVERTICAL);
	wxBoxSizer* dirBoxH = new wxBoxSizer(wxHORIZONTAL);
	wxBoxSizer* buttonBoxH = new wxBoxSizer(wxHORIZONTAL);
	wxBoxSizer* statusBoxH = new wxBoxSizer(wxHORIZONTAL);

	dirBoxH->Add(mEngineDir, 1);
	dirBoxH->Add(mVersionPicker, 0, wxLEFT | wxUP, 4);
	dirBoxH->Add(mSettingsButton, 0, wxLEFT | wxUP, 4);
	dirBoxH->Add(mInfoButton, 0, wxLEFT | wxUP, 4);
	mainBoxV->Add(dirBoxH, 0, wxEXPAND | wxALL, 10);

	mainBoxV->Add(mChangelogText, 1, wxEXPAND | wxLEFT | wxRIGHT, 10);

	buttonBoxH->Add(mCustomButton, 3, wxEXPAND);
	buttonBoxH->Add(mDefaultButton, 2, wxEXPAND | wxLEFT, 10);
	//buttonBoxH->Add(mInfoButton, 0, wxLEFT, 10);
	mainBoxV->Add(buttonBoxH, 0, wxEXPAND | wxALL, 10);

	statusBoxH->Add(mStatusImage, 0, wxRIGHT, 10);
	statusBoxH->Add(mStatusText, 0, wxCENTRE);
	mainBoxV->Add(statusBoxH, 0, wxLEFT | wxBOTTOM | wxRIGHT, 10);

	this->SetSizer(mainBoxV);

	//Setup default selection.
	wxCommandEvent selectionEvent;
	if (mEngineVersions.size() > 0)
	{
		selectionEvent.SetInt(mEngineVersions.size() - 1);
	}
	else
	{
		selectionEvent.SetInt(0);
	}

	mVersionPicker->SetSelection(selectionEvent.GetInt());
	onVersionSelected(selectionEvent);
}

MainPanel::~MainPanel()
{

}

void MainPanel::SetupVersions()
{
	mVersionStrings.Clear();

	wxString versionsPath = wxGetCwd() + mVersionsPath;

	if (wxDirExists(versionsPath))
	{
		wxArrayString resultingVersions;
		if (wxDir::GetAllFiles(versionsPath, &resultingVersions, "info.dat", wxDIR_DEFAULT))
		{
			for (uint32_t i{ 0 }; i < resultingVersions.size(); i++)
			{
				readVersion(resultingVersions[i]);
			}
		}
	}

	if (mEngineVersions.size() > 0)
	{
		for (uint32_t i{ 0 }; i < mEngineVersions.size(); i++)
		{
			mVersionStrings.Add(mEngineVersions[i].engineVersion);
		}
	}
	else
	{
		mVersionStrings.Add("None");
	}
}

void MainPanel::onVersionSelected(wxCommandEvent& event)
{
	//Is none.
	if (mEngineVersions.size() == 0)
	{
		mEngineDir->Enable(false);
		mEngineDir->SetPath(wxEmptyString);

		mCustomButton->Enable(false);
		mDefaultButton->Enable(false);

		//Clear result message.
		mStatusText->SetLabelText(wxEmptyString);
		mStatusImage->setFrameTarget(0);

		mChangelogText->Clear();

		//Setup empty changelog.
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK, wxNullColour, *wxSMALL_FONT));
		mChangelogText->AppendText("Rock Pocket Engine ");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLUE));
		mChangelogText->AppendText("0.0");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK));
		mChangelogText->AppendText(" (Unreal Engine ");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLUE));
		mChangelogText->AppendText("0.0");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK));
		mChangelogText->AppendText(")\n\n");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK, wxNullColour, wxSWISS_FONT->Bold()));
		mChangelogText->AppendText("Changelog:\n");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK, wxNullColour, *wxNORMAL_FONT));
		mChangelogText->AppendText("No version selected.");
		mChangelogText->ShowPosition(0);
	}
	//Version selected.
	else
	{
		const int32_t engineIndex = event.GetInt();

		mEngineDir->Enable(true);
		if (!bSourceMode)
		{
			mEngineDir->SetPath(mEngineVersions[engineIndex].unrealDir);
		}

		mCustomButton->Enable(true);
		mDefaultButton->Enable(true);

		//Clear result message.
		mStatusText->SetLabelText(wxEmptyString);
		mStatusImage->setFrameTarget(4);

		mChangelogText->Clear();

		//Setup changelog.
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK, wxNullColour, *wxSMALL_FONT));
		mChangelogText->AppendText("Rock Pocket Engine ");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLUE));
		mChangelogText->AppendText(mEngineVersions[engineIndex].engineVersion);
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK));
		mChangelogText->AppendText(" (Unreal Engine ");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLUE));
		mChangelogText->AppendText(mEngineVersions[engineIndex].unrealVersion);
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK));
		mChangelogText->AppendText(")\n\n");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK, wxNullColour, wxSWISS_FONT->Bold()));
		mChangelogText->AppendText("Changelog:\n");
		mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK, wxNullColour, *wxNORMAL_FONT));
		mChangelogText->AppendText(mEngineVersions[engineIndex].changelog);

		//Add changelog for parent versions.
		if (mEngineVersions[engineIndex].parentVersion.empty() == false)
		{
			mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK, wxNullColour, wxSWISS_FONT->Bold()));
			mChangelogText->AppendText("\n\nPrevious Changelogs:\n");
			mChangelogText->SetDefaultStyle(wxTextAttr(*wxBLACK, wxNullColour, *wxNORMAL_FONT));
			wxString parentVersion = mEngineVersions[engineIndex].parentVersion;
			while (parentVersion.empty() == false)
			{
				for (uint32_t i{ 0 }; i < mEngineVersions.size(); i++)
				{
					if (mEngineVersions[i].engineVersion == parentVersion)
					{
						mChangelogText->AppendText(mEngineVersions[i].changelog);
						parentVersion = mEngineVersions[i].parentVersion;
						break;
					}
				}

				if (parentVersion.empty() == false)
				{
					mChangelogText->AppendText("\n\n");
				}
			}
		}

		mChangelogText->ShowPosition(0);
	}
}

bool MainPanel::readVersion(const wxString filePath)
{
	bool versionAdded{ false };

	if (wxFileExists(filePath))
	{
		wxFile* versionFile = new wxFile;
		versionFile->Open(filePath, wxFile::read);

		//Make sure the file is at or above the minimum size.
		if (versionFile->Length() >= 20)
		{
			//Ensure header.
			char* headerBuffer = new char[14];
			versionFile->Read(headerBuffer, 14U);
			if (wxString(headerBuffer, 14U) == "RPEngineHeader")
			{
				EngineInfo addedVersion;
				addedVersion.infoDir = filePath;

				//Find the length of the engine version string.
				uint32_t* engineVersionSizeBuffer = new uint32_t;
				versionFile->Read(engineVersionSizeBuffer, 4U);
				//Read the engine version string.
				if (*engineVersionSizeBuffer > 0)
				{
					char* engineVersionStringBuffer = new char[*engineVersionSizeBuffer];
					versionFile->Read(engineVersionStringBuffer, *engineVersionSizeBuffer);
					addedVersion.engineVersion = wxString(engineVersionStringBuffer, *engineVersionSizeBuffer);
					delete[] engineVersionStringBuffer;
				}
				delete engineVersionSizeBuffer;

				//Find the length of the parent version string.
				uint32_t* parentVersionSizeBuffer = new uint32_t;
				versionFile->Read(parentVersionSizeBuffer, 4U);
				//Read the parent version string.
				if (*parentVersionSizeBuffer > 0)
				{
					char* parentVersionStringBuffer = new char[*parentVersionSizeBuffer];
					versionFile->Read(parentVersionStringBuffer, *parentVersionSizeBuffer);
					addedVersion.parentVersion = wxString(parentVersionStringBuffer, *parentVersionSizeBuffer);
					delete[] parentVersionStringBuffer;
				}
				delete parentVersionSizeBuffer;

				//Find the length of the unreal version string.
				uint32_t* unrealVersionSizeBuffer = new uint32_t;
				versionFile->Read(unrealVersionSizeBuffer, 4U);
				//Read the unreal version string.
				if (*unrealVersionSizeBuffer > 0)
				{
					char* unrealVersionStringBuffer = new char[*unrealVersionSizeBuffer];
					versionFile->Read(unrealVersionStringBuffer, *unrealVersionSizeBuffer);
					addedVersion.unrealVersion = wxString(unrealVersionStringBuffer, *unrealVersionSizeBuffer);
					delete[] unrealVersionStringBuffer;
				}
				delete unrealVersionSizeBuffer;

				//Find the length of the unreal directory.
				uint32_t* unrealDirSizeBuffer = new uint32_t;
				versionFile->Read(unrealDirSizeBuffer, 4U);
				//Read the unreal directory string.
				if (*unrealDirSizeBuffer > 0)
				{
					char* unrealDirStringBuffer = new char[*unrealDirSizeBuffer];
					versionFile->Read(unrealDirStringBuffer, *unrealDirSizeBuffer);
					addedVersion.unrealDir = wxString(unrealDirStringBuffer, *unrealDirSizeBuffer);
					delete[] unrealDirStringBuffer;
				}
				delete unrealDirSizeBuffer;

				//Find the length of the changelog string.
				uint32_t* changelogSizeBuffer = new uint32_t;
				versionFile->Read(changelogSizeBuffer, 4U);
				//Read the changelog string.
				if (*changelogSizeBuffer > 0)
				{
					char* changelogStringBuffer = new char[*changelogSizeBuffer];
					versionFile->Read(changelogStringBuffer, *changelogSizeBuffer);
					addedVersion.changelog = wxString(changelogStringBuffer, *changelogSizeBuffer);
					delete[] changelogStringBuffer;
				}
				delete changelogSizeBuffer;

				//Find the number of files edited.
				uint32_t* fileNumBuffer = new uint32_t;
				versionFile->Read(fileNumBuffer, 4U);
				//Loop through all files.
				if (*fileNumBuffer > 0)
				{
					for (uint32_t i{ 0 }; i < *fileNumBuffer; i++)
					{
						EngineFile addedEngineFile;

						//Find the length of the path to the custom engine file.
						uint32_t* customPathSizeBuffer = new uint32_t;
						versionFile->Read(customPathSizeBuffer, 4U);
						//Read the string of the path to the custom engine file.
						if (*customPathSizeBuffer > 0)
						{
							char* customPathStringBuffer = new char[*customPathSizeBuffer];
							versionFile->Read(customPathStringBuffer, *customPathSizeBuffer);
							addedEngineFile.pathCustom = wxString(customPathStringBuffer, *customPathSizeBuffer);
							delete[] customPathStringBuffer;

							//Set the local file name.
							wxFileName fileName(addedEngineFile.pathCustom);
							addedEngineFile.localName = fileName.GetName() + "." + fileName.GetExt();
						}
						delete customPathSizeBuffer;

						//Find the length of the path to the default engine file.
						uint32_t* defaultPathSizeBuffer = new uint32_t;
						versionFile->Read(defaultPathSizeBuffer, 4U);
						//Read the string of the path to the default engine file.
						if (*defaultPathSizeBuffer > 0)
						{
							char* defaultPathStringBuffer = new char[*defaultPathSizeBuffer];
							versionFile->Read(defaultPathStringBuffer, *defaultPathSizeBuffer);
							addedEngineFile.pathDefault = wxString(defaultPathStringBuffer, *defaultPathSizeBuffer);
							delete[] defaultPathStringBuffer;

							//Set the local file name.
							wxFileName fileName(addedEngineFile.pathDefault);
							addedEngineFile.localName = fileName.GetName() + "." + fileName.GetExt();
						}
						delete defaultPathSizeBuffer;

						//Find the length of the target path of the file.
						uint32_t* targetPathSizeBuffer = new uint32_t;
						versionFile->Read(targetPathSizeBuffer, 4U);
						//Read the string of the target path of the file.
						if (*targetPathSizeBuffer > 0)
						{
							char* targetPathStringBuffer = new char[*targetPathSizeBuffer];
							versionFile->Read(targetPathStringBuffer, *targetPathSizeBuffer);
							addedEngineFile.pathTarget = wxString(targetPathStringBuffer, *targetPathSizeBuffer);
							delete[] targetPathStringBuffer;
						}
						delete targetPathSizeBuffer;

						addedVersion.files.push_back(addedEngineFile);
					}
				}
				delete fileNumBuffer;

				mEngineVersions.push_back(addedVersion);
				versionAdded = true;
			}
			delete[] headerBuffer;
		}

		versionFile->Close();
		delete versionFile;
	}

	return versionAdded;
}

bool MainPanel::writeVersion(const EngineInfo& versionInfo)
{
	wxFile* versionFile = new wxFile;

	//Try to open the file if it exists.
	if (wxFileExists(versionInfo.infoDir))
	{
		versionFile->Open(versionInfo.infoDir, wxFile::write);
	}
	//If not try to create it.
	else
	{
		if (!versionInfo.infoDir.empty())
		{
			versionFile->Create(versionInfo.infoDir, true);
			versionFile->Open(versionInfo.infoDir, wxFile::write);
		}
	}

	bool versionSaved{ false };
	
	if (versionFile->IsOpened())
	{
		versionFile->Write("RPEngineHeader", 14U);

		uint32_t* sizeBuffer = new uint32_t;

		//Write size and value of engine version.
		if (!versionInfo.engineVersion.empty())
		{
			*sizeBuffer = versionInfo.engineVersion.length();
			versionFile->Write(sizeBuffer, 4U);
			versionFile->Write(versionInfo.engineVersion, versionInfo.engineVersion.length());
		}
		else
		{
			*sizeBuffer = 0;
			versionFile->Write(sizeBuffer, 4U);
		}

		//Write size and value of parent version.
		if (!versionInfo.parentVersion.empty())
		{
			*sizeBuffer = versionInfo.parentVersion.length();
			versionFile->Write(sizeBuffer, 4U);
			versionFile->Write(versionInfo.parentVersion, versionInfo.parentVersion.length());
		}
		else
		{
			*sizeBuffer = 0;
			versionFile->Write(sizeBuffer, 4U);
		}

		//Write size and value of unreal version.
		if (!versionInfo.unrealVersion.empty())
		{
			*sizeBuffer = versionInfo.unrealVersion.length();
			versionFile->Write(sizeBuffer, 4U);
			versionFile->Write(versionInfo.unrealVersion, versionInfo.unrealVersion.length());
		}
		else
		{
			*sizeBuffer = 0;
			versionFile->Write(sizeBuffer, 4U);
		}

		//Write size and value of unreal directory.
		if (!versionInfo.unrealDir.empty())
		{
			*sizeBuffer = versionInfo.unrealDir.length();
			versionFile->Write(sizeBuffer, 4U);
			versionFile->Write(versionInfo.unrealDir, versionInfo.unrealDir.length());
		}
		else
		{
			*sizeBuffer = 0;
			versionFile->Write(sizeBuffer, 4U);
		}

		//Write size and value of change log.
		if (!versionInfo.changelog.empty())
		{
			*sizeBuffer = versionInfo.changelog.length();
			versionFile->Write(sizeBuffer, 4U);
			versionFile->Write(versionInfo.changelog, versionInfo.changelog.length());
		}
		else
		{
			*sizeBuffer = 0;
			versionFile->Write(sizeBuffer, 4U);
		}

		//Write the number of edited files and edited file paths.
		if (versionInfo.files.size() > 0)
		{
			*sizeBuffer = versionInfo.files.size();
			versionFile->Write(sizeBuffer, 4U);

			for (uint32_t i{ 0 }; i < versionInfo.files.size(); i++)
			{
				//Write size and value of custom engine file path.
				if (!versionInfo.files[i].pathCustom.empty())
				{
					*sizeBuffer = versionInfo.files[i].pathCustom.length();
					versionFile->Write(sizeBuffer, 4U);
					versionFile->Write(versionInfo.files[i].pathCustom, versionInfo.files[i].pathCustom.length());
				}
				else
				{
					*sizeBuffer = 0;
					versionFile->Write(sizeBuffer, 4U);
				}

				//Write size and value of default engine file path.
				if (!versionInfo.files[i].pathDefault.empty())
				{
					*sizeBuffer = versionInfo.files[i].pathDefault.length();
					versionFile->Write(sizeBuffer, 4U);
					versionFile->Write(versionInfo.files[i].pathDefault, versionInfo.files[i].pathDefault.length());
				}
				else
				{
					*sizeBuffer = 0;
					versionFile->Write(sizeBuffer, 4U);
				}

				//Write size and value of the target file path.
				if (!versionInfo.files[i].pathTarget.empty())
				{
					*sizeBuffer = versionInfo.files[i].pathTarget.length();
					versionFile->Write(sizeBuffer, 4U);
					versionFile->Write(versionInfo.files[i].pathTarget, versionInfo.files[i].pathTarget.length());
				}
				else
				{
					*sizeBuffer = 0;
					versionFile->Write(sizeBuffer, 4U);
				}
			}
		}
		else
		{
			*sizeBuffer = 0;
			versionFile->Write(sizeBuffer, 4U);
		}

		delete sizeBuffer;

		versionFile->Close();
		versionSaved = true;
	}

	delete versionFile;

	return versionSaved;
}

bool MainPanel::setupLocalEngineFiles(EngineInfo& versionInfo)
{
	//Set path to engine info file.
	if (versionInfo.infoDir.empty())
	{
		versionInfo.infoDir = wxGetCwd() + mVersionsPath + versionInfo.engineVersion + "\\info.dat";
	}

	//Make sure all the version folders exists. 
	if (wxDirExists(wxGetCwd() + mVersionsPath) == false)
	{
		wxFileName::Mkdir(wxGetCwd() + mVersionsPath);
	}
	if (wxDirExists(wxGetCwd() + mVersionsPath + versionInfo.engineVersion) == false)
	{
		wxFileName::Mkdir(wxGetCwd() + mVersionsPath + versionInfo.engineVersion);
	}
	if (wxDirExists(wxGetCwd() + mVersionsPath + versionInfo.engineVersion + mCustomEnginePath) == false)
	{
		wxFileName::Mkdir(wxGetCwd() + mVersionsPath + versionInfo.engineVersion + mCustomEnginePath);
	}
	if (wxDirExists(wxGetCwd() + mVersionsPath + versionInfo.engineVersion + mDefaultEnginePath) == false)
	{
		wxFileName::Mkdir(wxGetCwd() + mVersionsPath + versionInfo.engineVersion + mDefaultEnginePath);
	}

	for (uint32_t i{ 0 }; i < versionInfo.files.size(); i++)
	{
		if (versionInfo.files[i].pathCustom.empty() == false)
		{
			const wxString targetPath = mVersionsPath + versionInfo.engineVersion + mCustomEnginePath + versionInfo.files[i].localName;
			
			//File path is not finale.
			if (versionInfo.files[i].pathCustom != targetPath)
			{
				//Right path but absolute.
				if (versionInfo.files[i].pathCustom == wxGetCwd() + targetPath)
				{
					versionInfo.files[i].pathCustom = targetPath;
				}
				//Needs moving.
				else
				{
					if (wxFileExists(wxGetCwd() + targetPath))
					{
						//Break write lock if read only.
						DWORD dwAttrsFile = GetFileAttributes((wxGetCwd() + targetPath).wc_str());
						if ((dwAttrsFile & FILE_ATTRIBUTE_READONLY))
						{
							SetFileAttributes((wxGetCwd() + targetPath).wc_str(), FILE_ATTRIBUTE_NORMAL);
						}
					}
					wxLogNull errorSuppression;
					//Give 5 attempts.
					uint8_t copyAttempts{ 0 };
					while (copyAttempts < 5)
					{
						if (wxCopyFile(versionInfo.files[i].pathCustom, wxGetCwd() + targetPath, true))
						{
							break;
						}
						else
						{
							copyAttempts++;
							//Wait 1 second and try again.
							wxSleep(1);
						}
					}
					if (copyAttempts >= 5)
					{
						errorSuppression.~wxLogNull();
						return false;
					}
					versionInfo.files[i].pathCustom = targetPath;
					errorSuppression.~wxLogNull();
				}
			}
		}
		if (versionInfo.files[i].pathDefault.empty() == false)
		{
			const wxString targetPath = mVersionsPath + versionInfo.engineVersion + mDefaultEnginePath + versionInfo.files[i].localName;

			//File path is not finale.
			if (versionInfo.files[i].pathDefault != targetPath)
			{
				//Right path but absolute.
				if (versionInfo.files[i].pathDefault == wxGetCwd() + targetPath)
				{
					versionInfo.files[i].pathDefault = targetPath;
				}
				//Needs moving.
				else
				{
					if (wxFileExists(wxGetCwd() + targetPath))
					{
						//Break write lock if read only.
						DWORD dwAttrsFile = GetFileAttributes((wxGetCwd() + targetPath).wc_str());
						if ((dwAttrsFile & FILE_ATTRIBUTE_READONLY))
						{
							SetFileAttributes((wxGetCwd() + targetPath).wc_str(), FILE_ATTRIBUTE_NORMAL);
						}
					}
					wxLogNull errorSuppression;
					//Give 5 attempts.
					uint8_t copyAttempts{ 0 };
					while (copyAttempts < 5)
					{
						if (wxCopyFile(versionInfo.files[i].pathDefault, wxGetCwd() + targetPath, true))
						{
							break;
						}
						else
						{
							copyAttempts++;
							//Wait 1 second and try again.
							wxSleep(1);
						}
					}
					if (copyAttempts >= 5)
					{
						errorSuppression.~wxLogNull();
						return false;
					}
					versionInfo.files[i].pathDefault = targetPath;
					errorSuppression.~wxLogNull();
				}
			}
		}
	}

	return true;
}

bool MainPanel::removeLocalEngineFiles(const uint32_t engineIndex)
{
	//Remove the local engine directory with all files.
	const wxString dirPath = wxGetCwd() + mVersionsPath + mEngineVersions[engineIndex].engineVersion;
	return removeDirectoryFiles(dirPath);
}

bool MainPanel::removeDirectoryFiles(const wxString& dirPath)
{
	wxDir dir(dirPath);
	if (dir.IsOpened())
	{
		wxString filename;
		bool dirContent = dir.GetFirst(&filename);
		while (dirContent)
		{
			wxString fullPath = dirPath + "\\" + filename;
			if (wxFileName::FileExists(fullPath))
			{
				//Break write lock if read only.
				DWORD dwAttrsFile = GetFileAttributes(fullPath.wc_str());
				if ((dwAttrsFile & FILE_ATTRIBUTE_READONLY))
				{
					SetFileAttributes(fullPath.wc_str(), FILE_ATTRIBUTE_NORMAL);
				}

				wxRemoveFile(fullPath);
			}
			else if (wxFileName::DirExists(fullPath))
			{
				if (!removeDirectoryFiles(fullPath))
				{
					return false;
				}
			}
			dirContent = dir.GetNext(&filename);
		}

		return wxRmdir(dirPath);
	}
	else
	{
		return false;
	}
}

void MainPanel::onButtonSettings(wxCommandEvent& event)
{
	//Clear result message.
	mStatusText->SetLabelText(wxEmptyString);
	mStatusImage->setFrameTarget(4);

	//A list of all setups that failed.
	wxVector<wxString> failedVersions = wxVector<wxString>();

	SettingsDialog dialog(this, mEngineVersions);
	if (dialog.ShowModal() == wxID_OK)
	{
		wxVector<EngineInfo> updatedEngines = dialog.getEngines();
		//Do removals first.
		for (int32_t i{ int32_t(updatedEngines.size()) - 1 }; i >= 0; i--)
		{
			switch (updatedEngines[i].status)
			{
				case eEng_Modify:
					//Remove old version if the version number has changed.
					if (updatedEngines[i].engineVersion.IsSameAs(mEngineVersions[i].engineVersion, false) == false)
					{
						removeLocalEngineFiles(i);
					}
					//Find files that has been removed.
					else
					{
						for (uint32_t oldFileIndex{ 0 }; oldFileIndex < mEngineVersions[i].files.size(); oldFileIndex++)
						{
							bool removeFile{ true };
							for (uint32_t newFileIndex{ 0 }; newFileIndex < updatedEngines[i].files.size(); newFileIndex++)
							{
								if (mEngineVersions[i].files[oldFileIndex].localName == updatedEngines[i].files[newFileIndex].localName)
								{
									removeFile = false;
									break;
								}
							}

							if (removeFile)
							{
								if (mEngineVersions[i].files[oldFileIndex].pathCustom.empty() == false)
								{
									const wxString pathCustomFull = wxGetCwd() + mEngineVersions[i].files[oldFileIndex].pathCustom;
									if (wxFileExists(pathCustomFull))
									{
										//Break write lock if read only.
										DWORD dwAttrsFile = GetFileAttributes(pathCustomFull.wc_str());
										if ((dwAttrsFile & FILE_ATTRIBUTE_READONLY))
										{
											SetFileAttributes(pathCustomFull.wc_str(), FILE_ATTRIBUTE_NORMAL);
										}

										wxRemoveFile(pathCustomFull);
									}
								}
								if (mEngineVersions[i].files[oldFileIndex].pathDefault.empty() == false)
								{
									const wxString pathDefaultFull = wxGetCwd() + mEngineVersions[i].files[oldFileIndex].pathDefault;
									if (wxFileExists(pathDefaultFull))
									{
										//Break write lock if read only.
										DWORD dwAttrsFile = GetFileAttributes(pathDefaultFull.wc_str());
										if ((dwAttrsFile & FILE_ATTRIBUTE_READONLY))
										{
											SetFileAttributes(pathDefaultFull.wc_str(), FILE_ATTRIBUTE_NORMAL);
										}

										wxRemoveFile(pathDefaultFull);
									}
								}
							}
						}
					}
					break;
				case eEng_Remove:
					if (removeLocalEngineFiles(i))
					{
						updatedEngines.erase(updatedEngines.begin() + i);
					}
					else
					{
						updatedEngines[i].status = eEng_None;
					}
					break;
				default:
					break;
			}
		}

		for (int32_t i{ int32_t(updatedEngines.size()) - 1 }; i >= 0; i--)
		{
			switch (updatedEngines[i].status)
			{
			case eEng_Add:
				if (setupLocalEngineFiles(updatedEngines[i]))
				{
					writeVersion(updatedEngines[i]);
					updatedEngines[i].status = eEng_None;
				}
				else
				{
					failedVersions.push_back(updatedEngines[i].engineVersion);
					updatedEngines.erase(updatedEngines.begin() + i);
				}
				break;
			case eEng_Modify:
				if (setupLocalEngineFiles(updatedEngines[i]))
				{
					writeVersion(updatedEngines[i]);
					updatedEngines[i].status = eEng_None;

					//Update parent numbers if the version number has changed.
					if (updatedEngines[i].engineVersion != mEngineVersions[i].engineVersion)
					{
						//Update parent numbers.
						for (uint32_t j{ 0 }; j < updatedEngines.size(); j++)
						{
							if (updatedEngines[j].parentVersion == mEngineVersions[i].engineVersion)
							{
								updatedEngines[j].parentVersion = updatedEngines[i].engineVersion;
								if (updatedEngines[j].status == eEng_None)
								{
									writeVersion(updatedEngines[j]);
								}
							}
						}
					}
				}
				else
				{
					failedVersions.push_back(updatedEngines[i].engineVersion);
					updatedEngines.erase(updatedEngines.begin() + i);
				}
				break;
			default:
				break;
			}
		}
		mEngineVersions = updatedEngines;

		mVersionStrings.Clear();
		if (mEngineVersions.size() > 0)
		{
			for (uint32_t i{ 0 }; i < mEngineVersions.size(); i++)
			{
				mVersionStrings.Add(mEngineVersions[i].engineVersion);
			}
		}
		else
		{
			mVersionStrings.Add("None");
		}
	}

	//Setup default selection.
	wxCommandEvent selectionEvent;
	if (mEngineVersions.size() > 0)
	{
		selectionEvent.SetInt(mEngineVersions.size() - 1);
	}
	else
	{
		selectionEvent.SetInt(0);
	}

	mVersionPicker->Set(mVersionStrings);
	mVersionPicker->SetSelection(selectionEvent.GetInt());
	onVersionSelected(selectionEvent);

	//Add error for fails.
	if (failedVersions.size() > 0)
	{
		wxString errorMessage{ "Failed to setup files for Rock Pocket Engine " };
		for (uint32_t i{ 0 }; i < failedVersions.size(); i++)
		{
			errorMessage += failedVersions[i];

			const uint32_t remainingFails = failedVersions.size() - i - 1;
			switch (remainingFails)
			{
			case 0:
				errorMessage += ".";
				break;
			case 1:
				errorMessage += " and ";
				break;
			default:
				errorMessage += ", ";
				break;
			}
		}

		mStatusText->SetForegroundColour(wxColour(100, 50, 50));
		mStatusText->SetLabelText(errorMessage);
		mStatusImage->setFrameTarget(0);
		Layout();
	}
}

void MainPanel::onButtonInfo(wxCommandEvent& event)
{
	InfoDialog dialog(this);
	dialog.ShowModal();
}

void MainPanel::onButtonCustom(wxCommandEvent& event)
{
	replaceEngineFiles(true, mVersionPicker->GetSelection());
}

void MainPanel::onButtonDefault(wxCommandEvent& event)
{
	replaceEngineFiles(false, mVersionPicker->GetSelection());
}

void MainPanel::onShowStatusContextMenu(wxMouseEvent& event)
{
	wxMenu menu;
	if (bSourceMode)
	{
		menu.Append(0, "Install to Engine")->SetBitmap(wxIcon("IDI_CD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		wxMenuItem* prevOption = menu.Append(1, "Install to Source");
		prevOption->SetBitmap(wxIcon("IDI_CD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		prevOption->Enable(false);
	}
	else
	{
		wxMenuItem* prevOption = menu.Append(0, "Install to Engine");
		prevOption->SetBitmap(wxIcon("IDI_CD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
		prevOption->Enable(false);
		menu.Append(1, "Install to Source")->SetBitmap(wxIcon("IDI_CD1", wxBITMAP_TYPE_ICO_RESOURCE, 16, 16));
	}
	menu.Bind(wxEVT_COMMAND_MENU_SELECTED, &MainPanel::onStatusContextMenuSelected, this);
	PopupMenu(&menu);
}

void MainPanel::onStatusContextMenuSelected(wxCommandEvent& event)
{
	bSourceMode = !bSourceMode;

	if (bSourceMode)
	{
		static_cast<MainFrame*>(GetParent())->SetTitle("Rock Pocket Engine Installer (Source Mode)");
		mEngineDir->GetTextCtrl()->SetHint("Select the Unreal Engine source directory.");
		mEngineDir->SetPath(wxEmptyString);
	}
	else
	{
		static_cast<MainFrame*>(GetParent())->SetTitle("Rock Pocket Engine Installer");
		mEngineDir->GetTextCtrl()->SetHint("Select the Unreal Engine directory.");
		if (mEngineVersions.size() > 0)
		{
			mEngineDir->SetPath(mEngineVersions[mVersionPicker->GetSelection()].unrealDir);
		}
	}
}

void MainPanel::replaceEngineFiles(const bool customEngine, const uint32_t engineIndex)
{
	wxVector<wxString> filesToMoveFrom = wxVector<wxString>();
	wxVector<wxString> filesToMoveTo = wxVector<wxString>();
	wxVector<wxString> filesToRemove = wxVector<wxString>();
	wxVector<wxString> filesToIgnore = wxVector<wxString>();

	//Make sure the selected unreal directory is valid.
	if (wxDirExists(mEngineDir->GetPath()) == false || wxFileExists(mEngineDir->GetPath() + (bSourceMode ? mSourceTestPath : mEngineTestPath)) == false)
	{
		mStatusText->SetForegroundColour(wxColour(100, 50, 50));
		mStatusText->SetLabelText("An invalid directory was selected!\nPlease make sure the selected Unreal Engine directory is correct.");
		mStatusImage->setFrameTarget(0);
		Layout();
		return;
	}

	if (bSourceMode)
	{
		//Get all source files to modify. This includes parent versions.
		getEngineSourceFiles(customEngine, engineIndex, filesToMoveFrom, filesToMoveTo, filesToRemove, filesToIgnore);
	}
	else
	{
		//Check if user has source code installed. If not ignore .cpp files.
		const bool includeSource = wxFileExists(mEngineDir->GetPath() + mSourceTestPath);
		//Check if user has debugging symbols installed. If not ignore .pdb files.
		const bool includeSymbols = wxFileExists(mEngineDir->GetPath() + mSymbolTestPath);

		//Get all files to modify. This includes parent versions.
		getEngineFiles(customEngine, engineIndex, includeSource, includeSymbols, filesToMoveFrom, filesToMoveTo, filesToRemove, filesToIgnore);
	}

	//Test that all files are valid and readable/writable.
	for (uint32_t i{ 0 }; i < filesToMoveFrom.size(); i++)
	{
		if (testLocalFileAccessible(filesToMoveFrom[i]) == false)
		{
			return;
		}
	}

	for (uint32_t i{ 0 }; i < filesToMoveTo.size(); i++)
	{
		if (testEngineFileAccessible(filesToMoveTo[i]) == false)
		{
			return;
		}
	}

	for (uint32_t i{ 0 }; i < filesToRemove.size(); i++)
	{
		if (testEngineFileAccessible(filesToRemove[i]) == false)
		{
			return;
		}
	}

	//Try copying files.
	for (uint32_t i{ 0 }; i < filesToMoveFrom.size(); i++)
	{
		if (!ensureDirectory(filesToMoveTo[i]))
		{
			mStatusText->SetForegroundColour(wxColour(100, 50, 50));
			mStatusText->SetLabelText("Failed to find/make the directory for a file!");
			mStatusImage->setFrameTarget(0);
			Layout();

			return;
		}

		if (!wxCopyFile(filesToMoveFrom[i], filesToMoveTo[i], true))
		{
			mStatusText->SetForegroundColour(wxColour(100, 50, 50));
			mStatusText->SetLabelText("Failed to move a file!");
			mStatusImage->setFrameTarget(0);
			Layout();

			return;
		}
		else
		{
			//Set as read only.
			DWORD dwAttrsFile = GetFileAttributes(filesToMoveTo[i].wc_str());
			if (dwAttrsFile)
			{
				SetFileAttributes(filesToMoveTo[i].wc_str(), FILE_ATTRIBUTE_READONLY);
			}
		}
	}

	//Try removing files.
	for (uint32_t i{ 0 }; i < filesToRemove.size(); i++)
	{
		if (!wxRemoveFile(filesToRemove[i]))
		{
			mStatusText->SetForegroundColour(wxColour(100, 50, 50));
			mStatusText->SetLabelText("Failed to remove a file!");
			mStatusImage->setFrameTarget(0);
			Layout();

			return;
		}
	}

	mStatusText->SetForegroundColour(wxColour(50, 100, 50));
	if (customEngine)
	{
		mStatusText->SetLabelText("Rock Pocket Engine was successfully applied!");
	}
	else
	{
		mStatusText->SetLabelText("Default Unreal Engine successfully applied!");
	}
	mStatusImage->setFrameTarget(8);
	Layout();
}

void MainPanel::getEngineFiles(const bool customEngine, const uint32_t engineIndex, const bool includeSource, const bool includeSymbols, wxVector<wxString>& filesToMoveFrom, wxVector<wxString>& filesToMoveTo, wxVector<wxString>& filesToRemove, wxVector<wxString>& filesToIgnore) const
{
	//Find all files to modify.
	for (uint32_t i{ 0 }; i < mEngineVersions[engineIndex].files.size(); i++)
	{
		//Make sure there is a target path.
		if (mEngineVersions[engineIndex].files[i].pathTarget.empty() == false)
		{
			//Check if this file is in the ignore list.
			bool includeFile{ true };
			for (uint32_t j{ 0 }; j < filesToIgnore.size(); j++)
			{
				if (mEngineVersions[engineIndex].files[i].pathTarget.IsSameAs(filesToIgnore[j], false))
				{
					includeFile = false;
					break;
				}
			}

			if (includeFile)
			{
				//Add this file to ignore list so it does not get overwriteen by a parent (prioritize children).
				filesToIgnore.push_back(mEngineVersions[engineIndex].files[i].pathTarget);

				//Remove file if it is custom engine exclusive and we are going back to default engine.
				if (customEngine)
				{
					//Make sure there is a custom engine file.
					if (mEngineVersions[engineIndex].files[i].pathCustom.empty() == false)
					{
						//Ignore if debug symbols are not included and this is a .pdb file.
						if (shouldIncludeFile(mEngineVersions[engineIndex].files[i].pathCustom, includeSource, includeSymbols))
						{
							filesToMoveFrom.push_back(wxGetCwd() + mEngineVersions[engineIndex].files[i].pathCustom);
							filesToMoveTo.push_back(mEngineDir->GetPath() + mEngineVersions[engineIndex].files[i].pathTarget);
						}
					}
					//Remove file if it is default engine exclusive and we are using the custom engine.
					else if (mEngineVersions[engineIndex].files[i].pathDefault.empty() == false)
					{
						const wxString fileToRemove = mEngineDir->GetPath() + mEngineVersions[engineIndex].files[i].pathTarget;
						if (wxFileExists(fileToRemove))
						{
							filesToRemove.push_back(fileToRemove);
						}
					}
				}
				else
				{
					//Make sure there is a default engine file.
					if (mEngineVersions[engineIndex].files[i].pathDefault.empty() == false)
					{
						//Ignore if debug symbols are not included and this is a .pdb file.
						if (shouldIncludeFile(mEngineVersions[engineIndex].files[i].pathDefault, includeSource, includeSymbols))
						{
							filesToMoveFrom.push_back(wxGetCwd() + mEngineVersions[engineIndex].files[i].pathDefault);
							filesToMoveTo.push_back(mEngineDir->GetPath() + mEngineVersions[engineIndex].files[i].pathTarget);
						}
					}
					//Remove file if it is custom engine exclusive and we are going back to default engine.
					else if (mEngineVersions[engineIndex].files[i].pathCustom.empty() == false)
					{
						const wxString fileToRemove = mEngineDir->GetPath() + mEngineVersions[engineIndex].files[i].pathTarget;
						if (wxFileExists(fileToRemove))
						{
							filesToRemove.push_back(fileToRemove);
						}
					}
				}
			}
		}
	}

	//Do the same for the parent version.
	if (mEngineVersions[engineIndex].parentVersion.empty() == false)
	{
		for (uint32_t i{ 0 }; i < mEngineVersions.size(); i++)
		{
			if (mEngineVersions[i].engineVersion == mEngineVersions[engineIndex].parentVersion)
			{
				getEngineFiles(customEngine, i, includeSource, includeSymbols, filesToMoveFrom, filesToMoveTo, filesToRemove, filesToIgnore);
				break;
			}
		}
	}
}

void MainPanel::getEngineSourceFiles(const bool customEngine, const uint32_t engineIndex, wxVector<wxString>& filesToMoveFrom, wxVector<wxString>& filesToMoveTo, wxVector<wxString>& filesToRemove, wxVector<wxString>& filesToIgnore) const
{
	//Find all files to modify.
	for (uint32_t i{ 0 }; i < mEngineVersions[engineIndex].files.size(); i++)
	{
		//Make sure there is a target path.
		if (mEngineVersions[engineIndex].files[i].pathTarget.empty() == false)
		{
			//Check if this file is in the ignore list.
			bool includeFile{ true };
			for (uint32_t j{ 0 }; j < filesToIgnore.size(); j++)
			{
				if (mEngineVersions[engineIndex].files[i].pathTarget.IsSameAs(filesToIgnore[j], false))
				{
					includeFile = false;
					break;
				}
			}

			if (includeFile)
			{
				//Add this file to ignore list so it does not get overwriteen by a parent (prioritize children).
				filesToIgnore.push_back(mEngineVersions[engineIndex].files[i].pathTarget);

				//Remove file if it is custom engine exclusive and we are going back to default engine.
				if (customEngine)
				{
					//Make sure there is a custom engine file.
					if (mEngineVersions[engineIndex].files[i].pathCustom.empty() == false)
					{
						//Ignore if debug symbols are not included and this is a .pdb file.
						if (isSourceFile(mEngineVersions[engineIndex].files[i].pathCustom))
						{
							filesToMoveFrom.push_back(wxGetCwd() + mEngineVersions[engineIndex].files[i].pathCustom);
							filesToMoveTo.push_back(mEngineDir->GetPath() + mEngineVersions[engineIndex].files[i].pathTarget);
						}
					}
					//Remove file if it is default engine exclusive and we are using the custom engine.
					else if (mEngineVersions[engineIndex].files[i].pathDefault.empty() == false)
					{
						const wxString fileToRemove = mEngineDir->GetPath() + mEngineVersions[engineIndex].files[i].pathTarget;
						if (wxFileExists(fileToRemove))
						{
							filesToRemove.push_back(fileToRemove);
						}
					}
				}
				else
				{
					//Make sure there is a default engine file.
					if (mEngineVersions[engineIndex].files[i].pathDefault.empty() == false)
					{
						//Ignore if debug symbols are not included and this is a .pdb file.
						if (isSourceFile(mEngineVersions[engineIndex].files[i].pathDefault))
						{
							filesToMoveFrom.push_back(wxGetCwd() + mEngineVersions[engineIndex].files[i].pathDefault);
							filesToMoveTo.push_back(mEngineDir->GetPath() + mEngineVersions[engineIndex].files[i].pathTarget);
						}
					}
					//Remove file if it is custom engine exclusive and we are going back to default engine.
					else if (mEngineVersions[engineIndex].files[i].pathCustom.empty() == false)
					{
						const wxString fileToRemove = mEngineDir->GetPath() + mEngineVersions[engineIndex].files[i].pathTarget;
						if (wxFileExists(fileToRemove))
						{
							filesToRemove.push_back(fileToRemove);
						}
					}
				}
			}
		}
	}

	//Do the same for the parent version.
	if (mEngineVersions[engineIndex].parentVersion.empty() == false)
	{
		for (uint32_t i{ 0 }; i < mEngineVersions.size(); i++)
		{
			if (mEngineVersions[i].engineVersion == mEngineVersions[engineIndex].parentVersion)
			{
				getEngineSourceFiles(customEngine, i, filesToMoveFrom, filesToMoveTo, filesToRemove, filesToIgnore);
				break;
			}
		}
	}
}

bool MainPanel::testLocalFileAccessible(const wxString& filePath)
{
	wxLogNull errorSuppression;

	if (wxFileExists(filePath))
	{
		if (wxIsReadable(filePath))
		{
			return true;
		}
		else
		{
			mStatusText->SetForegroundColour(wxColour(100, 50, 50));
			mStatusText->SetLabelText("Version files can't be read!\nPlease close any file instances and try again.");
			mStatusImage->setFrameTarget(0);
			Layout();
			return false;
		}
	}
	else
	{
		mStatusText->SetForegroundColour(wxColour(100, 50, 50));
		mStatusText->SetLabelText("Version files are missing!");
		mStatusImage->setFrameTarget(0);
		Layout();
		return false;
	}

	errorSuppression.~wxLogNull();
}

bool MainPanel::testEngineFileAccessible(const wxString& filePath, const bool breakWriteLock)
{
	wxLogNull errorSuppression;

	if (wxFileExists(filePath))
	{
		if (breakWriteLock)
		{
			//Break write lock if read only.
			DWORD dwAttrsFile = GetFileAttributes(filePath.wc_str());
			if ((dwAttrsFile & FILE_ATTRIBUTE_READONLY))
			{
				SetFileAttributes(filePath.wc_str(), FILE_ATTRIBUTE_NORMAL);
			}
		}

		if (wxIsWritable(filePath))
		{
			return true;
		}
		else
		{
			mStatusText->SetForegroundColour(wxColour(100, 50, 50));
			mStatusText->SetLabelText("Can't write to unreal files!\nPlease close Unreal Engine if open and try again.");
			mStatusImage->setFrameTarget(0);
			Layout();
			return false;
		}
	}
	else
	{
		return true;
	}

	errorSuppression.~wxLogNull();
}

bool MainPanel::ensureDirectory(const wxString& filePath)
{
	const wxFileName fileName(filePath);
	const wxArrayString fileDirectories = fileName.GetDirs();

	if (fileDirectories.IsEmpty() == false)
	{
		wxLogNull errorSuppression;

		wxString currentDir = fileName.GetVolume() + ":\\" + fileDirectories[0];

		for (unsigned int i{ 1 }; i < fileDirectories.GetCount(); i++)
		{
			currentDir += ("\\" + fileDirectories[i]);
			
			if (wxDirExists(currentDir) == false)
			{
				if (wxFileName::Mkdir(currentDir) == false)
				{
					errorSuppression.~wxLogNull();
					return false;
				}
			}
		}

		errorSuppression.~wxLogNull();
	}
	else
	{
		return false;
	}

	return true;
}

bool MainPanel::shouldIncludeFile(const wxString& filePath, const bool includeSource, const bool includeSymbols) const
{
	const wxFileName fileName(filePath);
	if (fileName.HasExt())
	{
		const wxString extension = fileName.GetExt();
		if (extension == "cpp")
		{
			return includeSource;
		}
		else if (extension == "pdb")
		{
			return includeSymbols;
		}
		else
		{
			return true;
		}
	}
	else
	{
		return true;
	}
}

bool MainPanel::isSourceFile(const wxString& filePath) const
{
	const wxFileName fileName(filePath);
	if (fileName.HasExt())
	{
		const wxString extension = fileName.GetExt();
		if (extension == "cpp")
		{
			return true;
		}
		else if (extension == "h")
		{
			//Ignore if generated.h.
			return !fileName.GetName().Contains(".generated");
		}
		else
		{
			return false;
		}
	}
	else
	{
		return false;
	}
}

wxString MainPanel::getFileName(const wxString& filePath, const bool includeExtension) const
{
	wxFileName fileName(filePath);
	if (includeExtension)
	{
		return fileName.GetName() + "." + fileName.GetExt();
	}
	else
	{
		return fileName.GetName();
	}
}
