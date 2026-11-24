"""Check the saved interactive graphs used by the documentation build."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path


class FrameParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.frames = []

    def handle_starttag(self, tag, attrs):
        if tag == 'iframe':
            self.frames.append(dict(attrs))


def test_knowledge_graph_notebook_has_self_contained_interactive_outputs():
    path = Path(__file__).parents[1] / 'docs/practical_examples/knowledge_graph.ipynb'
    notebook = json.loads(path.read_text(encoding='utf-8'))
    graph_cells = [
        cell for cell in notebook['cells']
        if cell['cell_type'] == 'code' and ''.join(cell['source']).strip() == 'show_graph(graph)'
    ]
    assert len(graph_cells) == 2
    labels = []
    for cell in graph_cells:
        outputs = [output['data']['text/html'] for output in cell['outputs']
                   if 'text/html' in output.get('data', {})]
        assert len(outputs) == 1
        parser = FrameParser()
        parser.feed(''.join(outputs[0]))
        assert len(parser.frames) == 1
        frame = parser.frames[0]
        assert frame['sandbox'] == 'allow-scripts'
        document = frame['srcdoc']
        assert 'new vis.Network(' in document
        assert not re.search(r'<script[^>]+src="[^"]*vis-network', document)
        assert 'cdn.jsdelivr.net/npm/bootstrap@' not in document
        nodes = json.loads(re.search(r'nodes = new vis.DataSet\((.*?)\);', document).group(1))
        edges = json.loads(re.search(r'edges = new vis.DataSet\((.*?)\);', document).group(1))
        assert nodes and edges
        node_ids = {node['id'] for node in nodes}
        assert all(edge['from'] in node_ids and edge['to'] in node_ids for edge in edges)
        labels.append({edge['label'] for edge in edges})
    assert 'hdf:rank' in labels[0]
    assert {'foaf:firstName', 'foaf:lastName'} <= labels[1]
