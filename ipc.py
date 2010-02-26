import wx
import sys
import util

class CallbackContainer(object):
    def __init__(self):
        self.callback = None
    def __call__(self, message):
        if self.callback:
            wx.CallAfter(self.callback, message)
            
if sys.platform == 'win32':
    import win32file
    import win32pipe
    import time
    
    def init():
        container = CallbackContainer()
        message = '\n'.join(sys.argv[1:])
        name = r'\\.\pipe\FeedNotifier_%s' % wx.GetUserId()
        if client(name, message):
            return None, message
        else:
            util.start_thread(server, name, container)
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
            except Exception:
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
    import functools
    import socket
    import SocketServer
    
    def init():
        container = CallbackContainer()
        message = '\n'.join(sys.argv[1:])
        host, port = 'localhost', 31763
        try:
            server(host, port, container)
            return container, message
        except socket.error:
            client(host, port, message)
        return None, message
        
    def server(host, port, callback_func):
        class Handler(SocketServer.StreamRequestHandler):
            def __init__(self, callback_func, *args, **kwargs):
                self.callback_func = callback_func
                SocketServer.StreamRequestHandler.__init__(self, *args, **kwargs)
            def handle(self):
                data = self.rfile.readline().strip()
                self.callback_func(data)
        server = SocketServer.TCPServer((host, port), functools.partial(Handler, callback_func))
        util.start_thread(server.serve_forever)
        
    def client(host, port, message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.send(message)
        sock.close()
        