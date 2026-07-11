#pragma once

#include <wx/string.h>
#include <wx/vector.h>

enum EngineStatus : uint8_t
{
	eEng_None = 0,
	eEng_Modify,
	eEng_Add,
	eEng_Remove
};

struct EngineFile
{
	//A path to the custom engine file.
	wxString pathCustom{ wxEmptyString };
	//A path to the default engine file.
	wxString pathDefault{ wxEmptyString };
	//The target folder for the file (relative unreal path).
	wxString pathTarget{ wxEmptyString };
	//The file name when stored. This is the pathTarget name with the addition of a number if there are several files of the same name.
	wxString localName{ wxEmptyString };
};

struct EngineInfo
{
	//The path of the info file.
	wxString infoDir{ wxEmptyString };
	//The version of the custom engine.
	wxString engineVersion{ wxEmptyString };
	//Custom engine parent, all parent files is inherited.
	wxString parentVersion{ wxEmptyString };
	//The unreal version to overwrite.
	wxString unrealVersion{ wxEmptyString };
	//Changelog for this version.
	wxString changelog{ wxEmptyString };

	//The target unreal directory (default value, can be edited by user).
	wxString unrealDir{ wxEmptyString };

	//List of edited files.
	wxVector<EngineFile> files = wxVector<EngineFile>();

	//The modification status of the engine.
	EngineStatus status{ eEng_None };
};