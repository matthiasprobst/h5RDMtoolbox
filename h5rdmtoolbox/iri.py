class IRIManager:
    """Manager class to handle IRIs of opened HDF5 files"""

    def __init__(self):
        self.registries = {}

    def __contains__(self, item):
        return item in self.registries

    def get(self, name, existing_iri=None):
        if name not in self.registries:
            if existing_iri is None:
                existing_iri = {}
            self.registries[name] = existing_iri
        return self.registries[name]


class IRI:
    """Helper class to store a IRI (international resource identifier) as an attribute.
    It will write the value to the attribute and store the IRI in a separate attribute
    (see constant `ATTRIRI`).

    Example:
    --------
    >>> import h5rdmtoolbox as h5tbx
    >>> with h5tbx.File() as h5:
    >>>     h5.attrs['creator'] = h5tbx.IRI('https://orcid.org/0000-0001-8729-0482')
    """

    def __init__(self, value, iri):
        self.iri = iri
        self.value = value

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value}, {self.iri})'


irimanager = IRIManager()
