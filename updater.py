import wx
import os
import time
import urllib
import tempfile
import util
from settings import settings

class CancelException(Exception):
    pass
    
class DownloadDialog(wx.Dialog):
    def __init__(self, parent):
        super(DownloadDialog, self).__init__(parent, -1, 'Feed Notifier Update')
        util.set_icon(self)
        self.path = None
        text = wx.StaticText(self, -1, 'Downloading update, please wait...')
        self.gauge = wx.Gauge(self, -1, 100, size=(250, 16))
        cancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text)
        sizer.AddSpacer(8)
        sizer.Add(self.gauge, 0, wx.EXPAND)
        sizer.AddSpacer(8)
        sizer.Add(cancel, 0, wx.ALIGN_RIGHT)
        wrapper = wx.BoxSizer(wx.VERTICAL)
        wrapper.Add(sizer, 1, wx.EXPAND|wx.ALL, 10)
        self.SetSizerAndFit(wrapper)
        self.start_download()
    def start_download(self):
        util.start_thread(self.download)
    def download(self):
        try:
            self.path = download_installer(self.listener)
            wx.CallAfter(self.EndModal, wx.ID_OK)
        except CancelException:
            pass
        except Exception:
            wx.CallAfter(self.on_fail)
    def on_fail(self):
        dialog = wx.MessageDialog(self, 'Failed to download updates. Nothing will be installed at this time.', 'Update Failed', wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()
        self.EndModal(wx.ID_CANCEL)
    def update(self, percent):
        if self:
            self.gauge.SetValue(percent)
    def listener(self, blocks, block_size, total_size):
        size = blocks * block_size
        percent = size * 100 / total_size
        if self:
            wx.CallAfter(self.update, percent)
        else:
            raise CancelException
            
def get_remote_revision():
    file = None
    try:
        file = urllib.urlopen(settings.REVISION_URL)
        return int(file.read().strip())
    except Exception:
        return -1
    finally:
        if file:
            file.close()
            
def download_installer(listener):
    fd, path = tempfile.mkstemp('.exe')
    os.close(fd)
    path, headers = urllib.urlretrieve(settings.INSTALLER_URL, path, listener)
    return path
    
def should_check():
    last_check = settings.UPDATE_TIMESTAMP
    now = int(time.time())
    elapsed = now - last_check
    return elapsed >= settings.UPDATE_INTERVAL
    
def should_update(force):
    if not force:
        if not should_check():
            return False
    now = int(time.time())
    settings.UPDATE_TIMESTAMP = now
    local = settings.LOCAL_REVISION
    remote = get_remote_revision()
    if local < 0 or remote < 0:
        return False
    return remote > local
    
def do_check(controller, force=False):
    if should_update(force):
        wx.CallAfter(do_ask, controller)
    elif force:
        wx.CallAfter(do_tell, controller)
        
def do_ask(controller):
    dialog = wx.MessageDialog(None, 'Feed Notifier software updates are available.  Download and install now?', 'Update Feed Notifier?', wx.YES_NO|wx.YES_DEFAULT|wx.ICON_QUESTION)
    if dialog.ShowModal() == wx.ID_YES:
        do_download(controller)
    dialog.Destroy()
    
def do_tell(controller):
    dialog = wx.MessageDialog(None, 'No software updates are available at this time.', 'No Updates', wx.OK|wx.ICON_INFORMATION)
    dialog.ShowModal()
    dialog.Destroy()
    
def do_download(controller):
    dialog = DownloadDialog(None)
    dialog.Center()
    result = dialog.ShowModal()
    path = dialog.path
    dialog.Destroy()
    if result == wx.ID_OK:
        do_install(controller, path)
        
def do_install(controller, path):
    controller.close()
    time.sleep(1)
    os.execvp(path, (path, '/sp-', '/silent', '/norestart'))
    
def run(controller, force=False):
    if force or settings.CHECK_FOR_UPDATES:
        util.start_thread(do_check, controller, force)
        