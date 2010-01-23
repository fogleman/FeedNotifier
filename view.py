import wx
import util
import feeds
import threading
import feedparser
from settings import settings

class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self, controller):
        super(TaskBarIcon, self).__init__()
        self.controller = controller
        self.set_icon('icons/feed.png')
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
    def CreatePopupMenu(self):
        menu = wx.Menu()
        util.menu_item(menu, 'Add Feed...', self.on_add_feed, 'icons/add.png')
        util.menu_item(menu, 'Preferences...', self.on_settings, 'icons/cog.png')
        menu.AppendSeparator()
        if self.controller.enabled:
            util.menu_item(menu, 'Disable Updates', self.on_disable, 'icons/delete.png')
            util.menu_item(menu, 'Update Now', self.on_force_update, 'icons/transmit.png')
        else:
            util.menu_item(menu, 'Enable Updates', self.on_enable, 'icons/accept.png')
            item = util.menu_item(menu, 'Update Now', self.on_force_update, 'icons/transmit.png')
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
        self.controller = controller
        self.icon = TaskBarIcon(controller)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.CenterOnScreen()
    def on_close(self, event):
        event.Skip()
        wx.CallAfter(self.icon.Destroy)
        self.controller.manager.save()
        
class AddFeedDialog(wx.Dialog):
    @staticmethod
    def show_wizard(parent, url=''):
        while True:
            window = AddFeedDialog(parent, url)
            window.Center()
            result = window.ShowModal()
            data = window.result
            window.Destroy()
            if result != wx.ID_OK:
                return None
            url = data.href
            entries = data.get('entries', [])
            feed = feeds.Feed(url)
            feed.title = data.feed.title
            feed.link = data.feed.link
            feed.interval = util.guess_polling_interval(entries)
            window = EditFeedDialog(parent, feed, True)
            window.Center()
            result = window.ShowModal()
            window.Destroy()
            if result == wx.ID_BACKWARD:
                continue
            if result == wx.ID_OK:
                return feed
            return None
    def __init__(self, parent, initial_url=''):
        super(AddFeedDialog, self).__init__(parent, -1, 'Add RSS/Atom Feed')
        #self.SetIcon(wx.IconFromBitmap(wx.Bitmap('icons/feed.png')))
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
        value = self.get_initial_url()
        value = value.replace('feed://', 'http://')
        url = wx.TextCtrl(parent, -1, value, size=(300, -1))
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
        #self.SetIcon(wx.IconFromBitmap(wx.Bitmap('icons/feed.png')))
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
        units.Append('second(s)', 1)
        units.Append('minute(s)', 60)
        units.Append('hour(s)', 60*60)
        units.Append('day(s)', 60*60*24)
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
        label = wx.StaticText(parent, -1, 'The polling interval specifies how often the application will check the feed for new items. When adding a new feed, the application automatically fills this in by examining the items in the feed.')
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
        if interval < 60:
            dialog = wx.MessageDialog(self, 'Are you sure you want to check this feed every %d second(s)?\n\nYou might make the website administrator unhappy!' % interval, 'Confirm Polling Interval', wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
            result = dialog.ShowModal()
            dialog.Destroy()
            if result == wx.ID_NO:
                return
        self.feed.title = title
        self.feed.link = link
        self.feed.interval = interval
        self.EndModal(wx.ID_OK)
        
class Model(object):
    def __init__(self, controller):
        self.controller = controller
        self.reset()
    def reset(self):
        self._sort_column = -1
        feeds = self.controller.manager.feeds
        feeds = [feed.make_copy() for feed in feeds]
        self.feeds = feeds
        self.settings = {}
    def __getattr__(self, key):
        if key != key.upper():
            return super(Model, self).__getattr__(key)
        if key in self.settings:
            return self.settings[key]
        return getattr(settings, key)
    def __setattr__(self, key, value):
        if key != key.upper():
            return super(Model, self).__setattr__(key, value)
        self.settings[key] = value
    def apply(self):
        self.apply_feeds()
        self.apply_settings()
    def apply_settings(self):
        for key, value in self.settings.items():
            setattr(settings, key, value)
    def apply_feeds(self):
        before = {}
        after = {}
        controller = self.controller
        for feed in controller.manager.feeds:
            before[feed.uuid] = feed
        for feed in self.feeds:
            after[feed.uuid] = feed
        before_set = set(before.keys())
        after_set = set(after.keys())
        added = after_set - before_set
        deleted = before_set - after_set
        same = after_set & before_set
        for uuid in added:
            feed = after[uuid]
            controller.manager.feeds.append(feed)
        for uuid in deleted:
            feed = before[uuid]
            controller.manager.feeds.remove(feed)
        for uuid in same:
            a = before[uuid]
            b = after[uuid]
            a.copy_from(b)
    def sort_feeds(self, column):
        def cmp_enabled(a, b):
            return cmp(a.enabled, b.enabled)
        def cmp_interval(a, b):
            return cmp(a.interval, b.interval)
        def cmp_title(a, b):
            return cmp(a.title, b.title)
        def cmp_url(a, b):
            return cmp(a.url, b.url)
        funcs = {
            0: cmp_enabled,
            1: cmp_interval,
            2: cmp_title,
            3: cmp_url,
        }
        self.feeds.sort(cmp=funcs[column])
        if column == self._sort_column:
            self.feeds.reverse()
            self._sort_column = -1
        else:
            self._sort_column = column
            
class SettingsDialog(wx.Dialog):
    def __init__(self, parent, controller):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(SettingsDialog, self).__init__(parent, -1, 'Feed Notifier Preferences', style=style)
        #self.SetIcon(wx.IconFromBitmap(wx.Bitmap('icons/feed.png')))
        self.model = Model(controller)
        panel = self.create_panel(self)
        self.Fit()
        self.SetMinSize(self.GetSize())
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
        images.Add(wx.Bitmap('icons/info32.png'))
        notebook = wx.Toolbook(parent, -1)
        notebook.SetInternalBorder(0)
        notebook.AssignImageList(images)
        feeds = FeedsPanel(notebook, self)
        popups = PopupsPanel(notebook, self)
        options = OptionsPanel(notebook, self)
        about = AboutPanel(notebook)
        notebook.AddPage(feeds, 'Feeds', imageId=0)
        notebook.AddPage(popups, 'Pop-ups', imageId=1)
        notebook.AddPage(options, 'Options', imageId=2)
        notebook.AddPage(about, 'About', imageId=3)
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
        self.popups.update_model()
        self.options.update_model()
        self.model.apply()
        self.model.controller.poll()
    def on_change(self):
        self.apply_button.Enable()
    def on_ok(self, event):
        self.apply()
        event.Skip()
    def on_apply(self, event):
        self.apply()
        self.apply_button.Disable()
        
class FeedsList(wx.ListCtrl):
    def __init__(self, parent, dialog):
        style = wx.LC_REPORT|wx.LC_VIRTUAL#|wx.LC_HRULES|wx.LC_VRULES
        super(FeedsList, self).__init__(parent, -1, style=style)
        self.dialog = dialog
        self.model = dialog.model
        images = wx.ImageList(16, 16, True)
        images.AddWithColourMask(wx.Bitmap('icons/unchecked.png'), wx.WHITE)
        images.AddWithColourMask(wx.Bitmap('icons/checked.png'), wx.WHITE)
        self.AssignImageList(images, wx.IMAGE_LIST_SMALL)
        self.InsertColumn(0, 'Enabled')
        self.InsertColumn(1, 'Interval')
        self.InsertColumn(2, 'Feed Title')
        self.InsertColumn(3, 'Feed URL')
        self.SetColumnWidth(0, -2)
        self.SetColumnWidth(1, 100)
        self.SetColumnWidth(2, 180)
        self.SetColumnWidth(3, 180)
        self.SetMinSize((500, 250))
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.on_col_click)
        self.update()
    def update(self):
        self.SetItemCount(len(self.model.feeds))
        self.Refresh()
    def on_col_click(self, event):
        column = event.GetColumn()
        self.model.sort_feeds(column)
        self.update()
    def on_left_down(self, event):
        index, flags = self.HitTest(event.GetPosition())
        if index >= 0 and (flags & wx.LIST_HITTEST_ONITEMICON):
            self.toggle(index)
        event.Skip()
    def toggle(self, index):
        feed = self.model.feeds[index]
        feed.enabled = not feed.enabled
        self.RefreshItem(index)
        self.dialog.on_change()
    def OnGetItemImage(self, index):
        feed = self.model.feeds[index]
        return 1 if feed.enabled else 0
    def OnGetItemText(self, index, column):
        feed = self.model.feeds[index]
        if column == 1:
            return util.split_time_str(feed.interval)
        if column == 2:
            return feed.title
        if column == 3:
            return feed.url
        return ''
        
