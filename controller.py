import wx
import idle
import feeds
import popups
import view
import threading

URLS = [
    #'http://www.michaelfogleman.com/feed/',
    #'http://stackoverflow.com/feeds/tag/python',
    #'http://all-devel-01/portal/feeds/experiments/',
    #'http://all-devel-01/trac/eqteam/timeline?ticket=on&changeset=on&milestone=on&wiki=on&max=50&daysback=90&format=rss',
    #'http://planet.python.org/rss20.xml',
    #'http://feeds.digg.com/digg/popular.rss',
    #'http://www.faithandfearinflushing.com/feed/',
    #'http://stackoverflow.com/feeds/tag/java',
    #'http://blog.computationalcomplexity.org/feeds/posts/default',
    #'http://code.activestate.com/feeds/recipes/',
    #'http://forums.topcoder.com/?module=RSS&categoryID=13',
]

class Controller(object):
    def __init__(self):
        self.frame = view.HiddenFrame(self)
        self.manager = feeds.FeedManager()
        self.popup = None
        self.polling = False
        self.enabled = True
        for url in URLS:
            self.manager.add_url(url)
        self.poll()
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
        self._poll()
    def disable(self):
        self.frame.icon.set_icon('icons/feed_delete.png')
        self.enabled = False
    def poll(self):
        try:
            self._poll()
        finally:
            wx.CallLater(5000, self.poll)
    def _poll(self):
        if self.polling:
            return
        if not self.enabled:
            return
        if idle.get_idle_duration() > 60:
            return
        if not self.manager.should_poll():
            return
        self.polling = True
        self.frame.icon.set_icon('icons/feed_go.png')
        thread = threading.Thread(target=self._poll_thread)
        thread.setDaemon(True)
        thread.start()
    def _poll_thread(self):
        try:
            new_items = self.manager.poll()
            wx.CallAfter(self._poll_complete, new_items)
        finally:
            self.polling = False
    def _poll_complete(self, new_items):
        self.frame.icon.set_icon('icons/feed.png')
        if not new_items:
            return
        items = self.manager.items
        if self.popup:
            index = self.popup.index
        else:
            index = len(items)
        items.extend(new_items)
        self.show_items(items, index)
    def force_poll(self):
        for feed in self.manager.feeds:
            feed.last_poll = 0
        self._poll()
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
    def about(self):
        window = view.AboutDialog(self.frame)
        window.CenterOnScreen()
        window.Show()
    def add_feed(self, url=''):
        feed = view.AddFeedDialog.show_wizard(self.frame, url)
        if not feed:
            return
        self.manager.feeds.append(feed)
        self._poll()
    def edit_settings(self):
        window = view.SettingsDialog(self.frame, self)
        window.CenterOnScreen()
        window.ShowModal()
        window.Destroy()
    def close(self):
        if self.popup:
            self.popup.on_close()
        self.frame.Close()
    def on_popup_close(self, event):
        self.popup = None
        self.manager.purge_items()
        