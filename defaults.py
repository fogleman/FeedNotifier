# Helper Functions
def load_revision():
    try:
        with open('revision.txt', 'r') as file:
            return int(file.read().strip())
    except Exception:
        return -1
        
# Popup Settings
POPUP_DURATION = 5
POPUP_AUTO_PLAY = True
POPUP_THEME = 'default'
POPUP_WIDTH = 400
POPUP_POSITION = (1, 1)
POPUP_TRANSPARENCY = 230
POPUP_TITLE_LENGTH = 120
POPUP_BODY_LENGTH = 400

# Application Settings
APP_ID = 'FeedNotifier'
APP_NAME = 'Feed Notifier'
APP_VERSION = '2.1'
APP_URL = 'http://www.feednotifier.com/'
USER_AGENT = '%s/%s +%s' % (APP_ID, APP_VERSION, APP_URL)
DEFAULT_POLLING_INTERVAL = 60 * 15
USER_IDLE_TIMEOUT = 60
DISABLE_WHEN_IDLE = True
ITEM_CACHE_AGE = 60 * 60 * 24 * 1
FEED_CACHE_SIZE = 500

# Initial Setup
DEFAULT_FEED_URLS = [
    'http://www.feednotifier.com/welcome.xml',
]

# Proxy Settings
USE_PROXY = False
PROXY_URL = ''

# Updater Settings
LOCAL_REVISION = load_revision()
REVISION_URL = 'http://www.feednotifier.com/update/revision.txt'
INSTALLER_URL = 'http://www.feednotifier.com/update/installer.exe'
CHECK_FOR_UPDATES = True
UPDATE_INTERVAL = 60 * 60 * 24 * 7
UPDATE_TIMESTAMP = 0

del load_revision
