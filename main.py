import wx
import os
import ipc
import controller

def set_path():
    file = controller.__file__
    file = os.path.abspath(file)
    while file and not os.path.isdir(file):
        file, ext = os.path.split(file)
    os.chdir(file)
    
def main():
    set_path()
    container, message = ipc.init()
    if not container:
        return
    app = wx.PySimpleApp()#redirect=True, filename='log.txt')
    ctrl = controller.Controller()
    container.callback = ctrl.parse_args
    container(message)
    app.MainLoop()
    
if __name__ == '__main__':
    main()
    