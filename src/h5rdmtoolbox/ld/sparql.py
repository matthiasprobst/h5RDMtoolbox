from typing import Dict, Optional, Union

import h5py
import rdflib
from ._types import RDFMappingEntry


def sparql(
        source,
        query: str,
        *,
        contextual: bool = True,
        structural: bool = True,
        skipND: int = 1,
        file_uri: Optional[Union[str, Dict[str, str]]] = None,
        format: str = "ttl",
        context: Optional[Dict] = None,
        rdf_mappings: Dict[str, RDFMappingEntry] = None,
        as_dataframe: bool = False,
        **kwargs
):
    from ..wrapper.core import File as H5tbxFile
    if isinstance(source, H5tbxFile):
        from .. import serialize
        rdf_data = source.serialize(
            fmt=format,
            structural=structural,
            contextual=contextual,
            skipND=skipND,
            file_uri=file_uri,
            context=context,
            rdf_mappings=rdf_mappings,
            **kwargs
        )
    else:
        from .. import serialize
        rdf_data = serialize(
            source,
            format=format,
            structural=structural,
            contextual=contextual,
            skipND=skipND,
            file_uri=file_uri,
            context=context,
            rdf_mappings=rdf_mappings,
            **kwargs
        )

    g = rdflib.Graph()
    g.parse(data=rdf_data, format=format)

    results = g.query(query)

    if as_dataframe:
        import pandas as pd
        rows = [dict(row.asdict()) for row in results]
        return pd.DataFrame(rows)

    return results
