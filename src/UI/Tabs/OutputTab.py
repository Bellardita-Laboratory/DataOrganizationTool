from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QFormLayout,
    QVBoxLayout,
    QPushButton
)

from UI.Tabs.TabWidget import TabWidget
from UI.UtilsUI import MessageType, show_message, add_input_to_form_layout
from FileOrganizer import FileOrganizer

class OutputTab(TabWidget):
    """
        Tab to select the output parameters
    """
    # List of folder names to ask the user (dictionnary key, display parameter name, parameter default value)
    folder_name_parameters : list[tuple[str, str, float]] = [
        ("side_folder_name", "Side folder name (Name of the side view folder to create)", "side_view_analysis"),
        ("ventral_folder_name", "Ventral folder name (Name of the ventral view folder to create)", "ventral_view_analysis"),
        ("video_folder_name", "Video folder name (Name of the video folder to create)", "Video")
    ]

    def __init__(self, file_organizer:FileOrganizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.file_organizer = file_organizer
        self.output_parameters_dict : dict[str, str] = dict()

        self._setup_ui()
    
    def _setup_ui(self):
        """
            Setup the UI of the tab
        """
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)

        ### Parameters selection
        parameters_selection_group = QGroupBox("Parameters")
        parameters_selection_group.setFlat(True)
        v_layout.addWidget(parameters_selection_group)

        parameters_form_layout = QFormLayout()
        parameters_selection_group.setLayout(parameters_form_layout)

        # Adds these parameters to the form layout
        add_input_to_form_layout(parameters_form_layout, None, OutputTab.folder_name_parameters, self.output_parameters_dict)

        ### Organize button
        organize_btn = QPushButton("Organize Files")
        organize_btn.clicked.connect(self._organize_btn_clicked)
        v_layout.addWidget(organize_btn)

    def _organize_btn_clicked(self):
        try:
            self.file_organizer.organize_files(**self.output_parameters_dict)
        except Exception as e:
            show_message(str(e), MessageType.ERROR)
            raise e
        else:
            # Show a message box to inform the user that the files have been organized
            show_message("Files have been organized", MessageType.INFORMATION)
        