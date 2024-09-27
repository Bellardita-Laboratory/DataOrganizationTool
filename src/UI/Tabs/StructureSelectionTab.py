import os
from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton
)

from UI.Tabs.TabWidget import TabWidget
from UI.UtilsUI import get_user_folder_path, add_input_to_form_layout
from FileOrganizer import FileOrganizer

class StructureSelectionTab(TabWidget):
    """
        Tab to select the structure parameters
    """
    # List of structure parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    structure_parameters : list[tuple[str, str, str]] = [
        ("default_batch_name", "Default batch name (Name of the batch folder to create in case no batch name is found from the data's file name)", "Batch")
    ]

    # List of delimiters parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    delimiters_parameters : dict[tuple[str, str, list[tuple[str,str]]]] = [
        ("dataset_name_delimiters", "Dataset name delimiters (The name of the dataset is between 'Start' and 'End' in the file name)", [("Start", "CnF_"), ("End", "_Test")]),
        ("mouse_name_delimiters", "Mouse name delimiters (The name of the mouse is between 'Start' and 'End' in the file name)", [("Start", "ventral_"), ("End", "_CnF")]),
        ("run_name_delimiters", "Run name delimiters (The name of the run is between 'Start' and 'End' in the file name)", [("Start", "Treadmill"), ("End", "DLC")]),
        ("batch_name_delimiters", "Batch name delimiters (The name of the batch is between 'Start' and 'End' in the file name)", [("Start", ''), ("End", '')])
    ]

    def __init__(self, file_organizer:FileOrganizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.file_organizer = file_organizer
        self.structure_parameters_dict : dict[str, str|tuple[str,str]] = dict()

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
        add_input_to_form_layout(parameters_form_layout, None, StructureSelectionTab.structure_parameters, self.structure_parameters_dict)


        ### Delimiters selection
        delimiters_selection_group = QGroupBox("Delimiters")
        delimiters_selection_group.setFlat(True)
        v_layout.addWidget(delimiters_selection_group)

        delimiter_v_layout = QVBoxLayout()
        delimiters_selection_group.setLayout(delimiter_v_layout)

        delimiters_description = QLabel("""Delimiters support regular expressions. 
                                        - Use '.' for any character
                                        - Use '*' for repeating the previous character 0 or more times
                                        - Use '+' for repeating the previous character 1 or more times
                                        - Use '?' for repeating the previous character 0 or 1 time
                                        - Use '()' for grouping characters
                                        - Use '[' and ']' for specifying a set of characters (eg [0-9] for any digit)
                                        - Use '^' for negating a set of characters (eg [^0-9] for any character that is not a digit)
                                        - Use '\\' to escape special characters
                                        """)
        delimiters_description.setWordWrap(True)
        delimiter_v_layout.addWidget(delimiters_description)

        delimiters_form_layout = QFormLayout()
        delimiter_v_layout.addLayout(delimiters_form_layout)

        # Adds these parameters to the form layout
        add_input_to_form_layout(delimiters_form_layout, None, StructureSelectionTab.delimiters_parameters, self.structure_parameters_dict)

        # Next button
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self._next_btn_clicked)
        v_layout.addWidget(next_btn)

    def actualize_UI(self):
        """
            Actualize the UI of the tab
        """
        pass

    def _next_btn_clicked(self):
        """
            Function called when the user clicks on the next button
        """
        # Check if the batch delimiters are empty, if so set them to None
        batch_name_delimiters = self.structure_parameters_dict["batch_name_delimiters"]
        if batch_name_delimiters is not None and batch_name_delimiters[0] == '' and batch_name_delimiters[1] == '':
            self.structure_parameters_dict["batch_name_delimiters"] = None
        
        # Save the structure parameters
        self.file_organizer.set_structure_parameters(**self.structure_parameters_dict)

        # Emit the signal to change the tab
        self.change_tab_signal.emit()