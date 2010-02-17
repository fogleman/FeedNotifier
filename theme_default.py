import wx
import controls
import popups
import util
from settings import settings

BACKGROUND = (230, 230, 230)

class Frame(wx.Frame):
    def __init__(self, item, context):
        title = settings.APP_NAME
        style = wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR | wx.BORDER_NONE
        super(Frame, self).__init__(None, -1, title, style=style)
        self.item = item
        self.context = context
        container = self.create_container(self)
        self.Fit()
    def on_link(self, event):
        e = popups.Event(self, popups.EVT_LINK)
        e.link = event.link
        wx.PostEvent(self, e)
    def bind_links(self, widgets):
        for widget in widgets:
            widget.Bind(controls.EVT_HYPERLINK, self.on_link)
    def create_container(self, parent):
        panel1 = wx.Panel(parent, -1)
        panel1.SetBackgroundColour(wx.BLACK)
        panel2 = wx.Panel(panel1, -1)
        panel2.SetBackgroundColour(wx.WHITE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel2, 1, wx.EXPAND|wx.ALL, 3)
        panel1.SetSizer(sizer)
        contents = self.create_contents(panel2)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(contents, 1, wx.EXPAND|wx.ALL, 1)
        panel2.SetSizer(sizer)
        panel1.Fit()
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
        return sizer
    def create_header(self, parent):
        panel = wx.Panel(parent, -1)
        panel.SetBackgroundColour(wx.Colour(*BACKGROUND))
        feed = self.item.feed
        if feed.has_favicon:
            path = feed.favicon_path
        else:
            path = 'icons/feed.png'
        bitmap = wx.Bitmap(path)
        bitmap = util.scale_bitmap(bitmap, 16, 16, wx.Colour(*BACKGROUND))
        icon = controls.BitmapLink(panel, feed.link, bitmap)
        icon.SetBackgroundColour(wx.Colour(*BACKGROUND))
        width, height = icon.GetSize()
        feed = self.create_feed(panel, width)
        button = controls.BitmapLink(panel, popups.COMMAND_CLOSE, wx.Bitmap('themes/default/cross.png'), wx.Bitmap('themes/default/cross_hover.png'))
        button.SetBackgroundColour(wx.Colour(*BACKGROUND))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(icon, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        sizer.Add(feed, 1, wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 5)
        sizer.Add(button, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        panel.SetSizer(sizer)
        self.bind_links([icon, button])
        return panel
    def create_feed(self, parent, icon_width):
        width = settings.POPUP_WIDTH - 64 - icon_width
        link = controls.Link(parent, width, self.item.feed.link, self.item.feed.title)
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
        return sizer
    def create_body(self, parent):
        width = settings.POPUP_WIDTH - 28
        link = controls.Link(parent, width, self.item.link, self.item.title)
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
        return sizer
    def create_footer(self, parent):
        panel = wx.Panel(parent, -1)
        panel.SetBackgroundColour(wx.Colour(*BACKGROUND))
        first = controls.BitmapLink(panel, popups.COMMAND_FIRST, wx.Bitmap('themes/default/control_start.png'), wx.Bitmap('themes/default/control_start_blue.png'))
        previous = controls.BitmapLink(panel, popups.COMMAND_PREVIOUS, wx.Bitmap('themes/default/control_rewind.png'), wx.Bitmap('themes/default/control_rewind_blue.png'))
        text = '%s of %s' % (self.context['item_index'], self.context['item_count'])
        text = controls.Text(panel, 0, text)
        text.SetBackgroundColour(wx.Colour(*BACKGROUND))
        text.fit_no_wrap()
        next = controls.BitmapLink(panel, popups.COMMAND_NEXT, wx.Bitmap('themes/default/control_fastforward.png'), wx.Bitmap('themes/default/control_fastforward_blue.png'))
        last = controls.BitmapLink(panel, popups.COMMAND_LAST, wx.Bitmap('themes/default/control_end.png'), wx.Bitmap('themes/default/control_end_blue.png'))
        play = controls.BitmapLink(panel, popups.COMMAND_PLAY, wx.Bitmap('themes/default/control_play.png'), wx.Bitmap('themes/default/control_play_blue.png'))
        pause = controls.BitmapLink(panel, popups.COMMAND_PAUSE, wx.Bitmap('themes/default/control_pause.png'), wx.Bitmap('themes/default/control_pause_blue.png'))
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
        return panel
        
if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = Frame()
    frame.Show()
    app.MainLoop()
    