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

class DataSelectionTab(TabWidget):
    """
        Tab to select the data folders
    """
    # List of folder selection parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    folder_selection_parameters : list[tuple[str, str, os.PathLike]] = [
        ("data_folder_path", "Data folder", os.path.abspath('./Data')),
        ("target_folder_path", "Target folder",os.path.abspath('./Output'))
    ]

    # List of extension parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    extension_parameters : list[tuple[str, str, float]] = [ 
        ("csv_extension", "CSV extension", ".csv"),
        ("video_extension", "Video extension", ".mp4")
    ]

    # List of keywords parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    keyword_parameters : list[tuple[str, str, str]] = [
        ("side_keyword", "CSV Side keyword (Keywords contained ONLY in the names of the side view files)", "sideview"),
        ("ventral_keyword", "CSV Ventral keyword (Keywords contained ONLY in the names of the ventral view files)", "ventralview")
    ]
    
    def __init__(self, file_organizer:FileOrganizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.file_organizer = file_organizer
        self.data_selection_dict : dict[str, os.PathLike] = dict()

        self._setup_ui()
    
    def _setup_ui(self):
        """
            Setup the UI of the tab
        """
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)


        ### Folder selection
        folder_selection_group = QGroupBox("Folders selection")
        folder_selection_group.setFlat(True)
        v_layout.addWidget(folder_selection_group)

        folder_form_layout = QFormLayout()
        folder_selection_group.setLayout(folder_form_layout)

        # Instantiate the folder selection widgets
        for key_name, display_str, default_value in DataSelectionTab.folder_selection_parameters:
            self.data_selection_dict[key_name] = default_value

            folder_layout = self._create_select_folder_layout(key_name, default_value, self.data_selection_dict)
            folder_form_layout.addRow(display_str, folder_layout)
        

        ### Parameters selection
        parameters_selection_group = QGroupBox("Parameters")
        parameters_selection_group.setFlat(True)
        v_layout.addWidget(parameters_selection_group)

        parameters_form_layout = QFormLayout()
        parameters_selection_group.setLayout(parameters_form_layout)        

        # Adds these parameters to the form layout
        add_input_to_form_layout(parameters_form_layout, None, DataSelectionTab.extension_parameters, self.data_selection_dict)

        add_input_to_form_layout(parameters_form_layout, None, DataSelectionTab.keyword_parameters, self.data_selection_dict)


        ## Next button
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self._next_btn_clicked)
        v_layout.addWidget(next_btn)

    def _create_select_folder_layout(self, filepath_dict_key:str, default_value:str, dictionary:dict[str, os.PathLike]):
        """
            Returns the layout for a folder selection widget,
            Calling self.select_folder when a new folder is selected
        """
        folder_layout = QHBoxLayout()
        folder_label = QLabel(default_value)
        folder_btn = QPushButton("Select folder")

        folder_btn.clicked.connect(
            lambda : self._select_folder(folder_label, filepath_dict_key, dictionary)
        )
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(folder_btn)

        return folder_layout
    
    def _select_folder(self, label:QLabel, filepath_dict_key:str, dictionary:dict[str, os.PathLike]):
        """
            Asks the user to select a directory, display the result in the label and saves it in self.parameters_dict with the key filepath_dict_key
        """
        file = get_user_folder_path("Select folder", os.path.abspath('.'))
        
        if file is None or file == '':
            return
        
        label.setText(file)
        dictionary[filepath_dict_key] = file

    def _next_btn_clicked(self):
        """
            Called when the next button is clicked
        """
        self.file_organizer.set_and_load_data_parameters(**self.data_selection_dict)
        
        self.change_tab_signal.emit()