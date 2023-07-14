import json
from typing import Union, Dict

from .errors import StandardNameTableError
from .standard_name import StandardName
from .table import StandardNameTable
from ..standard_attribute import StandardAttribute
from ... import cache


class StandardNameAttribute(StandardAttribute):
    """Standard Name attribute"""

    name = 'standard_name'

    def set(self, new_standard_name: Union[str, StandardName]):
        """Writes attribute standard_name if passed string is not None.
        The rules for the standard_name is checked before writing to file."""
        if new_standard_name:
            snt = self.parent.standard_name_table
            if isinstance(snt, StandardNameTable):
                if not snt.check(new_standard_name, self.parent.attrs.get('units', None)):
                    raise StandardNameTableError(f'Standard name "{new_standard_name}" '
                                                 f'failed the check of standard name table ')
                return self.parent.attrs.create(self.name, str(new_standard_name))
            raise ValueError(f'No standard name table found for {self.parent.name}')

    @staticmethod
    def validate(name, value, obj=None):
        snt = obj.snt
        return snt.check_name(value)

    def get(self, src=None, name=None, default=None) -> Union[StandardName, None]:
        """Return the standardized name of the dataset. The attribute name is `standard_name`.
        Returns `None` if it does not exist."""
        sn = super().get()
        if sn is None:
            return None
        try:
            snt = self.parent.standard_name_table
        except Exception as e:
            raise Exception(f'No standard name table found for {self.parent.name}') from e
        return snt[sn]
        # return StandardName(name=sn,
        #                     canonical_units=self.parent.attrs.get('units', None),
        #                     snt=self.parent.attrs.get('standard_name_table', None)
        #                     )


class StandardNameTableAttribute(StandardAttribute):
    """Standard Name Table attribute"""

    name = 'standard_name_table'

    @staticmethod
    def _store_in_cache(root, snt: Dict):
        """Store standard name table in cache"""
        assert isinstance(snt, StandardNameTable)
        cache.STANDARD_NAME_TABLES[root.file.id.id] = snt

    def set(self, snt: Union[str, StandardNameTable]):
        """Set (write to root group) Standard Name Table

        Raises
        ------
        StandardNameTableError
            If no write intent on file.

        """
        if isinstance(snt, str):
            StandardNameTable.print_registered()
            if snt[0] == '{':
                snt_dict = json.loads(snt)
                snt = StandardNameTable.from_dict(snt_dict)
            else:
                snt = StandardNameTable.load_registered(snt)

        if self.parent.mode == 'r':
            raise StandardNameTableError('Cannot write Standard Name Table (no write intent on file)')

        StandardNameTableAttribute._store_in_cache(self.parent, snt)

        # store meta data
        snt.to_dict()
        return super().set(value=json.dumps(snt.to_dict()), target=self.parent.rootparent)

    def get(self, src=None, name=None, default=None) -> StandardNameTable:
        """Get (if exists) Standard Name Table from file.

        Raises
        ------
        KeyError
            If cannot load SNT from registration.
        """
        try:
            return cache.STANDARD_NAME_TABLES[self.parent.file.id.id]
        except KeyError:
            pass  # not cached

        snt = super().get(src=self.parent.rootparent)

        if snt is None:
            # return Empty_Standard_Name_Table
            print(self.parent, type(self.parent))
            raise AttributeError(f'No standard name table found for file {self.parent.file.filename}')

        if snt.startswith('{'):
            snt_dict = json.loads(snt)
            if set(("url", "project_id", "ref_name", "file_path")).issubset(snt_dict):
                # it is a gitlab project
                return StandardNameTable.from_gitlab(**snt_dict)
            return snt_dict
        return StandardNameTable.from_web(snt)
