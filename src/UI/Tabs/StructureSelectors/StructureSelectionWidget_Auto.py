from copy import deepcopy
from typing import override
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
)

from UI.Tabs.StructureSelectors.StructureSelectionWidget import StructureSelectionWidget
from UI.UtilsUI import MessageType
from FileOrganizer import FileOrganizer
from StructureFinder import StructureFinder

from UI.UtilsUI import (
    split_with_separators, 
    get_fused_limits, 
    NoWheelComboBox,
    FlowLayout
)

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
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.combo = NoWheelComboBox()
        v_layout.addWidget(self.combo)

        self.combo.addItems(possible_values)
        self.combo.currentIndexChanged.connect(self._combo_index_changed)

    def _combo_index_changed(self, index:int):
        self.value_changed_signal.emit(self.struct_id, self.combo.currentText())

    def get_value(self):
        return self.combo.currentText()

    def set_value(self, value:str):
        self.combo.setCurrentText(value)

class StructureSelectorWidget(QWidget):
    value_changed_signal = Signal()

    none_value_str = "None"

    def __init__(self, parent = None):
        super().__init__(parent)

        self.structure_widgets : list[StructureElementWidget] = []
        self.example_structure : list[str] = []

        self._setup_UI()

    def _setup_UI(self):
        self.h_layout = FlowLayout()
        self.setLayout(self.h_layout)

    def clear_widget(self):
        """
            Clear the structure widget
        """
        for widget in self.structure_widgets:
            widget.deleteLater()
            widget.setParent(None)
        
        self.structure_widgets.clear()

    def setup_structure(self, example_str:str, separators:list[str], possible_values:list[str]):
        """
            Setup the structure widget with the given example structure string and possible values
        """
        # Save the example structure and possible values (with the None value)
        self.example_str = deepcopy(example_str)
        self.possible_values = deepcopy(possible_values)
        self.possible_values.append(StructureSelectorWidget.none_value_str)

        # Set the separators and actualize the structure widget
        self.set_separators(separators)

    def set_separators(self, separators:list[str]):
        """
            Set the separators used to split the example structure string, and actualize the structure widget with the new separators
        """
        # Remove empty separators
        separators = [separator for separator in separators if separator != ""]
        if len(separators) == 0:
            raise ValueError("No separator given")
        
        self.separators = separators
        
        self._actualize_structure()

    def set_representative(self, representative:str):
        """
            Set the representative of the structure widget
        """
        self.example_str = deepcopy(representative)
        self._actualize_structure()

    def actualize_example_structure(self):
        """
            Actualize the example structure with the current separators and example_str
        """
        self.example_structure, self.example_limits = split_with_separators(self.example_str, self.separators)

    def _actualize_structure(self):
        """
            Actualize the structure widget with the current example structure
        """
        self.clear_widget()

        # Update the example structure with the current separators
        self.actualize_example_structure()

        for i, example_val in enumerate(self.example_structure):
            struct_widget = StructureElementWidget(i, example_val, self.possible_values)
            struct_widget.set_value(StructureSelectorWidget.none_value_str)
            self.h_layout.addWidget(struct_widget)

            self.structure_widgets.append(struct_widget)
            struct_widget.value_changed_signal.connect(self._structure_value_changed)
    
    def _structure_value_changed(self, struct_id:int, value:str):
        """
            Function called when the value of a structure element changes

            Makes sure that the same value only exist adjacent to each other
        """
        adjacent_ids = set([struct_id - 1, struct_id, struct_id + 1])
        for i in range(struct_id, len(self.structure_widgets)):
            if i in adjacent_ids and self.structure_widgets[i].get_value() == value:
                adjacent_ids.add(i+1)
            if i not in adjacent_ids and self.structure_widgets[i].get_value() == value:
                self.structure_widgets[i].set_value(StructureSelectorWidget.none_value_str)

        for i in range(struct_id, 0, -1):
            if i in adjacent_ids and self.structure_widgets[i].get_value() == value:
                adjacent_ids.add(i-1)
            if i not in adjacent_ids and self.structure_widgets[i].get_value() == value:
                self.structure_widgets[i].set_value(StructureSelectorWidget.none_value_str)

        self.value_changed_signal.emit()

    def get_selected_structure_pos(self):
        """
            Get the selected structure positions in the example structure
        """
        selected_structure = [widget.get_value() for widget in self.structure_widgets]
        fused_ids = get_fused_limits(selected_structure)
        fused_structure = [selected_structure[start] for start, _ in fused_ids]

        index_selected_struct = tuple(fused_structure.index(val) if val in fused_structure else None 
                                      for val in self.possible_values if val != StructureSelectorWidget.none_value_str)

        return index_selected_struct
    
    def get_fused_example_structure(self):
        """
            Get the fused example structure, ie the example structure separated into the selected structure groups
        """
        selected_structure = [widget.get_value() for widget in self.structure_widgets]
        fused_ids = get_fused_limits(selected_structure)

        fused_example : list[str] = []
        for start, end in fused_ids:
            example_start,_ = self.example_limits[start]
            _, example_end = self.example_limits[end]
            fused_example.append(self.example_str[example_start:example_end])

        return fused_example
        

