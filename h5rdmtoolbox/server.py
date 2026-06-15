import pathlib
import urllib.parse
import logging
from typing import Optional

import rdflib

from h5rdmtoolbox.ld import get_ld

logger = logging.getLogger(__name__)


def create_app(hdf_filename: pathlib.Path,
               structural: bool = True,
               contextual: bool = True,
               file_uri: Optional[str] = None):
    """Create a FastAPI app serving RDF extracted from a single HDF5 file.

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

    # Load graph once at startup
    graph = get_ld(hdf_filename, structural=structural, contextual=contextual, file_uri=file_uri)

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

    file_key = pathlib.Path(hdf_filename).stem

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
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

            with H5File(hdf_filename, mode='r') as fh:
                tree = fh.get_tree_structure(recursive=True)
            body = "<ul>"
            for key, node in tree.items():
                body += render_tree(key, node)
            body += "</ul>"
            page = f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\"> 
  <title>h5RDMtoolbox — {pathlib.Path(hdf_filename).name}</title>
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
            return HTMLResponse(tmpl.render(file_key=file_key, filename=str(hdf_filename)))

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
        return HTMLResponse(tmpl.render(filename=str(hdf_filename), file_key=file_key, turtle=ttl))

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
    app.state.hdf_filename = str(hdf_filename)
    app.state.file_key = file_key

    return app


def run_server(host: str = "127.0.0.1",
               port: int = 8000,
               filename: Optional[str] = None,
               structural: bool = True,
               contextual: bool = True,
               file_uri: Optional[str] = None):
    """Run a FastAPI/uvicorn server exposing RDF for the given file."""
    if filename is None:
        raise ValueError("filename must be provided to run the server")
    import uvicorn

    app = create_app(pathlib.Path(filename), structural=structural, contextual=contextual, file_uri=file_uri)
    url = f"http://{host}:{port}/"
    logger.info("Starting h5rdmtoolbox RDF server at %s serving file %s", url, filename)
    uvicorn.run(app, host=host, port=port)
