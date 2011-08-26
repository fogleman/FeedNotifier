import wx
import util
import feeds
import filters
from settings import settings

INDEX_ENABLED = 0
INDEX_URL = 1
INDEX_TITLE = 2
INDEX_INTERVAL = 3
INDEX_ITEM_COUNT = 4
INDEX_CLICKS = 5

INDEX_RULES = 1
INDEX_FEEDS = 2
INDEX_IN = 3
INDEX_OUT = 4

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
        self.SetIcon(icon, settings.APP_NAME)
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
            url = data.original_url
            entries = util.get(data, 'entries', [])
            feed = feeds.Feed(url)
            feed.title = util.get(data.feed, 'title', '')
            feed.link = util.get(data.feed, 'link', '')
            feed.username = util.encode_password(data.username)
            feed.password = util.encode_password(data.password)
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
        util.set_icon(self)
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
        value = value.replace('feed:https://', 'https://')
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
        self.lock()
        util.start_thread(self.check_feed, url)
    def on_valid(self, result):
        self.result = result
        self.EndModal(wx.ID_OK)
    def on_invalid(self):
        dialog = wx.MessageDialog(self, 'The URL entered does not appear to be a valid RSS/Atom feed.', 'Invalid Feed', wx.OK|wx.ICON_ERROR)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
        self.unlock()
    def on_password(self, url, username, password):
        dialog = PasswordDialog(self, username, password)
        dialog.Center()
        result = dialog.ShowModal()
        username = dialog.username.GetValue()
        password = dialog.password.GetValue()
        dialog.Destroy()
        if result == wx.ID_OK:
            util.start_thread(self.check_feed, url, username, password)
        else:
            self.unlock()
    def lock(self):
        self.url.Disable()
        self.next.Disable()
        self.status.SetLabel('Checking feed, please wait...')
    def unlock(self):
        self.url.Enable()
        self.next.Enable()
        self.status.SetLabel('')
        self.url.SelectAll()
        self.url.SetFocus()
    def check_feed(self, url, username=None, password=None):
        d = util.parse(url, username, password)
        if not self: # cancelled
            return
        status = util.get(d, 'status', 0)
        if status == 401: # auth required
            wx.CallAfter(self.on_password, url, username, password)
        elif util.is_valid_feed(d):
            d['original_url'] = url
            d['username'] = username
            d['password'] = password
            wx.CallAfter(self.on_valid, d)
        else:
            wx.CallAfter(self.on_invalid)
            
