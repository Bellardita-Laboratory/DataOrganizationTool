from PySide6.QtCore import Signal, QObject, QThread
from typing import Callable
import multiprocessing

from UI.UtilsUI import (
    show_message, MessageType,
    delete_worker_thread
)

class FuncCall_Worker(QObject):
    """
        Worker class used to execute a function in a thread
    """
    finished_signal = Signal((object,))
    progress_signal = Signal(int, int)
    error_signal = Signal(str)

    # Signal to terminate the worker
    terminate_signal = Signal()

    def __init__(self, func:Callable, *args, with_progress:bool = False, **kwargs):
        super().__init__()

        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.with_progress = with_progress
        self.terminate_now = False

        self.terminate_signal.connect(self.terminate)

    def terminate(self):
        """
            Terminate the worker
        """
        if hasattr(self, 'terminate_event'):
            self.terminate_event.set()
        else:
            self.terminate_now = True

    def _raise_worker_interrupted(self):
        """
            Called when the worker is interrupted to emit an error signal
        """
        print("Worker terminated before finishing")
        self.error_signal.emit("Worker terminated before finishing")  # Emit an error signal if the worker was terminated

    def func_call(self):
        """
            Call the function in the worker thread and handle termination, progress bar update, and errors
        """
        manager = multiprocessing.Manager()

        # Check necessary since the manager creation takes time: the worker could be terminated before the event is created
        if self.terminate_now:
            self._raise_worker_interrupted()
            return

        self.terminate_event = manager.Event()

        try:
            if self.with_progress:
                ret = self.func(*self.args, terminate_event=self.terminate_event, progress_signal=self.progress_signal, **self.kwargs)
            else:
                ret = self.func(*self.args, terminate_event=self.terminate_event, **self.kwargs)
        except Exception as e:
            self.error_signal.emit(str(e))
            raise e

        if not self.terminate_event.is_set():
            self.finished_signal.emit(ret)
        else:
            self._raise_worker_interrupted()

    @staticmethod
    def error_delete_worker_thread(error:str, worker:QObject, thread:QThread):
        """
            Called when an error was encountered when retrieving the data
        """
        show_message(error, MessageType.ERROR)

        return delete_worker_thread(worker, thread)