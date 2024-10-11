# main.py

from modules.app import App
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    app = App(BASE_DIR)
    app.mainloop()