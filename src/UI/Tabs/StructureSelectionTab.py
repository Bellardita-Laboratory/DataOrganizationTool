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
        self._subformats = {}

    def add_subformat(self, name, format):
        self._subformats[name] = format

    def add_mapping(self, pattern, format):
        self._mappings[pattern] = format

    def highlightBlock(self, text):
        for pattern, format in self._mappings.items():
            for _match in re.finditer(pattern, text):
                start, end = _match.span()
                self.setFormat(start, end - start, format)

                nested_groups = _match.capturesdict()
                for group_name in nested_groups:
                    if group_name in self._subformats:
                        group_start, group_end = _match.span(group_name)
                        self.setFormat(group_start, group_end - group_start, self._subformats[group_name])

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
        """Structure of the file names: use '(' and ')' to capture a group (A group can be Group, Timepoint, Mouse or Run)
The structure of the captured group can be specified with ':'
eg: To capture a group name that doesn't contain '_' : (Group:[^_]*)_(Timepoint)_(Mouse)_(Run)""",
        "Dual_side_and_ventral_(Mouse)_Post_(Timepoint:(WT|MU_C(x|X)|MU_Saline|.*))_(Group)_Run(Run:[0-9])"
    )

    delimiter_description = """Structure supports regular expressions. 
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
    - If the file name is 'Group1_Timepoint3_Mouse245_Run78', we can use 'Group(Group)_Timepoint(Timepoint)_Mouse(Mouse)_Run(Run)'
        It will find '1' for the group name, '3' for the timepoint name, '245' for the mouse name and '78' for the run name
                                        """

    # Parameters for the user to make the structure building string
    delimiters_keywords:list[str]=['Group', 'Timepoint', 'Mouse', 'Run']
    delimiter_opener:str='('
    delimiter_closer:str=')'
    delimiter_structure_start:str=':'

    # List of parameters names to display in the list widget
    name_list_parameters : list[str] = ["Group", "Timepoint", "Mouse", "Run"]

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

        delimiters_description = QLabel(StructureSelectionTab.delimiter_description)
        delimiters_description.setWordWrap(True)
        delimiter_v_layout.addWidget(delimiters_description)

        # Create the input for the structure string
        structure_str_instructions = QLabel(StructureSelectionTab.structure_str_paramters[1])
        structure_str_instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delimiter_v_layout.addWidget(structure_str_instructions)

        self.structure_str_input = QPlainTextEdit(StructureSelectionTab.structure_str_paramters[2])
        self.structure_str_input.setFixedHeight(30)
        delimiter_v_layout.addWidget(self.structure_str_input)

        # Connect the signal to actualize the input dict and the names display
        self.structure_str_input.textChanged.connect(self.refresh_names_display)

        ### Highlighter
        # Create the highlighter
        self.highlighter = Highlighter()

        # Create the subgroups text format for the highlighter
        sub_format = QTextCharFormat()
        sub_format.setFontItalic(True)
        sub_format.setForeground(Qt.darkGreen)

        # Add the format of the subgroups to the highlighter
        self.highlighter.add_subformat("sub_format", sub_format)

        # Create the keyword text format for the highlighter
        kw_format = QTextCharFormat()
        kw_format.setFontItalic(True)
        kw_format.setForeground(Qt.red)

        # Add the mappings for highlighting the delimiters
        for keyword in StructureSelectionTab.delimiters_keywords:
            # Add the mapping for the keyword
            #   The regex pattern is used to match any character and an even number of parentheses ((?R) is used to match the outer pattern itself (recursive), ie an open and closed parenthesis with any character in between)
            structured_delimited_keyword = f"\\{StructureSelectionTab.delimiter_opener}{keyword}(?P<sub_format>{StructureSelectionTab.delimiter_structure_start}[^)(]*(?P<rs>\\((?:[^)(]+|(?P>rs))*\\))?[^)()]*)?\\{StructureSelectionTab.delimiter_closer}"
            self.highlighter.add_mapping(structured_delimited_keyword, kw_format)

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
            for name in StructureSelectionTab.name_list_parameters:
                self._actualize_list_widget(name, [])
            return
        
        for i, name in enumerate(StructureSelectionTab.name_list_parameters):
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

    def _next_btn_clicked(self):
        """
            Function called when the user clicks on the next button
        """
        # Set the structure parameters in the file organizer
        self.file_organizer.set_structure_str_parameters(**self.structure_str_parameters_dict)

        # Emit the signal to change the tab
        self.change_tab_signal.emit()
