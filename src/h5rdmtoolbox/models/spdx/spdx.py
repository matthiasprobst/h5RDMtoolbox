from typing import Union, Optional

import rdflib
from pydantic import Field, field_validator

from ontolutils import Thing, urirefs, namespaces
from ontolutils.namespacelib.spdx import SPDX
from ontolutils.typing import AnyThing


@namespaces(spdx="http://spdx.org/rdf/terms#")
@urirefs(Checksum='spdx:Checksum',
         algorithm='spdx:algorithm',
         checksumValue='spdx:checksumValue')
class Checksum(Thing):
    """An spdx:Checksum describing a digest and its algorithm.

        ``checksumValue`` (alias ``value``) is required. Supply ``algorithm``
        explicitly, for example ``"sha256"``, ``"sha1"``, ``"md5"``, or the
        algorithm's full SPDX IRI. String names are lowercased and looked up
        as ``SPDX.checksumAlgorithm_<name>``; hyphenated display names such
        as ``"SHA-256"`` are not normalized to ``"sha256"``.
    """
    algorithm: Optional[AnyThing] = Field(default="None")  # dcat:algorithm
    checksumValue: str = Field(alias="value")  # dcat:value

    @field_validator("algorithm", mode="before")
    @classmethod
    def validate_algorithm(cls, algorithm_value: Union[str, AnyThing]) -> Union[str, AnyThing]:
        if isinstance(algorithm_value, rdflib.URIRef):
            return str(algorithm_value)
        if isinstance(algorithm_value, str) and str(algorithm_value).startswith("http"):
            return str(algorithm_value)
        if isinstance(algorithm_value, str):
            guess_name = f"checksumAlgorithm_{algorithm_value.lower()}"
            return str(SPDX[guess_name])
        return str(algorithm_value)
