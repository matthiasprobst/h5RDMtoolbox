import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Tuple

STANDARD_NAME_TABLE_FORMAT_FILE = Path(__file__).parent / 'standard_name_table_format.html'

EMAIL_REGREX = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@"
                          r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])")


def is_valid_email_address(email: str) -> bool:
    """validates an email address.
    Taken from: https://stackabuse.com/python-validate-email-address-with-regular-expressions-regex/"""
    if re.fullmatch(EMAIL_REGREX, email):
        return True
    return False


def dict2xml(convention_dict: dict, name: str, filename: Path, version: int,
             institution: str, contact: str, datetime_str=None) -> Path:
    """writes standard_names dictionary into a xml in style of cf-standard-name-table"""
    if not is_valid_email_address(contact):
        raise ValueError(f'Invalid email address: {contact}')

    if datetime_str is None:
        datetime_str = '%Y-%m-%d_%H:%M:%S'

    root = ET.Element(name)

    item_version = ET.Element("version")
    item_version.text = str(version)

    item_last_modified = ET.Element("last_modified")
    item_last_modified.text = datetime.now().strftime(datetime_str)

    item_institution = ET.Element("institution")
    item_institution.text = institution

    item_contact = ET.Element("contact")
    item_contact.text = contact

    root.append(item_version)
    root.append(item_last_modified)
    root.append(item_institution)
    root.append(item_contact)

    for k, v in convention_dict.items():
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


def xml2dict(xml_filename: Path) -> Tuple[dict, dict]:
    """reads an xml convention xml file and returns data and meta dictionaries"""
    tree = ET.parse(xml_filename)
    root = tree.getroot()
    standard_names = {}
    meta = {'name': root.tag, 'version': int(root.find('version').text), 'contact': root.find('contact').text,
            'institution': root.find('institution').text, 'last_modified': root.find('last_modified').text}
    for child in root.iter('entry'):
        standard_names[child.attrib['id']] = {}
        for c in child:
            standard_names[child.attrib['id']][c.tag] = c.text
    return standard_names, meta
