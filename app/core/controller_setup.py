from app.core.editor_trim import EditorTrimController
from app.core.editor_export import EditorExportController
from app.core.editor_clips import EditorClipsController
from app.core.editor_frame import EditorFrameController
from app.core.editor_sequence import EditorSequenceController
from app.core.media_library import MediaLibraryController
from app.core.moment_analysis_controller import MomentAnalysisController


def setup_editor_controllers(window):
    """Создаёт контроллеры, необходимые непосредственно при сборке страницы монтажа."""
    window.editor_trim_controller = EditorTrimController(window)
    window.editor_export_controller = EditorExportController(window)
    window.editor_clips_controller = EditorClipsController(window)
    window.editor_frame_controller = EditorFrameController(window)
    window.editor_sequence_controller = EditorSequenceController(window)


def setup_page_controllers(window):
    """Создаёт контроллеры, которым нужны уже созданные виджеты страниц."""
    window.media_library_controller = MediaLibraryController(window)
    window.moment_analysis_controller = MomentAnalysisController(window)


def setup_controllers(window):
    # Совместимость с прежними вызовами: сначала ранние контроллеры,
    # затем контроллеры, которым нужны готовые страницы.
    setup_editor_controllers(window)
    setup_page_controllers(window)
