import h5py
from qtpy.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

# Open the HDF5 file
with h5py.File(r"C:\Users\da4323\Documents\CeFaDBMeasurements\2022-11-11-n1000-DP100-DO63\recordings\2022-11-11-17-09-12_run.hdf", "r") as file:
    # Create a QApplication (required for creating a QWidget)
    app = QApplication([])

    # Create the tree widget
    tree = QTreeWidget()


    # Recursively add items to the tree widget
    def add_items(parent, obj):
        for key, val in obj.items():
            # Create a new tree widget item
            item = QTreeWidgetItem()
            # Set the text for the item
            item.setText(0, str(key))
            # Add the item to the parent
            parent.addChild(item)
            # If the value is a group (HDF5 dataset), recursively add its content to the tree
            if isinstance(val, h5py.Group):
                add_items(item, val)


    # Add the root item to the tree widget
    root = QTreeWidgetItem(tree)
    root.setText(0, "root")
    add_items(root, file)

    # Show the tree widget
    tree.show()

    # Run the QApplication (starts the event loop)
    app.exec_()

    # Close the HDF5 file
    file.close()