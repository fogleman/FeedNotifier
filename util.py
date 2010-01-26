import wx
import os
import re
import time
import calendar
from htmlentitydefs import name2codepoint
from settings import settings

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
        timestamp = calendar.timegm(entry.get('date_parsed', time.gmtime()))
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
    if desired < choices[0]:
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
    