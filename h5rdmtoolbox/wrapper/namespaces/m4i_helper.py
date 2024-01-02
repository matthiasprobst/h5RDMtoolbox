import datetime
import json
import pathlib

__this_dir__ = pathlib.Path(__file__).parent


def generate_namespace_file(namespace: str):
    """Generate M4I_NAMESPACE.py file from m4i_context.jsonld"""

    context_url = 'https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld'
    # context_file = generate_temporary_directory() / 'm4i_context.jsonld'
    context_file = __this_dir__ / 'm4i_context.jsonld'
    if not context_file.exists():
        with open(context_file, 'w', encoding='utf-8') as f:
            import requests
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


if __name__ == '__main__':
    generate_namespace_file('m4i')
    generate_namespace_file('obo')
