# Creating and deploying a GUI

## Converting .ui to .py

Convert the `main.ui` file to `main.py` like so. The file `main.py` will be used to create the GUI
by importing the class `Ui_MainWindow` from it. So don't manipulate the `main.py` file!

```bash
pyuic5 -x main.ui -o main.py
```