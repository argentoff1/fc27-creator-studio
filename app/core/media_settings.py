
def load_media_folders(settings):
    saved_folders = settings.value("media/folders", [])

    if isinstance(saved_folders, str):
        saved_folders = [saved_folders]

    return list(saved_folders)


def save_media_folders(settings, folders):
    settings.setValue(
        "media/folders",
        folders
    )

def load_saved_clips(settings):
    saved_clips = settings.value(
        "editor/exported_clips",
        []
    )

    if isinstance(saved_clips, str):
        saved_clips = [saved_clips]

    return list(saved_clips)


def save_saved_clips(settings, clips):
    settings.setValue(
        "editor/exported_clips",
        clips
    )
