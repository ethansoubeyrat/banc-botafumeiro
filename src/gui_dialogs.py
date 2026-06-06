import tkinter as tk
import tkinter.messagebox

# Selction amongst a list of items
class ListBoxSelect:
    def __init__ (self, title, geometry, deviceList):
        self.selectedDevice = ""
        self.root = tk.Tk()
        self.root.geometry (geometry)
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.title (title)
        listbox = tk.Listbox (self.root)
        listbox.pack (fill="both", expand=True)
        for device in deviceList:
            listbox.insert (tk.END, device)
        listbox.bind ('<Double-1>', lambda x: self._select_list_item(self.root, listbox))
        buttonSel = tk.Button (self.root, text="Select", command=lambda : self._select_list_item(self.root, listbox))
        buttonSel.pack ()

    def _select_list_item (self, root, listBox):
        deviceID = listBox.get (tk.ANCHOR)
        if (deviceID):
            self.selectedDevice = deviceID
            root.destroy ()

    def select_item (self):
        self.root.wait_window ()
        return (self.selectedDevice)

# Modal text box of one of the types "error", "warning", "info", "question"
class AlarmBox:
    def __init__ (self, text, type="warning"):
        self.root = tk.Tk()
        self.root.geometry ("1x1+300+300")
        self.root.withdraw ()
        tk.messagebox.showinfo (message=text, icon=type)
