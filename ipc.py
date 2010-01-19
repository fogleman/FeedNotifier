import wx
import sys

class CallbackContainer(object):
    def __init__(self):
        self.callback = None
    def __call__(self, message):
        if self.callback:
            wx.CallAfter(self.callback, message)
            
if sys.platform == 'win32':
    import win32file
    import win32pipe
    import threading
    import time
    
    def init():
        container = CallbackContainer()
        message = '\n'.join(sys.argv[1:])
        name = r'\\.\pipe\FeedNotifier_%s' % wx.GetUserId()
        if client(name, message):
            return None, message
        else:
            thread = threading.Thread(target=server, args=(name, container))
            thread.setDaemon(True)
            thread.start()
            return container, message
            
    def server(name, callback_func):
        buffer = 4096
        timeout = 1000
        error = False
        while True:
            if error:
                time.sleep(1)
                error = False
            handle = win32pipe.CreateNamedPipe(
                name,
                win32pipe.PIPE_ACCESS_INBOUND,
                win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
                win32pipe.PIPE_UNLIMITED_INSTANCES,
                buffer,
                buffer,
                timeout,
                None)
            if handle == win32file.INVALID_HANDLE_VALUE:
                error = True
                continue
            try:
                if win32pipe.ConnectNamedPipe(handle) != 0:
                    error = True
                else:
                    code, message = win32file.ReadFile(handle, buffer, None)
                    if code == 0:
                        callback_func(message)
                    else:
                        error = True
            except:
                error = True
            finally:
                win32pipe.DisconnectNamedPipe(handle)
                win32file.CloseHandle(handle)
                
    def client(name, message):
        try:
            file = open(name, 'wb')
            file.write(message)
            file.close()
            return True
        except IOError:
            return False
else:
    def init():
        container = CallbackContainer()
        message = '\n'.join(sys.argv[1:])
        return container, message
        