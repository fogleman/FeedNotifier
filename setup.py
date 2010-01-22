import os
import py2exe
import sys
from distutils.core import setup

# Don't require the command line argument.
sys.argv.append('py2exe')

# Include these data files.
def get_data_files():
    def filter_files(files):
        def match(file):
            extensions = ['.dat']
            for extension in extensions:
                if file.endswith(extension):
                    return True
            return False
        return tuple(file for file in files if not match(file))
    def tree(src):
        return [(root, map(lambda f: os.path.join(root, f), filter_files(files))) for (root, dirs, files) in os.walk(os.path.normpath(src)) if '.svn' not in root and '.svn' in dirs]
    def include(src):
        result = tree(src)
        result = [('.', item[1]) for item in result]
        return result
    data_files = []
    data_files += tree('./icons')
    data_files += tree('./themes')
    #data_files += include('./extras')
    return data_files
    
# Build the distribution.
setup(
    options = {"py2exe":{
        "compressed": 1,
        "optimize": 2,
        "bundle_files": 1,
        "skip_scan": ['wx.lib.iewin'],
        "includes": ['wx.lib.iewin', 'wx.lib.activex', 'comtypes.gen.SHDocVw'],
    }},
    windows = [{
        "script": "main.py",
        "dest_base": "notifier",
        "icon_resources": [(1, "icons/feed.ico")],
    }],
    data_files = get_data_files(),
)
