from PySide6.QtCore import Signal, QLocale, QThread, QObject
from PySide6.QtGui import QValidator, QDoubleValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,    
    QMessageBox,
    QProgressBar,
    QFileDialog
    )

from enum import StrEnum

class PositiveFloatValidator(QDoubleValidator):
    """
        Input validator restricting the input to a positive float
    """
    def __init__(self):
        super().__init__()

        # Locale to have . instead of , as a number separator
        locale = QLocale(QLocale.Language.C)
        # Removes the use of , as a group separator in the input
        locale.setNumberOptions(QLocale.NumberOption.RejectGroupSeparator)

        # Set the locale and the minimum value
        self.setLocale(locale)
        self.setBottom(0)

class VectorInputLayout(QHBoxLayout):
    """
        Widget to ask the user to input an arbitrary number of components as integer
    """
    # Signal emitted when one of the values of the vector is changed
    # The new value is sent as a parameter (tuple[int,...])
    textChanged = Signal(tuple)

    def __init__(self, line_edit_validator:QValidator, parameters: list[tuple[str, int]], data_type=str):
        super().__init__()

        self.data_type = data_type

        self.parameters_name = [param_name for param_name,_ in parameters]
        self.values : dict[str, int] = dict()

        def get_text_changed_func(param_name):
            return lambda new_value_txt: self.text_changed(param_name, new_value_txt)

        for param_name, default_value in parameters:
            self.values[param_name] = default_value

            v_layout = QVBoxLayout()

            label = QLabel(param_name)
            v_layout.addWidget(label)

            line_edit = QLineEdit(str(default_value))
            line_edit.setValidator(line_edit_validator)
            v_layout.addWidget(line_edit)

            param_text_changed_func = get_text_changed_func(param_name)
            line_edit.textChanged.connect(param_text_changed_func)

            self.addLayout(v_layout)

    def text_changed(self, param_name, new_value_txt):
        """
            Function called whenever a vector input is changed by the user
            Input: 
                - param_name is the name of the changed parameter
                - new_value_txt is the new value of the parameter (as a string)
        """
        # Tries to convert the new_value_txt to a float
        new_value = tryconvert(new_value_txt, None, self.data_type)
        if new_value is None:
            return
        
        # Actualize the values dictionnary
        self.values[param_name] = new_value

        # Creates the new vector value tuple as a list
        list_values = []
        # Use the list to keep the order of the parameters
        for name in self.parameters_name:
            list_values.append(self.values[name])

        # Emit the signal with the new value of the vector
        self.textChanged.emit(tuple(list_values))

def tryconvert(value, default, *types):
    for t in types:
        try:
            return t(value)
        except (ValueError, TypeError):
            continue
    return default

class MessageType(StrEnum):
    ERROR = "Error"
    WARNING = "Warning"
    INFORMATION = "Message"

def show_message(msg_txt:str, message_type:MessageType):
    """
        Displays an message window with the message msg_txt
        The window display changes accordingly with the message type
    """
    msg_type_str = message_type.value
    if message_type == MessageType.ERROR:
        msg_icon = QMessageBox.Critical
    elif message_type == MessageType.WARNING:
        msg_icon = QMessageBox.Warning
    else:
        msg_icon = QMessageBox.Information

    msg = QMessageBox()
    msg.setIcon(msg_icon)
    msg.setText(msg_type_str)
    msg.setInformativeText(msg_txt)
    msg.setWindowTitle(msg_type_str)
    msg.exec()

    return

def get_user_folder_path(label:str, default_dir:str=""):
    """
        Asks the user to select a directory and returns it
    """
    return str(QFileDialog.getExistingDirectory(caption=label, dir=default_dir))

def create_combo_box_layout(label_str:str, combo_box:QComboBox):
    """
        Creates the layout for a labeled combo boxes
    """
    h_layout = QHBoxLayout()

    label = QLabel(label_str)
    h_layout.addWidget(label)

    h_layout.addWidget(combo_box)

    return h_layout

def get_change_dict_parameter_func(parameters_dict:dict, param_name:str, type):
        """
            Returns a function changing the value of the parameter param_name from parameters_dict by trying to convert it to type
        """
        def _(new_value):
            """
                Tries to convert the new_value_txt to type and assign it to parameters_dict if successful
            """
            new_value_converted = tryconvert(new_value, None, type)
            if new_value_converted is None:
                return
            
            parameters_dict[param_name] = new_value_converted
        
        return _

def add_input_to_form_layout(form_layout:QFormLayout, validator:QValidator, parameters:list[tuple[str,str,list[tuple[str,int]] | float|int|str]], parameter_dict:dict[str,tuple[int,...]]=None):
    """
        Adds a list of vector or single input boxes to the form layout form_layout, with the given validator
        The list of inputs is parameters, where each item is of the form (parameter key in parameter_dict, string to display beside the input box, default value of the parameter)
        The input values are stored in parameter_dict with the key being the param_key
    """
    param_line_edit_dict:dict[str, VectorInputLayout | QLineEdit] = dict()
    # Create the vector widgets to ask the user for the values of the vector parameters
    for param_key, display_str, default_value in parameters:
        # Type of the inputed data
        input_data_type = type(default_value)
        
        # If the value is a vector type
        if input_data_type is list:
            # Create the line edit widget
            param_line_edit = VectorInputLayout(validator, default_value)

            # Change the type to tuple to store it since the size is now fixed
            input_data_type = tuple

            # Extract the value to store in the dictionnary as a tuple
            list_default_value = [val for _,val in default_value]
            default_dict_value = input_data_type(list_default_value)
        # Otherwise the value is single type
        else:
            # Creates the line edit widget
            param_line_edit = QLineEdit(str(default_value))
            param_line_edit.setValidator(validator)

            default_dict_value = default_value

        if parameter_dict is not None:
            # Creates the value in the dictionnary
            parameter_dict[param_key] = default_dict_value

            # Assign a change in the widget values to actualize the dictionnary
            change_param_func = get_change_dict_parameter_func(parameter_dict, param_key, input_data_type)
            param_line_edit.textChanged.connect(change_param_func)

        # Add the vector widget to the form layout
        form_layout.addRow(display_str, param_line_edit)

        param_line_edit_dict[param_key] = param_line_edit

    return param_line_edit_dict


def setup_loading_bar(loading_bar:QProgressBar, max_value:int=0):
    """
        Setup the loading bar with the maximum value

        If max_value is 0 (or none is given), the loading bar will display a busy indicator
    """
    loading_bar.setMinimum(0)
    loading_bar.setMaximum(max_value)

    if max_value == 0:
        loading_bar.setFormat("Loading...")
    else:
        loading_bar.resetFormat()
        
    loading_bar.reset()

def update_loading_bar(loading_bar:QProgressBar, value:int):
    """
        Update the loading bar with the new value
    """
    loading_bar.setValue(value)

def delete_thread(thread:QThread):
    """
        Stops the thread
    """
    thread.quit()
    thread.wait()
    thread.deleteLater()
    thread = None

def delete_worker_thread(worker:QObject|None, thread:QThread|None):
    """
        Deletes the worker and the thread
    """
    if worker is not None:
        worker.deleteLater()
        worker = None

    if thread is not None:
        delete_thread(thread)
        thread = None

    return worker, thread