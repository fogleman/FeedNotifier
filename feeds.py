import os
import time
import calendar
import uuid
import urlparse
import urllib2
import random
import util
import Queue
import logging
import cPickle as pickle
from settings import settings

def cmp_timestamp(a, b):
    return cmp(a.timestamp, b.timestamp)
    
def create_id(entry):
    keys = ['id', 'link', 'title']
    values = tuple(util.get(entry, key, None) for key in keys)
    return values if any(values) else uuid.uuid4().hex
    
class Item(object):
    def __init__(self, feed, id):
        self.feed = feed
        self.id = id
        self.timestamp = int(time.time())
        self.received = int(time.time())
        self.title = ''
        self.description = ''
        self.link = ''
        self.author = ''
        self.read = False
    @property
    def time_since(self):
        return util.time_since(self.timestamp)
        
class Feed(object):
    def __init__(self, url):
        self.uuid = uuid.uuid4().hex
        self.url = url
        self.username = None
        self.password = None
        self.enabled = True
        self.last_poll = 0
        self.interval = settings.DEFAULT_POLLING_INTERVAL
        self.etag = None
        self.modified = None
        self.title = ''
        self.link = ''
        self.clicks = 0
        self.item_count = 0
        self.id_list = []
        self.id_set = set()
    def make_copy(self):
        feed = Feed(self.url)
        for key in ['uuid', 'enabled', 'interval', 'title', 'link', 'clicks', 'item_count']:
            value = getattr(self, key)
            setattr(feed, key, value)
        return feed
    def copy_from(self, feed):
        for key in ['enabled', 'interval', 'title', 'link']:
            value = getattr(feed, key)
            setattr(self, key, value)
    @property
    def favicon_url(self):
        components = urlparse.urlsplit(self.link)
        scheme, domain = components[:2]
        return '%s://%s/favicon.ico' % (scheme, domain)
    @property
    def favicon_path(self):
        components = urlparse.urlsplit(self.link)
        scheme, domain = components[:2]
        path = 'icons/cache/%s.ico' % domain
        return os.path.abspath(path)
    @property
    def has_favicon(self):
        return os.path.exists(self.favicon_path)
    def download_favicon(self):
        # make cache directory if needed
        try:
            dir, name = os.path.split(self.favicon_path)
            os.makedirs(dir)
        except Exception:
            pass
        # try to download the favicon
        try:
            f = urllib2.urlopen(self.favicon_url)
            data = f.read()
            f.close()
            f = open(self.favicon_path, 'wb')
            f.write(data)
            f.close()
        except Exception:
            pass
    def clear_cache(self):
        self.id_list = []
        self.id_set = set()
        self.etag = None
        self.modified = None
    def clean_cache(self, size):
        for id in self.id_list[:-size]:
            self.id_set.remove(id)
        self.id_list = self.id_list[-size:]
    def should_poll(self):
        if not self.enabled:
            return False
        now = int(time.time())
        duration = now - self.last_poll
        return duration >= self.interval
    def poll(self, timestamp):
        logging.info('Polling feed "%s"' % self.url)
        result = []
        self.last_poll = timestamp
        username = util.decode_password(self.username)
        password = util.decode_password(self.password)
        d = util.parse(self.url, username, password, self.etag, self.modified)
        self.etag = util.get(d, 'etag', None)
        self.modified = util.get(d, 'modified', None)
        feed = util.get(d, 'feed', None)
        if feed:
            self.title = self.title or util.get(feed, 'title', '')
            self.link = self.link or util.get(feed, 'link', self.url)
        entries = util.get(d, 'entries', [])
        for entry in reversed(entries):
            id = create_id(entry)
            if id in self.id_set:
                continue
            self.item_count += 1
            self.id_list.append(id)
            self.id_set.add(id)
            item = Item(self, id)
            item.timestamp = calendar.timegm(util.get(entry, 'date_parsed', time.gmtime()))
            item.title = util.format(util.get(entry, 'title', ''), settings.POPUP_TITLE_LENGTH)
            item.description = util.format(util.get(entry, 'description', ''), settings.POPUP_BODY_LENGTH)
            item.link = util.get(entry, 'link', '')
            item.author = util.format(util.get(entry, 'author', '')) # TODO: max length
            result.append(item)
        self.clean_cache(settings.FEED_CACHE_SIZE)
        return result
        
class FeedManager(object):
    def __init__(self):
        self.feeds = []
        self.items = []
    def add_feed(self, feed):
        logging.info('Adding feed "%s"' % feed.url)
        self.feeds.append(feed)
    def remove_feed(self, feed):
        logging.info('Removing feed "%s"' % feed.url)
        self.feeds.remove(feed)
    def should_poll(self):
        return any(feed.should_poll() for feed in self.feeds)
    def poll(self):
        now = int(time.time())
        jobs = Queue.Queue()
        results = Queue.Queue()
        feeds = [feed for feed in self.feeds if feed.should_poll()]
        for feed in feeds:
            jobs.put(feed)
        count = len(feeds)
        logging.info('Starting worker threads')
        for i in range(min(count, settings.MAX_WORKER_THREADS)):
            util.start_thread(self.worker, now, jobs, results)
        while count:
            items = results.get()
            count -= 1
            if items:
                yield items
        logging.info('Worker threads completed')
    def worker(self, now, jobs, results):
        while True:
            try:
                feed = jobs.get(False)
            except Queue.Empty:
                break
            try:
                items = feed.poll(now)
                items.sort(cmp=cmp_timestamp)
                if items and not feed.has_favicon:
                    feed.download_favicon()
                results.put(items)
                jobs.task_done()
            except Exception:
                results.put([])
                jobs.task_done()
    def purge_items(self, max_age):
        now = int(time.time())
        feeds = set(self.feeds)
        for item in list(self.items):
            age = now - item.received
            if age > max_age or item.feed not in feeds:
                self.items.remove(item)
    def load(self, path='feeds.dat'):
        logging.info('Loading feed data from "%s"' % path)
        try:
            with open(path, 'rb') as input:
                self.feeds, self.items = pickle.load(input)
        except Exception:
            self.feeds, self.items = [], []
        # backward compatibility
        attributes = {
            'clicks': 0,
            'item_count': 0,
            'username': None,
            'password': None,
        }
        for feed in self.feeds:
            for name, value in attributes.iteritems():
                if not hasattr(feed, name):
                    setattr(feed, name, value)
    def save(self, path='feeds.dat'):
        logging.info('Saving feed data to "%s"' % path)
        with open(path, 'wb') as output:
            data = (self.feeds, self.items)
            pickle.dump(data, output, -1)
    def clear_item_history(self):
        logging.info('Clearing item history')
        del self.items[:]
    def clear_feed_cache(self):
        logging.info('Clearing feed caches')
        for feed in self.feeds:
            feed.clear_cache()
            