class FeedsPanel(wx.Panel):
    def __init__(self, parent, dialog):
        super(FeedsPanel, self).__init__(parent, -1)
        self.dialog = dialog
        self.model = dialog.model
        panel = self.create_panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        line = wx.StaticLine(self, -1)
        sizer.Add(line, 0, wx.EXPAND)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        self.SetSizerAndFit(sizer)
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        list = FeedsList(panel, self.dialog)
        list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection)
        list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_selection)
        list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_edit)
        list.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
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
    def update(self):
        self.list.update()
        self.update_buttons()
        self.dialog.on_change()
    def on_selection(self, event):
        event.Skip()
        self.update_buttons()
    def update_buttons(self):
        count = self.list.GetSelectedItemCount()
        self.edit.Enable(count == 1)
        self.delete.Enable(count > 0)
    def on_left_down(self, event):
        index, flags = self.list.HitTest(event.GetPosition())
        if flags & wx.LIST_HITTEST_NOWHERE:
            self.edit.Disable()
            self.delete.Disable()
        event.Skip()
    def on_edit(self, event):
        count = self.list.GetSelectedItemCount()
        if count != 1:
            return
        index = self.list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        feed = self.model.feeds[index]
        window = EditFeedDialog(self, feed)
        window.CenterOnScreen()
        result = window.ShowModal()
        window.Destroy()
        if result == wx.ID_OK:
            self.update()
    def on_new(self, event):
        feed = AddFeedDialog.show_wizard(self)
        if feed:
            self.model.feeds.append(feed)
            self.update()
    def on_delete(self, event):
        feeds = []
        index = -1
        while True:
            index = self.list.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index < 0:
                break
            feed = self.model.feeds[index]
            feeds.append(feed)
        if feeds:
            for feed in feeds:
                self.model.feeds.remove(feed)
            self.update()
            
