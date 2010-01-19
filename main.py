import wx
import ipc
import controller

def main():
    container, message = ipc.init()
    if not container:
        return
    app = wx.PySimpleApp()
    ctrl = controller.Controller()
    container.callback = ctrl.parse_args
    container(message)
    app.MainLoop()
    
if __name__ == '__main__':
    main()
    