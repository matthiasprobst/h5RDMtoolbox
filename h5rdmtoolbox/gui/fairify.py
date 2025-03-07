"""main gui"""
import getpass
import logging
import pathlib
import sys
from typing import Dict, Union, Tuple

import h5py
import rdflib
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont
from ontolutils import M4I, SCHEMA, OBO, CODEMETA, QUDT_UNIT, QUDT_KIND
from ontolutils.classes.utils import split_URIRef
from pivmetalib.namespace import PIVMETA
from ssnolib.namespace import SSNO

import h5rdmtoolbox as h5tbx
from .src.main import Ui_MainWindow

__this_dir__ = pathlib.Path(__file__).parent
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
for h in logger.handlers:
    h.setLevel(logging.DEBUG)

logger.info('Loading GUI...')

INIT_DIR = pathlib.Path.cwd()

USER = getpass.getuser()


def on_error(func):
    """Decorator to catch exceptions and print them to the console"""

    def wrapper(*args, **kwargs):
        """Wrapper function to catch exceptions and print them to the console"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f'Error: {e}')
            return None

    return wrapper


def get_tree_structure(grp: h5py.Group) -> Dict:
    """Return the tree (attributes, names, shapes) of the group and subgroups"""
    tree = {}
    for k, v in grp.items():
        if isinstance(v, h5py.Dataset):
            tree[v.name] = v
        if isinstance(v, h5py.Group):
            tree[v.name] = get_tree_structure(v)
    return tree


class Ui(QtWidgets.QMainWindow, Ui_MainWindow):
    """MainGui class"""

    def __init__(self, grp: h5py.Group):
        super(Ui, self).__init__()
        self.setupUi(self)
        self.setWindowTitle(f'HDF5 Fairify GUI')
        self.log_message(f'Hello {USER}!')
        self.grp = grp
        self.populate_tree()
        self.h5TreeWidget.itemSelectionChanged.connect(self.on_selection_changed)

        self.suffix_dict = {}
        self.namespacelib = {}

        for name, ns in (('M4I', M4I), ('PIVMETA', PIVMETA), ('SCHEMA', SCHEMA), ('OBO', OBO),
                         ('CODEMETA', CODEMETA), ('QUDT_UNIT', QUDT_UNIT), ('QUDT_KIND', QUDT_KIND), ('SSNO', SSNO),
                         ('FOAF', rdflib.FOAF), ('RDFS', rdflib.RDFS), ('RDF', rdflib.RDF), ('OWL', rdflib.OWL),
                         ('SKOS', rdflib.SKOS), ('PROV', rdflib.PROV)):
            self.namespacelib[name.lower()] = ns
            self.comboBoxPrefix1.addItem(name.lower())
            self.comboBoxPrefix2.addItem(name.lower())
            self.suffix_dict[name.lower()] = [k for k, v in ns.__annotations__.items()]

        self.update_prefix1(False)
        self.update_suffix1(False)

        self.update_prefix2(False)
        self.update_suffix2(False)

        self.comboBoxPrefix1.currentTextChanged.connect(self.update_prefix1)
        self.comboBoxSuffix1.currentTextChanged.connect(self.update_suffix1)

        self.comboBoxPrefix2.currentTextChanged.connect(self.update_prefix2)
        self.comboBoxSuffix2.currentTextChanged.connect(self.update_suffix2)

        self.lineEditIRI1.returnPressed.connect(self.update_presuf1_from_text)
        self.lineEditIRI2.returnPressed.connect(self.update_presuf2_from_text)

        self.write1.clicked.connect(self.write1_clicked)
        self.write2.clicked.connect(self.write2_clicked)

        self.show()

    def get_curr_obj(self) -> Tuple[Union[h5py.Group, h5py.Dataset, None], Union[str, None]]:
        """Return the current HDF object selected in the tree widget"""
        selected_items = self.h5TreeWidget.selectedItems()
        if not selected_items:
            return None, None

        if selected_items:
            selected_item = selected_items[0]

            item_text = selected_item.text(0)
            parent_item = selected_item.parent()

            self.log_message(f"Selected item value: {item_text}")
            if parent_item:
                parent_text = parent_item.text(0)
                self.log_message(f"parent_text: {parent_text}")

            if item_text in self.grp:
                self.log_message(f'Dataset or Group is selected: {item_text}')
                hdf_path = item_text
                attr_name = None
            else:
                self.log_message(f'Attribute is selected: {item_text}')
                hdf_path = parent_text
                attr_name = item_text
            self.log_message(f'HDF Obj is selected: {hdf_path}')

            return self.grp[hdf_path], attr_name

    @on_error
    def write1_clicked(self, *args, **kwargs):
        """Write IRI to the selected object's attribute.
        If an attribute is selected, the IRI refers to the RDF predicate.
        If a dataset or group is selected, the IRI refers to the RDF predicate.
        """
        obj, attr_name = self.get_curr_obj()
        if obj is None:
            self.log_message('No object selected', 'red')
            return

        rdf_predicate = self.lineEditIRI1.text()
        if not rdf_predicate.startswith('http'):
            self.log_message(f'Not a valid URI: {rdf_predicate}', 'red')
            return

        if attr_name is None:  # dataset or group selected
            try:
                obj.rdf.predicate = rdf_predicate
                self.log_message(f'Successfully wrote predicate {rdf_predicate} to HDF obj {obj.basename}', 'green')
            except Exception as e:
                self.log_message(f'Error writing to predicate: {e}', 'red')
        else:
            try:
                obj.rdf.predicate[attr_name] = rdf_predicate
                self.log_message(f'Successfully wrote predicate {rdf_predicate} to attribute {attr_name} of '
                                 f'object {obj.name}', 'green')
            except Exception as e:
                self.log_message(f'Error writing to predicate: {e}', 'red')

        self.populate_tree()

    @on_error
    def write2_clicked(self, *args, **kwargs):
        """Write IRI to the selected object's attribute.
        If an attribute is selected, the IRI refers to the RDF object.
        If a dataset or group is selected, the IRI refers to the RDF subject.
        """
        obj, attr_name = self.get_curr_obj()
        if obj is None:
            self.log_message('No object selected', 'red')
            return

        if attr_name is None:  # dataset or group selected
            rdf_subject = self.lineEditIRI2.text()
            if not rdf_subject.startswith('http'):
                self.log_message(f'Not a valid URI: {rdf_subject}', 'red')
                return

            try:
                obj.rdf.subject = rdf_subject
                self.log_message(f'Successfully wrote predicate {rdf_subject} to attribute {attr_name} of '
                                 f'object {obj.name}', 'green')
            except Exception as e:
                self.log_message(f'Error writing to predicate: {e}', 'red')
        else:
            rdf_object = self.lineEditIRI2.text()
            if not rdf_object.startswith('http'):
                self.log_message(f'Not a valid URI: {rdf_object}', 'red')
                return

            try:
                obj.rdf.object[attr_name] = rdf_object
                self.log_message(f'Successfully wrote predicate {rdf_object} to attribute {attr_name} of '
                                 f'object {obj.name}', 'green')
            except Exception as e:
                self.log_message(f'Error writing to predicate: {e}', 'red')

        self.populate_tree()

    def update_presuf1_from_text(self, pred=None):
        """Update the prefix and suffix from the text box"""
        if pred is None:
            pred = self.lineEditIRI1.text()
        self.log_message(f'updating prefix and suffix from text: {pred}')
        ns, key = split_URIRef(pred)
        if ns is not None:
            if ns.startswith('http'):
                for name, n in self.namespacelib.items():
                    if str(n._NS) == ns:
                        self.comboBoxPrefix1.setCurrentText(name)
                        self.comboBoxSuffix1.setCurrentText(key)
                        break
            else:
                self.comboBoxPrefix1.setCurrentText(ns)
                self.comboBoxSuffix1.setCurrentText(key)

    def update_presuf2_from_text(self, pred=None):
        """Update the prefix and suffix from the text box"""
        if pred is None:
            pred = self.lineEditIRI2.text()
        self.log_message(f'updating prefix and suffix from text: {pred}')
        ns, key = split_URIRef(pred)
        self.log_message(f'Try to update combo boxes with ns={ns} and key={key}')
        if ns is not None:
            if ns.startswith('http'):
                for name, n in self.namespacelib.items():
                    if str(n._NS) == ns:
                        self.log_message(f'Found ns={ns} in {name}')
                        self.comboBoxPrefix2.setCurrentText(name)
                        self.comboBoxSuffix2.setCurrentText(key)
                        break
            else:
                self.comboBoxPrefix2.setCurrentText(ns)
                self.comboBoxSuffix2.setCurrentText(key)

    def update_prefix1(self, update_lineedit=True):
        """Update the line edit for prefix 1"""
        self.log_message('Clearing combo box...')
        self.comboBoxSuffix1.clear()
        current_prefix = self.comboBoxPrefix1.currentText()

        self.log_message(f'Updating combo box with data: {current_prefix}...')
        self.comboBoxSuffix1.addItems(self.suffix_dict[current_prefix])
        ns, key = split_URIRef(self.lineEditIRI1.text())

        ns_uri = self.namespacelib[current_prefix]._NS

        if update_lineedit:
            self.lineEditIRI1.setText(f'{ns_uri}{key}')

    def update_prefix2(self, update_lineedit=True):
        """Update the line edit for prefix 1"""
        self.log_message('Clearing combo box...')
        self.comboBoxSuffix2.clear()
        current_prefix = self.comboBoxPrefix2.currentText()

        self.log_message(f'Updating combo box with data: {current_prefix}...')
        self.comboBoxSuffix2.addItems(self.suffix_dict[current_prefix])
        ns, key = split_URIRef(self.lineEditIRI2.text())

        ns_uri = self.namespacelib[current_prefix]._NS

        if update_lineedit:
            self.lineEditIRI2.setText(f'{ns_uri}{key}')

    def update_suffix1(self, update_lineedit=True):
        """Update the line edit for suffix 1"""
        current_prefix = self.comboBoxPrefix1.currentText()
        ns_uri = self.namespacelib[current_prefix]._NS
        current_suffix = self.comboBoxSuffix1.currentText()
        if update_lineedit:
            self.lineEditIRI1.setText(f'{ns_uri}{current_suffix}')

    def update_suffix2(self, update_lineedit=True):
        """Update the line edit for suffix 1"""
        current_prefix = self.comboBoxPrefix2.currentText()
        ns_uri = self.namespacelib[current_prefix]._NS
        current_suffix = self.comboBoxSuffix2.currentText()
        if update_lineedit:
            self.lineEditIRI2.setText(f'{ns_uri}{current_suffix}')

    def on_selection_changed(self):
        """Update call if selection in tree view changes"""

        self.lineEditIRI1.setText('')
        self.lineEditIRI1.setToolTip('')
        self.lineEditIRI2.setText('')
        self.lineEditIRI2.setToolTip('')

        obj, attr_display_name = self.get_curr_obj()
        if attr_display_name:
            attr_name = attr_display_name.split('=', 1)[0]
        else:
            attr_name = attr_display_name
        if obj is None:
            self.groupBox1.setTitle(f'nothing selected')
            self.groupBox2.setTitle(f'nothing selected')
            self.groupBox1.setEnabled(False)
            self.groupBox2.setEnabled(False)
            return
        self.groupBox1.setEnabled(True)
        self.groupBox2.setEnabled(True)

        if attr_name is None:  # is a dataset or group
            obj_name = obj.name
            self.groupBox1.setTitle(f'subject of "{obj_name}"')
            self.groupBox2.setTitle(f'type of "{obj_name}"')

            self.comboBoxPrefix1.setEnabled(False)
            self.comboBoxSuffix1.setEnabled(False)
            self.comboBoxPrefix2.setEnabled(True)
            self.comboBoxSuffix2.setEnabled(True)

            subj = obj.rdf.subject
            if subj:
                self.lineEditIRI1.setText(subj)
                self.groupBox1.setToolTip(f'"{obj.basename}" is entity <{subj}>')
            else:
                self.lineEditIRI1.setText('')
                self.groupBox1.setToolTip(f'no subject found for "{obj.basename}"')

            subj = obj.rdf.type
            if subj:
                self.lineEditIRI1.setText(subj)
                self.groupBox1.setToolTip(f'"{obj.basename}" is of type <{subj}>')
            else:
                self.lineEditIRI1.setText('')
                self.groupBox1.setToolTip(f'no type found for "{obj.basename}"')
        else:
            self.comboBoxPrefix1.setEnabled(True)
            self.comboBoxSuffix1.setEnabled(True)
            self.comboBoxPrefix2.setEnabled(False)
            self.comboBoxSuffix2.setEnabled(False)

            self.groupBox1.setTitle(f'RDF predicate for attr. name "{attr_name}"')
            self.groupBox2.setTitle(f'RDF object for attr. value "{obj.attrs[attr_name]}"')
            pred = obj.rdf.predicate.get(attr_name, '')
            self.lineEditIRI1.setText(pred)
            if pred != '':
                self.update_presuf1_from_text(pred=pred)

            rdf_object = obj.rdf.object.get(attr_name, '')
            self.lineEditIRI2.setText(rdf_object)
            if rdf_object != '':
                self.update_presuf2_from_text(pred=rdf_object)

    def populate_tree(self):
        """Populate the tree widget with data from the HDF5 file"""
        self.log_message('Populating tree widget with data...')
        self.h5TreeWidget.setHeaderHidden(True)  # Hide the header
        self.h5TreeWidget.clear()  # Clear existing items
        self._add_items_recursive(self.grp, self.h5TreeWidget)
        self.h5TreeWidget.setItemsExpandable(True)
        self.h5TreeWidget.expandAll()

    def _add_items_recursive(self, grp, parent_item):
        """Add items to the tree widget recursively"""
        grp_item = QtWidgets.QTreeWidgetItem(parent_item, [grp.name])
        grp_item.setFont(0, QFont('Arial', -1, QFont.Bold))

        # get subject, predicate and object RDF for current selected item
        item_name = grp.name

        def _build_tooltip(attr_name, s=None, p=None, o=None) -> str:
            tt: str = attr_name
            if s:
                tt += f'\n\tRDF subject:   {s}'
            if p:
                tt += f'\n\tRDF predicate: {p}'
            if o:
                tt += f'\n\tRDF object:    {o}'
            return tt

        s, p, o = grp.rdf.subject, grp.rdf.predicate.get(item_name, None), grp.rdf.object.get(item_name, None)
        grp_item.setToolTip(0, _build_tooltip(item_name, s=s, p=p, o=o))
        if any((s, p, o)):
            font = grp_item.font(0)
            font.setUnderline(True)
            grp_item.setFont(0, font)

        grp_item.addChild(grp_item)
        for ak, av in grp.attrs.items():
            if not ak.isupper():
                attr_item = QtWidgets.QTreeWidgetItem(grp_item, [f"{ak}={av}"])
                s, p, o = None, grp.rdf.predicate.get(ak, None), grp.rdf.object.get(ak, None)
                if any((s, p, o)):
                    font = attr_item.font(0)
                    font.setUnderline(True)
                    attr_item.setFont(0, font)
                attr_item.setToolTip(0, _build_tooltip(f'{ak}="{av}"', s=s, p=p, o=o))
                attr_item.addChild(attr_item)

        if isinstance(grp, h5py.Group):
            for name, obj in grp.items():
                self._add_items_recursive(obj, grp_item)

    def log_message(self, message, color='k'):
        """Write a message to the plain text edit box"""
        logger.debug(f'log_message: {message}')
        if color in ('k', 'black'):
            self.messageTextEdit.appendPlainText(str(message))
        elif color in ('r', 'red'):
            self.messageTextEdit.appendHtml(f'<font color="red">{message}</font><br>')
        elif color in ('g', 'green'):
            self.messageTextEdit.appendHtml(f'<font color="green">{message}</font><br>')
        else:
            logger.critical(f'Unknown color: {color}')
            raise ValueError(f'Unknown color: {color}')


def start(*args, filename=None, wd=None, console: bool = True):
    """call the gui"""
    if console:
        logger.debug('Initializing gui from console...')
        app = QtWidgets.QApplication([*args, ])
    else:
        logger.debug('Initializing gui from python script...')
        app = QtWidgets.QApplication(*args)

    if filename is not None and not filename.exists():
        raise FileNotFoundError(f'File not found: {filename}')

    use_test_file = False
    if filename is None:
        use_test_file = True
        filename = __this_dir__ / 'test.hdf5'
        with h5tbx.File(filename, 'w') as h5:
            h5.attrs['rootattr'] = 2
            ds = h5.create_dataset('ds1', data=[1, 2, 3, 4, 5, 6, ])
            ds.attrs['attr1'] = 'value1'
            ds = h5.create_dataset('grp/ds2', data=[1, 2, 3, 4, 5, 6, ])
            ds.attrs['attr2'] = 'value2'

    with h5tbx.File(filename, 'r+') as h5:
        _ = Ui(h5)
        print('Starting gui ...')
        app.exec_()

    if use_test_file:
        filename.unlink(missing_ok=True)


if __name__ == "__main__":
    start(sys.argv)
