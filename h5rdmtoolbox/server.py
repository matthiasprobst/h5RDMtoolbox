import pathlib
import re
import urllib.parse
import logging
import json
from html import escape
from typing import Optional, Sequence, Union

import rdflib

from h5rdmtoolbox.ld import get_ld

logger = logging.getLogger(__name__)
HDF5_SUFFIXES = {".h5", ".hdf", ".hdf5"}
PREFIX_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
STANDARD_PREFIXES = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dcterms": "http://purl.org/dc/terms/",
    "doi": "https://doi.org/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "prof": "http://www.w3.org/ns/dx/prof/",
    "prov": "http://www.w3.org/ns/prov#",
    "qudt": "http://qudt.org/schema/qudt/",
    "quantitykind": "http://qudt.org/vocab/quantitykind/",
    "schema": "https://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "ssno": "https://matthiasprobst.github.io/ssno#",
    "unit": "http://qudt.org/vocab/unit/",
    "zenodo": "https://zenodo.org/records/",
    "zenodo_record": "https://zenodo.org/record/",
}
RDF_FORMATS = {
    "ttl": ("turtle", "text/turtle; charset=utf-8", "Turtle"),
    "jsonld": ("json-ld", "application/ld+json; charset=utf-8", "JSON-LD"),
    "nt": ("nt", "application/n-triples; charset=utf-8", "N-Triples"),
    "xml": ("xml", "application/rdf+xml; charset=utf-8", "RDF/XML"),
}
DEFAULT_SPARQL_QUERY = """SELECT ?subject ?predicate ?object
WHERE {
  ?subject ?predicate ?object .
}
LIMIT 25"""
SAMPLE_SPARQL_QUERIES = [
    (
        "Standard names",
        """SELECT ?subject ?object
WHERE {
  ?subject ssno:standardName ?object .
  ?subject a ssno:StandardName .
}
LIMIT 25""",
    ),
    (
        "RDF types",
        """SELECT ?subject ?type
WHERE {
  ?subject a ?type .
}
LIMIT 25""",
    ),
    (
        "Units",
        """SELECT ?subject ?unit
WHERE {
  ?subject qudt:unit ?unit .
}
LIMIT 25""",
    ),
]


def discover_hdf_files(directory: Union[str, pathlib.Path] = ".") -> list[pathlib.Path]:
    """Return HDF5 files in *directory* sorted by filename."""
    root = pathlib.Path(directory)
    return sorted(
        (path for path in root.iterdir() if path.is_file() and path.suffix.lower() in HDF5_SUFFIXES),
        key=lambda path: path.name.lower(),
    )


def _as_file_list(hdf_filenames: Optional[Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]]) -> list[pathlib.Path]:
    if hdf_filenames is None:
        return discover_hdf_files()
    if isinstance(hdf_filenames, (str, pathlib.Path)):
        filenames = [hdf_filenames]
    else:
        filenames = list(hdf_filenames)
    return [pathlib.Path(filename) for filename in filenames]


def _file_registry(hdf_filenames: Optional[Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]]) -> dict[str, pathlib.Path]:
    registry = {}
    for filename in _as_file_list(hdf_filenames):
        key = filename.name
        if key in registry:
            raise ValueError(f'Duplicate HDF5 filename "{key}" cannot be served twice')
        registry[key] = filename
    return registry


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _validate_prefix(prefix: Optional[str]) -> Optional[str]:
    if prefix in (None, ""):
        return None
    if not PREFIX_RE.match(prefix):
        raise ValueError("prefix must start with a letter or underscore and contain only letters, digits, '_', '.', or '-'")
    return prefix


def _bind_standard_prefixes(graph: rdflib.Graph) -> None:
    """Bind common RDF namespaces without replacing prefixes already defined by the graph."""
    for prefix, namespace in STANDARD_PREFIXES.items():
        graph.bind(prefix, rdflib.Namespace(namespace), override=False, replace=False)


