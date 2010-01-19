import wx
import util
import feeds
import threading
import feedparser

class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self, controller):
        super(TaskBarIcon, self).__init__()
        self.controller = controller
        self.set_icon('icons/feed.png')
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
    def CreatePopupMenu(self):
        menu = wx.Menu()
        util.menu_item(menu, 'Add Feed...', self.on_add_feed, 'icons/add.png')
        util.menu_item(menu, 'Settings...', self.on_event, 'icons/cog.png')
        util.menu_item(menu, 'About...', self.on_about, 'icons/information.png')
        menu.AppendSeparator()
        if self.controller.enabled:
            util.menu_item(menu, 'Disable Feeds', self.on_disable, 'icons/delete.png')
            util.menu_item(menu, 'Check Feeds Now', self.on_force_update, 'icons/transmit.png')
        else:
            util.menu_item(menu, 'Enable Feeds', self.on_enable, 'icons/accept.png')
            item = util.menu_item(menu, 'Check Feeds Now', self.on_force_update, 'icons/transmit.png')
            item.Enable(False)
        menu.AppendSeparator()
        util.menu_item(menu, 'Exit', self.on_exit, 'icons/door_out.png')
        return menu
    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, 'Feed Notifier')
    def on_event(self, event):
        print event
    def on_exit(self, event):
        self.controller.close()
    def on_left_down(self, event):
        self.controller.show_popup()
    def on_force_update(self, event):
        self.controller.force_poll()
    def on_about(self, event):
        self.controller.about()
    def on_disable(self, event):
        self.controller.disable()
    def on_enable(self, event):
        self.controller.enable()
    def on_add_feed(self, event):
        self.controller.add_feed()
        
class HiddenFrame(wx.Frame):
    def __init__(self, controller):
        super(HiddenFrame, self).__init__(None, -1, 'Feed Notifier')
        self.icon = TaskBarIcon(controller)
        self.Bind(wx.EVT_CLOSE, self.on_close)
    def on_close(self, event):
        event.Skip()
        wx.CallAfter(self.icon.Destroy)
        
class DialogFrame(wx.Frame):
    def __init__(self, parent, title):
        style = wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX & ~wx.RESIZE_BORDER
        super(DialogFrame, self).__init__(parent, -1, title, style=style)
        self.SetIcon(wx.IconFromBitmap(wx.Bitmap('icons/feed.png')))
        
class AboutDialog(DialogFrame):
    def __init__(self, parent):
        super(AboutDialog, self).__init__(parent, 'About Feed Notifier 2.0')
        panel = wx.Panel(self, -1)
        bitmap = wx.StaticBitmap(panel, -1, wx.Bitmap('icons/about.png'), style=wx.BORDER_SUNKEN)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(bitmap, 0, wx.ALL, 10)
        panel.SetSizerAndFit(sizer)
        self.Fit()
        
