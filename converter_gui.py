"""YouTube Transcriber GUI - PySide6 (Qt 6) Implementation.

Full NVDA / WCAG 2.1 AA accessibility, asynchronous QThread execution,
and native Windows OS theme integration.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from converter_engine import ConversionJob, YTConverterEngine, status_prefix


class ConversionWorker(QThread):
    """Asynchronous worker executing downloads without blocking UI event loop."""

    sig_status = Signal(str, str, dict)
    sig_progress = Signal(int)
    sig_finished = Signal(bool, str)

    def __init__(
        self,
        urls: List[str],
        out_dir: str,
        langs: List[str],
        cookies: Optional[str] = None,
    ):
        super().__init__()
        self.urls = urls
        self.out_dir = out_dir
        self.langs = langs
        self.cookies = cookies
        self._is_cancelled = False

    def request_cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            engine = YTConverterEngine(cookies_path=self.cookies)
        except OSError as err:  # unreadable or malformed cookies file
            self.sig_finished.emit(False, f"Cannot load cookies file: {err}")
            return
        job = ConversionJob(
            Path(self.out_dir),
            self.langs,
            on_status=self.sig_status.emit,
            check_cancelled=lambda: self._is_cancelled,
        )
        results = self._convert_all(engine, job)
        self.sig_finished.emit(*self._summarize(results))

    def _convert_all(self, engine, job) -> list:
        results = []
        total = len(self.urls)
        for i, url in enumerate(self.urls):
            if self._is_cancelled:
                break
            self.sig_status.emit("item_start", f"Processing {i + 1}/{total}: {url}", {})
            results.extend(engine.convert(url, job))
            self.sig_progress.emit(int(((i + 1) / total) * 100))
        return results

    def _summarize(self, results: list) -> tuple:
        failed = sum(1 for ok, _ in results if not ok)
        counts = f"{len(results) - failed} succeeded, {failed} failed"
        if self._is_cancelled:
            return False, f"Cancelled ({counts})"
        return failed == 0, f"Finished: {counts}"


class YTMainFrame(QMainWindow):
    """Main application window providing an accessible,
    responsive transcription interface.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Transcriber Pro")
        self.resize(850, 680)
        self.output_dir = str(Path.cwd() / "md")
        self.cookies_path: Optional[str] = None
        self.worker: Optional[ConversionWorker] = None
        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        main_layout.addWidget(self._create_queue_group())
        main_layout.addWidget(self._create_options_group())
        main_layout.addWidget(self._create_output_group())
        main_layout.addLayout(self._create_actions_layout())
        main_layout.addWidget(self._create_progress_bar())
        main_layout.addWidget(self._create_log_view())
        self._setup_accessibility_and_tab_order()

    def _create_queue_group(self) -> QGroupBox:
        box = QGroupBox("1. Video Queue", self)
        layout = QVBoxLayout(box)
        row = QHBoxLayout()

        lbl_url = QLabel("&URL:", box)
        self.txt_url = QLineEdit(box)
        lbl_url.setBuddy(self.txt_url)
        self.btn_add = QPushButton("&Add", box)
        self.btn_add.clicked.connect(self._on_add_url)
        self.txt_url.returnPressed.connect(self._on_add_url)
        row.addWidget(lbl_url)
        row.addWidget(self.txt_url, 1)
        row.addWidget(self.btn_add)
        layout.addLayout(row)

        self.lst_urls = QListWidget(box)
        layout.addWidget(self.lst_urls)
        btn_row = QHBoxLayout()
        self.btn_remove = QPushButton("&Remove Selected", box)
        self.btn_remove.clicked.connect(self._on_remove_url)
        self.btn_clear = QPushButton("&Clear Queue", box)
        self.btn_clear.clicked.connect(self._on_clear_urls)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return box

    def _create_options_group(self) -> QGroupBox:
        box = QGroupBox("2. Options", self)
        layout = QVBoxLayout(box)

        row_lang = QHBoxLayout()
        lbl_lang = QLabel("&Languages:", box)
        self.txt_langs = QLineEdit("ar, en", box)
        lbl_lang.setBuddy(self.txt_langs)
        row_lang.addWidget(lbl_lang)
        row_lang.addWidget(self.txt_langs)
        layout.addLayout(row_lang)

        row_cook = QHBoxLayout()
        self.lbl_cook = QLabel("Cookies: None", box)
        self.btn_cook = QPushButton("Select &Cookies File...", box)
        self.btn_cook.clicked.connect(self._on_select_cookies)
        row_cook.addWidget(self.lbl_cook, 1)
        row_cook.addWidget(self.btn_cook)
        layout.addLayout(row_cook)
        return box

    def _create_output_group(self) -> QGroupBox:
        box = QGroupBox("3. Output Destination", self)
        layout = QHBoxLayout(box)
        self.lbl_out = QLabel(f"Folder: {self.output_dir}", box)
        self.btn_dir = QPushButton("&Browse Folder...", box)
        self.btn_dir.clicked.connect(self._on_select_folder)
        layout.addWidget(self.lbl_out, 1)
        layout.addWidget(self.btn_dir)
        return box

    def _create_actions_layout(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        self.btn_run = QPushButton("&Start Processing", self)
        self.btn_run.setFixedHeight(40)
        self.btn_run.clicked.connect(self._on_start)
        self.btn_cancel = QPushButton("Ca&ncel", self)
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(self.btn_run, 3)
        layout.addWidget(self.btn_cancel, 1)
        return layout

    def _create_progress_bar(self) -> QProgressBar:
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        return self.progress

    def _create_log_view(self) -> QPlainTextEdit:
        self.log_view = QPlainTextEdit(self)
        self.log_view.setReadOnly(True)
        return self.log_view

    def _setup_accessibility_and_tab_order(self) -> None:
        self.txt_url.setAccessibleName("YouTube video or playlist link input")
        self.lst_urls.setAccessibleName("Queued links for transcription")
        self.txt_langs.setAccessibleName("Target language preference comma separated")
        self.btn_run.setAccessibleName("Start transcription processing")
        self.btn_cancel.setAccessibleName("Cancel current transcription task")
        self.progress.setAccessibleName("Transcription task progress percentage")
        self.log_view.setAccessibleName("Execution status activity log")

        QWidget.setTabOrder(self.txt_url, self.btn_add)
        QWidget.setTabOrder(self.btn_add, self.lst_urls)
        QWidget.setTabOrder(self.lst_urls, self.btn_remove)
        QWidget.setTabOrder(self.btn_remove, self.btn_clear)
        QWidget.setTabOrder(self.btn_clear, self.txt_langs)
        QWidget.setTabOrder(self.txt_langs, self.btn_cook)
        QWidget.setTabOrder(self.btn_cook, self.btn_dir)
        QWidget.setTabOrder(self.btn_dir, self.btn_run)
        QWidget.setTabOrder(self.btn_run, self.btn_cancel)
        QWidget.setTabOrder(self.btn_cancel, self.log_view)

    def _on_add_url(self) -> None:
        url = self.txt_url.text().strip()
        if url:
            self.lst_urls.addItem(url)
            self.txt_url.clear()

    def _on_remove_url(self) -> None:
        for item in self.lst_urls.selectedItems():
            self.lst_urls.takeItem(self.lst_urls.row(item))

    def _on_clear_urls(self) -> None:
        self.lst_urls.clear()

    def _on_select_cookies(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select cookies.txt", "", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.cookies_path = path
            self.lbl_cook.setText(f"Cookies: {Path(path).name}")

    def _on_select_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir
        )
        if chosen:
            self.output_dir = chosen
            self.lbl_out.setText(f"Folder: {chosen}")

    def _on_start(self) -> None:
        urls = [self.lst_urls.item(i).text() for i in range(self.lst_urls.count())]
        if not urls:
            QMessageBox.warning(
                self, "Empty Queue", "Please add at least one YouTube URL."
            )
            return
        langs = [ln.strip() for ln in self.txt_langs.text().split(",") if ln.strip()]
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress.setValue(0)
        self.worker = ConversionWorker(urls, self.output_dir, langs, self.cookies_path)
        self.worker.sig_status.connect(self._append_log)
        self.worker.sig_progress.connect(self.progress.setValue)
        self.worker.sig_finished.connect(self._on_finished)
        self.worker.start()

    def _append_log(self, event_type: str, msg: str, _details: dict) -> None:
        self.log_view.appendPlainText(f"{status_prefix(event_type)} {msg}")

    def _on_cancel(self) -> None:
        if self.worker and self.worker.isRunning():
            self.btn_cancel.setEnabled(False)
            self.log_view.appendPlainText("[*] Cancellation requested...")
            self.worker.request_cancel()

    def _on_finished(self, success: bool, message: str) -> None:
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.log_view.appendPlainText(f"[COMPLETED] {message}")
        show = QMessageBox.information if success else QMessageBox.warning
        show(self, "Process Result", message)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Qt aborts if a running QThread is destroyed with its window.
        if self.worker and self.worker.isRunning():
            self.worker.request_cancel()
            self.worker.wait()
        super().closeEvent(event)
