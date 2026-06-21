"""
YouTube Transcriber GUI - PyArabic Refinement UI
"""

import os
import threading
from typing import List, Optional
import wx
from converter_engine import YTConverterEngine


class YTMainFrame(wx.Frame):
    """Main GUI Window with PyArabic features."""

    def __init__(self):
        super().__init__(
            None,
            title="YouTube Transcriber Pro (Arabic Enhanced)",
            size=(900, 700),
        )
        self.engine = YTConverterEngine()
        self.urls: List[str] = []
        self.output_dir = os.getcwd()
        self.cookies_path: Optional[str] = None
        self.cancelled = False
        self.init_ui()
        self.Center()

    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Section 1: Inputs ---
        input_box = wx.StaticBox(panel, label="1. URL Queue")
        input_sizer = wx.StaticBoxSizer(input_box, wx.HORIZONTAL)
        self.txt_url = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.txt_url.SetHint("Paste link and press Enter...")
        btn_add = wx.Button(panel, label="Add URL")
        input_sizer.Add(self.txt_url, 1, wx.ALL, 5)
        input_sizer.Add(btn_add, 0, wx.ALL, 5)

        self.lst_urls = wx.ListBox(panel, style=wx.LB_EXTENDED)
        btn_rem = wx.Button(panel, label="Remove Selected")
        btn_clr = wx.Button(panel, label="Clear All")
        q_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        q_btn_sizer.Add(btn_rem, 0, wx.RIGHT, 5)
        q_btn_sizer.Add(btn_clr, 0)

        # --- Section 2: Options ---
        opt_box = wx.StaticBox(panel, label="2. Transcription Options")
        opt_sizer = wx.StaticBoxSizer(opt_box, wx.VERTICAL)

        # Languages
        lang_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lang_lbl = wx.StaticText(
            panel, label="Prefer Languages (comma separated):"
        )
        self.txt_langs = wx.TextCtrl(panel, value="ar, en, de")
        lang_sizer.Add(lang_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        lang_sizer.Add(self.txt_langs, 1, wx.EXPAND)

        # Cookies
        cook_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_cookies = wx.StaticText(panel, label="Cookies: Not Set")
        btn_cookies = wx.Button(panel, label="Select cookies.txt...")
        cook_sizer.Add(
            self.lbl_cookies, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5
        )
        cook_sizer.Add(btn_cookies, 0)

        opt_sizer.Add(lang_sizer, 0, wx.EXPAND | wx.ALL, 5)
        opt_sizer.Add(cook_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- Section 3: Output & Actions ---
        out_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_output = wx.StaticText(
            panel, label=f"Folder: {self.output_dir}"
        )
        btn_dir = wx.Button(panel, label="Browse Folder...")
        out_sizer.Add(self.lbl_output, 1, wx.ALIGN_CENTER_VERTICAL)
        out_sizer.Add(btn_dir, 0)

        # Action Buttons: Run and Cancel
        actions_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_run = wx.Button(
            panel, label="START PROCESSING", size=(-1, 50)
        )
        self.btn_run.SetBackgroundColour(wx.Colour(0, 120, 0))
        self.btn_run.SetForegroundColour(wx.WHITE)

        self.btn_cancel = wx.Button(panel, label="CANCEL", size=(-1, 50))
        self.btn_cancel.SetBackgroundColour(wx.Colour(180, 0, 0))
        self.btn_cancel.SetForegroundColour(wx.WHITE)
        self.btn_cancel.Disable()

        actions_sizer.Add(self.btn_run, 3, wx.EXPAND | wx.RIGHT, 10)
        actions_sizer.Add(self.btn_cancel, 1, wx.EXPAND)

        self.gauge = wx.Gauge(panel, range=100)
        self.txt_log = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY
        )

        # Assembly
        main_sizer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.lst_urls, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)
        main_sizer.Add(q_btn_sizer, 0, wx.LEFT | wx.BOTTOM, 15)
        main_sizer.Add(opt_sizer, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(out_sizer, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(actions_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)
        main_sizer.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.txt_log, 1, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main_sizer)

        # Events
        btn_add.Bind(wx.EVT_BUTTON, self.on_add)
        self.txt_url.Bind(wx.EVT_TEXT_ENTER, self.on_add)
        btn_rem.Bind(wx.EVT_BUTTON, self.on_remove)
        btn_clr.Bind(wx.EVT_BUTTON, self.on_clear)
        btn_cookies.Bind(wx.EVT_BUTTON, self.on_select_cookies)
        btn_dir.Bind(wx.EVT_BUTTON, self.on_change_dir)
        self.btn_run.Bind(wx.EVT_BUTTON, self.on_start)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)

    def on_add(self, _):
        u = self.txt_url.GetValue().strip()
        if u and u not in self.urls:
            self.urls.append(u)
            self.lst_urls.Append(u)
            self.txt_url.Clear()

    def on_remove(self, _):
        for i in reversed(self.lst_urls.GetSelections()):
            self.urls.pop(i)
            self.lst_urls.Delete(i)

    def on_clear(self, _):
        self.urls.clear()
        self.lst_urls.Clear()

    def on_select_cookies(self, _):
        with wx.FileDialog(
            self, "Select cookies.txt", wildcard="TXT files (*.txt)|*.txt"
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.cookies_path = dlg.GetPath()
                self.lbl_cookies.SetLabel(
                    f"Cookies: {os.path.basename(self.cookies_path)}"
                )

    def on_change_dir(self, _):
        with wx.DirDialog(
            self, "Select Output Folder", defaultPath=self.output_dir
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.output_dir = dlg.GetPath()
                self.lbl_output.SetLabel(f"Folder: {self.output_dir}")

    def on_cancel(self, _):
        self.cancelled = True
        self.btn_cancel.Disable()
        wx.CallAfter(
            self.txt_log.AppendText, "[*] Requesting cancellation...\n"
        )

    def on_start(self, _):
        if not self.urls:
            return
        self.btn_run.Disable()
        self.btn_cancel.Enable()
        self.cancelled = False
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        langs = [
            ln.strip()
            for ln in self.txt_langs.GetValue().split(",")
            if ln.strip()
        ]

        def check_cancelled():
            return self.cancelled

        def on_status(event_type, msg, details):
            if event_type == "start_video":
                wx.CallAfter(
                    self.txt_log.AppendText, f"    - Fetching: {msg}\n"
                )
            elif event_type == "success":
                wx.CallAfter(self.txt_log.AppendText, f"    ✔ {msg}\n")
            elif event_type == "fail":
                wx.CallAfter(self.txt_log.AppendText, f"    ✘ {msg}\n")

        try:
            for i, url in enumerate(self.urls):
                if self.cancelled:
                    break
                wx.CallAfter(
                    self.txt_log.AppendText,
                    f"[*] Processing {i+1}/{len(self.urls)}: {url}\n",
                )
                self.engine.convert(
                    url,
                    self.output_dir,
                    langs,
                    self.cookies_path,
                    on_status=on_status,
                    check_cancelled=check_cancelled,
                )
                wx.CallAfter(
                    self.gauge.SetValue, int(((i + 1) / len(self.urls)) * 100)
                )
        except Exception as e:
            wx.CallAfter(
                self.txt_log.AppendText, f"[!] Critical Error: {str(e)}\n"
            )
        finally:
            wx.CallAfter(self.btn_run.Enable)
            wx.CallAfter(self.btn_cancel.Disable)
            if self.cancelled:
                wx.CallAfter(
                    self.txt_log.AppendText, "[-] Task stopped by user.\n"
                )
                wx.CallAfter(
                    wx.MessageBox, "Task cancelled!", "Process Stopped"
                )
            else:
                wx.CallAfter(
                    wx.MessageBox, "All tasks finished!", "Process Complete"
                )
