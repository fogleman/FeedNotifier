import wx
import idle
import feeds
import popups
import view
import socket
import updater
import util
from settings import settings

INVALID_ADDRESSES = [
    '127.0.0',
    '169.254',
    '0.0.0.0',
]

class Controller(object):
    def __init__(self):
        self.frame = view.HiddenFrame(self)
        self.manager = feeds.FeedManager()
        self.manager.load()
        self.add_default_feeds()
        self.popup = None
        self.polling = False
        self.enabled = True
        self.on_poll()
        self.check_for_updates(False)
    def add_default_feeds(self):
        if self.manager.feeds:
            return
        for url in settings.DEFAULT_FEED_URLS:
            feed = feeds.Feed(url)
            feed.interval = 60 * 60 * 24
            self.manager.add_feed(feed)
    def parse_args(self, message):
        urls = message.split('\n')
        for url in urls:
            url = url.strip()
            if not url:
                continue
            self.add_feed(url)
    def enable(self):
        self.frame.icon.set_icon('icons/feed.png')
        self.enabled = True
        self.poll()
    def disable(self):
        self.frame.icon.set_icon('icons/feed_disabled.png')
        self.enabled = False
    def save(self):
        self.manager.save()
    def on_poll(self):
        try:
            self.poll()
        finally:
            wx.CallLater(5000, self.on_poll)
    def poll(self):
        if self.polling:
            return
        if not self.enabled:
            return
        if settings.DISABLE_WHEN_IDLE and idle.get_idle_duration() > settings.USER_IDLE_TIMEOUT:
            return
        if not self.manager.should_poll():
            return
        # make sure we're online
        address = socket.gethostbyname(socket.gethostname())
        for invalid in INVALID_ADDRESSES:
            if address.startswith(invalid):
                return
        self.polling = True
        self.frame.icon.set_icon('icons/feed_go.png')
        util.start_thread(self._poll_thread)
    def _poll_thread(self):
        found_new = False
        try:
            for new_items in self.manager.poll():
                found_new = True
                wx.CallAfter(self._poll_result, new_items)
        finally:
            wx.CallAfter(self._poll_complete, found_new)
    def _poll_result(self, new_items):
        items = self.manager.items
        if self.popup:
            index = self.popup.index
        else:
            index = len(items)
        items.extend(new_items)
        self.show_items(items, index)
    def _poll_complete(self, found_new):
        if found_new:
            self.save()
        self.polling = False
        self.frame.icon.set_icon('icons/feed.png')
    def force_poll(self):
        for feed in self.manager.feeds:
            feed.last_poll = 0
        self.poll()
    def show_items(self, items, index, auto=None):
        if not items:
            return
        if not self.popup:
            self.popup = popups.PopupManager()
            self.popup.Bind(popups.EVT_POPUP_CLOSE, self.on_popup_close)
        self.popup.set_items(items, index)
        if auto is not None:
            self.popup.auto = auto
    def show_popup(self):
        items = self.manager.items
        index = len(items) - 1
        self.show_items(items, index, False)
    def add_feed(self, url=''):
        feed = view.AddFeedDialog.show_wizard(self.frame, url)
        if not feed:
            return
        self.manager.add_feed(feed)
        self.save()
        self.poll()
    def edit_settings(self):
        window = view.SettingsDialog(self.frame, self)
        window.Center()
        window.ShowModal()
        window.Destroy()
    def check_for_updates(self, force=True):
        updater.run(self, force)
    def close(self):
        try:
            if self.popup:
                self.popup.on_close()
            self.frame.Close()
        finally:
            wx.GetApp().ExitMainLoop()
    def on_popup_close(self, event):
        self.popup = None
        self.manager.purge_items(settings.ITEM_CACHE_AGE)
        