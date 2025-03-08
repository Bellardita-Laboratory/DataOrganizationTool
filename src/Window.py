import os
from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QApplication, 
    QWidget, 
    QMainWindow, 
    QPushButton, 
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QTabWidget
    )

from FileOrganizer import FileOrganizer
from UI.Tabs.DataSelectionTab import DataSelectionTab
from UI.Tabs.StructureSelectionTab import StructureSelectionTab
from UI.Tabs.OutputTab import OutputTab

from UI.UtilsUI import show_message, MessageType

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self, window_title:str, min_win_size:QSize = QSize(1200,487)):
        super().__init__()
        self.setMinimumSize(min_win_size)        
        self.setWindowTitle(window_title)

        self.file_organizer = FileOrganizer()

        self._setup_ui()

    def _setup_ui(self):
        """
            Setup the UI of the main window
        """
        # Main layout
        v_layout = QVBoxLayout()
        widget = QWidget()
        widget.setLayout(v_layout)
        self.setCentralWidget(widget)

        # ## Save/load layout
        # self.save_load_layout = SaveLoadLayout(self.batch_analyzer)
        # self.save_load_layout.move_to_tab_signal.connect(self._move_to_max_tab)
        # self.v_layout.addLayout(self.save_load_layout)

        ## Tabs
        self.tabs = QTabWidget()
        v_layout.addWidget(self.tabs)

        # Data selection tab
        self.data_selection_tab = DataSelectionTab(self.file_organizer)
        self.data_selection_tab.change_tab_signal.connect(self._data_selection_next)
        self.tabs.addTab(self.data_selection_tab, "Data selection")

        # Structure selection tab
        self.structure_selection_tab = StructureSelectionTab(self.file_organizer)
        self.structure_selection_tab.change_tab_signal.connect(self._structure_selection_next)
        self.tabs.addTab(self.structure_selection_tab, "Structure selection")

        # Output tab
        self.output_tab = OutputTab(self.file_organizer)
        self.tabs.addTab(self.output_tab, "Output")

        # Disable all tabs after the data selection tab
        self._disable_tabs_from(self.data_selection_tab)

    def _data_selection_next(self):
        """
            Function called when the user clicks on the next button of the data selection tab
        """
        # Setup the structure selection tab
        try:
            self.structure_selection_tab.setup_widget()
        except Exception as e:
            show_message(
                str(e),
                MessageType.ERROR
            )
            raise e
        
        # Make sure that all tabs after the data selection tab are disabled to prevent them from displaying data with the previous values
        self._disable_tabs_from(self.data_selection_tab)

        # Turn on the crop compensation and param 3D tab
        self._enable_and_set_current_tab(self.structure_selection_tab, [self.structure_selection_tab])

    def _structure_selection_next(self):
        """
            Function called when the user clicks on the next button of the structure selection tab
        """
        # Make sure that all tabs after the structure selection tab are disabled to prevent them from displaying data with the previous values
        self._disable_tabs_from(self.structure_selection_tab)

        # Turn on the output tab
        self._enable_and_set_current_tab(self.output_tab, [self.output_tab])

    def _disable_tabs_from(self, tab:QWidget):
        """
            Disable all the tabs after the given tab
        """
        min_tab_index = self.tabs.indexOf(tab) + 1

        for i in range(min_tab_index, self.tabs.count()):
            self.tabs.setTabEnabled(i, False)

    def _enable_and_set_current_tab(self, new_current_tab:QWidget, tab_to_enable:list[QWidget]):
        """
            Move to the tab at the given index
        """
        for tab in tab_to_enable:
            self.tabs.setTabEnabled(self.tabs.indexOf(tab), True)
        
        self.tabs.setCurrentWidget(new_current_tab)

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
        file = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        
        if file is None or file == '':
            return
        
        label.setText(file)
        dictionary[filepath_dict_key] = file



if __name__ == "__main__":
    # You need one (and only one) QApplication instance per application.
    # Pass in sys.argv to allow command line arguments for your app.
    # If you know you won't use command line arguments QApplication([]) works too.
    app = QApplication([])

    # Create a Qt widget, which will be our window.
    window = MainWindow(window_title="KineMatrix - Data Organization Tool")
    window.show()  # IMPORTANT!!!!! Windows are hidden by default.

    # Start the event loop.
    app.exec()

    # Your application won't reach here until you exit and the event
    # loop has stopped.