class AutoStructureSelectionWidget(StructureSelectionWidget):
    """
        Tab to select the structure parameters
    """
    # Separators
    separators_description:str="Separators used to split the filenames\n(Multiple separators can be given separated by a comma ',')"

    default_separator:str='_'
    separators_separator:str=','

    # Structure selection
    structure_selection_description:str="""Select the structure of the filenames
    Multiple elements can be selected for each group as long as they are adjacent to each other"""

    def __init__(self, file_organizer:FileOrganizer, parent: QWidget | None = None) -> None:
        super().__init__(file_organizer, parent)

        self._side_structureFinder = StructureFinder()
        self._ventral_structureFinder = StructureFinder()
        self._video_structureFinder = StructureFinder()

        self._setup_ui()
    
    def _setup_ui(self):
        """
            Setup the UI of the tab
        """
        ### Structure selection
        structure_selection_group = QGroupBox("Structure selection")
        structure_selection_group.setFlat(True)
        self._structure_selection_layout.addWidget(structure_selection_group)

        structure_selection_group_layout = QVBoxLayout()
        structure_selection_group.setLayout(structure_selection_group_layout)

        # Separator selection
        separator_layout = QHBoxLayout()
        structure_selection_group_layout.addLayout(separator_layout)

        separator_label = QLabel(AutoStructureSelectionWidget.separators_description)
        # separator_label.setWordWrap(True)
        separator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator_layout.addWidget(separator_label)

        self.separator_edit = QLineEdit()
        self.separator_edit.setText(AutoStructureSelectionWidget.default_separator)
        separator_layout.addWidget(self.separator_edit)
        self.separator_edit.textChanged.connect(self._separator_text_changed)

        # Structure selection widget
        structure_selection_label = QLabel(AutoStructureSelectionWidget.structure_selection_description)
        structure_selection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        structure_selection_group_layout.addWidget(structure_selection_label)

        self.structure_selector = StructureSelectorWidget()
        self.structure_selector.value_changed_signal.connect(self.refresh_names_display)
        structure_selection_group_layout.addWidget(self.structure_selector)
    
    def _separator_text_changed(self):
        """
            Function called when the user changes the separator text
        """
        separators_txt = self.separator_edit.text()
        separators_list = separators_txt.split(AutoStructureSelectionWidget.separators_separator)
        try:
            self.structure_selector.set_separators(separators_list)
            self._set_structure_finders_separators(separators_list)

            new_best_representative, n_comp = self._side_structureFinder.get_best_representative()
            self.structure_selector.set_representative(new_best_representative)


            self.refresh_names_display()
        except Exception as e:
            self._update_status_display(f"Error: {e}", MessageType.ERROR)
            print("Error: ", e)
            raise e

    @override
    def setup_widget(self):
        """
            Setup the structure selection widget
        """
        self._set_structure_parameters()
        super().setup_widget()

    def _set_structure_finders_separators(self, separators_list:list[str]):
        """
            Set the separators for all the structure finders
        """
        self._side_structureFinder.set_separators(separators_list)
        self._ventral_structureFinder.set_separators(separators_list)
        self._video_structureFinder.set_separators(separators_list)

    def _set_structure_parameters(self):
        """
            Set the structure parameters in the structure finders and the file organizer
        """
        # Get all the possible names and the longest name (used to setup the structure selection widget)
        side_names = self.file_organizer.get_filenames(get_side=True)
        ventral_names = self.file_organizer.get_filenames(get_ventral=True)
        video_names = self.file_organizer.get_filenames(get_video=True)

        if len(side_names) == 0:
            raise ValueError("No side view file found")

        # Get the list of separators
        separators_txt = self.separator_edit.text()
        separators_list = separators_txt.split(AutoStructureSelectionWidget.separators_separator)

        try:
            self._side_structureFinder.set_parameters(side_names, separators_list)
            self._ventral_structureFinder.set_parameters(ventral_names, separators_list)
            self._video_structureFinder.set_parameters(video_names, separators_list)

            best_representative, n_comp = self._side_structureFinder.get_best_representative()


            # Setup the structure selection widget
            self.structure_selector.setup_structure(best_representative, separators_list, AutoStructureSelectionWidget.delimiters_keywords)
        except Exception as e:
            self._update_status_display(f"Error: {e}", MessageType.ERROR)
            print("Error: ", e)
            raise e
        
    # def _get_structure_string(self):
    #     """
    #         Get the regex structure string corresponding to the selected structure
    #     """
    #     try:
    #         # Get the structure selected by the user
    #         fused_structure = self.structure_selector.get_fused_example_structure()
    #         structure_positions = self.structure_selector.get_selected_structure_pos()

    #         self._structureFinder.find_structure(fused_structure, structure_positions)
            
    #         structure_str = self._structureFinder.get_structure_regexp(*structure_positions, *AutoStructureSelectionWidget.delimiters_keywords)
    #     except Exception as e:
    #         self._update_status_display(f"Error: {e}", MessageType.ERROR)
    #         print("Error: ", e)
    #         raise e
        
    #     return structure_str
    
    def _get_structures(self):
        """
            Get the list of structure dictionnaries corresponding to the selected structure for each file

            Returns a tuple of 3 lists of dictionnaries (side, ventral, video) containing the structure parameters
        """
        try:
            # Get the structure selected by the user
            fused_structure = self.structure_selector.get_fused_example_structure()
            structure_positions = self.structure_selector.get_selected_structure_pos()



            side_structure_dicts = self._side_structureFinder.find_structure(fused_structure, structure_positions, AutoStructureSelectionWidget.name_list_parameters)
            ventral_structure_dicts = self._ventral_structureFinder.find_structure(fused_structure, structure_positions, AutoStructureSelectionWidget.name_list_parameters)
            video_structure_dicts = self._video_structureFinder.find_structure(fused_structure, structure_positions, AutoStructureSelectionWidget.name_list_parameters)
        except Exception as e:
            self._update_status_display(f"Error: {e}", MessageType.ERROR)
            print("Error: ", e)
            raise e
        
        return side_structure_dicts, ventral_structure_dicts, video_structure_dicts
    
    def _actualize_file_organizer(self):
        # Set the constraints in the file organizer
        self.file_organizer.set_constraints(**self.constraints_dict)

        # Set the structure parameters in the file organizer
        struct_dicts = self._get_structures()
        self.file_organizer.set_structure_parameters(*struct_dicts)
        
    @override
    def refresh_names_display(self):
        """
            Get the names in each list of parameter and actualize the UI of the tab with them
        """
        self._actualize_file_organizer()

        super().refresh_names_display(use_regex=False)
