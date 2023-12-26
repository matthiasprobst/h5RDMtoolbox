import h5py
import json
import pathlib
import pydantic
import sys
from ast import literal_eval
from typing import Dict, Union, List


def to_hdf(jsonld_filename, grp: h5py.Group) -> None:
    """Takes a .jsonld file and writes it into a HDF5 group"""
    if not isinstance(grp, h5py.Group):
        raise TypeError(f'Expecting h5py.Group, got {type(grp)}')

    if not isinstance(jsonld_filename, (str, pathlib.Path)):
        raise TypeError(f'Expecting str or pathlib.Path, got {type(jsonld_filename)}')

    def _to_hdf(_h5: h5py.Group, jdict: Dict):
        """Takes a .jsonld file and writes it into a HDF5 group"""
        for k, v in jdict.items():
            if isinstance(v, dict):
                if k == 'has parameter':
                    label = v.get('label', '@id')
                    _h5.attrs[k] = v['@id']
                    if v.get('has numerical value', None):
                        ds = _h5.create_dataset(label, data=literal_eval(v['has numerical value']), track_order=True)
                        for kk, vv in v.items():
                            if kk != 'has numerical value':
                                ds.attrs[kk] = vv
                    else:
                        grp = _h5.create_group(label, track_order=True)
                        _to_hdf(grp, v)
                else:
                    grp = _h5.create_group(k, track_order=True)
                    _to_hdf(grp, v)
            elif isinstance(v, list):
                list_grp = _h5.create_group(k, track_order=True)
                for i, item in enumerate(v):
                    # _h5[k] =
                    obj_name = item.get('@id', str(i))
                    if item.get('has numerical value', None):
                        obj = list_grp.create_dataset(obj_name, data=literal_eval(item['has numerical value']),
                                                track_order=True)
                        for kk, vv in item.items():
                            if kk != 'has numerical value':
                                obj.attrs[kk] = vv
                    else:
                        obj = list_grp.create_group(obj_name, track_order=True)
                    _to_hdf(obj, item)
            else:
                _h5.attrs[k] = v

    with open(jsonld_filename, 'r') as f:
        return _to_hdf(grp, json.load(f))


def to_dict(grp: h5py.Group) -> Dict:
    """Converts the m4i process metadata into a dictionary"""
    if not isinstance(grp, h5py.Group):
        raise TypeError(f'Expecting h5py.Group, got {type(grp)}')
    if '@context' not in grp:
        raise KeyError(f'Expecting "@context" in {grp.name}')
    if '@graph' not in grp:
        raise KeyError(f'Expecting "@graph" in {grp.name}')
    context = dict(grp['@context'].attrs)
    graph = []
    for name, grp in grp['@graph'].items():
        proc = dict(grp.attrs)
        for k, v in grp.items():
            proc[k] = dict(v.attrs)

            if isinstance(v, h5py.Group):
                n_children = len(v.keys())
                if n_children == 1:
                    for kk, vv in v.items():
                        proc[k] = dict(vv.attrs)
                else:
                    # in this case, the group names are integers...sanity check:
                    # assert all([n.isdigit() for n in v.keys()])
                    proc[k] = [dict(vv.attrs) for vv in v.values()]
        graph.append(proc)
    return {'@context': context,
            '@graph': graph}


def to_json(grp: h5py.Group, target_filename) -> Dict:
    """Converts the m4i process metadata stored in the provided h5 group into a json file"""
    with open(target_filename, 'w') as f:
        json.dump(to_dict(grp), f, indent=4)


class M4IEntry(pydantic.BaseModel):
    name: str
    namespace: str = pydantic.Field(default='local')

    def getid(self):
        return f"{self.namespace}:{self.name}"

    def get_type(self) -> str:
        return self.__class__.__name__.lower().replace('_', '')

    def m4i_dump(self, **kwargs):
        _dict = {'@id': self.getid(),
                 '@type': self.get_type()}
        for k in self.model_fields:
            _field_value = getattr(self, k)
            if _field_value is not None:
                if isinstance(_field_value, list):
                    _dict[k.replace('_', ' ')] = [
                        _f.m4i_dump(**kwargs) if hasattr(_f, 'm4i_dump') else str(_f) for _f
                        in _field_value
                    ]
                elif hasattr(_field_value, 'getid'):
                    _dict[k.replace('_', ' ')] = _field_value.getid()
                else:
                    _dict[k.replace('_', ' ')] = str(_field_value)

        _dict.pop('namespace')
        return _dict

    def m4i_dump_json(self, **kwargs):
        return json.dumps(self.m4i_dump(**kwargs), **kwargs)


