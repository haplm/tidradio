import tkinter as tk
from tkinter import filedialog, messagebox
from pprint import pformat
from construct_parser import eepromLayout

def load_file():
    file_path = filedialog.askopenfilename(
        title="Select EEPROM File",
        filetypes=(("Binary files", "*.nfw"), ("All files", "*.*"))
    )
    if not file_path:
        return

    try:
        with open(file_path, "rb") as f:
            data = f.read()
        parsed = eepromLayout.parse(data)
        display_data(parsed)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse file: {e}")

def display_data(parsed):
    text_area.delete(1.0, tk.END)
    text_area.insert(tk.END, pformat(parsed))

# Set up the main application window
root = tk.Tk()
root.title("EEPROM Parser")

# Create a text area to display parsed data
text_area = tk.Text(root, wrap=tk.WORD, width=80, height=30)
text_area.pack(expand=True, fill=tk.BOTH)

# Create a button to load and parse a file
load_button = tk.Button(root, text="Load EEPROM File", command=load_file)
load_button.pack(pady=10)

# Start the Tkinter event loop
root.mainloop() 