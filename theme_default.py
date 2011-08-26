import wx
import controls
import popups
import util
from settings import settings

BACKGROUND = (230, 230, 230)

class Frame(wx.Frame):
    def __init__(self, item, context):
        title = settings.APP_NAME
        style = wx.FRAME_NO_TASKBAR | wx.BORDER_NONE
        if settings.POPUP_STAY_ON_TOP:
            style |= wx.STAY_ON_TOP
        super(Frame, self).__init__(None, -1, title, style=style)
        self.item = item
        self.context = context
        self.hover_count = 0
        container = self.create_container(self)
        container.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)
        container.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.container = container
        self.Fit()
    def post_link(self, link):
        event = popups.Event(self, popups.EVT_LINK)
        event.link = link
        wx.PostEvent(self, event)
    def on_link(self, event):
        self.post_link(event.link)
    def on_left_down(self, event):
        self.post_link(popups.COMMAND_NEXT)
    def on_mousewheel(self, event):
        if event.GetWheelRotation() < 0:
            self.post_link(popups.COMMAND_NEXT)
        else:
            self.post_link(popups.COMMAND_PREVIOUS)
    def on_focus(self, event):
        if event.GetEventObject() != self.container:
            self.container.SetFocusIgnoringChildren()
    def on_key_down(self, event):
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE:
            self.post_link(popups.COMMAND_CLOSE)
        elif code == wx.WXK_LEFT:
            self.post_link(popups.COMMAND_PREVIOUS)
        elif code == wx.WXK_RIGHT:
            self.post_link(popups.COMMAND_NEXT)
        elif code == wx.WXK_HOME:
            self.post_link(popups.COMMAND_FIRST)
        elif code == wx.WXK_END:
            self.post_link(popups.COMMAND_LAST)
    def on_enter(self, event):
        event.Skip()
        self.hover_count += 1
        if self.hover_count == 1:
            wx.PostEvent(self, popups.Event(self, popups.EVT_POPUP_ENTER))
    def on_leave(self, event):
        event.Skip()
        self.hover_count -= 1
        if self.hover_count == 0:
            wx.PostEvent(self, popups.Event(self, popups.EVT_POPUP_LEAVE))
    def bind_links(self, widgets):
        for widget in widgets:
            widget.Bind(controls.EVT_HYPERLINK, self.on_link)
            widget.Bind(wx.EVT_SET_FOCUS, self.on_focus)
            widget.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
            widget.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
    def bind_widgets(self, widgets):
        for widget in widgets:
            widget.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
            widget.Bind(wx.EVT_SET_FOCUS, self.on_focus)
            widget.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
            widget.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
    def create_container(self, parent):
        color = self.item.feed.color or settings.POPUP_BORDER_COLOR

        panel1 = wx.Panel(parent, -1, style=wx.WANTS_CHARS)
        panel1.SetBackgroundColour(wx.Color(*color))
        panel1.SetForegroundColour(wx.Color(*color))
        panel2 = wx.Panel(panel1, -1)
        panel2.SetBackgroundColour(wx.BLACK)
        panel2.SetForegroundColour(wx.BLACK)
        panel3 = wx.Panel(panel2, -1)
        panel3.SetBackgroundColour(wx.WHITE)
        panel3.SetForegroundColour(wx.BLACK)
        contents = self.create_contents(panel3)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel2, 1, wx.EXPAND|wx.ALL, max(0, settings.POPUP_BORDER_SIZE - 1))
        panel1.SetSizer(sizer)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel3, 1, wx.EXPAND|wx.ALL, 1)
        panel2.SetSizer(sizer)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(contents, 1, wx.EXPAND|wx.ALL)
        panel3.SetSizer(sizer)

        panel1.Fit()
        self.bind_widgets([panel1, panel2, panel3])
        return panel1
    def create_contents(self, parent):
        header = self.create_header(parent)
        body = self.create_body(parent)
        footer = self.create_footer(parent)
        pen = wx.Pen(wx.BLACK, style=wx.USER_DASH)
        pen.SetDashes([0, 2])
        line1 = controls.Line(parent, pen)
        line2 = controls.Line(parent, pen)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(header, 0, wx.EXPAND)
        sizer.Add(line1, 0, wx.EXPAND)
        sizer.Add(body, 1, wx.EXPAND)
        sizer.Add(line2, 0, wx.EXPAND)
        sizer.Add(footer, 0, wx.EXPAND)
        self.bind_widgets([line1, line2])
        return sizer
    def create_header(self, parent):
        panel = wx.Panel(parent, -1)
        panel.SetBackgroundColour(wx.Colour(*BACKGROUND))
        panel.SetForegroundColour(wx.BLACK)
        feed = self.item.feed
        paths = ['icons/feed.png']
        if feed.has_favicon:
            paths.insert(0, feed.favicon_path)
        for path in paths:
            try:
                bitmap = util.scale_bitmap(wx.Bitmap(path), 16, 16, wx.Colour(*BACKGROUND))
                break
            except Exception:
                pass
        else:
            bitmap = wx.EmptyBitmap(16, 16)
        icon = controls.BitmapLink(panel, feed.link, bitmap)
        icon.SetBackgroundColour(wx.Colour(*BACKGROUND))
        width, height = icon.GetSize()
        feed = self.create_feed(panel, width)
        button = controls.BitmapLink(panel, popups.COMMAND_CLOSE, wx.Bitmap('icons/cross.png'), wx.Bitmap('icons/cross_hover.png'))
        button.SetBackgroundColour(wx.Colour(*BACKGROUND))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(icon, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        sizer.Add(feed, 1, wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 5)
        sizer.Add(button, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        panel.SetSizer(sizer)
        self.bind_links([icon, button])
        self.bind_widgets([panel])
        return panel
    def create_feed(self, parent, icon_width):
        width = settings.POPUP_WIDTH - 64 - icon_width
        if self.item.feed.link:
            link = controls.Link(parent, width, self.item.feed.link, self.item.feed.title)
        else:
            link = controls.Text(parent, width, self.item.feed.title)
        link.SetBackgroundColour(wx.Colour(*BACKGROUND))
        font = link.GetFont()
        font.SetWeight(wx.BOLD)
        link.SetFont(font)
        if self.item.author:
            info = '%s ago by %s' % (self.item.time_since, self.item.author)
        else:
            info = '%s ago' % self.item.time_since
        info = controls.Text(parent, width, info)
        info.SetBackgroundColour(wx.Colour(*BACKGROUND))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(link, 0, wx.EXPAND)
        sizer.Add(info, 0, wx.EXPAND)
        self.bind_links([link])
        self.bind_widgets([info])
        return sizer
    def create_body(self, parent):
        width = settings.POPUP_WIDTH - 28
        if self.item.link:
            link = controls.Link(parent, width, self.item.link, self.item.title)
        else:
            link = controls.Text(parent, width, self.item.title)
        link.SetBackgroundColour(wx.WHITE)
        font = link.GetFont()
        font.SetWeight(wx.BOLD)
        font.SetPointSize(12)
        link.SetFont(font)
        text = controls.Text(parent, width, self.item.description)
        text.SetBackgroundColour(wx.WHITE)
        font = text.GetFont()
        font.SetPointSize(10)
        text.SetFont(font)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(5)
        sizer.Add(link, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 10)
        sizer.AddSpacer(5)
        sizer.Add(text, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 10)
        sizer.AddSpacer(10)
        self.bind_links([link])
        self.bind_widgets([text])
        return sizer
    def create_footer(self, parent):
        panel = wx.Panel(parent, -1)
        panel.SetBackgroundColour(wx.Colour(*BACKGROUND))
        panel.SetForegroundColour(wx.BLACK)
        first = controls.BitmapLink(panel, popups.COMMAND_FIRST, wx.Bitmap('icons/control_start.png'), wx.Bitmap('icons/control_start_blue.png'))
        previous = controls.BitmapLink(panel, popups.COMMAND_PREVIOUS, wx.Bitmap('icons/control_rewind.png'), wx.Bitmap('icons/control_rewind_blue.png'))
        text = '%s of %s' % (self.context['item_index'], self.context['item_count'])
        text = controls.Text(panel, 0, text)
        text.SetBackgroundColour(wx.Colour(*BACKGROUND))
        text.fit_no_wrap()
        next = controls.BitmapLink(panel, popups.COMMAND_NEXT, wx.Bitmap('icons/control_fastforward.png'), wx.Bitmap('icons/control_fastforward_blue.png'))
        last = controls.BitmapLink(panel, popups.COMMAND_LAST, wx.Bitmap('icons/control_end.png'), wx.Bitmap('icons/control_end_blue.png'))
        play = controls.BitmapLink(panel, popups.COMMAND_PLAY, wx.Bitmap('icons/control_play.png'), wx.Bitmap('icons/control_play_blue.png'))
        pause = controls.BitmapLink(panel, popups.COMMAND_PAUSE, wx.Bitmap('icons/control_pause.png'), wx.Bitmap('icons/control_pause_blue.png'))
        widgets = [first, previous, next, last, play, pause]
        self.bind_links(widgets)
        for widget in widgets:
            widget.SetBackgroundColour(wx.Colour(*BACKGROUND))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddSpacer(10)
        sizer.Add(first, 0, wx.TOP|wx.BOTTOM, 5)
        sizer.AddSpacer(8)
        sizer.Add(previous, 0, wx.TOP|wx.BOTTOM, 5)
        sizer.AddSpacer(8)
        sizer.Add(text, 0, wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 5)
        sizer.AddSpacer(8)
        sizer.Add(next, 0, wx.TOP|wx.BOTTOM, 5)
        sizer.AddSpacer(8)
        sizer.Add(last, 0, wx.TOP|wx.BOTTOM, 5)
        sizer.AddStretchSpacer(1)
        sizer.Add(play, 0, wx.TOP|wx.BOTTOM, 5)
        sizer.AddSpacer(8)
        sizer.Add(pause, 0, wx.TOP|wx.BOTTOM, 5)
        sizer.AddSpacer(10)
        panel.SetSizer(sizer)
        self.bind_widgets([panel, text])
        return panel
        
if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = Frame()
    frame.Show()
    app.MainLoop()
    