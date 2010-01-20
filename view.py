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
        util.menu_item(menu, 'Settings...', self.on_settings, 'icons/cog.png')
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
    def on_settings(self, event):
        self.controller.edit_settings()
        
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
    @staticmethod
    def show_wizard(parent, url=''):
        while True:
            window = AddFeedDialog(parent, url)
            window.CenterOnScreen()
            result = window.ShowModal()
            data = window.result
            window.Destroy()
            if result != wx.ID_OK:
                return None
            url = data.href
            feed = feeds.Feed(url)
            feed.title = data.feed.title
            feed.link = data.feed.link
            window = EditFeedDialog(parent, feed, True)
            window.CenterOnScreen()
            result = window.ShowModal()
            window.Destroy()
            if result == wx.ID_BACKWARD:
                continue
            if result == wx.ID_OK:
                return feed
            return None
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
    def __init__(self, parent, feed, add=False):
        title = 'Add RSS/Atom Feed' if add else 'Edit RSS/Atom Feed'
        super(EditFeedDialog, self).__init__(parent, -1, title)
        self.SetIcon(wx.IconFromBitmap(wx.Bitmap('icons/feed.png')))
        self.feed = feed
        self.add = add
        panel = self.create_panel(self)
        self.Fit()
        self.validate()
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        controls = self.create_controls(panel)
        if self.add:
            buttons = self.create_add_buttons(panel)
        else:
            buttons = self.create_edit_buttons(panel)
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
        url.ChangeValue(self.feed.url)
        title.ChangeValue(self.feed.title)
        link.ChangeValue(self.feed.link)
        url.Disable()
        _interval, _units = util.split_time(self.feed.interval)
        interval = wx.SpinCtrl(parent, -1, str(_interval), min=1, max=60, size=(64, -1))
        units = wx.Choice(parent, -1)
        units.Append('seconds', 1)
        units.Append('minutes', 60)
        units.Append('hours', 60*60)
        units.Append('days', 60*60*24)
        units.Select(_units)
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
    def create_add_buttons(self, parent):
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
    def create_edit_buttons(self, parent):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        next = wx.Button(parent, wx.ID_FORWARD, 'OK')
        cancel = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        next.SetDefault()
        next.Bind(wx.EVT_BUTTON, self.on_next)
        self.next = next
        sizer.AddStretchSpacer(1)
        sizer.Add(next)
        sizer.AddSpacer(8)
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
        self.feed.title = title
        self.feed.link = link
        self.feed.interval = interval
        self.EndModal(wx.ID_OK)
        
# TODO: cleanup code below here
class SettingsDialog(wx.Dialog):
    def __init__(self, parent, controller):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(SettingsDialog, self).__init__(parent, -1, 'Feed Notifier Settings', style=style)
        self.SetIcon(wx.IconFromBitmap(wx.Bitmap('icons/feed.png')))
        self.controller = controller
        panel = self.create_panel(self)
        self.Fit()
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        notebook = self.create_notebook(panel)
        line = wx.StaticLine(panel, -1)
        buttons = self.create_buttons(panel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 1, wx.EXPAND|wx.ALL, 0)
        sizer.Add(line, 0, wx.EXPAND)
        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 8)
        panel.SetSizerAndFit(sizer)
        return panel
    def create_notebook(self, parent):
        images = wx.ImageList(48, 32)
        images.Add(wx.Bitmap('icons/feed32.png'))
        images.Add(wx.Bitmap('icons/comment32.png'))
        images.Add(wx.Bitmap('icons/cog32.png'))
        notebook = wx.Toolbook(parent, -1, style=wx.BK_DEFAULT)
        notebook.AssignImageList(images)
        feeds = FeedsPanel(notebook, self.controller, self.on_event)
        popups = PopupsPanel(notebook)
        options = OptionsPanel(notebook)
        notebook.AddPage(feeds, 'Feeds', imageId=0)
        notebook.AddPage(popups, 'Pop-ups', imageId=1)
        notebook.AddPage(options, 'Options', imageId=2)
        self.feeds = feeds
        self.popups = popups
        self.options = options
        return notebook
    def create_buttons(self, parent):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(parent, wx.ID_OK, 'OK')
        cancel = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        apply = wx.Button(parent, wx.ID_APPLY, 'Apply')
        ok.Bind(wx.EVT_BUTTON, self.on_ok)
        apply.Bind(wx.EVT_BUTTON, self.on_apply)
        ok.SetDefault()
        apply.Disable()
        self.apply_button = apply
        sizer.AddStretchSpacer(1)
        sizer.Add(ok)
        sizer.AddSpacer(8)
        sizer.Add(cancel)
        sizer.AddSpacer(8)
        sizer.Add(apply)
        return sizer
    def apply(self):
        self.feeds.apply()
    def on_event(self):
        self.apply_button.Enable()
    def on_ok(self, event):
        event.Skip()
        self.apply()
    def on_apply(self, event):
        self.apply()
        self.apply_button.Disable()
        
