from copy import deepcopy
from PySide6.QtCore import Qt, Signal
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
    QCheckBox,
    QComboBox,
    QLineEdit
)

import numpy as np
import regex as re

from UI.Tabs.TabWidget import TabWidget
from UI.UtilsUI import MessageType
from FileOrganizer import FileOrganizer
from StructureFinder import StructureFinder

from UI.UtilsUI import split_with_separators, get_fused_limits

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

class StructureElementWidget(QWidget):
    value_changed_signal = Signal(int, str)

    def __init__(self, struct_id:int, struct_name:str, possible_values:list[str], parent = None):
        super().__init__(parent)

        self.struct_id = struct_id
        self.struct_name = struct_name

        self._setup_UI(struct_name, possible_values)

    def _setup_UI(self, struct_name:str, possible_values:list[str]):
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)

        label = QLabel(struct_name)
        v_layout.addWidget(label)

        self.combo = QComboBox()
        v_layout.addWidget(self.combo)

        self.combo.addItems(possible_values)
        self.combo.currentIndexChanged.connect(self._combo_index_changed)

    def _combo_index_changed(self, index:int):
        self.value_changed_signal.emit(self.struct_id, self.combo.currentText())

    def get_value(self):
        return self.combo.currentText()

    def set_value(self, value:str):
        self.combo.setCurrentText(value)

class StructureSelectionWidget(QWidget):
    value_changed_signal = Signal()

    none_value_str = "None"

    def __init__(self, parent = None):
        super().__init__(parent)

        self.structure_widgets : list[StructureElementWidget] = []
        self.example_structure : list[str] = []

        self._setup_UI()

    def _setup_UI(self):
        self.h_layout = QHBoxLayout()
        self.setLayout(self.h_layout)

    def clear_widget(self):
        for widget in self.structure_widgets:
            widget.deleteLater()
            widget.setParent(None)
        
        self.structure_widgets.clear()

    def setup_structure(self, example_str:str, separator:str, possible_values:list[str]):
        # Get the initial structure
        self.example_str = deepcopy(example_str)

        self.possible_values = deepcopy(possible_values)
        self.possible_values.append(StructureSelectionWidget.none_value_str)

        self.set_separator(separator)

    def set_separator(self, separator:str):
        self.separator = separator
        self.example_structure = self.example_str.split(separator)
        self._actualize_structure()

    def _actualize_structure(self):
        self.clear_widget()

        for i, example_val in enumerate(self.example_structure):
            struct_widget = StructureElementWidget(i, example_val, self.possible_values)
            struct_widget.set_value(StructureSelectionWidget.none_value_str)
            self.h_layout.addWidget(struct_widget)

            self.structure_widgets.append(struct_widget)
            struct_widget.value_changed_signal.connect(self._structure_value_changed)
    
    def _structure_value_changed(self, struct_id:int, value:str):
        adjacent_ids = set([struct_id - 1, struct_id, struct_id + 1])
        for i in range(struct_id, len(self.structure_widgets)):
            if i in adjacent_ids and self.structure_widgets[i].get_value() == value:
                adjacent_ids.add(i+1)
            if i not in adjacent_ids and self.structure_widgets[i].get_value() == value:
                self.structure_widgets[i].set_value(StructureSelectionWidget.none_value_str)

        for i in range(struct_id, 0, -1):
            if i in adjacent_ids and self.structure_widgets[i].get_value() == value:
                adjacent_ids.add(i-1)
            if i not in adjacent_ids and self.structure_widgets[i].get_value() == value:
                self.structure_widgets[i].set_value(StructureSelectionWidget.none_value_str)

        self.value_changed_signal.emit()

    def get_selected_structure_pos(self):
        selected_structure = [widget.get_value() for widget in self.structure_widgets]
        fused_ids = get_fused_limits(selected_structure)
        fused_structure = [selected_structure[start] for start, end in fused_ids]


        index_selected_struct = tuple(fused_structure.index(val) if val in fused_structure else None for val in self.possible_values if val != StructureSelectionWidget.none_value_str)

        return index_selected_struct
    
    def get_fused_example_structure(self):
        selected_structure = [widget.get_value() for widget in self.structure_widgets]
        fused_ids = get_fused_limits(selected_structure)

        fused_example = []
        for start, end in fused_ids:
            fused_example.append(self.separator.join(self.example_structure[start:end+1]))
        
        # fused_example = [[self.example_structure[0]]]
        # previous_value = selected_structure[0]
        # for i in range(1, len(selected_structure)):
        #     if selected_structure[i] == previous_value:
        #         fused_example[-1].append(self.example_structure[i])
        #     else:
        #         fused_example.append([self.example_structure[i]])
        #         previous_value = selected_structure[i]
        
        # fused_example_str = [self.separator.join(fused_group) for fused_group in fused_example]
        return fused_example
        

