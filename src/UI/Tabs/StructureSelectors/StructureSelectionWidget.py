from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QCheckBox
)

import numpy as np
import regex as re

from UI.UtilsUI import MessageType
from FileOrganizer import FileOrganizer

class StructureSelectionWidget(QWidget):
    """
        Tab to select the structure parameters
    """
    # List of boolean value parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    checkbox_parameters = [
        ("require_ventral_data", "Don't copy if no corresponding ventral view is found", False),
        ("require_video_data", "Don't copy if no corresponding video is found", False)
    ]

    # Parameters for the user to make the structure building string
    delimiters_keywords:list[str]=['Group', 'Timepoint', 'Mouse', 'Run']

    # List of parameters names to display in the list widget
    name_list_parameters : list[str] = ["Group", "Timepoint", "Mouse", "Run"]

    def __init__(self, file_organizer:FileOrganizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.file_organizer = file_organizer

        self.constraints_dict : dict[str, bool] = dict()
        self.list_widget_dict : dict[str, QListWidget] = dict()

        self._setup_main_ui()
    
    def _setup_main_ui(self):
        """
            Setup the UI of the tab
        """
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)

        ### Layout filled by child classes to display the structure selection
        self._structure_selection_layout = QVBoxLayout()
        v_layout.addLayout(self._structure_selection_layout)

        ### Constraints selection
        constraints_selection_group = QGroupBox("Constraints")
        constraints_selection_group.setFlat(True)
        v_layout.addWidget(constraints_selection_group)

        constraints_h_layout = QHBoxLayout()
        constraints_selection_group.setLayout(constraints_h_layout)

        # Adds these parameters to the form layout
        for param_key, display_str, default_value in StructureSelectionWidget.checkbox_parameters:
            self.constraints_dict[param_key] = default_value

            checkbox = QCheckBox(display_str)
            checkbox.setChecked(default_value)
            checkbox.stateChanged.connect(
                lambda state, param_key=param_key: self._checkbox_state_changed((state!=0), param_key)
            )

            constraints_h_layout.addWidget(checkbox)

        ### Names display
        self.name_display_status = QLabel()
        v_layout.addWidget(self.name_display_status, alignment=Qt.AlignmentFlag.AlignCenter)
        self._update_status_display("No issue", MessageType.INFORMATION)

        h_layout = QHBoxLayout()
        v_layout.addLayout(h_layout)

        for name in StructureSelectionWidget.name_list_parameters:
            in_v_layout = QVBoxLayout()
            h_layout.addLayout(in_v_layout)

            label = QLabel(name)
            in_v_layout.addWidget(label)

            list_widget = QListWidget()
            self.list_widget_dict[name] = list_widget
            in_v_layout.addWidget(list_widget)

    def setup_widget(self):
        """
            Setup the widget with the parameters in the file organizer
        """
        self.file_organizer.set_delimiters(StructureSelectionWidget.delimiters_keywords)
        self.refresh_names_display()

    def _checkbox_state_changed(self, state:bool, param_key:str):
        """
            Updates the value of the parameter param_key in self.constraints_dict when the checkbox state changes
        """
        self.constraints_dict[param_key] = state
        self.refresh_names_display()
        
    def refresh_names_display(self):
        """
            Get the names in each list of parameter and actualize the UI of the tab with them
        """
        pass

    def _update_status_display(self, message:str, message_type:MessageType):
        """
            Display the error message in the name display status
        """
        self.name_display_status.setText(message)

        if message_type == MessageType.ERROR:
            self.name_display_status.setStyleSheet("font-weight: bold; color: red")
        elif message_type == MessageType.INFORMATION:
            self.name_display_status.setStyleSheet("font-weight: bold")
        elif message_type == MessageType.WARNING:
            self.name_display_status.setStyleSheet("font-weight: bold; color: orange")

    def _actualize_names_display(self, associated_names:np.ndarray[np.ndarray[str]]):
        """
            Actualize the display of the names in the tab

            Args:
                associated_names: List of tuples containing the associated names (batch, dataset, mouse, run)
        """
        # If no element is found, display a warning message
        if associated_names.size == 0:
            self._update_status_display("No element found", MessageType.WARNING)

            # Actualize the list widgets with the names
            for name in StructureSelectionWidget.name_list_parameters:
                self._actualize_list_widget(name, [])
            return
        
        for i, name in enumerate(StructureSelectionWidget.name_list_parameters):
            # Remove duplicates
            names = list(set(associated_names[:,i]))

            # Get the number of associated elements for each name
            associated_numbers = [np.sum(associated_names[:,i] == name) for name in names]
            
            # Add the number of associated elements to the names
            file_names = [f"{name} ({associated_number} elements)" for name, associated_number in zip(names, associated_numbers)]
            
            # Actualize the list widgets with the names
            self._actualize_list_widget(name, file_names)

    def _actualize_list_widget(self, name:str, names_list:list[str]):
        """
            Actualize the content of the list widget with the given name
        """
        list_widget = self.list_widget_dict[name]
        list_widget.clear()
        list_widget.addItems(names_list)

    def refresh_names_display(self, use_regex:bool):
        """
            Get the names in each list of parameter and actualize the UI of the tab with them
        """
        # Get the associated names
        try:
            associated_names = self.file_organizer.get_names(use_regex)
        except re.error as e:
            self._update_status_display(f"Error in the regular expression: {e}", MessageType.ERROR)
            return
        else:
            self._update_status_display("No issue", MessageType.INFORMATION)
        
        self._actualize_names_display(associated_names)