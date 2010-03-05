import wx
import os
import re
import time
import base64
import calendar
import urllib2
import urlparse
import threading
import feedparser
from htmlentitydefs import name2codepoint
from settings import settings

def start_thread(func, *args):
    thread = threading.Thread(target=func, args=args)
    thread.setDaemon(True)
    thread.start()
    return thread
    
def scale_bitmap(bitmap, width, height, color):
    bw, bh = bitmap.GetWidth(), bitmap.GetHeight()
    if bw == width and bh == height:
        return bitmap
    if width < 0:
        width = bw
    if height < 0:
        height = bh
    buffer = wx.EmptyBitmap(bw, bh)
    dc = wx.MemoryDC(buffer)
    dc.SetBackground(wx.Brush(color))
    dc.Clear()
    dc.DrawBitmap(bitmap, 0, 0, True)
    image = wx.ImageFromBitmap(buffer)
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    result = wx.BitmapFromImage(image)
    return result
    
def menu_item(menu, label, func, icon=None, kind=wx.ITEM_NORMAL):
    item = wx.MenuItem(menu, -1, label, kind=kind)
    if func:
        menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    if icon:
        item.SetBitmap(wx.Bitmap(icon))
    menu.AppendItem(item)
    return item
    
def select_choice(choice, data):
    for index in range(choice.GetCount()):
        if choice.GetClientData(index) == data:
            choice.Select(index)
            return
    choice.Select(wx.NOT_FOUND)
    
def get_top_window(window):
    result = None
    while window:
        result = window
        window = window.GetParent()
    return result
    
def get(obj, key, default):
    value = obj.get(key, None)
    return value or default
    
def abspath(path):
    path = os.path.abspath(path)
    path = 'file:///%s' % path.replace('\\', '/')
    return path
    
def parse(url, username=None, password=None, etag=None, modified=None):
    agent = settings.USER_AGENT
    handlers = get_proxy()
    if username and password:
        url = insert_credentials(url, username, password)
    return feedparser.parse(url, etag=etag, modified=modified, agent=agent, handlers=handlers)
    
def is_valid_feed(data):
    entries = get(data, 'entries', [])
    title = get(data.feed, 'title', '')
    link = get(data.feed, 'link', '')
    return entries or (title and link)
    
def insert_credentials(url, username, password):
    parts = urlparse.urlsplit(url)
    netloc = parts.netloc
    if '@' in netloc:
        netloc = netloc[netloc.index('@')+1:]
    netloc = '%s:%s@%s' % (username, password, netloc)
    parts = list(parts)
    parts[1] = netloc
    return urlparse.urlunsplit(tuple(parts))
    
def encode_password(password):
    return base64.b64encode(password) if password else None
    
def decode_password(password):
    return base64.b64decode(password) if password else None
    
def get_proxy():
    if settings.USE_PROXY:
        map = {
            'http': settings.PROXY_URL,
        }
        proxy = urllib2.ProxyHandler(map)
        return [proxy]
    else:
        return []
        
def find_themes():
    result = []
    names = os.listdir('themes')
    for name in names:
        if name.startswith('.'):
            continue
        path = os.path.join('themes', name)
        if os.path.isdir(path):
            result.append(name)
    return result
    
def guess_polling_interval(entries):
    if len(entries) < 2:
        return settings.DEFAULT_POLLING_INTERVAL
    timestamps = []
    for entry in entries:
        timestamp = calendar.timegm(get(entry, 'date_parsed', time.gmtime()))
        timestamps.append(timestamp)
    timestamps.sort()
    durations = [b - a for a, b in zip(timestamps, timestamps[1:])]
    mean = sum(durations) / len(durations)
    choices = [
        60,
        60*5,
        60*10,
        60*15,
        60*30,
        60*60,
        60*60*2,
        60*60*4,
        60*60*8,
        60*60*12,
        60*60*24,
    ]
    desired = mean / 2
    if desired == 0:
        interval = settings.DEFAULT_POLLING_INTERVAL
    elif desired < choices[0]:
        interval = choices[0]
    else:
        interval = max(choice for choice in choices if choice <= desired)
    return interval
    
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
    
def split_time(seconds):
    if seconds < 60:
        return seconds, 0
    minutes = seconds / 60
    if minutes < 60:
        return minutes, 1
    hours = minutes / 60
    days = hours / 24
    if days and hours % 24 == 0:
        return days, 3
    return hours, 2
    
def split_time_str(seconds):
    interval, units = split_time(seconds)
    strings = ['second', 'minute', 'hour', 'day']
    string = strings[units]
    if interval != 1:
        string += 's'
    return '%d %s' % (interval, string)
    
def pretty_name(name):
    name = ' '.join(s.title() for s in name.split('_'))
    last = '0'
    result = ''
    for c in name:
        if c.isdigit() and not last.isdigit():
            result += ' '
        result += c
        last = c
    return result
    
def replace_entities1(text):
    entity = re.compile(r'&#(\d+);')
    def func(match):
        try:
            return unichr(int(match.group(1)))
        except Exception:
            return match.group(0)
    return entity.sub(func, text)
    
def replace_entities2(text):
    entity = re.compile(r'&([a-zA-Z]+);')
    def func(match):
        try:
            return unichr(name2codepoint[match.group(1)])
        except Exception:
            return match.group(0)
    return entity.sub(func, text)
    
def remove_markup(text):
    html = re.compile(r'<[^>]+>')
    return html.sub(' ', text)
    
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
    