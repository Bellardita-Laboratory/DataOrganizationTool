from PySide6.QtCore import Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QPlainTextEdit,
    QCheckBox
)

import numpy as np
import regex as re

from UI.Tabs.TabWidget import TabWidget
from UI.UtilsUI import MessageType
from FileOrganizer import FileOrganizer

class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        QSyntaxHighlighter.__init__(self, parent)

        self._mappings = {}

    def add_mapping(self, pattern, format):
        self._mappings[pattern] = format

    def highlightBlock(self, text):
        for pattern, format in self._mappings.items():
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, format)

class StructureSelectionTab(TabWidget):
    """
        Tab to select the structure parameters
    """
    # List of boolean value parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    checkbox_parameters = [
        ("require_ventral_data", "Don't copy if no corresponding ventral view is found", False),
        ("require_video_data", "Don't copy if no corresponding video is found", False)
    ]

    structure_str_paramters : tuple[str, str, str] = (
        "structure_str", 
        """Structure of the file names: use '(' and ')' to capture a group
    A group can be Batch, Dataset, Mouse or Run
         eg: (Batch)_(Dataset)_(Mouse)_(Run)""", 
        "_Mouse(Mouse)_CnF_(Dataset)[_Test]?_(Batch)_[L|l]eft_Run(Run)DLC"
    )

    # Parameters for the user to make the structure building string
    delimiters_keywords:list[str]=['Batch', 'Dataset', 'Mouse', 'Run']
    delimiter_opener:str='('
    delimiter_closer:str=')'
    delimiter_structure_start:str=':'

    # List of parameters names to display in the list widget
    name_list_parameters : list[str] = ["Batch", "Dataset", "Mouse", "Run"]

    def __init__(self, file_organizer:FileOrganizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.file_organizer = file_organizer
        self.constraints_dict : dict[str, bool] = dict()
        self.structure_str_parameters_dict : dict[str, str] = dict()
        self.list_widget_dict : dict[str, QListWidget] = dict()

        self._setup_ui()
    
    def _setup_ui(self):
        """
            Setup the UI of the tab
        """
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)

        ### Constraints selection
        constraints_selection_group = QGroupBox("Constraints")
        constraints_selection_group.setFlat(True)
        v_layout.addWidget(constraints_selection_group)

        constraints_h_layout = QHBoxLayout()
        constraints_selection_group.setLayout(constraints_h_layout)

        # Adds these parameters to the form layout
        for param_key, display_str, default_value in StructureSelectionTab.checkbox_parameters:
            self.constraints_dict[param_key] = default_value

            checkbox = QCheckBox(display_str)
            checkbox.setChecked(default_value)
            checkbox.stateChanged.connect(
                lambda state, param_key=param_key: self._checkbox_state_changed((state!=0), param_key)
            )

            constraints_h_layout.addWidget(checkbox)

        ### Delimiters selection
        delimiters_selection_group = QGroupBox("Delimiters")
        delimiters_selection_group.setFlat(True)
        v_layout.addWidget(delimiters_selection_group)

        delimiter_v_layout = QVBoxLayout()
        delimiters_selection_group.setLayout(delimiter_v_layout)

        delimiters_description = QLabel("""Structure supports regular expressions. 
                                        - Use '.' for any character
                                        - Use '*' for repeating the previous character 0 or more times
                                        - Use '+' for repeating the previous character 1 or more times
                                        - Use '?' for repeating the previous character 0 or 1 time
                                        - Use '[' and ']' for specifying a set of characters (eg [0-9] for any digit)
                                        - Use '^' for negating a set of characters (eg [^0-9] for any character that is not a digit)
                                        - Use '\\' to escape special characters
                                        - Use '|' for or (eg 'a|b' for 'a' or 'b')
                                        - Use '^' at the start to specify the start of the string
                                        - Use '$' at the end to specify the end of the string

Examples:
    - If the file name is 'Batch1_Dataset3_Mouse245_Run78', we can use 'Batch(Batch)_Dataset(Dataset)_Mouse(Mouse)_Run(Run)'
        It will find '1' for the batch name, '3' for the dataset name, '245' for the mouse name and '78' for the run name
                                        """
        )
        delimiters_description.setWordWrap(True)
        delimiter_v_layout.addWidget(delimiters_description)

        delimiters_form_layout = QFormLayout()
        delimiter_v_layout.addLayout(delimiters_form_layout)

        # Create the input for the structure string
        self.structure_str_input = QPlainTextEdit(StructureSelectionTab.structure_str_paramters[2])
        self.structure_str_input.setFixedHeight(30)

        # Connect the signal to actualize the input dict and the names display
        self.structure_str_input.textChanged.connect(self.refresh_names_display)
        
        delimiters_form_layout.addRow(StructureSelectionTab.structure_str_paramters[1], self.structure_str_input)

        # Create the highlighter
        self.highlighter = Highlighter()

        # Add the mappings for highlighting the delimiters
        for keyword in StructureSelectionTab.delimiters_keywords:
            delimited_keyword = f"\\{StructureSelectionTab.delimiter_opener}{keyword}\\{StructureSelectionTab.delimiter_closer}"
            
            kw_format = QTextCharFormat()
            kw_format.setFontItalic(True)
            kw_format.setForeground(Qt.red)
            self.highlighter.add_mapping(delimited_keyword, kw_format)

        self.highlighter.setDocument(self.structure_str_input.document())


        ### Names display
        self.name_display_status = QLabel()
        v_layout.addWidget(self.name_display_status, alignment=Qt.AlignCenter)
        self._update_status_display("No issue", MessageType.INFORMATION)

        h_layout = QHBoxLayout()
        v_layout.addLayout(h_layout)

        for name in StructureSelectionTab.name_list_parameters:
            in_v_layout = QVBoxLayout()
            h_layout.addLayout(in_v_layout)

            label = QLabel(name)
            in_v_layout.addWidget(label)

            list_widget = QListWidget()
            self.list_widget_dict[name] = list_widget
            in_v_layout.addWidget(list_widget)

        # Next button
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self._next_btn_clicked)
        v_layout.addWidget(next_btn)

    def _checkbox_state_changed(self, state:bool, param_key:str):
        """
            Updates the value of the parameter param_key in self.constraints_dict when the checkbox state changes
        """
        self.constraints_dict[param_key] = state
        self.refresh_names_display()

    def _actualize_input_dict(self):
        """
            Actualize the input name display
        """
        new_text = self.structure_str_input.toPlainText()
        self.structure_str_parameters_dict[StructureSelectionTab.structure_str_paramters[0]] = new_text
        
    def refresh_names_display(self):
        """
            Get the names in each list of parameter and actualize the UI of the tab with them
        """
        # Actualize the structure string
        self._actualize_input_dict()

        # Set the constraints in the file organizer
        self.file_organizer.set_constraints(**self.constraints_dict)

        # Set the structure parameters in the file organizer
        self.file_organizer.set_structure_str_parameters(**self.structure_str_parameters_dict)

        # Get the associated names
        try:
            associated_names = self.file_organizer.get_names(StructureSelectionTab.delimiters_keywords, 
                                                             StructureSelectionTab.delimiter_opener, StructureSelectionTab.delimiter_closer,
                                                             StructureSelectionTab.delimiter_structure_start)
        except re.error as e:
            self._update_status_display(f"Error in the regular expression: {e}", MessageType.ERROR)
            return
        else:
            self._update_status_display("No issue", MessageType.INFORMATION)
        
        self._actualize_names_display(associated_names)

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
            self._actualize_list_widget("Batch", [])
            self._actualize_list_widget("Dataset", [])
            self._actualize_list_widget("Mouse", [])
            self._actualize_list_widget("Run", [])
            return

        # Remove duplicates
        batch_names = list(set(associated_names[:,0]))
        dataset_names = list(set(associated_names[:,1]))
        mouse_names = list(set(associated_names[:,2]))
        run_names = list(set(associated_names[:,3]))

        # Get the number of associated elements for each name
        associated_batch_numbers = [np.sum(associated_names[:,0] == batch_name) for batch_name in batch_names]
        associated_dataset_numbers = [np.sum(associated_names[:,1] == dataset_name) for dataset_name in dataset_names]
        associated_mouse_numbers = [np.sum(associated_names[:,2] == mouse_name) for mouse_name in mouse_names]
        associated_run_numbers = [np.sum(associated_names[:,3] == run_name) for run_name in run_names]

        # Add the number of associated elements to the names
        batch_names = [f"{batch_name} ({associated_number} elements)" for batch_name, associated_number in zip(batch_names, associated_batch_numbers)]
        dataset_names = [f"{dataset_name} ({associated_number} elements)" for dataset_name, associated_number in zip(dataset_names, associated_dataset_numbers)]
        mouse_names = [f"{mouse_name} ({associated_number} elements)" for mouse_name, associated_number in zip(mouse_names, associated_mouse_numbers)]
        run_names = [f"{run_name} ({associated_number} elements)" for run_name, associated_number in zip(run_names, associated_run_numbers)]

        # Actualize the list widgets with the names
        self._actualize_list_widget("Batch", batch_names)
        self._actualize_list_widget("Dataset", dataset_names)
        self._actualize_list_widget("Mouse", mouse_names)
        self._actualize_list_widget("Run", run_names)

    def _actualize_list_widget(self, name:str, names_list:list[str]):
        """
            Actualize the content of the list widget with the given name
        """
        list_widget = self.list_widget_dict[name]
        list_widget.clear()
        list_widget.addItems(names_list)

    def _next_btn_clicked(self):
        """
            Function called when the user clicks on the next button
        """
        # Set the structure parameters in the file organizer
        self.file_organizer.set_structure_str_parameters(**self.structure_str_parameters_dict)

        # Emit the signal to change the tab
        self.change_tab_signal.emit()
