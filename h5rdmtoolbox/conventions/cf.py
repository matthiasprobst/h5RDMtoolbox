"""Generates the standard name convention file for Fluids
This is work in progress and as long as there is no official version provided by the community
this repository uses this convention
"""

from h5rdmtoolbox.conventions.identifier import CFStandardNameTable


def fetch_cf_standard_name_table():
    """ download cf-standard-name-table"""
    try:
        import pooch
    except ImportError:
        raise ImportError(f'Package "pooch" is needed to download the file cf-standard-name-table.xml')
    file_path = pooch.retrieve(
        # URL to one of Pooch's test files
        url="https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml",
        known_hash='4c29b5ad70f6416ad2c35981ca0f9cdebf8aab901de5b7e826a940cf06f9bae4',
    )
    print(pooch.file_hash(file_path, 'sha256'))
    return CFStandardNameTable.from_xml(file_path)


if __name__ == '__main__':
    """creating xml convention files in xml/folder which will be installed with the package.
    So if something is changed here, update the version (also repo versioN), write the xml file and re-install the 
    package"""

    CF_Table = fetch_cf_standard_name_table()
    # cf_convention = NameIdentifierConvention.from_xml()
