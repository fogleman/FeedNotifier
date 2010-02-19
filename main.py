def set_path():
    import os
    import dummy
    file = dummy.__file__
    file = os.path.abspath(file)
    while file and not os.path.isdir(file):
        file, ext = os.path.split(file)
    os.chdir(file)
    
def main():
    set_path()
    import wx
    import ipc
    import controller
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
    