import wx
import webbrowser
from settings import settings

BLANK = 'about:blank'
COMMAND_CLOSE = 'http://close/'
COMMAND_NEXT = 'http://next/'
COMMAND_PREVIOUS = 'http://previous/'
COMMAND_FIRST = 'http://first/'
COMMAND_LAST = 'http://last/'
COMMAND_PLAY = 'http://play/'
COMMAND_PAUSE = 'http://pause/'

def position_window(window):
    index = settings.POPUP_DISPLAY
    if index >= wx.Display_GetCount():
        index = 0
    display = wx.Display(index)
    x, y, w, h = display.GetClientArea()
    cw, ch = window.GetSize()
    pad = 10
    x1 = x + pad
    y1 = y + pad
    x2 = x + w - cw - pad
    y2 = y + h - ch - pad
    x3 = x + w / 2 - cw / 2
    y3 = y + h / 2 - ch / 2
    lookup = {
        (-1, -1): (x1, y1),
        (1, -1): (x2, y1),
        (-1, 1): (x1, y2),
        (1, 1): (x2, y2),
        (0, 0): (x3, y3),
    }
    window.SetPosition(lookup[settings.POPUP_POSITION])
    
class Event(wx.PyEvent):
    def __init__(self, event_object, type):
        super(Event, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(event_object)
        
EVT_LINK = wx.PyEventBinder(wx.NewEventType())
EVT_POPUP_CLOSE = wx.PyEventBinder(wx.NewEventType())
EVT_POPUP_ENTER = wx.PyEventBinder(wx.NewEventType())
EVT_POPUP_LEAVE = wx.PyEventBinder(wx.NewEventType())

class PopupManager(wx.EvtHandler):
    def __init__(self):
        super(PopupManager, self).__init__()
        self.timer = None
        self.auto = settings.POPUP_AUTO_PLAY
        self.cache = {}
        self.hover_count = 0
    def set_items(self, items, index=0, focus=False):
        self.items = list(items)
        self.index = index
        self.count = len(self.items)
        self.clear_cache(keep_current_item=True)
        self.update(focus)
        self.set_timer()
    def update(self, focus=False):
        item = self.items[self.index]
        if item in self.cache:
            self.show_frame(focus)
            self.update_cache()
        else:
            self.update_cache(True)
            self.show_frame(focus)
            self.update_cache()
    def update_cache(self, current_only=False):
        indexes = set()
        indexes.add(self.index)
        if not current_only:
            indexes.add(self.index - 1)
            indexes.add(self.index + 1)
            #indexes.add(0)
            #indexes.add(self.count - 1)
        items = set(self.items[index] for index in indexes if index >= 0 and index < self.count)
        for item in items:
            if item in self.cache:
                continue
            frame = self.create_frame(item)
            self.cache[item] = frame
        for item, frame in self.cache.items():
            if item not in items:
                frame.Close()
                del self.cache[item]
    def clear_cache(self, keep_current_item=False):
        current_item = self.items[self.index]
        for item, frame in self.cache.items():
            if keep_current_item and item == current_item:
                continue
            frame.Close()
            del self.cache[item]
    def show_frame(self, focus=False):
        current_item = self.items[self.index]
        current_item.read = True
        for item, frame in self.cache.items():
            if item == current_item:
                if focus:
                    frame.Show()
                else:
                    frame.Disable()
                    frame.Show()
                    frame.Enable()
                frame.Update()
                if settings.POPUP_TRANSPARENCY < 255:
                    frame.SetTransparent(settings.POPUP_TRANSPARENCY)
        for item, frame in self.cache.items():
            if item != current_item:
                frame.Hide()
    def create_frame(self, item):
        if True:#settings.POPUP_THEME == 'default':
            import theme_default
            context = self.create_context(item)
            frame = theme_default.Frame(item, context)
            frame.Bind(EVT_LINK, self.on_link)
            frame.Bind(EVT_POPUP_ENTER, self.on_enter)
            frame.Bind(EVT_POPUP_LEAVE, self.on_leave)
        position_window(frame)
        if settings.POPUP_TRANSPARENCY < 255:
            frame.SetTransparent(0)
        return frame
    def create_context(self, item):
        context = {}
        count = str(self.count)
        index = str(self.items.index(item) + 1)
        index = '%s%s' % ('0' * (len(count) - len(index)), index)
        context['item_index'] = index
        context['item_count'] = count
        context['is_playing'] = self.auto
        context['is_paused'] = not self.auto
        context['POPUP_WIDTH'] = settings.POPUP_WIDTH
        context['COMMAND_CLOSE'] = COMMAND_CLOSE
        context['COMMAND_NEXT'] = COMMAND_NEXT
        context['COMMAND_PREVIOUS'] = COMMAND_PREVIOUS
        context['COMMAND_FIRST'] = COMMAND_FIRST
        context['COMMAND_LAST'] = COMMAND_LAST
        context['COMMAND_PLAY'] = COMMAND_PLAY
        context['COMMAND_PAUSE'] = COMMAND_PAUSE
        return context
    def set_timer(self):
        if self.timer and self.timer.IsRunning():
            return
        duration = settings.POPUP_DURATION * 1000
        self.timer = wx.CallLater(duration, self.on_timer)
    def stop_timer(self):
        if self.timer and self.timer.IsRunning():
            self.timer.Stop()
            self.timer = None
    def on_enter(self, event):
        event.Skip()
        self.hover_count += 1
    def on_leave(self, event):
        event.Skip()
        self.hover_count -= 1
    def on_link(self, event):
        link = event.link
        # track the click
        item = self.items[self.index]
        feed = item.feed
        if link == item.link or link == feed.link:
            feed.clicks += 1
        # handle the click
        if link == BLANK:
            event.Skip()
        elif link == COMMAND_CLOSE:
            self.on_close()
        elif link == COMMAND_FIRST:
            self.auto = False
            self.on_first()
        elif link == COMMAND_LAST:
            self.auto = False
            self.on_last()
        elif link == COMMAND_NEXT:
            self.auto = False
            self.on_next()
        elif link == COMMAND_PREVIOUS:
            self.auto = False
            self.on_previous()
        elif link == COMMAND_PLAY:
            if not self.auto:
                self.auto = True
                self.stop_timer()
                self.on_timer()
        elif link == COMMAND_PAUSE:
            self.auto = False
        else:
            webbrowser.open(link)
    def on_first(self):
        self.index = 0
        self.update(True)
    def on_last(self):
        self.index = self.count - 1
        self.update(True)
    def on_next(self, focus=True):
        if self.index < self.count - 1:
            self.index += 1
            self.update(focus)
        else:
            self.on_close()
    def on_previous(self):
        if self.index > 0:
            self.index -= 1
            self.update(True)
    def on_close(self):
        self.stop_timer()
        self.clear_cache()
        event = Event(self, EVT_POPUP_CLOSE)
        wx.PostEvent(self, event)
    def on_timer(self):
        self.timer = None
        set_timer = False
        if self.hover_count:
            set_timer = True
        elif self.auto:
            if self.index == self.count - 1:
                self.on_close()
            else:
                self.on_next(False)
                set_timer = True
        if set_timer:
            self.set_timer()
            