"""utility to automatically write namespaces python files automatically"""
import datetime
import json
import pathlib
import requests
import warnings

__this_dir__ = pathlib.Path(__file__).parent


def generate_namespace_file(namespace: str):
    """Generate M4I_NAMESPACE.py file from m4i_context.jsonld"""

    context_url = 'https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld'
    # context_file = generate_temporary_directory() / 'm4i_context.jsonld'
    context_file = __this_dir__ / 'm4i_context.jsonld'
    if not context_file.exists():
        with open(context_file, 'w', encoding='utf-8') as f:
            f.write(requests.get(context_url).text, )

    # read context file:
    with open(context_file) as f:
        context = json.load(f)

    url = context['@context'][namespace]

    iris = {}
    for k, v in context['@context'].items():
        if '@id' in v:
            if namespace in v['@id']:
                name = v["@id"].rsplit(":", 1)[-1]
                if name not in iris:
                    iris[name] = {'url': f'{url}{name}', 'keys': [k, ]}
                else:
                    iris[name]['keys'].append(k)

    with open(__this_dir__ / f'_{namespace}_namespace.py', 'w',
              encoding='UTF8') as f:
        f.write('from rdflib.namespace import DefinedNamespace, Namespace\n')
        f.write('from rdflib.term import URIRef\n')
        f.write(f'\n\nclass {namespace.upper()}(DefinedNamespace):')
        f.write('\n    # uri = "https://w3id.org/nfdi4ing/metadata4ing#"')
        f.write('\n    # Generated with h5rdmtoolbox.data.m4i.generate_namespace_file()')
        f.write(f'\n    # Date: {datetime.datetime.now()}')
        for k, v in iris.items():
            f.write(f'\n    {k}: URIRef  # {v["keys"]}')

        f.write(f'\n\n    _NS = Namespace("{url}")')

        f.write('\n\n')

        for k, v in iris.items():
            for kk in v["keys"]:
                key = kk.replace(' ', '_')
                f.write(f'\nsetattr({namespace.upper()}, "{key}", {namespace.upper()}.{k})')


def generate_qudt_unit_namespace():
    """Generate the qudt namespace."""
    from rdflib import Graph

    namespace = 'qudt_unit'

    g = Graph()
    g.parse("https://qudt.org/vocab/unit/")

    with open(__this_dir__ / f'_{namespace}_namespace.py', 'w',
              encoding='UTF8') as f:
        f.write('# automatically generated from https://qudt.org/vocab/unit/\n')
        f.write('from rdflib.namespace import Namespace\n')
        f.write('from rdflib.term import URIRef\n\n\n')
        f.write('class _QUDT_UNIT:')

        for s in g.subjects():
            u = str(s).rsplit('/', 1)[-1].replace('-', '_')
            if '#' in u:
                warnings.warn(f'Skipping {u} ({s}) because it has a "#" in it.')
            else:
                uri = str(s)
                f.write(f'\n    {u} = URIRef("{uri}")')

        f.write('\n\n    _NS = Namespace("https://qudt.org/vocab/unit/")')

        f.write('\n\n')
        f.write('\n\nQUDT_UNIT = _QUDT_UNIT()')


def generate_qudt_quantitykind_namespace():
    """Generate the qudt namespace."""
    from rdflib import Graph

    namespace = 'qudt_quantitykind'

    g = Graph()
    g.parse("https://qudt.org/vocab/quantitykind/")

    with open(__this_dir__ / f'_{namespace}_namespace.py', 'w',
              encoding='UTF8') as f:
        f.write('# automatically generated from https://qudt.org/vocab/quantitykind/\n')
        f.write('from rdflib.namespace import Namespace\n')
        f.write('from rdflib.term import URIRef\n\n\n')
        f.write('class _QUDT_QUANTITYKIND:')

        for s in g.subjects():
            u = str(s).rsplit('/', 1)[-1].replace('-', '_')
            if '#' in u:
                warnings.warn(f'Skipping {u} ({s}) because it has a "#" in it.')
            else:
                uri = str(s)
                f.write(f'\n    {u} = URIRef("{uri}")')

        f.write('\n\n    _NS = Namespace("https://qudt.org/vocab/quantitykind/")')

        f.write('\n\n')
        f.write('\n\nQUDT_QUANTITYKIND = _QUDT_QUANTITYKIND()')


if __name__ == '__main__':
    # generate_namespace_file('m4i')  # be careful, german lines must be manually uncommented
    # generate_namespace_file('obo')  # be careful, german lines must be manually uncommented
    generate_qudt_unit_namespace()  # write _qudt_namespace.py manually
    generate_qudt_quantitykind_namespace()  # write _qudt_quantitykind_namespace.py manually