def create_app(hdf_filename: Optional[Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]] = None,
               structural: bool = True,
               contextual: bool = True,
               file_uri: Optional[str] = None,
               list_landing: bool = True):
    """Create a FastAPI app serving RDF extracted from one or more HDF5 files.

    This function intentionally returns a *minimal* ASGI app using FastAPI if available.
    """
    try:
        from fastapi import FastAPI, Request, Response, HTTPException, Form
        from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
        from starlette.responses import Response as StarletteResponse
        from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape
    except Exception as e:
        raise RuntimeError("FastAPI and Jinja2 must be installed to use the server.\n"
                           "Install with: pip install 'h5rdmtoolbox[server]'\n") from e

    app = FastAPI(title="h5rdmtoolbox RDF server")
    hdf_files = _file_registry(hdf_filename)
    default_hdf_filename = next(iter(hdf_files.values()), None)

    # Load graph once at startup
    graph = rdflib.Graph()
    if default_hdf_filename is not None:
        graph = get_ld(default_hdf_filename, structural=structural, contextual=contextual, file_uri=file_uri)
        _bind_standard_prefixes(graph)

    # Jinja2 environment
    try:
        # Prefer FileSystemLoader to work directly from the repo during development/tests
        templates_dir = pathlib.Path(__file__).parent / "server" / "templates"
        if templates_dir.exists():
            loader = FileSystemLoader(str(templates_dir))
        else:
            loader = PackageLoader("h5rdmtoolbox", "server/templates")
        jenv = Environment(
            loader=loader,
            autoescape=select_autoescape(["html", "xml"]),
        )
    except Exception:
        # Last-resort: try PackageLoader
        from jinja2 import Environment, PackageLoader, select_autoescape
        jenv = Environment(
            loader=PackageLoader("h5rdmtoolbox", "server/templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )

    # mount static directory
    try:
        app.mount("/static", StaticFiles(directory=pathlib.Path(__file__).parent / "server" / "static"), name="static")
    except Exception:
        # best-effort; package data should include static files
        pass

    file_key = default_hdf_filename.stem if default_hdf_filename is not None else ""
    create_app_file_uri = file_uri

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        if list_landing or len(hdf_files) != 1:
            file_cards = []
            for key in hdf_files:
                encoded_key = urllib.parse.quote(key)
                format_links = "".join(
                    f'<a class="format-link" href="/{encoded_key}/{format_key}">{escape(label)}</a>'
                    for format_key, (_, _, label) in RDF_FORMATS.items()
                )
                graph_link = f'<a class="format-link graph-link" href="/{encoded_key}/graph">Graph</a>'
                query_link = f'<a class="format-link query-link" href="/{encoded_key}/query">Query</a>'
                metrics_link = f'<a class="format-link metrics-link" href="/{encoded_key}/metrics">Metrics</a>'
                file_cards.append(f"""<article class="file-card">
  <div>
    <h2>{escape(key)}</h2>
    <p>{escape(str(hdf_files[key]))}</p>
  </div>
  <div class="format-actions">{format_links}{graph_link}{query_link}{metrics_link}</div>
</article>""")
            body = (
                '<section class="empty">No HDF5 files found in this directory.</section>'
                if not file_cards
                else f'<section class="file-list">{"".join(file_cards)}</section>'
            )
            return HTMLResponse(f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>h5RDMtoolbox HDF5 files</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --border: #d8dee6;
      --accent: #0b6f85;
      --accent-hover: #084f5f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    main {{
      width: min(960px, calc(100% - 32px));
      margin: 32px auto;
    }}
    header {{
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 1.8rem;
      font-weight: 650;
    }}
    .subtitle {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .file-list {{
      display: grid;
      gap: 12px;
    }}
    .file-card {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    .file-card h2 {{
      margin: 0 0 4px;
      font-size: 1rem;
      font-weight: 650;
      overflow-wrap: anywhere;
    }}
    .file-card p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.875rem;
      overflow-wrap: anywhere;
    }}
    .format-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .format-link {{
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 0 12px;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 600;
    }}
    .format-link:hover {{
      background: var(--accent-hover);
    }}
    .empty {{
      padding: 20px;
      background: var(--panel);
      border: 1px dashed var(--border);
      border-radius: 8px;
      color: var(--muted);
    }}
    @media (max-width: 680px) {{
      .file-card {{
        grid-template-columns: 1fr;
      }}
      .format-actions {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>HDF5 files</h1>
    <p class="subtitle">Select a file and RDF serialization format. Each view includes controls for structural data, contextual data, and file URI.</p>
  </header>
  {body}
</main>
</body>
</html>
""")

        # Render an HTML skeleton of the HDF5 file using get_tree_structure()
        try:
            from h5rdmtoolbox import File as H5File

            def render_tree(name, node):
                """Recursively render a node (group or dataset) to HTML."""
                html = ""
                if isinstance(node, dict) and ('shape' in node or 'ndim' in node):
                    # dataset
                    shape = node.get('shape')
                    dtype = node.get('dtype', '')
                    attrs = {k: v for k, v in node.items() if k not in ('shape', 'ndim', 'dtype')}
                    html += f"<li><strong>Dataset: {name}</strong> <small>shape={shape} dtype={dtype}</small>"
                    if attrs:
                        html += "<ul>"
                        for ak, av in attrs.items():
                            html += f"<li><code>{ak}</code>: {av}</li>"
                        html += "</ul>"
                    html += "</li>"
                elif isinstance(node, dict):
                    # group
                    html += f"<li><details open><summary><strong>Group: {name}</strong></summary>"
                    # attributes of the group are those items which are not dicts or datasets
                    attrs = {k: v for k, v in node.items() if not isinstance(v, dict)}
                    children = {k: v for k, v in node.items() if isinstance(v, dict)}
                    if attrs:
                        html += "<div><em>Attributes</em><ul>"
                        for ak, av in attrs.items():
                            html += f"<li><code>{ak}</code>: {av}</li>"
                        html += "</ul></div>"
                    if children:
                        html += "<div><em>Members</em><ul>"
                        for child_name, child_node in children.items():
                            html += render_tree(child_name, child_node)
                        html += "</ul></div>"
                    html += "</details></li>"
                else:
                    html += f"<li>{name}: {node}</li>"
                return html

            with H5File(default_hdf_filename, mode='r') as fh:
                tree = fh.get_tree_structure(recursive=True)
            body = "<ul>"
            for key, node in tree.items():
                body += render_tree(key, node)
            body += "</ul>"
            page = f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\"> 
  <title>h5RDMtoolbox — {default_hdf_filename.name}</title>
  <link rel=\"stylesheet\" href=\"/static/style.css\"> 
  <style>details summary {{ cursor: pointer; padding: 0.2rem 0.2rem; }}</style>
</head>
<body>
<div class=\"card\">{body}</div>
</body>
</html>
"""
            return HTMLResponse(page)
        except Exception:
            # fallback to simple index template
            tmpl = jenv.get_template("index.html")
            return HTMLResponse(tmpl.render(file_key=file_key, filename=str(default_hdf_filename)))

    def negotiate_format(request: Request, override: Optional[str] = None) -> str:
        # override by query param
        if override:
            fmt = override.lower()
            if fmt in ("ttl", "turtle"):
                return "turtle"
            if fmt in ("html",):
                return "html"
            if fmt in ("jsonld", "json-ld", "json"):
                return "json-ld"
        accept = request.headers.get("accept", "")
        if "text/turtle" in accept or "application/x-turtle" in accept:
            return "turtle"
        if "text/html" in accept:
            return "html"
        if "application/ld+json" in accept or "json" in accept:
            return "json-ld"
        # default
        return "turtle"

    @app.get("/file/{fk}")
    def get_file(request: Request, fk: str, format: Optional[str] = None):
        if fk != file_key:
            raise HTTPException(status_code=404, detail="Unknown file key")
        fmt = negotiate_format(request, format)
        if fmt == "turtle":
            data = graph.serialize(format="turtle")
            return PlainTextResponse(content=data, media_type="text/turtle; charset=utf-8")
        if fmt == "json-ld":
            data = graph.serialize(format="json-ld")
            return JSONResponse(content=data, media_type="application/ld+json")
        # html
        tmpl = jenv.get_template("file.html")
        ttl = graph.serialize(format="turtle")
        return HTMLResponse(tmpl.render(filename=str(default_hdf_filename), file_key=file_key, turtle=ttl))

    def _format_controls(filename: str,
                         format_key: str,
                         serialized: str,
                         structural: bool,
                         contextual: bool,
                         file_uri: Optional[str],
                         prefix: Optional[str]) -> HTMLResponse:
        encoded_filename = urllib.parse.quote(filename)
        format_links = " ".join(
            f'<a href="/{encoded_filename}/{key}">{escape(label)}</a>'
            for key, (_, _, label) in RDF_FORMATS.items()
        )
        escaped_file_uri = escape(file_uri or "")
        raw_href = (
            f"/{encoded_filename}/{format_key}"
            f"?structural={_bool_str(structural)}"
            f"&contextual={_bool_str(contextual)}"
            f"&raw=true"
        )
        if file_uri:
            raw_href += f"&file_uri={urllib.parse.quote(file_uri, safe=':/')}"
        if prefix:
            raw_href += f"&prefix={urllib.parse.quote(prefix)}"
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(filename)} {escape(RDF_FORMATS[format_key][2])}</title>
  <style>
    body {{ font-family: sans-serif; margin: 1.5rem; }}
    form {{ display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: end; margin: 1rem 0; }}
    label {{ display: grid; gap: 0.25rem; }}
    input[type="text"] {{ min-width: 24rem; }}
    .toolbar {{ display: flex; gap: 0.75rem; align-items: center; margin: 1rem 0; }}
    .copy-button {{
      min-height: 34px;
      padding: 0 12px;
      border: 0;
      border-radius: 6px;
      background: #0b6f85;
      color: #fff;
      font-weight: 600;
      cursor: pointer;
    }}
    .copy-button:hover {{ background: #084f5f; }}
    .copy-status {{ color: #667085; font-size: 0.875rem; }}
    pre {{ padding: 1rem; background: #f6f8fa; overflow: auto; }}
  </style>
</head>
<body>
<nav><a href="/">Files</a> | {format_links}</nav>
<h1>{escape(filename)} - {escape(RDF_FORMATS[format_key][2])}</h1>
<form method="get" action="/{encoded_filename}/{format_key}">
  <label>Structural
    <select name="structural">
      <option value="true" {"selected" if structural else ""}>true</option>
      <option value="false" {"selected" if not structural else ""}>false</option>
    </select>
  </label>
  <label>Contextual
    <select name="contextual">
      <option value="true" {"selected" if contextual else ""}>true</option>
      <option value="false" {"selected" if not contextual else ""}>false</option>
    </select>
  </label>
  <label>File URI
    <input type="text" name="file_uri" value="{escaped_file_uri}" placeholder="https://example.org/data/">
  </label>
  <label>Prefix
    <input type="text" name="prefix" value="{escape(prefix or "")}" placeholder="ex">
  </label>
  <button type="submit">Update</button>
  <a href="{raw_href}">Raw</a>
</form>
<div class="toolbar">
  <button class="copy-button" type="button" data-copy-target="serialization-output">Copy to clipboard</button>
  <span class="copy-status" id="copy-status" role="status" aria-live="polite"></span>
</div>
<pre id="serialization-output">{escape(serialized)}</pre>
<script>
  const copyButton = document.querySelector("[data-copy-target]");
  const copyStatus = document.getElementById("copy-status");
  copyButton.addEventListener("click", async () => {{
    const target = document.getElementById(copyButton.dataset.copyTarget);
    const text = target.innerText;
    try {{
      if (navigator.clipboard && window.isSecureContext) {{
        await navigator.clipboard.writeText(text);
      }} else {{
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }}
      copyStatus.textContent = "Copied";
    }} catch (error) {{
      copyStatus.textContent = "Copy failed";
    }}
    window.setTimeout(() => {{ copyStatus.textContent = ""; }}, 1800);
  }});
</script>
</body>
</html>
"""
        return HTMLResponse(page)

    def _graph_mode_flags(mode: str) -> tuple[bool, bool]:
        if mode == "both":
            return True, True
        if mode == "structural":
            return True, False
        if mode == "contextual":
            return False, True
        raise HTTPException(status_code=400, detail="mode must be one of: both, structural, contextual")

    def _graph_label(value, rdf_graph: Optional[rdflib.Graph] = None) -> str:
        if isinstance(value, rdflib.URIRef):
            namespace_manager = rdf_graph.namespace_manager if rdf_graph is not None else rdflib.Graph().namespace_manager
            text = str(value)
            try:
                normalized = str(namespace_manager.normalizeUri(value))
                if not normalized.startswith("<") and not re.match(r"^ns\d+:", normalized):
                    return normalized
            except Exception:
                pass
            for prefix, namespace in STANDARD_PREFIXES.items():
                if text.startswith(namespace) and text != namespace:
                    return f"{prefix}:{text[len(namespace):]}"
            try:
                return namespace_manager.qname(value)
            except Exception:
                pass
            if rdf_graph is not None:
                namespaces = sorted(
                    ((prefix, str(namespace)) for prefix, namespace in rdf_graph.namespaces() if prefix),
                    key=lambda item: len(item[1]),
                    reverse=True,
                )
                for prefix, namespace in namespaces:
                    if text.startswith(namespace) and text != namespace:
                        return f"{prefix}:{text[len(namespace):]}"
            text = str(value)
            return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text
        text = str(value)
        return text if len(text) <= 48 else f"{text[:45]}..."

    def _graph_data(rdf_graph: rdflib.Graph) -> dict[str, list[dict[str, str]]]:
        class_palette = [
            ("#d8eef2", "#0b6f85"),
            ("#e4def8", "#6b4bb3"),
            ("#dff3df", "#287a3e"),
            ("#fff0cc", "#a66b00"),
            ("#f8dfe8", "#b33963"),
            ("#dbeafe", "#2563eb"),
            ("#f1e7d0", "#8a5a18"),
            ("#e0f2fe", "#0369a1"),
        ]
        type_by_node = {
            str(subject): _graph_label(obj, rdf_graph)
            for subject, obj in rdf_graph.subject_objects(rdflib.RDF.type)
        }
        class_groups = {}
        for index, class_label in enumerate(sorted(set(type_by_node.values()))):
            background, border = class_palette[index % len(class_palette)]
            class_groups[f"class:{class_label}"] = {
                "color": {"background": background, "border": border},
            }
        groups = {
            "resource": {"color": {"background": "#eceff3", "border": "#667085"}},
            "blank": {"color": {"background": "#eceff3", "border": "#667085"}},
            **class_groups,
        }
        nodes = {}
        edges = []

        def node_group(value) -> str:
            class_label = type_by_node.get(str(value))
            if class_label:
                return f"class:{class_label}"
            return "resource" if isinstance(value, rdflib.URIRef) else "blank"

        for subject, predicate, obj in rdf_graph:
            subject_id = str(subject)
            nodes.setdefault(subject_id, {
                "id": subject_id,
                "label": _graph_label(subject, rdf_graph),
                "group": node_group(subject),
                "rdf_class": type_by_node.get(subject_id, ""),
                "literals": [],
            })
            if isinstance(obj, rdflib.Literal):
                nodes[subject_id]["literals"].append({
                    "predicate": _graph_label(predicate, rdf_graph),
                    "value": str(obj),
                })
                continue
            object_id = str(obj)
            nodes.setdefault(object_id, {
                "id": object_id,
                "label": _graph_label(obj, rdf_graph),
                "group": node_group(obj),
                "rdf_class": type_by_node.get(object_id, ""),
                "literals": [],
            })
            edges.append({
                "from": subject_id,
                "to": object_id,
                "label": _graph_label(predicate, rdf_graph),
                "arrows": "to",
            })
        return {"nodes": list(nodes.values()), "edges": edges, "groups": groups}

    def _graph_page(filename: pathlib.Path,
                    mode: str = "both",
                    file_uri: Optional[str] = None,
                    prefix: Optional[str] = None) -> HTMLResponse:
        structural_graph, contextual_graph = _graph_mode_flags(mode)
        graph_file_uri = file_uri if file_uri is not None else create_app_file_uri
        try:
            graph_prefix = _validate_prefix(prefix)
            rdf_graph = get_ld(
                filename,
                structural=structural_graph,
                contextual=contextual_graph,
                file_uri=graph_file_uri,
            )
            _bind_standard_prefixes(rdf_graph)
            if graph_prefix and graph_file_uri:
                rdf_graph.bind(graph_prefix, rdflib.URIRef(graph_file_uri), override=True, replace=True)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        encoded_filename = urllib.parse.quote(filename.name)
        graph_json = json.dumps(_graph_data(rdf_graph)).replace("</", "<\\/")
        escaped_file_uri = escape(graph_file_uri or "")
        graph_nav = " ".join(
            f'<a href="/{encoded_filename}/{key}">{escape(label)}</a>'
            for key, (_, _, label) in RDF_FORMATS.items()
        )
        checked = {
            "both": "checked" if mode == "both" else "",
            "structural": "checked" if mode == "structural" else "",
            "contextual": "checked" if mode == "contextual" else "",
        }
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(filename.name)} Graph</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {{
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --border: #d8dee6;
      --accent: #0b6f85;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      height: 100%;
    }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      overflow: hidden;
    }}
    main {{
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      height: 100dvh;
      min-height: 520px;
      gap: 12px;
      padding: 18px;
    }}
    header {{
      display: grid;
      gap: 12px;
      padding: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      color: var(--muted);
    }}
    nav a {{ color: var(--accent); font-weight: 600; text-decoration: none; }}
    h1 {{ margin: 0; font-size: 1.35rem; }}
    form {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: end;
    }}
    fieldset {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 0;
      padding: 0;
      border: 0;
    }}
    legend {{
      width: 100%;
      margin-bottom: 2px;
      color: var(--muted);
      font-size: 0.875rem;
    }}
    label {{ display: grid; gap: 4px; color: var(--muted); font-size: 0.875rem; }}
    .radio-label {{ display: inline-flex; align-items: center; gap: 6px; color: var(--text); }}
    input[type="text"] {{
      min-width: min(28rem, 80vw);
      min-height: 34px;
      padding: 0 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
    }}
    button {{
      min-height: 34px;
      padding: 0 14px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      font-weight: 650;
      cursor: pointer;
    }}
    .graph-panel {{
      min-height: 0;
      height: 100%;
      display: grid;
    }}
    .hidden-node-menu {{
      position: absolute;
      left: 14px;
      top: 14px;
      z-index: 2;
    }}
    .hidden-node-menu button,
    .hide-node-button {{
      min-height: 30px;
      padding: 0 10px;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #fff;
      color: var(--text);
      font-size: 0.85rem;
      font-weight: 650;
      cursor: pointer;
    }}
    .hidden-node-list {{
      display: none;
      width: min(320px, calc(100vw - 64px));
      max-height: 280px;
      overflow: auto;
      margin-top: 8px;
      padding: 8px;
      background: rgba(255, 255, 255, 0.96);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: 0 12px 28px rgba(31, 41, 51, 0.16);
    }}
    .hidden-node-list.open {{
      display: grid;
      gap: 6px;
    }}
    .hidden-node-list p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.85rem;
    }}
    .hidden-node-list button {{
      width: 100%;
      justify-content: start;
      text-align: left;
      overflow-wrap: anywhere;
    }}
    #network {{
      width: 100%;
      height: 100%;
      min-height: 0;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
    }}
    .node-details {{
      position: absolute;
      right: 30px;
      bottom: 30px;
      width: min(380px, calc(100% - 60px));
      max-height: min(420px, calc(100% - 60px));
      overflow: auto;
      display: none;
      padding: 14px;
      background: rgba(255, 255, 255, 0.96);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: 0 12px 28px rgba(31, 41, 51, 0.16);
    }}
    .node-details h2 {{
      margin: 0 0 10px;
      font-size: 1rem;
      overflow-wrap: anywhere;
    }}
    .node-details-header {{
      display: flex;
      gap: 10px;
      align-items: start;
      justify-content: space-between;
    }}
    .hide-node-button {{
      flex: 0 0 auto;
    }}
    .node-details dl {{
      display: grid;
      grid-template-columns: minmax(7rem, max-content) minmax(0, 1fr);
      column-gap: 14px;
      row-gap: 8px;
      margin: 0;
      align-items: start;
    }}
    .node-details dt {{
      color: var(--muted);
      font-size: 0.8rem;
      font-weight: 650;
      overflow-wrap: anywhere;
    }}
    .node-details dd {{
      margin: 0;
      overflow-wrap: anywhere;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      font-size: 0.85rem;
    }}
    @media (max-width: 560px) {{
      .node-details dl {{
        grid-template-columns: 1fr;
        row-gap: 4px;
      }}
      .node-details dd {{
        margin-bottom: 8px;
      }}
    }}
    .node-details .no-literals {{
      margin: 0;
      color: var(--muted);
    }}
    .graph-panel {{
      position: relative;
    }}
    .empty-graph {{
      display: none;
      color: var(--muted);
      padding: 12px;
    }}
  </style>
</head>
<body>
<main>
  <header>
    <nav><a href="/">Files</a> {graph_nav}</nav>
    <h1>{escape(filename.name)} - Graph</h1>
    <form id="graph-form" method="get" action="/{encoded_filename}/graph">
      <fieldset>
        <legend>RDF content</legend>
        <label class="radio-label"><input type="radio" name="mode" value="both" {checked["both"]}> Structural + contextual</label>
        <label class="radio-label"><input type="radio" name="mode" value="structural" {checked["structural"]}> Structural only</label>
        <label class="radio-label"><input type="radio" name="mode" value="contextual" {checked["contextual"]}> Contextual only</label>
      </fieldset>
      <label>File URI
        <input type="text" name="file_uri" value="{escaped_file_uri}" placeholder="https://example.org/data/">
      </label>
      <label>Prefix
        <input type="text" name="prefix" value="{escape(prefix or "")}" placeholder="ex">
      </label>
      <button type="submit">Update</button>
    </form>
  </header>
  <section class="graph-panel">
    <div class="hidden-node-menu">
      <button type="button" id="hidden-node-toggle" aria-expanded="false">Hidden nodes (0)</button>
      <div class="hidden-node-list" id="hidden-node-list"></div>
    </div>
    <div id="network"></div>
    <aside class="node-details" id="node-details" aria-live="polite"></aside>
    <p class="empty-graph" id="empty-graph">No RDF triples are available for this selection.</p>
  </section>
</main>
<script>
  const graphData = {graph_json};
  const graphForm = document.getElementById("graph-form");
  const container = document.getElementById("network");
  const emptyGraph = document.getElementById("empty-graph");
  const nodeDetails = document.getElementById("node-details");
  const hiddenNodeToggle = document.getElementById("hidden-node-toggle");
  const hiddenNodeList = document.getElementById("hidden-node-list");
  const allNodes = graphData.nodes;
  const allEdges = graphData.edges;
  const hiddenNodeIds = new Set();
  const nodeById = new Map(allNodes.map((node) => [node.id, node]));
  let hideNode = () => {{}};
  let unhideNode = () => {{}};
  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
  const updateHiddenNodeMenu = () => {{
    const hiddenNodes = Array.from(hiddenNodeIds)
      .map((nodeId) => nodeById.get(nodeId))
      .filter(Boolean)
      .sort((left, right) => left.label.localeCompare(right.label));
    hiddenNodeToggle.textContent = `Hidden nodes (${{hiddenNodes.length}})`;
    hiddenNodeToggle.disabled = hiddenNodes.length === 0;
    if (hiddenNodes.length === 0) {{
      hiddenNodeList.innerHTML = '<p>No hidden nodes.</p>';
      hiddenNodeList.classList.remove("open");
      hiddenNodeToggle.setAttribute("aria-expanded", "false");
      return;
    }}
    hiddenNodeList.innerHTML = hiddenNodes
      .map((node) => `<button type="button" data-node-id="${{escapeHtml(node.id)}}">${{escapeHtml(node.label)}}</button>`)
      .join("");
  }};
  const showNodeDetails = (node) => {{
    const literals = node.literals || [];
    const literalRows = literals.length
      ? `<dl>${{literals.map((literal) => `<dt>${{escapeHtml(literal.predicate)}}</dt><dd>${{escapeHtml(literal.value)}}</dd>`).join("")}}</dl>`
      : '<p class="no-literals">No literal values are available for this node.</p>';
    nodeDetails.innerHTML = `<div class="node-details-header"><h2>${{escapeHtml(node.label)}}</h2><button type="button" class="hide-node-button">Hide</button></div>${{literalRows}}`;
    nodeDetails.querySelector(".hide-node-button").addEventListener("click", () => {{
      hideNode(node.id);
    }});
    nodeDetails.style.display = "block";
  }};
  hiddenNodeToggle.addEventListener("click", () => {{
    const isOpen = hiddenNodeList.classList.toggle("open");
    hiddenNodeToggle.setAttribute("aria-expanded", String(isOpen));
  }});
  hiddenNodeList.addEventListener("click", (event) => {{
    const button = event.target.closest("button[data-node-id]");
    if (!button) {{
      return;
    }}
    unhideNode(button.dataset.nodeId);
  }});
  graphForm.querySelectorAll('input[name="mode"]').forEach((radio) => {{
    radio.addEventListener("change", () => {{
      if (radio.checked) {{
        graphForm.requestSubmit();
      }}
    }});
  }});
  if (graphData.nodes.length === 0) {{
    emptyGraph.style.display = "block";
  }} else if (window.vis) {{
    const nodes = new vis.DataSet(allNodes);
    const edges = new vis.DataSet(allEdges);
    const groups = graphData.groups || {{}};
    const refreshVisibleGraph = () => {{
      nodes.clear();
      nodes.add(allNodes.filter((node) => !hiddenNodeIds.has(node.id)));
      edges.clear();
      edges.add(allEdges.filter((edge) => !hiddenNodeIds.has(edge.from) && !hiddenNodeIds.has(edge.to)));
      updateHiddenNodeMenu();
    }};
    hideNode = (nodeId) => {{
      hiddenNodeIds.add(nodeId);
      nodeDetails.style.display = "none";
      refreshVisibleGraph();
    }};
    unhideNode = (nodeId) => {{
      hiddenNodeIds.delete(nodeId);
      refreshVisibleGraph();
    }};
    const network = new vis.Network(container, {{ nodes, edges }}, {{
      nodes: {{
        shape: "dot",
        size: 14,
        font: {{ size: 13, face: "Segoe UI" }},
        borderWidth: 1
      }},
      edges: {{
        arrows: "to",
        color: {{ color: "#9aa4b2", highlight: "#0b6f85" }},
        font: {{ align: "middle", size: 11, face: "Segoe UI" }},
        smooth: {{ type: "dynamic" }}
      }},
      groups,
      interaction: {{
        dragNodes: true,
        hover: true,
        navigationButtons: true
      }},
      physics: {{
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: {{
          gravitationalConstant: -55,
          centralGravity: 0.015,
          springLength: 125,
          springConstant: 0.08
        }},
        stabilization: {{ iterations: 180 }}
      }}
    }});
    network.on("click", (params) => {{
      if (params.nodes.length === 0) {{
        nodeDetails.style.display = "none";
        return;
      }}
      const node = nodeById.get(params.nodes[0]);
      if (node) {{
        showNodeDetails(node);
      }}
    }});
    updateHiddenNodeMenu();
  }} else {{
    emptyGraph.textContent = "The graph library could not be loaded.";
    emptyGraph.style.display = "block";
  }}
</script>
</body>
</html>
"""
        return HTMLResponse(page)

    def _query_result(graph: rdflib.Graph, query: str) -> tuple[str, str]:
        try:
            result = graph.query(query)
        except Exception as e:
            return f"SPARQL error: {e}", '<div class="query-error">SPARQL query failed.</div>'

        result_type = getattr(result, "type", None)
        if hasattr(result, "vars"):
            variables = [str(variable) for variable in result.vars]
            rows = []
            text_lines = ["\t".join(variables)]
            for row in result:
                values = ["" if value is None else _graph_label(value, graph) for value in row]
                rows.append(values)
                text_lines.append("\t".join(values))
            if not rows:
                return "No rows returned.", '<p class="empty-result">No rows returned.</p>'
            header = "".join(f"<th>{escape(variable)}</th>" for variable in variables)
            body = "".join(
                "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>"
                for row in rows
            )
            return "\n".join(text_lines), f'<table class="result-table"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'

        if result_type == "ASK":
            answer = str(bool(result))
            return answer, f'<p class="ask-result">{escape(answer)}</p>'

        result_graph = getattr(result, "graph", None)
        if result_graph is not None:
            _bind_standard_prefixes(result_graph)
            turtle = result_graph.serialize(format="turtle")
            return turtle, f"<pre>{escape(turtle)}</pre>"

        text = str(result)
        return text, f"<pre>{escape(text)}</pre>"

    def _query_page(filename: pathlib.Path, query: Optional[str] = None) -> HTMLResponse:
        sparql_query = query or DEFAULT_SPARQL_QUERY
        rdf_graph = get_ld(
            filename,
            structural=True,
            contextual=True,
            file_uri=create_app_file_uri,
        )
        _bind_standard_prefixes(rdf_graph)
        result_text = ""
        result_html = '<p class="empty-result">Run the example query or edit it before submitting.</p>'
        if query is not None:
            result_text, result_html = _query_result(rdf_graph, sparql_query)

        encoded_filename = urllib.parse.quote(filename.name)
        sample_queries_json = json.dumps([query for _, query in SAMPLE_SPARQL_QUERIES]).replace("</", "<\\/")
        sample_buttons = "".join(
            f'<button type="button" class="sample-query-button" data-query-index="{index}">{escape(label)}</button>'
            for index, (label, _) in enumerate(SAMPLE_SPARQL_QUERIES)
        )
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(filename.name)} Query</title>
  <style>
    :root {{
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --border: #d8dee6;
      --accent: #0b6f85;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 24px auto;
      display: grid;
      gap: 14px;
    }}
    header, .query-panel, .result-panel {{
      padding: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 10px;
    }}
    nav a {{ color: var(--accent); font-weight: 650; text-decoration: none; }}
    h1 {{ margin: 0; font-size: 1.4rem; }}
    form {{
      display: grid;
      gap: 10px;
    }}
    label {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 0.9rem;
      font-weight: 650;
    }}
    textarea {{
      width: 100%;
      min-height: 210px;
      resize: vertical;
      padding: 12px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      font-size: 0.9rem;
      line-height: 1.45;
      color: var(--text);
      background: #fff;
    }}
    textarea[readonly] {{
      min-height: 120px;
      background: #f6f8fa;
    }}
    button {{
      justify-self: start;
      min-height: 36px;
      padding: 0 14px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      font-weight: 650;
      cursor: pointer;
    }}
    .sample-query-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .sample-query-actions span {{
      color: var(--muted);
      font-size: 0.9rem;
      font-weight: 650;
    }}
    .sample-query-button {{
      min-height: 32px;
      padding: 0 10px;
      background: #fff;
      color: var(--accent);
      border: 1px solid var(--border);
    }}
    .sample-query-button:hover {{
      border-color: var(--accent);
    }}
    .result-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 0.9rem;
    }}
    .result-table th {{
      color: var(--muted);
      text-align: left;
      font-weight: 650;
      padding: 4px 12px 6px 0;
    }}
    .result-table td {{
      padding: 5px 12px 5px 0;
      vertical-align: top;
      overflow-wrap: anywhere;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
    }}
    .query-error {{
      color: #a31919;
      font-weight: 650;
      margin-top: 10px;
    }}
    .empty-result {{
      color: var(--muted);
      margin: 10px 0 0;
    }}
    pre {{
      padding: 12px;
      background: #f6f8fa;
      overflow: auto;
    }}
  </style>
</head>
<body>
<main>
  <header>
    <nav><a href="/">Files</a><a href="/{encoded_filename}/graph">Graph</a><a href="/{encoded_filename}/ttl">Turtle</a></nav>
    <h1>{escape(filename.name)} - SPARQL Query</h1>
  </header>
  <section class="query-panel">
    <form method="get" action="/{encoded_filename}/query">
      <div class="sample-query-actions">
        <span>Samples</span>
        {sample_buttons}
      </div>
      <label>SPARQL query
        <textarea id="sparql-query" name="query">{escape(sparql_query)}</textarea>
      </label>
      <button type="submit">Run query</button>
    </form>
  </section>
  <section class="result-panel">
    <label>Result
      <textarea id="sparql-result" readonly>{escape(result_text)}</textarea>
    </label>
    {result_html}
  </section>
</main>
<script>
  const sampleQueries = {sample_queries_json};
  const sparqlQueryTextarea = document.getElementById("sparql-query");
  document.querySelectorAll("[data-query-index]").forEach((button) => {{
    button.addEventListener("click", () => {{
      const query = sampleQueries[Number(button.dataset.queryIndex)];
      if (query) {{
        sparqlQueryTextarea.value = query;
        sparqlQueryTextarea.focus();
      }}
    }});
  }});
</script>
</body>
</html>
"""
        return HTMLResponse(page)

    def _count_table(rows: list[tuple[str, int]], empty_message: str) -> str:
        if not rows:
            return f'<p class="empty-result">{escape(empty_message)}</p>'
        body = "".join(
            f"<tr><td>{escape(label)}</td><td>{count}</td></tr>"
            for label, count in rows
        )
        return f'<table class="metric-table"><tbody>{body}</tbody></table>'

    def _graph_metrics(rdf_graph: rdflib.Graph) -> dict[str, object]:
        subjects = set()
        objects = set()
        resources = set()
        literal_count = 0
        predicate_counts = {}
        class_counts = {}
        degree_counts = {}
        adjacency = {}

        def add_degree(node, amount: int = 1) -> None:
            degree_counts[node] = degree_counts.get(node, 0) + amount

        for subject, predicate, obj in rdf_graph:
            subjects.add(subject)
            predicate_label = _graph_label(predicate, rdf_graph)
            predicate_counts[predicate_label] = predicate_counts.get(predicate_label, 0) + 1
            resources.add(subject)
            add_degree(subject)

            if predicate == rdflib.RDF.type:
                class_label = _graph_label(obj, rdf_graph)
                class_counts[class_label] = class_counts.get(class_label, 0) + 1

            if isinstance(obj, rdflib.Literal):
                literal_count += 1
                continue

            objects.add(obj)
            resources.add(obj)
            add_degree(obj)
            adjacency.setdefault(subject, set()).add(obj)
            adjacency.setdefault(obj, set()).add(subject)

        nodes = set(subjects) | objects
        seen = set()
        component_sizes = []
        for node in nodes:
            if node in seen:
                continue
            stack = [node]
            seen.add(node)
            size = 0
            while stack:
                current = stack.pop()
                size += 1
                for neighbor in adjacency.get(current, set()):
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            component_sizes.append(size)

        top_predicates = sorted(predicate_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        top_classes = sorted(class_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        top_nodes = [
            (_graph_label(node, rdf_graph), count)
            for node, count in sorted(degree_counts.items(), key=lambda item: (-item[1], _graph_label(item[0], rdf_graph)))[:10]
        ]

        return {
            "triples": len(rdf_graph),
            "nodes": len(nodes),
            "subjects": len(subjects),
            "resources": len(resources),
            "literals": literal_count,
            "predicates": len(predicate_counts),
            "classes": len(class_counts),
            "components": len(component_sizes),
            "largest_component": max(component_sizes, default=0),
            "isolated_nodes": sum(1 for size in component_sizes if size == 1),
            "top_predicates": top_predicates,
            "top_classes": top_classes,
            "top_nodes": top_nodes,
        }

    def _metrics_page(filename: pathlib.Path) -> HTMLResponse:
        rdf_graph = get_ld(
            filename,
            structural=True,
            contextual=True,
            file_uri=create_app_file_uri,
        )
        _bind_standard_prefixes(rdf_graph)
        metrics = _graph_metrics(rdf_graph)
        encoded_filename = urllib.parse.quote(filename.name)
        cards = [
            ("Triples", metrics["triples"]),
            ("Graph nodes", metrics["nodes"]),
            ("Subjects", metrics["subjects"]),
            ("Resources", metrics["resources"]),
            ("Literal values", metrics["literals"]),
            ("Predicate types", metrics["predicates"]),
            ("RDF classes", metrics["classes"]),
            ("Components", metrics["components"]),
            ("Largest component", metrics["largest_component"]),
            ("Isolated nodes", metrics["isolated_nodes"]),
        ]
        card_html = "".join(
            f'<article class="metric-card"><span>{escape(label)}</span><strong>{value}</strong></article>'
            for label, value in cards
        )
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(filename.name)} Metrics</title>
  <style>
    :root {{
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --border: #d8dee6;
      --accent: #0b6f85;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 24px auto;
      display: grid;
      gap: 14px;
    }}
    header, section {{
      padding: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 10px;
    }}
    nav a {{ color: var(--accent); font-weight: 650; text-decoration: none; }}
    h1 {{ margin: 0; font-size: 1.4rem; }}
    h2 {{ margin: 0 0 10px; font-size: 1rem; }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }}
    .metric-card {{
      display: grid;
      gap: 4px;
      padding: 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #fff;
    }}
    .metric-card span {{
      color: var(--muted);
      font-size: 0.85rem;
      font-weight: 650;
    }}
    .metric-card strong {{
      font-size: 1.55rem;
      line-height: 1.1;
    }}
    .metric-sections {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
    }}
    .metric-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    .metric-table td {{
      padding: 5px 12px 5px 0;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    .metric-table td:first-child {{
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
    }}
    .metric-table td:last-child {{
      width: 1%;
      white-space: nowrap;
      color: var(--muted);
      font-weight: 650;
      text-align: right;
    }}
    .empty-result {{
      margin: 0;
      color: var(--muted);
    }}
  </style>
</head>
<body>
<main>
  <header>
    <nav><a href="/">Files</a><a href="/{encoded_filename}/graph">Graph</a><a href="/{encoded_filename}/query">Query</a><a href="/{encoded_filename}/ttl">Turtle</a></nav>
    <h1>{escape(filename.name)} - Graph Metrics</h1>
  </header>
  <section>
    <div class="metric-grid">{card_html}</div>
  </section>
  <div class="metric-sections">
    <section>
      <h2>Top Predicates</h2>
      {_count_table(metrics["top_predicates"], "No predicates found.")}
    </section>
    <section>
      <h2>RDF Classes</h2>
      {_count_table(metrics["top_classes"], "No RDF classes found.")}
    </section>
    <section>
      <h2>Most Connected Nodes</h2>
      {_count_table(metrics["top_nodes"], "No connected nodes found.")}
    </section>
  </div>
</main>
</body>
</html>
"""
        return HTMLResponse(page)

    def _formatted_response(filename: pathlib.Path,
                            format_key: str,
                            structural: bool = True,
                            contextual: bool = True,
                            file_uri: Optional[str] = None,
                            prefix: Optional[str] = None,
                            raw: bool = False):
        """Return the HDF5 file RDF dump in the requested format."""
        if not structural and not contextual:
            raise HTTPException(
                status_code=400,
                detail="At least one of structural or contextual must be True.",
            )
        if format_key not in RDF_FORMATS:
            raise HTTPException(status_code=404, detail="Unknown RDF format")
        graph_file_uri = file_uri if file_uri is not None else create_app_file_uri
        try:
            graph_prefix = _validate_prefix(prefix)
            rdf_graph = get_ld(
                filename,
                structural=structural,
                contextual=contextual,
                file_uri=graph_file_uri,
            )
            _bind_standard_prefixes(rdf_graph)
            if graph_prefix and graph_file_uri:
                rdf_graph.bind(graph_prefix, rdflib.URIRef(graph_file_uri), override=True, replace=True)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        rdflib_format, media_type, _ = RDF_FORMATS[format_key]
        serialized = rdf_graph.serialize(format=rdflib_format)
        if raw:
            return PlainTextResponse(content=serialized, media_type=media_type)
        return _format_controls(
            filename=filename.name,
            format_key=format_key,
            serialized=serialized,
            structural=structural,
            contextual=contextual,
            file_uri=graph_file_uri,
            prefix=prefix,
        )

    @app.get("/{filename}/ttl")
    def get_file_ttl(filename: str,
                     structural: bool = True,
                     contextual: bool = True,
                     file_uri: Optional[str] = None,
                     prefix: Optional[str] = None,
                     raw: bool = False):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _formatted_response(hdf_file, "ttl", structural=structural, contextual=contextual,
                                   file_uri=file_uri, prefix=prefix, raw=raw)

    @app.get("/{filename}/jsonld")
    def get_file_jsonld(filename: str,
                        structural: bool = True,
                        contextual: bool = True,
                        file_uri: Optional[str] = None,
                        prefix: Optional[str] = None,
                        raw: bool = False):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _formatted_response(hdf_file, "jsonld", structural=structural, contextual=contextual,
                                   file_uri=file_uri, prefix=prefix, raw=raw)

    @app.get("/{filename}/nt")
    def get_file_nt(filename: str,
                    structural: bool = True,
                    contextual: bool = True,
                    file_uri: Optional[str] = None,
                    prefix: Optional[str] = None,
                    raw: bool = False):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _formatted_response(hdf_file, "nt", structural=structural, contextual=contextual,
                                   file_uri=file_uri, prefix=prefix, raw=raw)

    @app.get("/{filename}/xml")
    def get_file_xml(filename: str,
                     structural: bool = True,
                     contextual: bool = True,
                     file_uri: Optional[str] = None,
                     prefix: Optional[str] = None,
                     raw: bool = False):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _formatted_response(hdf_file, "xml", structural=structural, contextual=contextual,
                                   file_uri=file_uri, prefix=prefix, raw=raw)

    @app.get("/{filename}/graph")
    def get_file_graph(filename: str,
                       mode: str = "both",
                       file_uri: Optional[str] = None,
                       prefix: Optional[str] = None):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _graph_page(hdf_file, mode=mode, file_uri=file_uri, prefix=prefix)

    @app.get("/{filename}/query")
    def get_file_query(filename: str, query: Optional[str] = None):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _query_page(hdf_file, query=query)

    @app.get("/{filename}/metrics")
    def get_file_metrics(filename: str):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _metrics_page(hdf_file)

    @app.get("/ttl")
    def get_ttl(structural: bool = True,
                contextual: bool = True,
                file_uri: Optional[str] = None,
                prefix: Optional[str] = None,
                raw: bool = False):
        if default_hdf_filename is None:
            raise HTTPException(status_code=404, detail="No HDF5 file available")
        return _formatted_response(default_hdf_filename, "ttl", structural=structural, contextual=contextual,
                                   file_uri=file_uri, prefix=prefix, raw=raw)

    @app.get("/resource/{encoded_iri:path}")
    def get_resource(request: Request, encoded_iri: str, format: Optional[str] = None):
        iri = urllib.parse.unquote(encoded_iri)
        # create subgraph with triples where subject == iri
        subj = None
        try:
            subj = rdflib.URIRef(iri)
        except Exception:
            # fallback to blank node lookup by identifier
            subj = rdflib.BNode(iri)

        subg = rdflib.Graph()
        # bind namespace prefixes from original
        for prefix, ns in graph.namespaces():
            subg.bind(prefix, ns)

        for t in graph.triples((subj, None, None)):
            subg.add(t)
        # if empty, also try to find by fragment suffix (e.g., '#/my/path' or local:... ending with path)
        if len(subg) == 0:
            # try to find matching subjects by string match on their str()
            for s in set(graph.subjects()):
                if isinstance(s, rdflib.URIRef) and iri in str(s):
                    for t in graph.triples((s, None, None)):
                        subg.add(t)
        fmt = negotiate_format(request, format)
        if fmt == "turtle":
            data = subg.serialize(format="turtle")
            return PlainTextResponse(content=data, media_type="text/turtle; charset=utf-8")
        if fmt == "json-ld":
            data = subg.serialize(format="json-ld")
            return JSONResponse(content=data, media_type="application/ld+json")
        # html
        tmpl = jenv.get_template("resource.html")
        ttl = subg.serialize(format="turtle")
        return HTMLResponse(tmpl.render(iri=iri, turtle=ttl, file_key=file_key))

    @app.post("/sparql")
    async def sparql(request: Request):
        # robust parsing of body according to content-type
        content_type = request.headers.get("content-type", "")
        raw = await request.body()
        query = None
        # If the client sent a raw SPARQL query in the body
        if raw and ("application/sparql-query" in content_type or content_type.strip().startswith("sparql-query") or content_type.strip().startswith("application/sparql-query")):
            try:
                query = raw.decode("utf-8")
            except Exception:
                query = None
        else:
            # try JSON first (common for clients)
            if raw and "application/json" in content_type:
                try:
                    import json

                    parsed = json.loads(raw.decode("utf-8"))
                    if isinstance(parsed, dict):
                        query = parsed.get("query")
                except Exception:
                    # fall back to form parsing below
                    query = None
            # if not yet found, try form-encoded
            if query is None:
                try:
                    form = await request.form()
                    if hasattr(form, "get"):
                        query = form.get("query")
                except Exception:
                    # try query param
                    qp = request.query_params.get("query")
                    if qp:
                        query = qp
        if not query:
            raise HTTPException(status_code=400, detail="Missing SPARQL query")
        try:
            res = graph.query(query)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"SPARQL execution error: {e}")
        # handle different result types
        # ASK/SELECT/CONSTRUCT/DESCRIBE handling
        try:
            rtype = getattr(res, "type", None)
        except Exception:
            rtype = None
        # ASK
        if rtype == "ASK":
            try:
                # rdflib returns a boolean for ask
                return JSONResponse({"boolean": bool(res)})
            except Exception:
                return JSONResponse({"boolean": False})
        # SELECT → iterator with vars attribute
        if hasattr(res, "vars"):
            vars_list = [str(v) for v in res.vars]
            bindings = []
            for row in res:
                b = {}
                for i, v in enumerate(row):
                    varname = vars_list[i]
                    b[varname] = str(v) if v is not None else None
                bindings.append(b)
            return JSONResponse({"head": {"vars": vars_list}, "results": {"bindings": bindings}})
        # CONSTRUCT/DESCRIBE → res.graph
        try:
            g = None
            if hasattr(res, "graph") and res.graph is not None:
                g = res.graph
            elif isinstance(res, rdflib.Graph):
                g = res
            if g is not None:
                data = g.serialize(format="turtle")
                return PlainTextResponse(content=data, media_type="text/turtle; charset=utf-8")
        except Exception:
            pass
        # fallback
        return PlainTextResponse(content=str(res))

    # attach graph to app state for potential external use
    app.state.hdf_graph = graph
    app.state.hdf_filename = str(default_hdf_filename) if default_hdf_filename is not None else None
    app.state.hdf_files = {key: str(value) for key, value in hdf_files.items()}
    app.state.file_key = file_key

    return app


def run_server(host: str = "127.0.0.1",
               port: int = 8000,
               filename: Optional[str] = None,
               filenames: Optional[Sequence[Union[str, pathlib.Path]]] = None,
               structural: bool = True,
               contextual: bool = True,
               file_uri: Optional[str] = None):
    """Run a FastAPI/uvicorn server exposing RDF for HDF5 files."""
    if filenames is None:
        filenames = [filename] if filename is not None else None
    import uvicorn

    app = create_app(filenames, structural=structural, contextual=contextual, file_uri=file_uri)
    url = f"http://{host}:{port}/"
    logger.info("Starting h5rdmtoolbox RDF server at %s serving files %s", url, app.state.hdf_files)
    uvicorn.run(app, host=host, port=port)
