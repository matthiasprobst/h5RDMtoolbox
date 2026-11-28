"""Implementation of dcat:Role
"""

from ontolutils import urirefs, namespaces

from ..skos import Concept


@namespaces(dcat="http://www.w3.org/ns/dcat#")
@urirefs(Role='dcat:Role')
class Role(Concept):
    """Pydantic implementation of dcat:Role"""