class FeedsList(wx.ListCtrl):
    def __init__(self, parent, controller, func):
        style = wx.LC_REPORT|wx.LC_VIRTUAL#|wx.LC_HRULES|wx.LC_VRULES
        super(FeedsList, self).__init__(parent, -1, style=style)
        self.controller = controller
        self.func = func
        feeds = self.controller.manager.feeds
        feeds = [feed.make_copy() for feed in feeds]
        self.feeds = feeds
        images = wx.ImageList(16, 16, True)
        self.unchecked = images.AddWithColourMask(wx.Bitmap('icons/unchecked.png'), wx.WHITE)
        self.checked = images.AddWithColourMask(wx.Bitmap('icons/checked.png'), wx.WHITE)
        self.AssignImageList(images, wx.IMAGE_LIST_SMALL)
        self.InsertColumn(0, 'Enabled')
        self.InsertColumn(1, 'Interval')
        self.InsertColumn(2, 'Feed Title')
        self.InsertColumn(3, 'Feed URL')
        self.SetColumnWidth(0, -2)
        self.SetColumnWidth(1, 96)
        self.SetColumnWidth(2, 128)
        self.SetColumnWidth(3, 128)
        self.SetMinSize((450, 200))
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.update()
    def update(self):
        self.SetItemCount(len(self.feeds))
        self.Refresh()
    def on_left_down(self, event):
        index, flags = self.HitTest(event.GetPosition())
        if index >= 0 and (flags & wx.LIST_HITTEST_ONITEMICON):
            self.toggle(index)
        event.Skip()
    def toggle(self, index):
        feed = self.feeds[index]
        feed.enabled = not feed.enabled
        self.RefreshItem(index)
        self.func()
    def OnGetItemImage(self, index):
        feed = self.feeds[index]
        return 1 if feed.enabled else 0
    def OnGetItemText(self, index, column):
        feed = self.feeds[index]
        if column == 1:
            return util.split_time_str(feed.interval)
        if column == 2:
            return feed.title
        if column == 3:
            return feed.url
        return ''
        
class FeedsPanel(wx.Panel):
    def __init__(self, parent, controller, func):
        super(FeedsPanel, self).__init__(parent, -1)
        self.controller = controller
        self.func = func
        panel = self.create_panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        self.SetSizerAndFit(sizer)
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        list = FeedsList(panel, self.controller, self.func)
        list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection)
        list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_selection)
        list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_edit)
        self.list = list
        buttons = self.create_buttons(panel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(list, 1, wx.EXPAND)
        sizer.AddSpacer(8)
        sizer.Add(buttons, 0, wx.EXPAND)
        panel.SetSizerAndFit(sizer)
        return panel
    def create_buttons(self, parent):
        new = wx.Button(parent, -1, 'Add...')
        #import_feeds = wx.Button(parent, -1, 'Import...')
        edit = wx.Button(parent, -1, 'Edit...')
        delete = wx.Button(parent, -1, 'Delete')
        new.Bind(wx.EVT_BUTTON, self.on_new)
        edit.Bind(wx.EVT_BUTTON, self.on_edit)
        delete.Bind(wx.EVT_BUTTON, self.on_delete)
        edit.Disable()
        delete.Disable()
        self.edit = edit
        self.delete = delete
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(new)
        sizer.AddSpacer(8)
        #sizer.Add(import_feeds)
        #sizer.AddSpacer(8)
        sizer.Add(edit)
        sizer.AddSpacer(8)
        sizer.Add(delete)
        sizer.AddStretchSpacer(1)
        return sizer
    def apply(self):
        before = {}
        after = {}
        for feed in self.controller.manager.feeds:
            before[feed.uuid] = feed
        for feed in self.list.feeds:
            after[feed.uuid] = feed
        before_set = set(before.keys())
        after_set = set(after.keys())
        added = after_set - before_set
        deleted = before_set - after_set
        same = after_set & before_set
        for uuid in added:
            feed = after[uuid]
            self.controller.manager.feeds.append(feed)
        for uuid in deleted:
            feed = before[uuid]
            self.controller.manager.feeds.remove(feed)
        for uuid in same:
            a = before[uuid]
            b = after[uuid]
            a.copy_from(b)
    def update(self):
        self.list.update()
        self.func()
    def on_selection(self, event):
        event.Skip()
        count = self.list.GetSelectedItemCount()
        self.edit.Enable(count == 1)
        self.delete.Enable(count > 0)
    def on_edit(self, event):
        count = self.list.GetSelectedItemCount()
        if count != 1:
            return
        index = self.list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        feed = self.list.feeds[index]
        window = EditFeedDialog(self, feed)
        window.CenterOnScreen()
        window.ShowModal()
        window.Destroy()
        self.update()
    def on_new(self, event):
        feed = AddFeedDialog.show_wizard(self)
        if feed:
            self.list.feeds.append(feed)
        self.update()
    def on_delete(self, event):
        feeds = []
        index = -1
        while True:
            index = self.list.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index < 0:
                break
            feed = self.list.feeds[index]
            feeds.append(feed)
        for feed in feeds:
            self.list.feeds.remove(feed)
        self.update()
        
class PopupsPanel(wx.Panel):
    def __init__(self, parent):
        super(PopupsPanel, self).__init__(parent, -1)
        panel = self.create_panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        self.SetSizerAndFit(sizer)
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        return panel
        
class OptionsPanel(wx.Panel):
    def __init__(self, parent):
        super(OptionsPanel, self).__init__(parent, -1)
        panel = self.create_panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        self.SetSizerAndFit(sizer)
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        return panel
        