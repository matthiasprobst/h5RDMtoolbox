import pathlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Union

from pint_xarray import unit_registry as ureg

STANDARD_NAME_TABLE_FORMAT_FILE = Path(__file__).parent / 'standard_name_table_format.html'

EMAIL_REGREX = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@"
                          r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])")


def equal_base_units(unit1, unit2):
    """Return if two units are equivalent"""
    base_unit1 = ureg(unit1).to_base_units().units.__format__(ureg.default_format)
    base_unit2 = ureg(unit2).to_base_units().units.__format__(ureg.default_format)
    return base_unit1 == base_unit2


def is_valid_email_address(email: str) -> bool:
    """validates an email address.
    Taken from: https://stackabuse.com/python-validate-email-address-with-regular-expressions-regex/"""
    if re.fullmatch(EMAIL_REGREX, email):
        return True
    return False


def dict2xml(filename: Union[str, pathlib.Path], name: str, dictionary: Dict, **metadata) -> Path:
    """writes standard_names dictionary into a xml in style of cf-standard-name-table

    data must be a Tuple where first entry is the dictionary and the second one is metadata
    """

    root = ET.Element(name)

    for k, v in metadata.items():
        item = ET.Element(k)
        item.text = str(v)
        root.append(item)

    for k, v in dictionary.items():
        entry = ET.SubElement(root, "entry", attrib={'id': k})
        for kk, vv in v.items():
            item = ET.SubElement(entry, kk)
            item.text = vv

    tree = ET.ElementTree(root)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    return Path(filename)


def xml_to_html_table_view(xml_filename, html_filename=None):
    """creates a table view of standard xml file"""
    xml_filename = Path(xml_filename)
    if html_filename is None:
        html_filename = xml_filename.parent / f'{xml_filename.stem}.html'
    with open(STANDARD_NAME_TABLE_FORMAT_FILE, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if '{filename}' in line:
            lines[i] = line.format(filename='fluid-standard-name-table.xml')

    with open(html_filename, 'w') as f:
        f.writelines(lines)
