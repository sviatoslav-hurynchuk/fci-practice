import tkinter as tk
from ui import SonarAppUI


def main():
    root = tk.Tk()
    app = SonarAppUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