class StructureSelectionTab(TabWidget):
    """
        Tab to select the structure parameters
    """
    # List of boolean value parameters to ask the user (dictionnary key, display parameter name, parameter default value)
    checkbox_parameters = [
        ("require_ventral_data", "Don't copy if no corresponding ventral view is found", False),
        ("require_video_data", "Don't copy if no corresponding video is found", False)
    ]

    default_separator:str='_'
    separators_separator:str=','

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
        self._structureFinder = StructureFinder()
        self.constraints_dict : dict[str, bool] = dict()
        self.list_widget_dict : dict[str, QListWidget] = dict()

        self._setup_ui()
    
    def _setup_ui(self):
        """
            Setup the UI of the tab
        """
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)

        ### Structure selection
        structure_selection_group = QGroupBox("Structure selection")
        structure_selection_group.setFlat(True)
        v_layout.addWidget(structure_selection_group)

        structure_selection_group_layout = QVBoxLayout()
        structure_selection_group.setLayout(structure_selection_group_layout)

        self.separator_edit = QLineEdit()
        self.separator_edit.setText(StructureSelectionTab.default_separator)
        structure_selection_group_layout.addWidget(self.separator_edit)
        self.separator_edit.textChanged.connect(self._separator_text_changed)

        self.structure_selector = StructureSelectionWidget()
        self.structure_selector.value_changed_signal.connect(self.refresh_names_display)
        structure_selection_group_layout.addWidget(self.structure_selector)
        

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

        ### Names display
        self.name_display_status = QLabel()
        v_layout.addWidget(self.name_display_status, alignment=Qt.AlignmentFlag.AlignCenter)
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

    def _separator_text_changed(self):
        """
            Function called when the user changes the separator text
        """
        separator = self.separator_edit.text()
        try:
            self.structure_selector.set_separator(separator)
            self.refresh_names_display()
        except Exception as e:
            self._update_status_display(f"Error: {e}", MessageType.ERROR)
            print("Error: ", e)

    def setup_widget(self):
        """
            Setup the structure selection widget
        """
        possible_names = self.file_organizer.get_all_filenames()
        longest_example = max(possible_names, key=len)
        separator = self.separator_edit.text()

        try:
            self.structure_selector.setup_structure(longest_example, separator, StructureSelectionTab.delimiters_keywords)
            initial_structure = self.structure_selector.get_fused_example_structure()

            self._structureFinder.set_parameters(possible_names, separator)
            self._structureFinder.find_structure(initial_structure)
        except Exception as e:
            self._update_status_display(f"Error: {e}", MessageType.ERROR)
            print("Error: ", e)
            raise e
        
    def _get_structure_string(self):
        try:
            fused_structure = self.structure_selector.get_fused_example_structure()
            self._structureFinder.find_structure(fused_structure)
            structure_positions = self.structure_selector.get_selected_structure_pos()
            structure_str = self._structureFinder.get_structure_str(*structure_positions, *StructureSelectionTab.delimiters_keywords)
        except Exception as e:
            self._update_status_display(f"Error: {e}", MessageType.ERROR)
            print("Error: ", e)
            structure_str = ""
        
        return structure_str
        
    def refresh_names_display(self):
        """
            Get the names in each list of parameter and actualize the UI of the tab with them
        """
        # Actualize
        # ...

        # Set the constraints in the file organizer
        self.file_organizer.set_constraints(**self.constraints_dict)

        # Set the structure parameters in the file organizer
        structure_str = self._get_structure_string()
        self.file_organizer.set_structure_str_parameters(structure_str)

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
        structure_str = self._get_structure_string()
        self.file_organizer.set_structure_str_parameters(structure_str)

        # Emit the signal to change the tab
        self.change_tab_signal.emit()