class Metadata(pydantic.BaseModel):
    graph: List[M4IEntry]
    context: Dict[str, pydantic.HttpUrl] = pydantic.Field(
        default={'@import': "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld"}
    )

    def m4i_dump(self, **kwargs):
        return {'@context': {k: str(v) for k, v in self.context.items()},
                '@graph': [e.m4i_dump(**kwargs) for e in self.graph]}

    def m4i_dump_json(self, **kwargs):
        # TODO: check if name space of all entries are registered in the context
        return json.dumps(self.m4i_dump(), **kwargs)


class Person(M4IEntry):
    first_name: str
    last_name: str
    ORCID_Id: pydantic.HttpUrl


class Variable(M4IEntry):
    label: str
    has_symbol: str = None
    has_value: str = None
    has_variable_description: str = None


class Method(M4IEntry):
    label: str
    description: str = None
    has_participant: Union[Person, List[Person]] = None
    has_employed_tool: str = None
    has_parameter: Union[Variable, List[Variable]] = None


class Numerical_Variable(Variable):
    has_numerical_value: str
    has_unit: pydantic.HttpUrl
    has_kind_of_quantity: Union[str, pydantic.HttpUrl] = None


class Processing_Step(M4IEntry):
    label: str
    description: str = None
    has_participant: Union[Person, List[Person]] = None
    has_employed_tool: str = None
    has_parameter: Union[Variable, List[Variable]] = None
    # TODO add more...


# compare both

if __name__ == '__main__':
    person = Person(namespace='local',
                    name='JD',
                    first_name='John',
                    last_name='Doe',
                    ORCID_Id='https://orcid.org/0000-0002-1825-0097')
    pivRec = Processing_Step(namespace='local',
                             name='pivRec',
                             label='PIV recording',
                             has_participant=person)
    pivEval = Method(namespace='local',
                     name='pivEval',
                     label='PIV evaluation',
                     has_participant=person,
                     has_parameter=[Numerical_Variable(namespace='piv',
                                                       name='PulseDelay',
                                                       label='Pulse Delay',
                                                       has_numerical_value='120',
                                                       has_unit='https://qudt.org/vocab/unit/MilliSEC',
                                                       has_kind_of_quantity='http://dbpedia.org/resource/Time')],
                     )

    print(Metadata(graph=[person, pivEval],
                   context={
                       'local': "https://local-domain.org/",
                       'piv': "https://piv.org/",
                       '@import': "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld"
                   }).m4i_dump_json(indent=4))
    # sys.exit(0)

    person = Person(namespace='local',
                    name='JD',
                    first_name='John',
                    last_name='Doe',
                    ORCID_Id='https://orcid.org/0000-0002-1825-0097')

    meth1 = Method(namespace='local',
                   name='preparation_0001:method',
                   label='Preparation',
                   has_participant=person)

    step1 = Processing_Step(namespace='local',
                           name='preparation_0001',
                           label='Preparation',
                           has_participant=person,
                           realizes_method=meth1
                           )

    numparam = Numerical_Variable(namespace='local',
                                  name='preparation_0001:temperature',
                                  label='Temperature',
                                  has_numerical_value='20',
                                  has_unit='http://purl.obolibrary.org/obo/UO_0000027',
                                  has_kind_of_quantity='http://purl.obolibrary.org/obo/OBI_0000299')

    # pprint(step1.m4i_dump())

    # print(Metadata(graph=[person, step1, meth1, numparam]).m4i_dump())
    print(Metadata(graph=[person, step1, meth1, numparam],
                   context={
                       'local': "https://local-domain.org/",
                       '@import': "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld"
                   }).m4i_dump_json(indent=4))

    # test m4i example
    import h5rdmtoolbox as h5tbx
    with h5tbx.File() as h5:
        json_filename = 'min_m4i_ex.jsonld'

        to_hdf(json_filename, h5.create_group('metadata'))

        exp_dict = to_dict(h5['metadata'])

        # and back
        to_json(h5['metadata'], 'min_m4i_ex_check.jsonld')

        with open('min_m4i_ex_check.jsonld') as f:
            ref_dict = json.load(f)

        assert exp_dict == ref_dict

    # test m4i example with multiple parameters
    with h5tbx.File() as h5:
        json_filename = 'multiple_parameters.json'

        to_hdf(json_filename, h5.create_group('metadata'))

        exp_dict = to_dict(h5['metadata'])

        # and back
        to_json(h5['metadata'], 'multiple_parameters_check.json')

        with open('multiple_parameters_check.json') as f:
            ref_dict = json.load(f)

        assert exp_dict == ref_dict
