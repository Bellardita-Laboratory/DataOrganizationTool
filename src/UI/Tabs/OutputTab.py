import os
from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox
)

from UI.Tabs.TabWidget import TabWidget
from UI.UtilsUI import MessageType, show_message, add_input_to_form_layout
from FileOrganizer import FileOrganizer
from UI.Tabs.StructureSelectionTab import StructureSelectionTab

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

    # List of boolean value parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    checkbox_parameters = [
        ("require_ventral_data", "Don't copy if no corresponding ventral view is found", False),
        ("require_video_data", "Don't copy if no corresponding video is found", False)
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


        ### Constraints selection
        constraints_selection_group = QGroupBox("Constraints")
        constraints_selection_group.setFlat(True)
        v_layout.addWidget(constraints_selection_group)

        constraints_h_layout = QHBoxLayout()
        constraints_selection_group.setLayout(constraints_h_layout)

        # Adds these parameters to the form layout
        for param_key, display_str, default_value in OutputTab.checkbox_parameters:
            self.output_parameters_dict[param_key] = default_value

            checkbox = QCheckBox(display_str)
            checkbox.setChecked(default_value)
            checkbox.stateChanged.connect(
                lambda state, param_key=param_key: self._checkbox_state_changed((state!=0), param_key)
            )

            constraints_h_layout.addWidget(checkbox)

        ### Organize button
        organize_btn = QPushButton("Organize Files")
        organize_btn.clicked.connect(self._organize_btn_clicked)
        v_layout.addWidget(organize_btn)

    def _checkbox_state_changed(self, state:bool, param_key:str):
        """
            Updates the value of the parameter param_key in self.organize_file_parameters_dict when the checkbox state changes
        """
        self.output_parameters_dict[param_key] = state

    def _organize_btn_clicked(self):
        try:
            self.file_organizer.organize_files(**self.output_parameters_dict,
                                               delimiters_keywords=StructureSelectionTab.delimiters_keywords, delimiter_opener=StructureSelectionTab.delimiter_opener, delimiter_closer=StructureSelectionTab.delimiter_closer)
        except Exception as e:
            show_message(str(e), MessageType.ERROR)
            raise e
        else:
            # Show a message box to inform the user that the files have been organized
            show_message("Files have been organized", MessageType.INFORMATION)
        