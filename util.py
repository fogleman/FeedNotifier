import wx
import re
import time
from htmlentitydefs import name2codepoint

def menu_item(menu, label, func, icon=None, kind=wx.ITEM_NORMAL):
    item = wx.MenuItem(menu, -1, label, kind=kind)
    if func:
        menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    if icon:
        item.SetBitmap(wx.Bitmap(icon))
    menu.AppendItem(item)
    return item
    
def time_since(t):
    t = int(t)
    now = int(time.time())
    seconds = max(now - t, 0)
    if seconds == 1:
        return '1 second'
    if seconds < 60:
        return '%d seconds' % seconds
    minutes = seconds / 60
    if minutes == 1:
        return '1 minute'
    if minutes < 60:
        return '%d minutes' % minutes
    hours = minutes / 60
    if hours == 1:
        return '1 hour'
    if hours < 24:
        return '%d hours' % hours
    days = hours / 24
    if days == 1:
        return '1 day'
    return '%d days' % days
    
def replace_entities1(text):
    entity = re.compile(r'&#(\d+);')
    def func(match):
        try:
            return unichr(int(match.group(1)))
        except:
            return match.group(0)
    return entity.sub(func, text)
    
def replace_entities2(text):
    entity = re.compile(r'&([a-zA-Z]+);')
    def func(match):
        try:
            return unichr(name2codepoint[match.group(1)])
        except:
            return match.group(0)
    return entity.sub(func, text)
    
def remove_markup(text):
    html = re.compile(r'<[^>]+>')
    return html.sub('', text)
    
def format(text, max_length=400):
    previous = ''
    while text != previous:
        previous = text
        text = replace_entities1(text)
        text = replace_entities2(text)
    text = remove_markup(text)
    text = ' '.join(text.split())
    if len(text) > max_length:
        text = text[:max_length].strip()
        text = text.split()[:-1]
        text.append('[...]')
        text = ' '.join(text)
    return text
    