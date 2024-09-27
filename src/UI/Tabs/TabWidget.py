from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QLineEdit,
    QComboBox,
    QProgressBar
)
from typing import Iterable, Callable

from UI.UtilsUI import MessageType, show_message, delete_worker_thread, setup_loading_bar, update_loading_bar
from UI.FuncCallWorker import FuncCall_Worker

class TabWidget(QWidget):
    change_tab_signal = Signal()
    enable_all_inputs = Signal(bool)

    input_types = [QLineEdit, QPushButton, QComboBox]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._worker = None
        self._thread = None
        self._worker_progress_bar = None

    def stop_worker_thread(self):
        """
            Stop the worker thread if it is running
        """
        if self._worker is not None:
            self._worker.terminate()

        if self._thread is not None:
            self._thread.quit()
            # self._thread.terminate() ## DANGER
            self._thread.wait()
        
        self._worker, self._thread = delete_worker_thread(self._worker, self._thread)

    def all_inputs_set_enabled(self, enable:bool):
        """
            Enable or disable all inputs in this widget
        """
        for type in TabWidget.input_types:
            self._all_widget_type_set_enabled(type, enable)

    def _all_widget_type_set_enabled(self, type:QWidget, enable:bool):
        """
            Enable or disable all widgets of a certain type in this widget
        """
        children : Iterable[QWidget] = self.findChildren(type, options=Qt.FindChildrenRecursively)
        for widget in children:
            widget.setEnabled(enable)

    def _start_func_call_worker(self, on_worker_finished:Callable, func:Callable, *args, 
                                worker_block_inputs:bool=True, worker_progress_bar:QProgressBar|None=None, **kwargs):
        """
            Start a worker thread to execute a function

            The function must have a terminate_event and progress_signal parameters if worker_progress_bar is not None

            Args:
                on_worker_finished: Callable to call when the worker is finished
                func: Function to execute
                *args: Arguments to pass to the function
                worker_block_inputs: If True, block all inputs while the worker is running
                worker_progress_bar: Progress bar to update
                **kwargs: Keyword arguments to pass to the function
        """
        if worker_block_inputs:
            self.enable_all_inputs.emit(False)

        self._worker_block_input = worker_block_inputs
        self._worker_progress_bar = worker_progress_bar

        # Set the progress bar to loading
        with_progress = worker_progress_bar is not None
        if with_progress:
            self._update_progress_bar(0, 0)

        try:
            # Delete the previous worker and thread
            self._worker, self._thread = delete_worker_thread(self._worker, self._thread)

            # Create the worker
            self._worker = FuncCall_Worker(func, *args, with_progress=with_progress, **kwargs)

            # Create the thread
            self._thread : QThread = QThread()
            self._worker.moveToThread(self._thread)

            # Connect the signals
            self._worker.finished_signal.connect(lambda: self._worker_finished(on_worker_finished))
            self._worker.progress_signal.connect(self._update_progress_bar)
            self._worker.error_signal.connect(self._worker_error)
            self._thread.started.connect(self._worker.func_call)

            # Start the thread
            self._thread.start()
        except Exception as e:
            if worker_block_inputs:
                self.enable_all_inputs.emit(True)
            
            show_message(str(e), MessageType.ERROR)
            raise e

    def _update_progress_bar(self, value:int, max_value:int):
        '''
            Update the progress bar
        '''
        setup_loading_bar(self._worker_progress_bar, max_value)
        update_loading_bar(self._worker_progress_bar, value)
    
    def _worker_error(self, error:str):
        """
            Called when an error was encountered when retrieving the data
        """
        show_message(error, MessageType.ERROR)

        self._worker, self._thread = delete_worker_thread(self._worker, self._thread)

        if self._worker_block_input:
            self.enable_all_inputs.emit(True)

    def _worker_finished(self, on_worker_finished:Callable):
        """
            Called when the worker has finished
        """
        if self._thread is not None:
            self._thread.quit()

        self._worker, self._thread = delete_worker_thread(self._worker, self._thread)

        if self._worker_block_input:
            self.enable_all_inputs.emit(True)

        on_worker_finished()