class AddFeedDialog(wx.Dialog):
    def __init__(self, parent, initial_url=''):
        super(AddFeedDialog, self).__init__(parent, -1, 'Add RSS/Atom Feed')
        self.SetIcon(wx.IconFromBitmap(wx.Bitmap('icons/feed.png')))
        self.initial_url = initial_url
        self.result = None
        panel = self.create_panel(self)
        self.Fit()
        self.validate()
    def get_initial_url(self):
        if self.initial_url:
            return self.initial_url
        if wx.TheClipboard.Open():
            object = wx.TextDataObject()
            success = wx.TheClipboard.GetData(object)
            wx.TheClipboard.Close()
            if success:
                url = object.GetText()
                if url.startswith('http'):
                    return url
        return ''
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        controls = self.create_controls(panel)
        buttons = self.create_buttons(panel)
        line = wx.StaticLine(panel, -1)
        sizer.AddStretchSpacer(1)
        sizer.Add(controls, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 25)
        sizer.AddStretchSpacer(1)
        sizer.Add(line, 0, wx.EXPAND)
        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 8)
        panel.SetSizerAndFit(sizer)
        return panel
    def create_controls(self, parent):
        sizer = wx.GridBagSizer(8, 8)
        label = wx.StaticText(parent, -1, 'Feed URL')
        font = label.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        label.SetFont(font)
        url = wx.TextCtrl(parent, -1, self.get_initial_url(), size=(300, -1))
        url.Bind(wx.EVT_TEXT, self.on_text)
        status = wx.StaticText(parent, -1, '')
        sizer.Add(label, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        sizer.Add(url, (0, 1))
        sizer.Add(status, (1, 1))
        self.url = url
        self.status = status
        return sizer
    def create_buttons(self, parent):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        back = wx.Button(parent, wx.ID_BACKWARD, '< Back')
        next = wx.Button(parent, wx.ID_FORWARD, 'Next >')
        cancel = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        back.Disable()
        next.SetDefault()
        next.Bind(wx.EVT_BUTTON, self.on_next)
        self.next = next
        sizer.AddStretchSpacer(1)
        sizer.Add(back)
        sizer.AddSpacer(4)
        sizer.Add(next)
        sizer.AddSpacer(16)
        sizer.Add(cancel)
        return sizer
    def validate(self):
        if self.url.GetValue():
            self.next.Enable()
        else:
            self.next.Disable()
    def on_text(self, event):
        self.validate()
    def on_next(self, event):
        url = self.url.GetValue()
        self.url.Disable()
        self.next.Disable()
        self.status.SetLabel('Checking feed, please wait...')
        thread = threading.Thread(target=self.check_feed, args=(url,))
        thread.setDaemon(True)
        thread.start()
    def on_valid(self, result):
        self.result = result
        self.EndModal(wx.ID_OK)
    def on_invalid(self):
        self.url.Enable()
        self.next.Enable()
        self.status.SetLabel('')
        dialog = wx.MessageDialog(self, 'The URL entered does not appear to be a valid RSS/Atom feed.', 'Invalid Feed', wx.OK|wx.ICON_ERROR)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
        self.url.SelectAll()
        self.url.SetFocus()
    def check_feed(self, url):
        d = feedparser.parse(url)
        if not self: # cancelled
            return
        if d['entries']:
            wx.CallAfter(self.on_valid, d)
        else:
            wx.CallAfter(self.on_invalid)
            
class EditFeedDialog(wx.Dialog):
    def __init__(self, parent, data):
        super(EditFeedDialog, self).__init__(parent, -1, 'Add RSS/Atom Feed')
        self.SetIcon(wx.IconFromBitmap(wx.Bitmap('icons/feed.png')))
        self.feed = None
        self.data = data
        panel = self.create_panel(self)
        self.Fit()
        self.validate()
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        controls = self.create_controls(panel)
        buttons = self.create_buttons(panel)
        line = wx.StaticLine(panel, -1)
        sizer.AddStretchSpacer(1)
        sizer.Add(controls, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 25)
        sizer.AddStretchSpacer(1)
        sizer.Add(line, 0, wx.EXPAND)
        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 8)
        panel.SetSizerAndFit(sizer)
        return panel
    def create_controls(self, parent):
        sizer = wx.GridBagSizer(8, 8)
        indexes = [0, 1, 3, 5]
        labels = ['Feed URL', 'Feed Title', 'Feed Link', 'Polling Interval']
        for index, text in zip(indexes, labels):
            label = wx.StaticText(parent, -1, text)
            font = label.GetFont()
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            label.SetFont(font)
            sizer.Add(label, (index, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        controls = []
        for index in indexes[:-1]:
            control = wx.TextCtrl(parent, -1, '', size=(300, -1))
            control.Bind(wx.EVT_TEXT, self.on_text)
            sizer.Add(control, (index, 1), (1, 2))
            controls.append(control)
        url, title, link = controls
        self.url, self.title, self.link = controls
        url.ChangeValue(self.data.href)
        title.ChangeValue(self.data.feed.title)
        link.ChangeValue(self.data.feed.link)
        url.Disable()
        interval = wx.SpinCtrl(parent, -1, '15', min=1, max=60, size=(64, -1))
        units = wx.Choice(parent, -1)
        #units.Append('seconds', 1)
        units.Append('minutes', 60)
        units.Append('hours', 60*60)
        units.Append('days', 60*60*24)
        units.Select(0)
        self.interval, self.units = interval, units
        sizer.Add(interval, (5, 1))
        sizer.Add(units, (5, 2))
        label = wx.StaticText(parent, -1, 'The feed title will be shown in the pop-up window for items from this feed.')
        label.Wrap(300)
        sizer.Add(label, (2, 1), (1, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        label = wx.StaticText(parent, -1, 'The feed link will launch in your browser if you click on the feed title in a pop-up window.')
        label.Wrap(300)
        sizer.Add(label, (4, 1), (1, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        label = wx.StaticText(parent, -1, 'The polling interval specifies how often the application will check the feed for new items.')
        label.Wrap(300)
        sizer.Add(label, (6, 1), (1, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        return sizer
    def create_buttons(self, parent):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        back = wx.Button(parent, wx.ID_BACKWARD, '< Back')
        next = wx.Button(parent, wx.ID_FORWARD, 'Finish')
        cancel = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        next.SetDefault()
        next.Bind(wx.EVT_BUTTON, self.on_next)
        back.Bind(wx.EVT_BUTTON, self.on_back)
        self.next = next
        sizer.AddStretchSpacer(1)
        sizer.Add(back)
        sizer.AddSpacer(4)
        sizer.Add(next)
        sizer.AddSpacer(16)
        sizer.Add(cancel)
        return sizer
    def validate(self):
        controls = [self.url, self.title, self.link]
        if all(control.GetValue() for control in controls):
            self.next.Enable()
        else:
            self.next.Disable()
    def on_text(self, event):
        self.validate()
    def on_back(self, event):
        self.EndModal(wx.ID_BACKWARD)
    def on_next(self, event):
        url = self.url.GetValue()
        title = self.title.GetValue()
        link = self.link.GetValue()
        interval = int(self.interval.GetValue())
        multiplier = self.units.GetClientData(self.units.GetSelection())
        interval = interval * multiplier
        feed = feeds.Feed(url)
        feed.title = title
        feed.link = link
        feed.interval = interval
        self.feed = feed
        self.EndModal(wx.ID_OK)
        