import sys

if sys.platform == 'win32':
    from ctypes import Structure, windll, c_uint, sizeof, byref
    
    class LASTINPUTINFO(Structure):
        _fields_ = [
            ('cbSize', c_uint),
            ('dwTime', c_uint),
        ]
        
    def get_idle_duration():
        lastInputInfo = LASTINPUTINFO()
        lastInputInfo.cbSize = sizeof(lastInputInfo)
        windll.user32.GetLastInputInfo(byref(lastInputInfo))
        millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
        return millis / 1000.0
else:
    def get_idle_duration():
        return 0
        
if __name__ == '__main__':
    import time
    while True:
        duration = get_idle_duration()
        print 'User idle for %.2f seconds.' % duration
        time.sleep(1)
        