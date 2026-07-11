#pragma once
#include <wx/Panel.h>

#include "EngineInfo.h"

class wxButton;
class wxBitmapButton;
class wxDirPickerCtrl;
class wxTextCtrl;
class StatusImage;
class wxStaticText;
class wxChoice;

class MainPanel : public wxPanel
{
public:
	MainPanel(wxWindow* parent);
	~MainPanel();

private:
	//Find and setup all installed versions of the engines.
	void SetupVersions();

	//Called when a version is selected by the user.
	void onVersionSelected(wxCommandEvent& event);

	//Add a engine version from a info file. Returns true if a file was added.
	bool readVersion(const wxString filePath);
	//Save a engine version to a info file. Returns true if the file was saved.
	bool writeVersion(const EngineInfo& versionInfo);

	//Move all engine files relative to the project.
	bool setupLocalEngineFiles(EngineInfo& versionInfo);
	//Remove all files for a given engine.
	bool removeLocalEngineFiles(const uint32_t engineIndex);
	//Remove all files in a directory
	bool removeDirectoryFiles(const wxString& dirPath);

	//On button pressed to open settings dialog.
	void onButtonSettings(wxCommandEvent& event);
	//On button pressed to open info dialog.
	void onButtonInfo(wxCommandEvent& event);

	//On button pressed to update engine to custom engine.
	void onButtonCustom(wxCommandEvent& event);
	//On button pressed to update engine to default engine.
	void onButtonDefault(wxCommandEvent& event);

	void onShowStatusContextMenu(wxMouseEvent& event);
	void onStatusContextMenuSelected(wxCommandEvent& event);

	//Start replacing the engine files.
	void replaceEngineFiles(const bool customEngine, const uint32_t engineIndex);
	//Get all engine files needed for a engine modification. This is called recursivly for parent versions.
	void getEngineFiles(const bool customEngine, const uint32_t engineIndex, const bool includeSource, const bool includeSymbols, wxVector<wxString>& filesToMoveFrom, wxVector<wxString>& filesToMoveTo, wxVector<wxString>& filesToRemove, wxVector<wxString>& filesToIgnore) const;
	//Get all engine source files (.h/.cpp) needed for a engine modification. This is called recursivly for parent versions.
	void getEngineSourceFiles(const bool customEngine, const uint32_t engineIndex, wxVector<wxString>& filesToMoveFrom, wxVector<wxString>& filesToMoveTo, wxVector<wxString>& filesToRemove, wxVector<wxString>& filesToIgnore) const;

	//Test if a local file can be copied, if not or the file does not exist it sends an error and return false.
	bool testLocalFileAccessible(const wxString& filePath);
	//Test if a engine file can be written over or does not exist, if not it sends an error and returns false.
	bool testEngineFileAccessible(const wxString& filePath, const bool breakWriteLock = true);
	//Make sure the folder a file is in exists, if not create it.
	bool ensureDirectory(const wxString& filePath);

	//Test if a file is a debug source (.cpp) or a symbols file (.pdb) and return false if they are and should not be included.
	bool shouldIncludeFile(const wxString& filePath, const bool includeSource, const bool includeSymbols) const;
	//Test if a file is a source file (.h/.cpp).
	bool isSourceFile(const wxString& filePath) const;

	//Get the filename from a file path.
	wxString getFileName(const wxString& filePath, const bool includeExtension = true) const;


	wxDirPickerCtrl* mEngineDir{ nullptr };
	wxChoice* mVersionPicker{ nullptr };

	wxBitmapButton* mSettingsButton{ nullptr };
	wxBitmapButton* mInfoButton{ nullptr };

	wxTextCtrl* mChangelogText{ nullptr };

	wxButton* mCustomButton{ nullptr };
	wxButton* mDefaultButton{ nullptr };

	StatusImage* mStatusImage{ nullptr };
	wxStaticText* mStatusText{ nullptr };

	wxVector<EngineInfo> mEngineVersions = wxVector<EngineInfo>();

	wxArrayString mVersionStrings;

	bool bSourceMode{ false };

	//Helper path used to ease adding engine files.
	wxString mRockPocketHelperPath{ wxEmptyString };
	//Helper path used to ease adding engine files.
	wxString mUnrealHelperPath{ wxEmptyString };

	//The relative program path to where the versions are located.
	const wxString mVersionsPath{ "\\Versions\\" };
	//The relative engine version path to where the custom engine files are located.
	const wxString mCustomEnginePath{ "\\Custom\\" };
	//The relative engine version path to where the default engine files are located.
	const wxString mDefaultEnginePath{ "\\Default\\" };

	//Path to test if the engine location is valid.
	const wxString mEngineTestPath{ "\\Engine\\Binaries\\Win64\\UnrealEditor-Engine.dll" };
	//Path to test if the user has source code installed.
	const wxString mSourceTestPath{ "\\Engine\\Source\\Runtime\\Engine\\Private\\Actor.cpp" };
	//Path to test if the user has debugging symbols installed.
	const wxString mSymbolTestPath{ "\\Engine\\Binaries\\Win64\\UnrealEditor-Engine.pdb" };
};