from typing import override
from PySide6.QtCore import Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QVBoxLayout,
    QLabel,
    QPlainTextEdit
)

import regex as re

from FileOrganizer import FileOrganizer
from UI.Tabs.StructureSelectors.StructureSelectionWidget import StructureSelectionWidget

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

class RegexStructureSelectionWidget(StructureSelectionWidget):
    """
        Tab to select the structure parameters
    """
    structure_str_paramters : tuple[str, str, str] = (
        "structure_str", 
        """Structure of the file names: use '(' and ')' to capture a group (A group can be Batch, Group, Mouse or Run)
The structure of the captured group can be specified with ':'
eg: To capture a group name that doesn't contain '_' : (Batch:[^_]*)_(Group)_(Mouse)_(Run)""",
        "Dual_side_and_ventral_(Mouse)_Post_(Group:(WT|MU_C(x|X)|MU_Saline|.*))_(Batch)_Run(Run:[0-9])"
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
    - If the file name is 'Batch1_Group3_Mouse245_Run78', we can use 'Batch(Batch)_Group(Group)_Mouse(Mouse)_Run(Run)'
        It will find '1' for the batch name, '3' for the group name, '245' for the mouse name and '78' for the run name
                                        """

    # Parameters for the user to make the structure building string
    delimiter_opener:str='('
    delimiter_closer:str=')'
    delimiter_structure_start:str=':'

    def __init__(self, file_organizer:FileOrganizer, parent: QWidget | None = None) -> None:
        super().__init__(file_organizer, parent)

        self.structure_str_parameters_dict : dict[str, str] = dict()

        self._setup_ui()
    
    def _setup_ui(self):
        """
            Setup the UI of the tab
        """
        ### Delimiters selection
        delimiters_selection_group = QGroupBox("Delimiters")
        delimiters_selection_group.setFlat(True)
        self._structure_selection_layout.addWidget(delimiters_selection_group)

        delimiter_v_layout = QVBoxLayout()
        delimiters_selection_group.setLayout(delimiter_v_layout)

        delimiters_description = QLabel(RegexStructureSelectionWidget.delimiter_description)
        delimiters_description.setWordWrap(True)
        delimiter_v_layout.addWidget(delimiters_description)

        # Create the input for the structure string
        structure_str_instructions = QLabel(RegexStructureSelectionWidget.structure_str_paramters[1])
        structure_str_instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delimiter_v_layout.addWidget(structure_str_instructions)

        self.structure_str_input = QPlainTextEdit(RegexStructureSelectionWidget.structure_str_paramters[2])
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
        sub_format.setForeground(Qt.GlobalColor.darkGreen)

        # Add the format of the subgroups to the highlighter
        self.highlighter.add_subformat("sub_format", sub_format)

        # Create the keyword text format for the highlighter
        kw_format = QTextCharFormat()
        kw_format.setFontItalic(True)
        kw_format.setForeground(Qt.GlobalColor.red)

        # Add the mappings for highlighting the delimiters
        for keyword in RegexStructureSelectionWidget.delimiters_keywords:
            # Add the mapping for the keyword
            #   The regex pattern is used to match any character and an even number of parentheses ((?R) is used to match the outer pattern itself (recursive), ie an open and closed parenthesis with any character in between)
            structured_delimited_keyword = f"\\{RegexStructureSelectionWidget.delimiter_opener}{keyword}(?P<sub_format>{RegexStructureSelectionWidget.delimiter_structure_start}[^)(]*(?P<rs>\\((?:[^)(]+|(?P>rs))*\\))?[^)()]*)?\\{RegexStructureSelectionWidget.delimiter_closer}"
            self.highlighter.add_mapping(structured_delimited_keyword, kw_format)

        self.highlighter.setDocument(self.structure_str_input.document())

    @override
    def setup_widget(self):
        """
            Setup the widget with the parameters in the file organizer
        """
        self.file_organizer.set_delimiters(
            delimiters_keywords=StructureSelectionWidget.delimiters_keywords,
            delimiter_opener=RegexStructureSelectionWidget.delimiter_opener,
            delimiter_closer=RegexStructureSelectionWidget.delimiter_closer,
            delimiter_structure_start=RegexStructureSelectionWidget.delimiter_structure_start
        )

        super().setup_widget()

    def _actualize_input_dict(self):
        """
            Actualize the input name display
        """
        new_text = self.structure_str_input.toPlainText()
        self.structure_str_parameters_dict[RegexStructureSelectionWidget.structure_str_paramters[0]] = new_text
        
    @override
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

        super().refresh_names_display(use_regex=True)
