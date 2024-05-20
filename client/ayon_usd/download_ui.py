"""Download UI."""
import threading
import uuid
from functools import partial

from ayon_api import TransferProgress
from ayon_core import style
from qtpy import QtCore, QtWidgets

from .utils import download_usd


class DownloadItem:
    """Download item."""

    def __init__(self, title, func):
        """Download item.

        Args:
            title (str): Title.
            func (Callable): Function.

        """
        self._id = uuid.uuid4().hex
        progress = TransferProgress()
        self._func = partial(func, progress)
        self.title = title
        self.progress = progress
        self._thread = None

    @property
    def id(self):
        """Id."""
        return self._id

    @property
    def finished(self):
        """Check if download is finished."""
        return True if self._thread is None else not self._thread.is_alive()

    def download(self):
        """Download."""
        if self._thread is None:
            self._thread = threading.Thread(target=self._func)
            self._thread.start()

    def finish(self):
        """Finish."""
        if self._thread is None:
            return
        self._thread.join()
        self._thread = None


class DownloadController:
    """Download controller."""
    
    def __init__(self, usd):
        """Download controller.
        
        Args:
            usd (bool): Download usd.
            
        """
        self._items = [DownloadItem("usd", download_usd)]

        self._items_by_id = {
            item.id: item
            for item in self._items
        }
        self._download_started = False
        self._download_finished = False

    def items(self):
        """Items."""
        yield from self._items_by_id.items()

    @property
    def download_items(self):
        """Download items."""
        yield from self._items

    @property
    def download_started(self):
        """Check if download is started."""
        return self._download_started

    @property
    def download_finished(self):
        """Check if download is finished."""
        return self._download_finished

    @property
    def is_downloading(self):
        """Check if downloading is in progress."""
        if not self._download_started or self._download_finished:
            return False

        return any(not item.finished for item in self.download_items)

    def start_download(self):
        """Start download."""
        if self._download_started:
            return
        self._download_started = True
        for item in self.download_items:
            item.download()

    def finish_download(self):
        """Finish download."""
        if self._download_finished:
            return
        for item in self.download_items:
            item.finish()
        self._download_finished = True


class DownloadItemWidget(QtWidgets.QWidget):
    """Download item widget."""

    def __init__(self, download_item, parent):
        """Download item widget.

        Args:
            download_item (DownloadItem): Download item.
            parent (QWidget): Parent widget.

        """
        super(DownloadItemWidget, self).__init__(parent)

        title_label = QtWidgets.QLabel(download_item.title, self)
        progress_label = QtWidgets.QLabel("0%", self)

        content_layout = QtWidgets.QHBoxLayout(self)
        content_layout.addWidget(title_label, 1)
        content_layout.addWidget(progress_label, 0)

        self._title_label = title_label
        self._progress_label = progress_label
        self._download_item = download_item

    def update_progress(self):
        """Update progress."""
        if self._download_item.finished:
            self._progress_label.setText("Finished")
            return

        progress = self._download_item.progress
        if not progress.started:
            return

        # TODO replace with 'progress.is_running' once is fixed
        progress_is_running = not (
            not progress.started
            or progress.transfer_done
            or progress.failed
        )
        if progress_is_running:
            transfer_progress = progress.transfer_progress
            if transfer_progress is None:
                transfer_progress = "Downloading..."
            else:
                transfer_progress = "{:.2f}%".format(transfer_progress)
            self._progress_label.setText(transfer_progress)
            return
        self._progress_label.setText("Extracting...")


class DownloadWindow(QtWidgets.QWidget):
    """Download window."""

    finished = QtCore.Signal()

    def __init__(self, controller, parent=None):
        """Download window.

        Args:
            controller (DownloadController): Download controller.
            parent (QWidget): Parent widget.

        """
        super(DownloadWindow, self).__init__(parent=parent)

        self.setWindowTitle("Downloading 3rd party dependencies")

        content_widget = QtWidgets.QWidget(self)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        item_widgets = []
        for item in controller.download_items:
            item_widget = DownloadItemWidget(item, content_widget)
            item_widgets.append(item_widget)
            content_layout.addWidget(item_widget, 0)
        content_layout.addStretch(1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(content_widget, 1)

        timer = QtCore.QTimer()
        timer.setInterval(10)
        timer.timeout.connect(self._on_timer)

        self._timer = timer
        self._controller = controller
        self._item_widgets = item_widgets
        self._first_show = True
        self._start_on_show = False

    def showEvent(self, event):
        """Show event."""
        super(DownloadWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            # Set stylesheet and resize
            self.setStyleSheet(style.load_stylesheet())
            self.resize(360, 200)

        if self._start_on_show:
            self.start()

    def _update_progress(self):
        for widget in self._item_widgets:
            widget.update_progress()

    def _on_timer(self):
        if self._controller.download_finished:
            self._timer.stop()
            self.finished.emit()
            return

        if not self._controller.download_started:
            self._controller.start_download()
            self._update_progress()
            return

        if self._controller.is_downloading:
            self._update_progress()
            return

        self._controller.finish_download()
        self._update_progress()

    def start(self):
        """Start download."""
        if self._first_show:
            self._start_on_show = True
            return
        if self._controller.download_started:
            return
        self._timer.start()


def show_download_window(usd, parent=None):
    """Show download window.

    Args:
        usd (bool): Download usd.
        parent (QWidget): Parent widget.

    """
    controller = DownloadController(usd)
    window = DownloadWindow(controller, parent=parent)
    window.show()
    window.start()
    return window
