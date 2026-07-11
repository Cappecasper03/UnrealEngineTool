#include "FileDropTarget.h"
#include "FileList.h"

FileDropTarget::FileDropTarget(FileList* list) : mList(list)
{
	SetDataObject(new wxFileDataObject);
}

bool FileDropTarget::OnDrop(wxCoord x, wxCoord y)
{
	if (bEnabled)
	{
		return wxFileDropTarget::OnDrop(x, y);
	}
	//Ignore if not enabled.
	else
	{
		//Process a failed event using the list.
		if (mList)
		{
			wxCommandEvent event(EVT_CUSTOM_DROP_FAILED, mList->GetId());
			mList->ProcessWindowEvent(event);
		}
		return false;
	}
}

bool FileDropTarget::OnDropFiles(wxCoord x, wxCoord y, const wxArrayString& filenames)
{
	if (mList)
	{
		for (uint32_t i{ 0 }; i < filenames.size(); i++)
		{
			wxString customFile{ wxEmptyString };
			wxString defaultFile{ wxEmptyString };
			wxString relativePath{ wxEmptyString };

			//Make sure the file is part of a build directory.
			if (filenames[i].starts_with(mCustomPath))
			{
				relativePath = filenames[i].Mid(mCustomPath.length());

				customFile = mCustomPath + relativePath;
				defaultFile = mDefaultPath + relativePath;
			}
			else if (filenames[i].starts_with(mDefaultPath))
			{
				relativePath = filenames[i].Mid(mDefaultPath.length());

				customFile = mCustomPath + relativePath;
				defaultFile = mDefaultPath + relativePath;
			}

			if (customFile.empty() == false)
			{
				//Clear path if invalid.
				if (wxFileExists(customFile) == false)
				{
					customFile = wxEmptyString;
				}
			}
			if (defaultFile.empty() == false)
			{
				//Clear path if invalid.
				if (wxFileExists(defaultFile) == false)
				{
					defaultFile = wxEmptyString;
				}
			}

			//If there is atleast one valid file, add it to the list..
			if (customFile.empty() == false || defaultFile.empty() == false)
			{
				EngineFile file;
				file.pathCustom = customFile;
				file.pathDefault = defaultFile;
				file.pathTarget = relativePath;
				mList->addItem(file);
			}
		}
	}

	//Don't need anything else.
	return false;
}

void FileDropTarget::setPaths(const wxString& customPath, const wxString& defaultPath)
{
	setCustomPath(customPath, false);
	setDefaultPath(defaultPath, false);

	checkPaths();
}

void FileDropTarget::setCustomPath(const wxString& path, const bool refresh)
{
	mCustomPath = path;
	if (mCustomPath.empty() == false)
	{
		//Make sure the path exist.
		if (wxDirExists(mCustomPath))
		{
			//Make sure the path is valid.
			if (wxFileExists(mCustomPath + mBuildTestPath) == false)
			{
				mCustomPath = wxEmptyString;
			}
		}
		else
		{
			mCustomPath = wxEmptyString;
		}
	}

	if (refresh)
	{
		checkPaths();
	}
}

void FileDropTarget::setDefaultPath(const wxString& path, const bool refresh)
{
	mDefaultPath = path;
	if (mDefaultPath.empty() == false)
	{
		//Make sure the path exist.
		if (wxDirExists(mDefaultPath))
		{
			//Make sure the path is valid.
			if (wxFileExists(mDefaultPath + mBuildTestPath) == false)
			{
				mDefaultPath = wxEmptyString;
			}
		}
		else
		{
			mDefaultPath = wxEmptyString;
		}
	}

	if (refresh)
	{
		checkPaths();
	}
}

void FileDropTarget::checkPaths()
{
	if (mCustomPath.empty() == false && mDefaultPath.empty() == false)
	{
		if (mCustomPath != mDefaultPath)
		{
			bEnabled = true;
		}
		else
		{
			bEnabled = false;
		}
		
	}
	else
	{
		bEnabled = false;
	}
}
