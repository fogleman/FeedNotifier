import util

class InvalidSettingError(Exception):
    pass

class NOT_SET(object):
    pass
    
class Settings(object):
    def __init__(self, parent):
        self._parent = parent
    def __getattr__(self, name):
        if name.startswith('_'):
            return super(Settings, self).__getattr__(name)
        value = self.get(name)
        if value != NOT_SET:
            return value
        if self._parent:
            return getattr(self._parent, name)
        raise InvalidSettingError, 'Invalid setting: %s' % name
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super(Settings, self).__setattr__(name, value)
            return
        if self.set(name, value):
            return
        if self._parent:
            setattr(self._parent, name, value)
            return
        raise InvalidSettingError, 'Invalid setting: %s' % name
    def get(self, name):
        raise NotImplementedError, 'Settings subclasses must implement the get() method.'
    def set(self, name, value):
        raise NotImplementedError, 'Settings subclasses must implement the set() method.'
        
class ModuleSettings(Settings):
    def __init__(self, parent, module):
        super(ModuleSettings, self).__init__(parent)
        self._module = module
    def get(self, name):
        module = self._module
        if hasattr(module, name):
            return getattr(module, name)
        return NOT_SET
    def set(self, name, value):
        return False
        
class FileSettings(Settings):
    def __init__(self, parent, file):
        super(FileSettings, self).__init__(parent)
        self._file = file
        self.load()
    def load(self):
        try:
            self._settings = util.safe_load(self._file)
        except Exception:
            self._settings = {}
    def save(self):
        util.safe_save(self._file, self._settings)
    def get(self, name):
        if name in self._settings:
            return self._settings[name]
        return NOT_SET
    def set(self, name, value):
        if value != getattr(self, name):
            self._settings[name] = value
            self.save()
        return True
        
def create_chain():
    import defaults
    settings = ModuleSettings(None, defaults)
    settings = FileSettings(settings, 'settings.dat')
    return settings
    
settings = create_chain()