class PopupsPanel(wx.Panel):
    def __init__(self, parent, dialog):
        super(PopupsPanel, self).__init__(parent, -1)
        self.dialog = dialog
        self.model = dialog.model
        panel = self.create_panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        line = wx.StaticLine(self, -1)
        sizer.Add(line, 0, wx.EXPAND)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.update_controls()
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        behavior = self.create_behavior(panel)
        appearance = self.create_appearance(panel)
        content = self.create_content(panel)
        sizer.Add(behavior, 0, wx.EXPAND)
        sizer.AddSpacer(8)
        sizer.Add(appearance, 0, wx.EXPAND)
        sizer.AddSpacer(8)
        sizer.Add(content, 0, wx.EXPAND)
        panel.SetSizerAndFit(sizer)
        return panel
    def create_appearance(self, parent):
        box = wx.StaticBox(parent, -1, 'Appearance')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.GridBagSizer(8, 8)
        labels = ['Theme', 'Width', 'Position', 'Transparency']
        positions = [(0, 0), (0, 3), (1, 0), (1, 3)]
        for label, position in zip(labels, positions):
            text = wx.StaticText(parent, -1, label)
            grid.Add(text, position, flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        theme = wx.Choice(parent, -1)
        for name in util.find_themes():
            theme.Append(util.pretty_name(name), name)
        position = wx.Choice(parent, -1)
        position.Append('Upper Left', (-1, -1))
        position.Append('Upper Right', (1, -1))
        position.Append('Lower Left', (-1, 1))
        position.Append('Lower Right', (1, 1))
        position.Append('Center', (0, 0))
        width = wx.SpinCtrl(parent, -1, '1', min=1, max=9999, size=(64, -1))
        transparency = wx.SpinCtrl(parent, -1, '0', min=0, max=255, size=(64, -1))
        grid.Add(theme, (0, 1))
        grid.Add(position, (1, 1))
        grid.Add(width, (0, 4))
        grid.Add(transparency, (1, 4))
        text = wx.StaticText(parent, -1, 'pixels')
        grid.Add(text, (0, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        text = wx.StaticText(parent, -1, '[0-255], 255=opaque')
        grid.Add(text, (1, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        theme.Bind(wx.EVT_CHOICE, self.on_change)
        position.Bind(wx.EVT_CHOICE, self.on_change)
        width.Bind(wx.EVT_SPINCTRL, self.on_change)
        transparency.Bind(wx.EVT_SPINCTRL, self.on_change)
        
        self.theme = theme
        self.position = position
        self.width = width
        self.transparency = transparency
        return sizer
    def create_behavior(self, parent):
        box = wx.StaticBox(parent, -1, 'Behavior')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.GridBagSizer(8, 8)
        
        text = wx.StaticText(parent, -1, 'Duration')
        grid.Add(text, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        text = wx.StaticText(parent, -1, 'seconds')
        grid.Add(text, (0, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        
        duration = wx.SpinCtrl(parent, -1, '1', min=1, max=60, size=(64, -1))
        auto = wx.CheckBox(parent, -1, 'Auto-play new items')
        grid.Add(duration, (0, 1))
        grid.Add(auto, (0, 4), flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        duration.Bind(wx.EVT_SPINCTRL, self.on_change)
        auto.Bind(wx.EVT_CHECKBOX, self.on_change)
        
        self.duration = duration
        self.auto = auto
        return sizer
    def create_content(self, parent):
        box = wx.StaticBox(parent, -1, 'Content')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.GridBagSizer(8, 8)
        
        text = wx.StaticText(parent, -1, 'Max. Title Length')
        grid.Add(text, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        text = wx.StaticText(parent, -1, 'Max. Body Length')
        grid.Add(text, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        text = wx.StaticText(parent, -1, 'characters')
        grid.Add(text, (0, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        text = wx.StaticText(parent, -1, 'characters')
        grid.Add(text, (1, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        
        title = wx.SpinCtrl(parent, -1, '1', min=1, max=9999, size=(64, -1))
        body = wx.SpinCtrl(parent, -1, '1', min=1, max=9999, size=(64, -1))
        grid.Add(title, (0, 1))
        grid.Add(body, (1, 1))
        
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        title.Bind(wx.EVT_SPINCTRL, self.on_change)
        body.Bind(wx.EVT_SPINCTRL, self.on_change)
        
        self.title = title
        self.body = body
        return sizer
    def update_controls(self):
        model = self.model
        self.width.SetValue(model.POPUP_WIDTH)
        self.transparency.SetValue(model.POPUP_TRANSPARENCY)
        self.duration.SetValue(model.POPUP_DURATION)
        self.auto.SetValue(model.POPUP_AUTO_PLAY)
        self.title.SetValue(model.POPUP_TITLE_LENGTH)
        self.body.SetValue(model.POPUP_BODY_LENGTH)
        util.select_choice(self.theme, model.POPUP_THEME)
        util.select_choice(self.position, model.POPUP_POSITION)
    def update_model(self):
        model = self.model
        model.POPUP_WIDTH = self.width.GetValue()
        model.POPUP_TRANSPARENCY = self.transparency.GetValue()
        model.POPUP_DURATION = self.duration.GetValue()
        model.POPUP_TITLE_LENGTH = self.title.GetValue()
        model.POPUP_BODY_LENGTH = self.body.GetValue()
        model.POPUP_AUTO_PLAY = self.auto.GetValue()
        model.POPUP_THEME = self.theme.GetClientData(self.theme.GetSelection())
        model.POPUP_POSITION = self.position.GetClientData(self.position.GetSelection())
    def on_change(self, event):
        self.dialog.on_change()
        event.Skip()
        
class OptionsPanel(wx.Panel):
    def __init__(self, parent, dialog):
        super(OptionsPanel, self).__init__(parent, -1)
        self.dialog = dialog
        self.model = dialog.model
        panel = self.create_panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        line = wx.StaticLine(self, -1)
        sizer.Add(line, 0, wx.EXPAND)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.update_controls()
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        polling = self.create_polling(panel)
        caching = self.create_caching(panel)
        sizer.Add(polling, 0, wx.EXPAND)
        sizer.AddSpacer(8)
        sizer.Add(caching, 0, wx.EXPAND)
        panel.SetSizerAndFit(sizer)
        return panel
    def create_polling(self, parent):
        box = wx.StaticBox(parent, -1, 'Polling')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.GridBagSizer(8, 8)
        
        idle = wx.CheckBox(parent, -1, "Don't check feeds if I've been idle for")
        grid.Add(idle, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        text = wx.StaticText(parent, -1, 'seconds')
        grid.Add(text, (0, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        
        timeout = wx.SpinCtrl(parent, -1, '1', min=1, max=9999, size=(64, -1))
        grid.Add(timeout, (0, 1))
        
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        timeout.Bind(wx.EVT_SPINCTRL, self.on_change)
        idle.Bind(wx.EVT_CHECKBOX, self.on_change)
        
        self.idle = idle
        self.timeout = timeout
        return sizer
    def create_caching(self, parent):
        box = wx.StaticBox(parent, -1, 'Caching')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.GridBagSizer(8, 8)
        
        text = wx.StaticText(parent, -1, 'Item History')
        grid.Add(text, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        text = wx.StaticText(parent, -1, 'Feed Cache')
        grid.Add(text, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        text = wx.StaticText(parent, -1, 'days')
        grid.Add(text, (0, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        text = wx.StaticText(parent, -1, 'items per feed')
        grid.Add(text, (1, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        
        item = wx.SpinCtrl(parent, -1, '1', min=1, max=365, size=(64, -1))
        grid.Add(item, (0, 1))
        feed = wx.SpinCtrl(parent, -1, '1', min=1, max=9999, size=(64, -1))
        grid.Add(feed, (1, 1))
        
        clear_item = wx.Button(parent, -1, 'Clear')
        grid.Add(clear_item, (0, 3))
        clear_feed = wx.Button(parent, -1, 'Clear')
        grid.Add(clear_feed, (1, 3))
        
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        item.Bind(wx.EVT_SPINCTRL, self.on_change)
        feed.Bind(wx.EVT_SPINCTRL, self.on_change)
        clear_item.Bind(wx.EVT_BUTTON, self.on_clear_item)
        clear_feed.Bind(wx.EVT_BUTTON, self.on_clear_feed)
        
        self.item = item
        self.feed = feed
        self.clear_item = clear_item
        self.clear_feed = clear_feed
        return sizer
    def update_controls(self):
        model = self.model
        self.idle.SetValue(model.DISABLE_WHEN_IDLE)
        self.timeout.SetValue(model.USER_IDLE_TIMEOUT)
        one_day = 60 * 60 * 24
        self.item.SetValue(model.ITEM_CACHE_AGE / one_day)
        self.feed.SetValue(model.FEED_CACHE_SIZE)
    def update_model(self):
        model = self.model
        model.DISABLE_WHEN_IDLE = self.idle.GetValue()
        model.USER_IDLE_TIMEOUT = self.timeout.GetValue()
        one_day = 60 * 60 * 24
        model.ITEM_CACHE_AGE = self.item.GetValue() * one_day
        model.FEED_CACHE_SIZE = self.feed.GetValue()
    def on_change(self, event):
        self.dialog.on_change()
        event.Skip()
    def on_clear_item(self, event):
        self.model.controller.manager.clear_item_history()
        self.clear_item.Disable()
    def on_clear_feed(self, event):
        self.model.controller.manager.clear_feed_cache()
        self.clear_feed.Disable()
        
class AboutPanel(wx.Panel):
    def __init__(self, parent):
        super(AboutPanel, self).__init__(parent, -1)
        panel = self.create_panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        line = wx.StaticLine(self, -1)
        sizer.Add(line, 0, wx.EXPAND)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        self.SetSizerAndFit(sizer)
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1, style=wx.BORDER_SUNKEN)
        panel.SetBackgroundColour(wx.WHITE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        bitmap = wx.StaticBitmap(panel, -1, wx.Bitmap('icons/about.png'))
        sizer.AddStretchSpacer(1)
        sizer.Add(bitmap, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddStretchSpacer(1)
        panel.SetSizerAndFit(sizer)
        return panel
        