class PasswordDialog(wx.Dialog):
    def __init__(self, parent, username=None, password=None):
        super(PasswordDialog, self).__init__(parent, -1, 'Password Required')
        util.set_icon(self)
        panel = self.create_panel(self)
        if username:
            self.username.SetValue(username)
        if password:
            self.password.SetValue(password)
        self.Fit()
        self.validate()
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        controls = self.create_controls(panel)
        buttons = self.create_buttons(panel)
        sizer.AddStretchSpacer(1)
        sizer.Add(controls, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 12)
        sizer.AddStretchSpacer(1)
        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL&~wx.TOP, 12)
        panel.SetSizerAndFit(sizer)
        return panel
    def create_controls(self, parent):
        sizer = wx.GridBagSizer(8, 8)
        label = wx.StaticText(parent, -1, 'Username')
        username = wx.TextCtrl(parent, -1, '', size=(180, -1))
        username.Bind(wx.EVT_TEXT, self.on_text)
        sizer.Add(label, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        sizer.Add(username, (0, 1))
        self.username = username
        label = wx.StaticText(parent, -1, 'Password')
        password = wx.TextCtrl(parent, -1, '', size=(180, -1), style=wx.TE_PASSWORD)
        password.Bind(wx.EVT_TEXT, self.on_text)
        sizer.Add(label, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        sizer.Add(password, (1, 1))
        self.password = password
        return sizer
    def create_buttons(self, parent):
        ok = wx.Button(parent, wx.ID_OK, 'OK')
        cancel = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        ok.SetDefault()
        ok.Disable()
        self.ok = ok
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddStretchSpacer(1)
        sizer.Add(ok)
        sizer.AddSpacer(8)
        sizer.Add(cancel)
        return sizer
    def validate(self):
        if self.username.GetValue() and self.password.GetValue():
            self.ok.Enable()
        else:
            self.ok.Disable()
    def on_text(self, event):
        self.validate()
        
class EditFeedDialog(wx.Dialog):
    def __init__(self, parent, feed, add=False):
        title = 'Add RSS/Atom Feed' if add else 'Edit RSS/Atom Feed'
        super(EditFeedDialog, self).__init__(parent, -1, title)
        util.set_icon(self)
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
            style = wx.TE_READONLY if index == 0 else 0
            control = wx.TextCtrl(parent, -1, '', size=(300, -1), style=style)
            control.Bind(wx.EVT_TEXT, self.on_text)
            sizer.Add(control, (index, 1), (1, 2))
            controls.append(control)
        url, title, link = controls
        self.url, self.title, self.link = controls
        url.ChangeValue(self.feed.url)
        title.ChangeValue(self.feed.title)
        link.ChangeValue(self.feed.link)
        url.SetBackgroundColour(parent.GetBackgroundColour())
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
        
class EditFilterDialog(wx.Dialog):
    def __init__(self, parent, model, filter=None):
        title = 'Edit Filter' if filter else 'Add Filter'
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(EditFilterDialog, self).__init__(parent, -1, title, style=style)
        util.set_icon(self)
        self.model = model
        self.filter = filter or feeds.Filter('')
        panel = self.create_panel(self)
        buttons = self.create_buttons(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL&~wx.TOP, 8)
        self.SetSizerAndFit(sizer)
        self.validate()
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        rules = self.create_rules(panel)
        options = self.create_options(panel)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(rules, 1, wx.EXPAND)
        sizer.AddSpacer(8)
        sizer.Add(options, 0, wx.EXPAND)
        panel.SetSizer(sizer)
        return panel
    def create_buttons(self, parent):
        ok = wx.Button(parent, wx.ID_OK, 'OK')
        cancel = wx.Button(parent, wx.ID_CANCEL, 'Cancel')
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddStretchSpacer(1)
        sizer.Add(ok)
        sizer.AddSpacer(8)
        sizer.Add(cancel)
        ok.SetDefault()
        ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.ok = ok
        return sizer
    def create_rules(self, parent):
        box = wx.StaticBox(parent, -1, 'Filter Rules')
        box = wx.StaticBoxSizer(box, wx.VERTICAL)
        code = wx.TextCtrl(parent, -1, self.filter.code, style=wx.TE_MULTILINE, size=(250, -1))
        text = '''
        Examples:
        -microsoft and -apple (exclude microsoft and apple)
        google or yahoo (require google or yahoo)
        -author:BoringGuy (search author field only)
        '''
        text = '\n'.join(line.strip() for line in text.strip().split('\n'))
        help = wx.StaticText(parent, -1, text)
        box.Add(code, 1, wx.EXPAND|wx.ALL, 8)
        box.Add(help, 0, wx.EXPAND|wx.ALL&~wx.TOP, 8)
        code.Bind(wx.EVT_TEXT, self.on_event)
        self.code = code
        return box
    def create_options(self, parent):
        sizer = wx.BoxSizer(wx.VERTICAL)
        box = wx.StaticBox(parent, -1, 'Options')
        box = wx.StaticBoxSizer(box, wx.VERTICAL)
        match_case = wx.CheckBox(parent, -1, 'Match Case')
        match_whole_words = wx.CheckBox(parent, -1, 'Match Whole Words')
        match_case.SetValue(not self.filter.ignore_case)
        match_whole_words.SetValue(self.filter.whole_word)
        box.Add(match_case, 0, wx.ALL, 8)
        box.Add(match_whole_words, 0, wx.ALL&~wx.TOP, 8)
        sizer.Add(box, 0, wx.EXPAND)
        sizer.AddSpacer(8)
        box = wx.StaticBox(parent, -1, 'Apply Filter To')
        box = wx.StaticBoxSizer(box, wx.VERTICAL)
        all_feeds = wx.RadioButton(parent, -1, 'All Feeds', style=wx.RB_GROUP)
        selected_feeds = wx.RadioButton(parent, -1, 'Selected Feeds')
        if self.filter.feeds:
            selected_feeds.SetValue(True)
        feeds = wx.CheckListBox(parent, -1, size=(150, 150), style=wx.LB_HSCROLL|wx.LB_EXTENDED)
        def cmp_title(a, b):
            return cmp(a.title.lower(), b.title.lower())
        self.lookup = {}
        items = self.model.controller.manager.feeds
        for index, feed in enumerate(sorted(items, cmp=cmp_title)):
            feeds.Append(feed.title)
            self.lookup[index] = feed
            feeds.Check(index, feed in self.filter.feeds)
        box.Add(all_feeds, 0, wx.ALL, 8)
        box.Add(selected_feeds, 0, wx.ALL&~wx.TOP, 8)
        box.Add(feeds, 1, wx.ALL&~wx.TOP, 8)
        sizer.Add(box, 1, wx.EXPAND)
        match_case.Bind(wx.EVT_CHECKBOX, self.on_event)
        match_whole_words.Bind(wx.EVT_CHECKBOX, self.on_event)
        all_feeds.Bind(wx.EVT_RADIOBUTTON, self.on_event)
        selected_feeds.Bind(wx.EVT_RADIOBUTTON, self.on_event)
        feeds.Bind(wx.EVT_CHECKLISTBOX, self.on_event)
        self.match_case = match_case
        self.match_whole_words = match_whole_words
        self.all_feeds = all_feeds
        self.selected_feeds = selected_feeds
        self.feeds = feeds
        return sizer
    def get_selected_feeds(self):
        result = set()
        if self.selected_feeds.GetValue():
            for index in range(self.feeds.GetCount()):
                if self.feeds.IsChecked(index):
                    result.add(self.lookup[index])
        return result
    def validate(self):
        feeds = self.get_selected_feeds()
        valid = True
        valid = valid and self.code.GetValue()
        valid = valid and (self.all_feeds.GetValue() or feeds)
        try:
            filters.parse(self.code.GetValue())
        except Exception:
            valid = False
        self.ok.Enable(bool(valid))
        self.feeds.Enable(self.selected_feeds.GetValue())
    def on_event(self, event):
        self.validate()
    def on_ok(self, event):
        filter = self.filter
        filter.code = self.code.GetValue()
        filter.ignore_case = not self.match_case.GetValue()
        filter.whole_word = self.match_whole_words.GetValue()
        filter.feeds = self.get_selected_feeds()
        event.Skip()
        
class Model(object):
    def __init__(self, controller):
        self.controller = controller
        self.reset()
    def reset(self):
        self._feed_sort = -1
        self._filter_sort = -1
        feeds = self.controller.manager.feeds
        feeds = [feed.make_copy() for feed in feeds]
        self.feeds = feeds
        filters = self.controller.manager.filters
        filters = [filter.make_copy() for filter in filters]
        self.filters = filters
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
        self.apply_filters()
        self.apply_feeds()
        self.apply_settings()
        self.controller.save()
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
            controller.manager.add_feed(feed)
        for uuid in deleted:
            feed = before[uuid]
            controller.manager.remove_feed(feed)
        for uuid in same:
            a = before[uuid]
            b = after[uuid]
            a.copy_from(b)
    def apply_filters(self):
        before = {}
        after = {}
        controller = self.controller
        for filter in controller.manager.filters:
            before[filter.uuid] = filter
        for filter in self.filters:
            after[filter.uuid] = filter
        before_set = set(before.keys())
        after_set = set(after.keys())
        added = after_set - before_set
        deleted = before_set - after_set
        same = after_set & before_set
        for uuid in added:
            filter = after[uuid]
            controller.manager.add_filter(filter)
        for uuid in deleted:
            filter = before[uuid]
            controller.manager.remove_filter(filter)
        for uuid in same:
            a = before[uuid]
            b = after[uuid]
            a.copy_from(b)
    def sort_feeds(self, column):
        def cmp_enabled(a, b):
            return cmp(a.enabled, b.enabled)
        def cmp_clicks(a, b):
            return cmp(b.clicks, a.clicks)
        def cmp_item_count(a, b):
            return cmp(b.item_count, a.item_count)
        def cmp_interval(a, b):
            return cmp(a.interval, b.interval)
        def cmp_title(a, b):
            return cmp(a.title.lower(), b.title.lower())
        def cmp_url(a, b):
            return cmp(a.url.lower(), b.url.lower())
        funcs = {
            INDEX_ENABLED: cmp_enabled,
            INDEX_URL: cmp_url,
            INDEX_TITLE: cmp_title,
            INDEX_INTERVAL: cmp_interval,
            INDEX_CLICKS: cmp_clicks,
            INDEX_ITEM_COUNT: cmp_item_count,
        }
        self.feeds.sort(cmp=funcs[column])
        if column == self._feed_sort:
            self.feeds.reverse()
            self._feed_sort = -1
        else:
            self._feed_sort = column
    def sort_filters(self, column):
        def cmp_enabled(a, b):
            return cmp(a.enabled, b.enabled)
        def cmp_rules(a, b):
            return cmp(a.code, b.code)
        def cmp_feeds(a, b):
            return cmp(len(a.feeds), len(b.feeds))
        def cmp_in(a, b):
            return cmp(b.inputs, a.inputs)
        def cmp_out(a, b):
            return cmp(b.outputs, a.outputs)
        funcs = {
            INDEX_ENABLED: cmp_enabled,
            INDEX_RULES: cmp_rules,
            INDEX_FEEDS: cmp_feeds,
            INDEX_IN: cmp_in,
            INDEX_OUT: cmp_out,
        }
        self.filters.sort(cmp=funcs[column])
        if column == self._filter_sort:
            self.filters.reverse()
            self._filter_sort = -1
        else:
            self._filter_sort = column
            
class SettingsDialog(wx.Dialog):
    def __init__(self, parent, controller):
        title = '%s Preferences' % settings.APP_NAME
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(SettingsDialog, self).__init__(parent, -1, title, style=style)
        util.set_icon(self)
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
        images.Add(util.scale_bitmap(wx.Bitmap('icons/feed32.png'), -1, -1, self.GetBackgroundColour()))
        images.Add(util.scale_bitmap(wx.Bitmap('icons/comment32.png'), -1, -1, self.GetBackgroundColour()))
        images.Add(util.scale_bitmap(wx.Bitmap('icons/cog32.png'), -1, -1, self.GetBackgroundColour()))
        images.Add(util.scale_bitmap(wx.Bitmap('icons/filter32.png'), -1, -1, self.GetBackgroundColour()))
        images.Add(util.scale_bitmap(wx.Bitmap('icons/info32.png'), -1, -1, self.GetBackgroundColour()))
        notebook = wx.Toolbook(parent, -1)
        notebook.SetInternalBorder(0)
        notebook.AssignImageList(images)
        feeds = FeedsPanel(notebook, self)
        popups = PopupsPanel(notebook, self)
        options = OptionsPanel(notebook, self)
        filters = FiltersPanel(notebook, self)
        about = AboutPanel(notebook)
        notebook.AddPage(feeds, 'Feeds', imageId=0)
        notebook.AddPage(popups, 'Pop-ups', imageId=1)
        notebook.AddPage(options, 'Options', imageId=2)
        notebook.AddPage(filters, 'Filters', imageId=3)
        notebook.AddPage(about, 'About', imageId=4)
        self.popups = popups
        self.options = options
        notebook.Fit()
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
        self.InsertColumn(INDEX_ENABLED, 'On')
        self.InsertColumn(INDEX_URL, 'Feed URL')
        self.InsertColumn(INDEX_TITLE, 'Feed Title')
        self.InsertColumn(INDEX_INTERVAL, 'Interval')
        self.InsertColumn(INDEX_ITEM_COUNT, 'Items')
        self.InsertColumn(INDEX_CLICKS, 'Clicks')
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.on_col_click)
        self.update()
        self.SetColumnWidth(INDEX_ENABLED, 32)
        self.SetColumnWidth(INDEX_URL, 165)
        self.SetColumnWidth(INDEX_TITLE, 165)
        self.SetColumnWidth(INDEX_INTERVAL, 75)
        self.SetColumnWidth(INDEX_ITEM_COUNT, -2)
        self.SetColumnWidth(INDEX_CLICKS, -2)
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
        if column == INDEX_URL:
            return feed.url
        if column == INDEX_TITLE:
            return feed.title
        if column == INDEX_INTERVAL:
            return util.split_time_str(feed.interval)
        if column == INDEX_CLICKS:
            return str(feed.clicks) if feed.clicks else ''
        if column == INDEX_ITEM_COUNT:
            return str(feed.item_count) if feed.item_count else ''
        return ''
        
class FiltersList(wx.ListCtrl):
    def __init__(self, parent, dialog):
        style = wx.LC_REPORT|wx.LC_VIRTUAL#|wx.LC_HRULES|wx.LC_VRULES
        super(FiltersList, self).__init__(parent, -1, style=style)
        self.dialog = dialog
        self.model = dialog.model
        images = wx.ImageList(16, 16, True)
        images.AddWithColourMask(wx.Bitmap('icons/unchecked.png'), wx.WHITE)
        images.AddWithColourMask(wx.Bitmap('icons/checked.png'), wx.WHITE)
        self.AssignImageList(images, wx.IMAGE_LIST_SMALL)
        self.InsertColumn(INDEX_ENABLED, 'On')
        self.InsertColumn(INDEX_RULES, 'Filter Rules')
        self.InsertColumn(INDEX_FEEDS, 'Feeds')
        self.InsertColumn(INDEX_IN, 'In')
        self.InsertColumn(INDEX_OUT, 'Out')
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.on_col_click)
        self.update()
        self.SetColumnWidth(INDEX_ENABLED, 32)
        self.SetColumnWidth(INDEX_RULES, 200)
        self.SetColumnWidth(INDEX_FEEDS, 64)
        self.SetColumnWidth(INDEX_IN, 64)
        self.SetColumnWidth(INDEX_OUT, 64)
    def update(self):
        self.SetItemCount(len(self.model.filters))
        self.Refresh()
    def on_col_click(self, event):
        column = event.GetColumn()
        self.model.sort_filters(column)
        self.update()
    def on_left_down(self, event):
        index, flags = self.HitTest(event.GetPosition())
        if index >= 0 and (flags & wx.LIST_HITTEST_ONITEMICON):
            self.toggle(index)
        event.Skip()
    def toggle(self, index):
        filter = self.model.filters[index]
        filter.enabled = not filter.enabled
        self.RefreshItem(index)
        self.dialog.on_change()
    def OnGetItemImage(self, index):
        filter = self.model.filters[index]
        return 1 if filter.enabled else 0
    def OnGetItemText(self, index, column):
        filter = self.model.filters[index]
        if column == INDEX_RULES:
            return filter.code.replace('\n', ' ')
        if column == INDEX_FEEDS:
            return str(len(filter.feeds)) if filter.feeds else 'All'
        if column == INDEX_IN:
            return str(filter.inputs)
        if column == INDEX_OUT:
            return str(filter.outputs)
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
        dialog = wx.MessageDialog(self.dialog, 'Are you sure you want to delete the selected feed(s)?', 'Confirm Delete', wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
        result = dialog.ShowModal()
        dialog.Destroy()
        if result != wx.ID_YES:
            return
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
            
class FiltersPanel(wx.Panel):
    def __init__(self, parent, dialog):
        super(FiltersPanel, self).__init__(parent, -1)
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
        list = FiltersList(panel, self.dialog)
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
        filter = self.model.filters[index]
        window = EditFilterDialog(self, self.model, filter)
        window.Center()
        result = window.ShowModal()
        window.Destroy()
        if result == wx.ID_OK:
            self.update()
    def on_new(self, event):
        window = EditFilterDialog(self, self.model)
        window.Center()
        result = window.ShowModal()
        filter = window.filter
        window.Destroy()
        if result == wx.ID_OK:
            self.model.filters.append(filter)
            self.update()
    def on_delete(self, event):
        dialog = wx.MessageDialog(self.dialog, 'Are you sure you want to delete the selected filter(s)?', 'Confirm Delete', wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
        result = dialog.ShowModal()
        dialog.Destroy()
        if result != wx.ID_YES:
            return
        filters = []
        index = -1
        while True:
            index = self.list.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index < 0:
                break
            filter = self.model.filters[index]
            filters.append(filter)
        if filters:
            for filter in filters:
                self.model.filters.remove(filter)
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
        self.update_controls()
        self.SetSizerAndFit(sizer)
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
        labels = ['Position', 'Width', 'Monitor', 'Transparency', 'Border', 'Border Size']
        positions = [(0, 0), (0, 3), (1, 0), (1, 3), (2, 0), (2, 3)]
        for label, position in zip(labels, positions):
            text = wx.StaticText(parent, -1, label)
            grid.Add(text, position, flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        position = wx.Choice(parent, -1)
        position.Append('Upper Left', (-1, -1))
        position.Append('Upper Right', (1, -1))
        position.Append('Lower Left', (-1, 1))
        position.Append('Lower Right', (1, 1))
        position.Append('Center', (0, 0))
        width = wx.SpinCtrl(parent, -1, '1', min=1, max=9999, size=(64, -1))
        transparency = wx.SpinCtrl(parent, -1, '0', min=0, max=255, size=(64, -1))
        display = wx.Choice(parent, -1)
        for index in range(wx.Display_GetCount()):
            display.Append('Monitor #%d' % (index + 1), index)
        border_color = wx.Button(parent, -1)
        border_size = wx.SpinCtrl(parent, -1, '1', min=1, max=10, size=(64, -1))

        grid.Add(position, (0, 1), flag=wx.EXPAND)
        grid.Add(display, (1, 1), flag=wx.EXPAND)
        grid.Add(width, (0, 4))
        grid.Add(transparency, (1, 4))
        grid.Add(border_color, (2, 1), flag=wx.EXPAND)
        grid.Add(border_size, (2, 4))
        text = wx.StaticText(parent, -1, 'pixels')
        grid.Add(text, (0, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        text = wx.StaticText(parent, -1, '[0-255], 255=opaque')
        grid.Add(text, (1, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        text = wx.StaticText(parent, -1, 'pixels')
        grid.Add(text, (2, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        position.Bind(wx.EVT_CHOICE, self.on_change)
        display.Bind(wx.EVT_CHOICE, self.on_change)
        width.Bind(wx.EVT_SPINCTRL, self.on_change)
        transparency.Bind(wx.EVT_SPINCTRL, self.on_change)
        border_size.Bind(wx.EVT_SPINCTRL, self.on_change)
        border_color.Bind(wx.EVT_BUTTON, self.on_border_color)
        
        self.position = position
        self.display = display
        self.width = width
        self.transparency = transparency
        self.border_color = border_color
        self.border_size = border_size
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
        auto = wx.CheckBox(parent, -1, 'Infinite duration')
        sound = wx.CheckBox(parent, -1, 'Sound notification')
        hover = wx.CheckBox(parent, -1, 'Wait if hovering')
        top = wx.CheckBox(parent, -1, 'Stay on top')

        grid.Add(duration, (0, 1))
        grid.Add(auto, (0, 4), flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(sound, (1, 4), flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(hover, (0, 6), flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(top, (1, 6), flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        duration.Bind(wx.EVT_SPINCTRL, self.on_change)
        auto.Bind(wx.EVT_CHECKBOX, self.on_change)
        sound.Bind(wx.EVT_CHECKBOX, self.on_change)
        hover.Bind(wx.EVT_CHECKBOX, self.on_change)
        top.Bind(wx.EVT_CHECKBOX, self.on_change)
        
        self.duration = duration
        self.auto = auto
        self.sound = sound
        self.hover = hover
        self.top = top
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
        self.auto.SetValue(not model.POPUP_AUTO_PLAY)
        self.sound.SetValue(model.PLAY_SOUND)
        self.hover.SetValue(model.POPUP_WAIT_ON_HOVER)
        self.top.SetValue(model.POPUP_STAY_ON_TOP)
        self.title.SetValue(model.POPUP_TITLE_LENGTH)
        self.body.SetValue(model.POPUP_BODY_LENGTH)
        util.select_choice(self.position, model.POPUP_POSITION)
        util.select_choice(self.display, model.POPUP_DISPLAY)
        self.border_color.SetBackgroundColour(wx.Color(*settings.POPUP_BORDER_COLOR))
        self.border_size.SetValue(model.POPUP_BORDER_SIZE)
    def update_model(self):
        model = self.model
        model.POPUP_WIDTH = self.width.GetValue()
        model.POPUP_TRANSPARENCY = self.transparency.GetValue()
        model.POPUP_DURATION = self.duration.GetValue()
        model.POPUP_TITLE_LENGTH = self.title.GetValue()
        model.POPUP_BODY_LENGTH = self.body.GetValue()
        model.POPUP_AUTO_PLAY = not self.auto.GetValue()
        model.POPUP_WAIT_ON_HOVER = self.hover.GetValue()
        model.POPUP_STAY_ON_TOP = self.top.GetValue()
        model.PLAY_SOUND = self.sound.GetValue()
        model.POPUP_POSITION = self.position.GetClientData(self.position.GetSelection())
        model.POPUP_DISPLAY = self.display.GetClientData(self.display.GetSelection())
        model.POPUP_BORDER_SIZE = self.border_size.GetValue()
        color = self.border_color.GetBackgroundColour()
        model.POPUP_BORDER_COLOR = (color.Red(), color.Green(), color.Blue())
    def on_border_color(self, event):
        data = wx.ColourData()
        data.SetColour(self.border_color.GetBackgroundColour())
        dialog = wx.ColourDialog(self, data)
        if dialog.ShowModal() == wx.ID_OK:
            self.border_color.SetBackgroundColour(dialog.GetColourData().GetColour())
            self.on_change(event)
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
        self.update_controls()
        self.SetSizerAndFit(sizer)
    def create_panel(self, parent):
        panel = wx.Panel(parent, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        general = self.create_general(panel)
        caching = self.create_caching(panel)
        proxy = self.create_proxy(panel)
        sizer.Add(general, 0, wx.EXPAND)
        sizer.AddSpacer(8)
        sizer.Add(caching, 0, wx.EXPAND)
        sizer.AddSpacer(8)
        sizer.Add(proxy, 0, wx.EXPAND)
        panel.SetSizerAndFit(sizer)
        return panel
    def create_general(self, parent):
        box = wx.StaticBox(parent, -1, 'General')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.GridBagSizer(8, 8)
        
        idle = wx.CheckBox(parent, -1, "Don't check feeds if I've been idle for")
        grid.Add(idle, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        text = wx.StaticText(parent, -1, 'seconds')
        grid.Add(text, (0, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        
        timeout = wx.SpinCtrl(parent, -1, '1', min=1, max=9999, size=(64, -1))
        grid.Add(timeout, (0, 1))
        
        auto_update = wx.CheckBox(parent, -1, 'Check for software updates automatically')
        grid.Add(auto_update, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        check_now = wx.Button(parent, -1, 'Check Now')
        grid.Add(check_now, (1, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        timeout.Bind(wx.EVT_SPINCTRL, self.on_change)
        idle.Bind(wx.EVT_CHECKBOX, self.on_change)
        auto_update.Bind(wx.EVT_CHECKBOX, self.on_change)
        check_now.Bind(wx.EVT_BUTTON, self.on_check_now)
        
        self.idle = idle
        self.timeout = timeout
        self.auto_update = auto_update
        self.check_now = check_now
        return sizer
    def create_caching(self, parent):
        box = wx.StaticBox(parent, -1, 'Caching')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.GridBagSizer(8, 8)
        
        text = wx.StaticText(parent, -1, 'Pop-up History')
        grid.Add(text, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        #text = wx.StaticText(parent, -1, 'Item Cache')
        #grid.Add(text, (1, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        text = wx.StaticText(parent, -1, 'days')
        grid.Add(text, (0, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        #text = wx.StaticText(parent, -1, 'items per feed')
        #grid.Add(text, (1, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        
        item = wx.SpinCtrl(parent, -1, '1', min=1, max=365, size=(64, -1))
        grid.Add(item, (0, 1))
        #feed = wx.SpinCtrl(parent, -1, '1', min=1, max=9999, size=(64, -1))
        #grid.Add(feed, (1, 1))
        
        clear_item = wx.Button(parent, -1, 'Clear')
        grid.Add(clear_item, (0, 3))
        #clear_feed = wx.Button(parent, -1, 'Clear')
        #grid.Add(clear_feed, (1, 3))
        
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        item.Bind(wx.EVT_SPINCTRL, self.on_change)
        #feed.Bind(wx.EVT_SPINCTRL, self.on_change)
        clear_item.Bind(wx.EVT_BUTTON, self.on_clear_item)
        #clear_feed.Bind(wx.EVT_BUTTON, self.on_clear_feed)
        
        self.item = item
        #self.feed = feed
        self.clear_item = clear_item
        #self.clear_feed = clear_feed
        return sizer
    def create_proxy(self, parent):
        box = wx.StaticBox(parent, -1, 'Proxy')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.GridBagSizer(8, 8)
        
        use_proxy = wx.CheckBox(parent, -1, 'Use a proxy server')
        grid.Add(use_proxy, (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        proxy_url = wx.TextCtrl(parent, -1, style=wx.TE_PASSWORD)
        grid.Add(proxy_url, (1, 0), flag=wx.EXPAND)
        text = wx.StaticText(parent, -1, 'Format: http://<username>:<password>@<proxyserver>:<proxyport>\nLeave blank to use Windows proxy settings.')
        grid.Add(text, (2, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 8)
        
        use_proxy.Bind(wx.EVT_CHECKBOX, self.on_change)
        proxy_url.Bind(wx.EVT_TEXT, self.on_change)
        
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        return sizer
    def update_controls(self):
        model = self.model
        self.idle.SetValue(model.DISABLE_WHEN_IDLE)
        self.timeout.SetValue(model.USER_IDLE_TIMEOUT)
        self.auto_update.SetValue(model.CHECK_FOR_UPDATES)
        one_day = 60 * 60 * 24
        self.item.SetValue(model.ITEM_CACHE_AGE / one_day)
        self.use_proxy.SetValue(model.USE_PROXY)
        self.proxy_url.ChangeValue(model.PROXY_URL)
        self.enable_controls()
    def update_model(self):
        model = self.model
        model.DISABLE_WHEN_IDLE = self.idle.GetValue()
        model.USER_IDLE_TIMEOUT = self.timeout.GetValue()
        model.CHECK_FOR_UPDATES = self.auto_update.GetValue()
        one_day = 60 * 60 * 24
        model.ITEM_CACHE_AGE = self.item.GetValue() * one_day
        model.USE_PROXY = self.use_proxy.GetValue()
        model.PROXY_URL = self.proxy_url.GetValue()
    def enable_controls(self):
        self.timeout.Enable(self.idle.GetValue())
        self.proxy_url.Enable(self.use_proxy.GetValue())
    def on_change(self, event):
        self.enable_controls()
        self.dialog.on_change()
        event.Skip()
    def on_clear_item(self, event):
        self.model.controller.manager.clear_item_history()
        self.clear_item.Disable()
    def on_clear_feed(self, event):
        self.model.controller.manager.clear_feed_cache()
        self.clear_feed.Disable()
    def on_check_now(self, event):
        self.check_now.Disable()
        self.model.controller.check_for_updates()
        
class AboutPanel(wx.Panel):
    def __init__(self, parent):
        super(AboutPanel, self).__init__(parent, -1)
        panel = self.create_panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        line = wx.StaticLine(self, -1)
        sizer.Add(line, 0, wx.EXPAND)
        sizer.Add(panel, 1, wx.EXPAND|wx.ALL, 8)
        credits = '''
        %s %s :: Build %d :: Copyright (c) 2009-2010, Michael Fogleman
        
        16x16px icons in this application are from the Silk Icon set provided by Mark James under a Creative Commons Attribution 2.5 License. http://www.famfamfam.com/lab/icons/silk/
        
        Third-party components of this software include the following:
        
        * Python 2.6 - http://www.python.org/
        * wxPython 2.8.10 - http://www.wxpython.org/
        * Universal Feed Parser - http://www.feedparser.org/
        * PLY 3.3 - http://www.dabeaz.com/ply/
        * py2exe 0.6.9 - http://www.py2exe.org/
        * Inno Setup - http://www.jrsoftware.org/isinfo.php
        
        
        Universal Feed Parser, a component of this software, requires that the following text be included in the distribution of this application:
        
        Copyright (c) 2002-2005, Mark Pilgrim
        All rights reserved.
        
        Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
        
        * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
        
        * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
        
        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
        
        
        PLY 3.3 (Python Lex-Yacc), a component of this software, requires that the following text be included in the distribution of this application:

        Copyright (C) 2001-2009,
        David M. Beazley (Dabeaz LLC)
        All rights reserved.
        
        Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
        
        * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
        
        * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
        
        * Neither the name of the David Beazley or Dabeaz LLC may be used to endorse or promote products derived from this software without specific prior written permission.
        
        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
        ''' % (settings.APP_NAME, settings.APP_VERSION, settings.LOCAL_REVISION)
        credits = '\n'.join(line.strip() for line in credits.strip().split('\n'))
        text = wx.TextCtrl(self, -1, credits, style=wx.TE_MULTILINE|wx.TE_READONLY)
        text.SetBackgroundColour(self.GetBackgroundColour())
        sizer.Add(text, 0, wx.EXPAND|wx.ALL&~wx.TOP, 8)
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
        