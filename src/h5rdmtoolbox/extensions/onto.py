from rdflib.namespace import FOAF

from h5rdmtoolbox.wrapper.accessor import Accessor, register_accessor


@register_accessor("onto", "Group")
class OntologyAccessor(Accessor):

    def create_person(self,
                      orcid_id: str,
                      first_name: str = None,
                      last_name: str = None,
                      mbox: str = None,
                      affiliation: str = None,
                      group_name: str = None):
        """Adds a prov:Person. If group_name is None, first_name, first_name and last_name, or orcid_id will be used to
        create a group_name. If all are None, orcid_id will be used."""
        if group_name is None:
            if first_name:
                if last_name:
                    group_name = f'{first_name}_{last_name}'
                else:
                    group_name = first_name
            else:
                group_name = orcid_id
        grp = self._obj.create_group(group_name)
        grp.rdf.type = 'https://www.w3.org/ns/prov/Person'
        if orcid_id:
            grp.attrs['orcid_id', 'http://w3id.org/nfdi4ing/metadata4ing#orcidId'] = orcid_id
            grp.rdf.subject = orcid_id
        if first_name:
            grp.attrs['first_name', FOAF.firstName] = first_name
        if last_name:
            grp.attrs['last_name', FOAF.lastName] = last_name
        if mbox:
            grp.attrs['mbox', FOAF.mbox] = mbox
        if affiliation:
            grp.attrs['affiliation', 'http://www.w3.org/ns/prov#affiliation'] = affiliation
        return grp

    # def create_software_agent(self,
    #                           name: str,
    #                           mbox: str = None,
    #                           group_name: str = None, ):
    #     if group_name is None:
    #         group_name = name
    #     grp = self._obj.create_group(group_name)
    #     grp.rdf.type = 'https://www.w3.org/ns/prov/SoftwareAgent'
    #     grp.attrs['name', FOAF.name] = name
    #     if mbox:
    #         grp.attrs['mbox', FOAF.mbox] = mbox
    #     return grp
