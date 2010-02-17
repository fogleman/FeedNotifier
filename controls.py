import wx
import wx.lib.wordwrap as wordwrap
import util

class Event(wx.PyEvent):
    def __init__(self, event_object, type):
        super(Event, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(event_object)
        
EVT_HYPERLINK = wx.PyEventBinder(wx.NewEventType())

class Line(wx.PyPanel):
    def __init__(self, parent, pen=wx.BLACK_PEN):
        super(Line, self).__init__(parent, -1, style=wx.BORDER_NONE)
        self.pen = pen
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
    def on_size(self, event):
        self.Refresh()
    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.Clear()
        dc.SetPen(self.pen)
        width, height = self.GetClientSize()
        y = height / 2
        dc.DrawLine(0, y, width, y)
    def DoGetBestSize(self):
        return -1, self.pen.GetWidth()
        
class Text(wx.PyPanel):
    def __init__(self, parent, width, text):
        super(Text, self).__init__(parent, -1, style=wx.BORDER_NONE)
        self.text = text
        self.width = width
        self.wrap = True
        self.rects = []
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
    def on_size(self, event):
        self.Refresh()
    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        self.setup_dc(dc)
        dc.Clear()
        self.draw_lines(dc)
    def setup_dc(self, dc):
        dc.SetFont(self.GetFont())
        dc.SetTextBackground(self.GetBackgroundColour())
        dc.SetTextForeground(self.GetForegroundColour())
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
    def draw_lines(self, dc, emulate=False):
        if self.wrap:
            text = wordwrap.wordwrap(self.text.strip(), self.width, dc)
        else:
            text = self.text.strip()
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line]
        x, y = 0, 0
        rects = []
        for line in lines:
            if not emulate:
                dc.DrawText(line, x, y)
            w, h = dc.GetTextExtent(line)
            rects.append(wx.Rect(x, y, w, h))
            y += h
        if not emulate:
            self.rects = rects
        return y
    def compute_height(self):
        dc = wx.ClientDC(self)
        self.setup_dc(dc)
        height = self.draw_lines(dc, True)
        return height
    def fit_no_wrap(self):
        dc = wx.ClientDC(self)
        self.setup_dc(dc)
        width, height = dc.GetTextExtent(self.text.strip())
        self.width = width
        self.wrap = False
    def DoGetBestSize(self):
        height = self.compute_height()
        return self.width, height
        
class Link(Text):
    def __init__(self, parent, width, link, text):
        super(Link, self).__init__(parent, width, text)
        self.link = link
        self.trigger = False
        self.hover = False
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
    def hit_test(self, point):
        for rect in self.rects:
            if rect.Contains(point):
                self.on_hover()
                break
        else:
            self.on_unhover()
    def on_motion(self, event):
        self.hit_test(event.GetPosition())
    def on_leave(self, event):
        self.on_unhover()
    def on_hover(self):
        if self.hover:
            return
        self.hover = True
        font = self.GetFont()
        font.SetUnderlined(True)
        self.SetFont(font)
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.Refresh()
    def on_unhover(self):
        if not self.hover:
            return
        self.hover = False
        self.trigger = False
        font = self.GetFont()
        font.SetUnderlined(False)
        self.SetFont(font)
        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
        self.Refresh()
    def on_left_down(self, event):
        if self.hover:
            self.trigger = True
    def on_left_up(self, event):
        if self.hover and self.trigger:
            event = Event(self, EVT_HYPERLINK)
            event.link = self.link
            wx.PostEvent(self, event)
        self.trigger = False
        
class BitmapLink(wx.PyPanel):
    def __init__(self, parent, link, bitmap, hover_bitmap=None):
        super(BitmapLink, self).__init__(parent, -1)
        self.link = link
        self.bitmap = bitmap
        self.hover_bitmap = hover_bitmap or bitmap
        self.hover = False
        self.trigger = False
        self.SetInitialSize(bitmap.GetSize())
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()
        bitmap = self.hover_bitmap if self.hover else self.bitmap
        dc.DrawBitmap(bitmap, 0, 0, True)
    def on_enter(self, event):
        self.hover = True
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.Refresh()
    def on_leave(self, event):
        self.trigger = False
        self.hover = False
        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
        self.Refresh()
    def on_left_down(self, event):
        self.trigger = True
    def on_left_up(self, event):
        if self.trigger:
            event = Event(self, EVT_HYPERLINK)
            event.link = self.link
            wx.PostEvent(self, event)
        self.trigger = False
        