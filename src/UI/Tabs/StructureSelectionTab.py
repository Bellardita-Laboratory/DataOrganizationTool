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
    QCheckBox,
    QStackedLayout
)

import numpy as np
import regex as re

from UI.Tabs.TabWidget import TabWidget
from UI.UtilsUI import MessageType
from FileOrganizer import FileOrganizer
from UI.Tabs.StructureSelectors.StructureSelectionWidget_Regex import RegexStructureSelectionWidget
from UI.Tabs.StructureSelectors.StructureSelectionWidget_Auto import AutoStructureSelectionWidget

class StructureSelectionTab(TabWidget):
    """
        Tab to select the structure parameters
    """
    use_regex_checkbox_text = "Use regex to select the structure"

    def __init__(self, file_organizer:FileOrganizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.file_organizer = file_organizer

        self._setup_ui()
    
    def _setup_ui(self):
        """
            Setup the UI of the tab
        """
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)

        ### Use regex or auto structure selection
        self.use_regex_checkbox = QCheckBox(StructureSelectionTab.use_regex_checkbox_text)
        v_layout.addWidget(self.use_regex_checkbox)
        self.use_regex_checkbox.stateChanged.connect(self._use_regex_checkbox_state_changed)

        ### Structure selection
        # Create the stqcked layout
        self.structure_selection_layout = QStackedLayout()
        v_layout.addLayout(self.structure_selection_layout)

        # Instantiate the two structure selection widgets
        self.auto_structure_selector = AutoStructureSelectionWidget(self.file_organizer)
        self.structure_selection_layout.addWidget(self.auto_structure_selector)

        self.regex_structure_selector = RegexStructureSelectionWidget(self.file_organizer)
        self.structure_selection_layout.addWidget(self.regex_structure_selector)

        # Set the current widget to the auto structure selector
        self.structure_selection_layout.setCurrentWidget(self.auto_structure_selector)
        self._switch_structure_selector(use_regex=False)

        # Next button
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self._next_btn_clicked)
        v_layout.addWidget(next_btn)

    def setup_widget(self):
        """
            Setup the widget with the parameters in the file organizer
        """
        self.regex_structure_selector.setup_widget()
        self.auto_structure_selector.setup_widget()

    def _switch_structure_selector(self, use_regex:bool):
        """
            Switch the structure selector between regex and auto
        """
        self.file_organizer.set_use_regex(use_regex)
        
        if use_regex:
            self.structure_selection_layout.setCurrentWidget(self.regex_structure_selector)
        else:
            self.structure_selection_layout.setCurrentWidget(self.auto_structure_selector)

    def _use_regex_checkbox_state_changed(self, state:int):
        """
            Function called when the state of the use regex checkbox changes
        """
        self._switch_structure_selector(state == Qt.CheckState.Checked.value)

    def _next_btn_clicked(self):
        """
            Function called when the user clicks on the next button
        """
        # Emit the signal to change the tab
        self.change_tab_signal.emit()
