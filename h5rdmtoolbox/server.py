import pathlib
import re
import urllib.parse
import urllib.request
import urllib.error
import logging
import json
import fnmatch
import tempfile
from html import escape
from typing import Optional, Sequence, Union

import rdflib

from h5rdmtoolbox.ld import get_ld
from h5rdmtoolbox.ld.metrics import (
    bind_standard_prefixes as _bind_standard_prefixes,
    compute_graph_metrics,
    graph_label as _graph_label,
)

logger = logging.getLogger(__name__)
HDF5_SUFFIXES = {".h5", ".hdf", ".hdf5"}
COMBINED_METRICS_DISTANCE_NODE_LIMIT = 2000
COMBINED_GRAPH_NODE_LIMIT = 1000
COMBINED_GRAPH_EDGE_LIMIT = 2000
PREFIX_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
RDF_FORMATS = {
    "ttl": ("turtle", "text/turtle; charset=utf-8", "Turtle"),
    "jsonld": ("json-ld", "application/ld+json; charset=utf-8", "JSON-LD"),
    "nt": ("nt", "application/n-triples; charset=utf-8", "N-Triples"),
    "xml": ("xml", "application/rdf+xml; charset=utf-8", "RDF/XML"),
}
RESOURCE_FORMAT_ALIASES = {
    "html": "html",
    "ttl": "ttl",
    "turtle": "ttl",
    "json": "jsonld",
    "jsonld": "jsonld",
    "json-ld": "jsonld",
    "nt": "nt",
    "ntriples": "nt",
    "n-triples": "nt",
    "xml": "xml",
    "rdf": "xml",
    "rdfxml": "xml",
    "rdf+xml": "xml",
}
RDF_FILE_FORMATS = {
    ".ttl": "turtle",
    ".turtle": "turtle",
    ".jsonld": "json-ld",
    ".json-ld": "json-ld",
    ".rdf": "xml",
    ".xml": "xml",
    ".nt": "nt",
}
KNOWN_ONTOLOGY_SOURCES = {
    "https://matthiasprobst.github.io/ssno#": {
        "label": "Standard Name Ontology",
        "ttl": "https://matthiasprobst.github.io/ssno/ssno.ttl",
    },
    "https://matthiasprobst.github.io/ssno/#": {
        "label": "Standard Name Ontology",
        "ttl": "https://matthiasprobst.github.io/ssno/ssno.ttl",
    },
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": {
        "label": "RDF",
        "ttl": "https://www.w3.org/1999/02/22-rdf-syntax-ns.ttl",
    },
    "http://www.w3.org/2000/01/rdf-schema#": {
        "label": "RDFS",
        "ttl": "https://www.w3.org/2000/01/rdf-schema.ttl",
    },
    "http://www.w3.org/2002/07/owl#": {
        "label": "OWL",
        "ttl": "https://www.w3.org/2002/07/owl.ttl",
    },
    "http://www.w3.org/2004/02/skos/core#": {
        "label": "SKOS",
        "ttl": "https://www.w3.org/2009/08/skos-reference/skos.rdf",
    },
    "https://qudt.org/vocab/unit/": {
        "label": "QUDT units",
        "ttl_template": "{iri}.ttl",
        "scheme_aliases": ["http", "https"],
    },
    "http://qudt.org/vocab/unit/": {
        "label": "QUDT units",
        "ttl_template": "https://qudt.org/vocab/unit/{suffix}.ttl",
        "scheme_aliases": ["http", "https"],
    },
    "https://qudt.org/vocab/quantitykind/": {
        "label": "QUDT quantity kinds",
        "ttl_template": "{iri}.ttl",
        "scheme_aliases": ["http", "https"],
    },
    "http://qudt.org/vocab/quantitykind/": {
        "label": "QUDT quantity kinds",
        "ttl_template": "https://qudt.org/vocab/quantitykind/{suffix}.ttl",
        "scheme_aliases": ["http", "https"],
    },
}
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
DEFAULT_SPARQL_QUERY = """SELECT ?subject ?predicate ?object
WHERE {
  ?subject ?predicate ?object .
}
LIMIT 25"""
DEFAULT_SHACL_SHAPES = """@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

hdf:FileShape
  a sh:NodeShape ;
  sh:targetClass hdf:File ;
  sh:property [
    sh:path hdf:rootGroup ;
    sh:minCount 1 ;
  ] .
"""
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


def _normalize_hdf_extensions(extensions: Optional[Sequence[str]] = None) -> set[str]:
    """Return normalized HDF5 filename extensions."""
    if extensions is None:
        return set(HDF5_SUFFIXES)
    normalized = set()
    for extension in extensions:
        extension = str(extension).strip().lower()
        if not extension:
            raise ValueError("HDF5 extension values must not be empty")
        if not extension.startswith("."):
            extension = f".{extension}"
        normalized.add(extension)
    return normalized


def discover_hdf_files(directory: Union[str, pathlib.Path] = ".",
                       extensions: Optional[Sequence[str]] = None) -> list[pathlib.Path]:
    """Return HDF5 files in *directory* sorted by filename."""
    root = pathlib.Path(directory)
    hdf_extensions = _normalize_hdf_extensions(extensions)
    return sorted(
        (path for path in root.iterdir() if path.is_file() and path.suffix.lower() in hdf_extensions),
        key=lambda path: path.name.lower(),
    )


def _as_file_list(hdf_filenames: Optional[Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]],
                  extensions: Optional[Sequence[str]] = None) -> list[pathlib.Path]:
    if hdf_filenames is None:
        return discover_hdf_files(extensions=extensions)
    if isinstance(hdf_filenames, (str, pathlib.Path)):
        filenames = [hdf_filenames]
    else:
        filenames = list(hdf_filenames)
    files = []
    for filename in filenames:
        path = pathlib.Path(filename)
        if path.is_dir():
            files.extend(discover_hdf_files(path, extensions=extensions))
        else:
            files.append(path)
    return files


def _file_registry(hdf_filenames: Optional[Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]],
                   extensions: Optional[Sequence[str]] = None) -> dict[str, pathlib.Path]:
    registry = {}
    for filename in _as_file_list(hdf_filenames, extensions=extensions):
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


def create_app(hdf_filename: Optional[Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]] = None,
               structural: bool = True,
               contextual: bool = True,
               file_uri: Optional[str] = None,
               list_landing: bool = True,
               local_iri_patterns: Optional[Union[str, Sequence[str]]] = None,
               h5_extensions: Optional[Sequence[str]] = None):
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
    hdf_files = _file_registry(hdf_filename, extensions=h5_extensions)
    default_hdf_filename = next(iter(hdf_files.values()), None)
    server_graph = rdflib.Graph()
    hdf_graph_cache: dict[pathlib.Path, rdflib.Graph] = {}
    local_subject_index: dict[str, tuple[object, rdflib.Graph]] = {}
    server_graph_version = 0
    combined_metrics_cache: Optional[tuple[int, int, dict[str, object]]] = None

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
    if local_iri_patterns is None:
        local_iri_pattern_list = []
    elif isinstance(local_iri_patterns, str):
        local_iri_pattern_list = [local_iri_patterns]
    else:
        local_iri_pattern_list = list(local_iri_patterns)

    def _matches_local_iri_pattern(iri: str) -> bool:
        return any(fnmatch.fnmatchcase(iri, pattern) for pattern in local_iri_pattern_list)

    def _local_iri_href(iri: str) -> str:
        if local_iri_pattern_list and not _matches_local_iri_pattern(iri):
            return ""
        return f"/resolve?iri={urllib.parse.quote(iri, safe='')}"

    def _subject_subgraph(rdf_graph: rdflib.Graph, subject) -> rdflib.Graph:
        subgraph = rdflib.Graph()
        for ns_prefix, namespace in rdf_graph.namespaces():
            subgraph.bind(ns_prefix, namespace)
        for triple in rdf_graph.triples((subject, None, None)):
            subgraph.add(triple)
        return subgraph

    def _merge_graph(target_graph: rdflib.Graph, source_graph: Optional[rdflib.Graph]) -> None:
        nonlocal server_graph_version, combined_metrics_cache
        if source_graph is None:
            return
        before = len(target_graph)
        for ns_prefix, namespace in source_graph.namespaces():
            target_graph.bind(ns_prefix, namespace)
        for triple in source_graph:
            target_graph.add(triple)
        if target_graph is server_graph and len(target_graph) != before:
            server_graph_version += 1
            combined_metrics_cache = None

    def _index_first_local_subjects(rdf_graph: rdflib.Graph) -> None:
        for subject in rdf_graph.subjects():
            subject_key = str(subject)
            if subject_key not in local_subject_index:
                local_subject_index[subject_key] = (subject, _subject_subgraph(rdf_graph, subject))

    def _load_hdf_graph(filename: pathlib.Path) -> rdflib.Graph:
        filename = pathlib.Path(filename)
        if filename in hdf_graph_cache:
            return hdf_graph_cache[filename]
        rdf_graph = get_ld(
            filename,
            structural=structural,
            contextual=contextual,
            file_uri=create_app_file_uri,
        )
        _bind_standard_prefixes(rdf_graph)
        hdf_graph_cache[filename] = rdf_graph
        _merge_graph(server_graph, rdf_graph)
        _index_first_local_subjects(rdf_graph)
        logger.info("Loaded served HDF5 RDF graph %s with %d triples", filename, len(rdf_graph))
        return rdf_graph

    for hdf_file in hdf_files.values():
        _load_hdf_graph(hdf_file)

    graph = server_graph

    zenodo_graph_cache: dict[str, list[rdflib.Graph]] = {}
    ontology_graph_cache: dict[str, Optional[rdflib.Graph]] = {}
    known_ontology_graph_cache: dict[str, Optional[rdflib.Graph]] = {}
    wikidata_graph_cache: dict[str, Optional[rdflib.Graph]] = {}

    def _zenodo_record_info(iri: str) -> Optional[tuple[str, str]]:
        parsed = urllib.parse.urlparse(iri)
        if not parsed.fragment:
            return None
        host = parsed.netloc.lower()
        path = parsed.path.strip("/")
        if host == "doi.org":
            match = re.match(r"(?P<prefix>10\.\d+)/zenodo\.(?P<record_id>\d+)$", path)
            if not match:
                return None
            api_host = "sandbox.zenodo.org" if match.group("prefix") == "10.5072" else "zenodo.org"
            return api_host, match.group("record_id")
        if host in {"zenodo.org", "www.zenodo.org", "sandbox.zenodo.org"}:
            match = re.match(r"(?:records|record)/(?P<record_id>\d+)$", path)
            if match:
                api_host = "sandbox.zenodo.org" if "sandbox" in host else "zenodo.org"
                return api_host, match.group("record_id")
        return None

    def _rdf_download_format(filename_or_url: str) -> Optional[str]:
        suffix = pathlib.Path(urllib.parse.urlparse(filename_or_url).path).suffix.lower()
        return RDF_FILE_FORMATS.get(suffix)

    def _zenodo_download_url(file_record: dict) -> Optional[str]:
        links = file_record.get("links") or {}
        return links.get("self") or links.get("download")

    def _load_zenodo_graphs(api_host: str, record_id: str) -> list[rdflib.Graph]:
        cache_key = f"{api_host}:{record_id}"
        if cache_key in zenodo_graph_cache:
            return zenodo_graph_cache[cache_key]

        api_url = f"https://{api_host}/api/records/{record_id}"
        try:
            with urllib.request.urlopen(api_url, timeout=10) as response:
                record = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=502, detail=f"Could not load Zenodo record metadata: {e}") from e

        cache_dir = pathlib.Path(tempfile.gettempdir()) / "h5rdmtoolbox-zenodo-rdf" / api_host / record_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        graphs = []
        for index, file_record in enumerate(record.get("files", [])):
            filename = file_record.get("key") or file_record.get("filename") or f"zenodo-rdf-{index}"
            download_url = _zenodo_download_url(file_record)
            rdf_format = _rdf_download_format(filename) or _rdf_download_format(download_url or "")
            if not download_url or rdf_format is None:
                continue
            target = cache_dir / pathlib.Path(filename).name
            try:
                if not target.exists():
                    with urllib.request.urlopen(download_url, timeout=20) as response:
                        target.write_bytes(response.read())
                graph_from_file = rdflib.Graph()
                graph_from_file.parse(target, format=rdf_format)
            except (urllib.error.URLError, TimeoutError, OSError, Exception) as e:
                logger.warning("Could not load RDF file %s from Zenodo record %s: %s", filename, record_id, e)
                continue
            _bind_standard_prefixes(graph_from_file)
            _merge_graph(server_graph, graph_from_file)
            graphs.append(graph_from_file)
        zenodo_graph_cache[cache_key] = graphs
        return graphs

    def _find_zenodo_subject_graph(iri: str) -> Optional[rdflib.Graph]:
        record_info = _zenodo_record_info(iri)
        if record_info is None:
            return None
        subject = rdflib.URIRef(iri)
        api_host, record_id = record_info
        for candidate_graph in _load_zenodo_graphs(api_host, record_id):
            if (subject, None, None) in candidate_graph:
                return _subject_subgraph(candidate_graph, subject)
        return None

    def _subject_candidates(iri: str) -> list[rdflib.URIRef]:
        parsed = urllib.parse.urlparse(iri)
        candidates = [rdflib.URIRef(iri)]
        if parsed.fragment and parsed.path and not pathlib.Path(parsed.path).suffix:
            alternate_path = parsed.path.rstrip("/") if parsed.path.endswith("/") else f"{parsed.path}/"
            alternate_iri = urllib.parse.urlunparse(parsed._replace(path=alternate_path))
            if alternate_iri != iri:
                candidates.append(rdflib.URIRef(alternate_iri))
        return candidates

    def _known_ontology_url(base_iri: str, ontology_info: dict, iri: str) -> str:
        if "ttl" in ontology_info:
            return ontology_info["ttl"]
        suffix = iri[len(base_iri):]
        return ontology_info["ttl_template"].format(iri=iri, suffix=suffix)

    def _known_ontology_subject_candidates(iri: str, ontology_info: dict) -> list[rdflib.URIRef]:
        candidates = _subject_candidates(iri)
        scheme_aliases = ontology_info.get("scheme_aliases", [])
        if scheme_aliases:
            for subject in list(candidates):
                parsed = urllib.parse.urlparse(str(subject))
                if parsed.scheme not in {"http", "https"}:
                    continue
                for scheme in scheme_aliases:
                    alias = urllib.parse.urlunparse(parsed._replace(scheme=scheme))
                    candidates.append(rdflib.URIRef(alias))
        unique_candidates = []
        seen = set()
        for candidate in candidates:
            if str(candidate) in seen:
                continue
            seen.add(str(candidate))
            unique_candidates.append(candidate)
        return unique_candidates

    def _load_known_ontology_graph(base_iri: str, ontology_info: dict, iri: str) -> Optional[rdflib.Graph]:
        ttl_url = _known_ontology_url(base_iri, ontology_info, iri)
        cache_key = f"{base_iri}|{ttl_url}"
        if cache_key in known_ontology_graph_cache:
            logger.info(
                "Using cached known ontology %s: %s",
                ttl_url,
                "hit" if known_ontology_graph_cache[cache_key] is not None else "miss",
            )
            return known_ontology_graph_cache[cache_key]
        logger.info("Loading known ontology %s from %s", ontology_info.get("label", base_iri), ttl_url)
        try:
            with urllib.request.urlopen(ttl_url, timeout=15) as response:
                data = response.read()
                response_url = response.geturl() if hasattr(response, "geturl") else ttl_url
        except (urllib.error.URLError, TimeoutError) as e:
            logger.warning("Could not load known ontology %s from %s: %s", base_iri, ttl_url, e)
            known_ontology_graph_cache[cache_key] = None
            return None
        graph_from_doc = _parse_rdf_bytes(data, response_url)
        _merge_graph(server_graph, graph_from_doc)
        known_ontology_graph_cache[cache_key] = graph_from_doc
        return graph_from_doc

    def _find_known_ontology_subject_graph(iri: str) -> Optional[rdflib.Graph]:
        matching_sources = [
            (base_iri, ontology_info)
            for base_iri, ontology_info in sorted(KNOWN_ONTOLOGY_SOURCES.items(), key=lambda item: len(item[0]), reverse=True)
            if iri.startswith(base_iri)
        ]
        if not matching_sources:
            return None
        logger.info(
            "Known ontology candidates for %s: %s",
            iri,
            [ontology_info.get("label", base_iri) for base_iri, ontology_info in matching_sources],
        )
        for base_iri, ontology_info in matching_sources:
            subject_candidates = _known_ontology_subject_candidates(iri, ontology_info)
            logger.info(
                "Known ontology subject candidates for %s in %s: %s",
                iri,
                ontology_info.get("label", base_iri),
                [str(subject) for subject in subject_candidates],
            )
            graph_from_doc = _load_known_ontology_graph(base_iri, ontology_info, iri)
            if graph_from_doc is None:
                continue
            for subject in subject_candidates:
                if (subject, None, None) in graph_from_doc:
                    logger.info("Found known ontology subject %s in %s", subject, ontology_info.get("label", base_iri))
                    return _subject_subgraph(graph_from_doc, subject)
            logger.info(
                "Known ontology %s has %d triples but no subject candidates matched %s",
                ontology_info.get("label", base_iri),
                len(graph_from_doc),
                [str(subject) for subject in subject_candidates],
            )
        return None

    def _ontology_document_urls(iri: str) -> list[str]:
        parsed = urllib.parse.urlparse(iri)
        if not parsed.fragment or parsed.scheme not in {"http", "https"}:
            return []
        if _zenodo_record_info(iri) is not None:
            return []
        document_url = urllib.parse.urlunparse(parsed._replace(fragment=""))
        suffix = pathlib.Path(parsed.path).suffix
        if parsed.path and not parsed.path.endswith("/") and not suffix:
            slash_url = urllib.parse.urlunparse(parsed._replace(path=f"{parsed.path}/", fragment=""))
            return [slash_url, document_url]
        return [document_url]

    def _parse_rdf_bytes(data: bytes, source_url: str) -> Optional[rdflib.Graph]:
        suffix_format = _rdf_download_format(source_url)
        formats = [fmt for fmt in [suffix_format, "turtle", "xml", "json-ld", "nt"] if fmt]
        seen_formats = set()
        logger.info("Trying to parse RDF document %s (%d bytes) as %s", source_url, len(data), formats)
        for rdf_format in formats:
            if rdf_format in seen_formats:
                continue
            seen_formats.add(rdf_format)
            graph_from_doc = rdflib.Graph()
            try:
                graph_from_doc.parse(data=data, format=rdf_format, publicID=source_url)
            except Exception as e:
                logger.info("Could not parse %s as %s: %s", source_url, rdf_format, e)
                continue
            _bind_standard_prefixes(graph_from_doc)
            logger.info("Parsed %s as %s with %d triples", source_url, rdf_format, len(graph_from_doc))
            return graph_from_doc
        logger.info("No RDF parser succeeded for %s", source_url)
        return None

    def _rdf_links_from_html(data: bytes, document_url: str) -> list[str]:
        try:
            html = data.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.info("Could not decode ontology HTML from %s: %s", document_url, e)
            return []
        links = []
        for href in re.findall(r"""href=["']([^"']+)["']""", html, flags=re.IGNORECASE):
            resolved = urllib.parse.urljoin(document_url, href)
            if _rdf_download_format(resolved):
                links.append(resolved)
        logger.info("Found %d linked RDF serialization candidates in %s: %s", len(links), document_url, links[:10])
        return links

    def _load_ontology_graph(document_url: str) -> Optional[rdflib.Graph]:
        if document_url in ontology_graph_cache:
            logger.info("Using cached ontology document %s: %s", document_url, "hit" if ontology_graph_cache[document_url] is not None else "miss")
            return ontology_graph_cache[document_url]
        logger.info("Loading ontology document %s", document_url)
        request = urllib.request.Request(
            document_url,
            headers={
                "Accept": (
                    "text/turtle, application/ld+json;q=0.9, "
                    "application/rdf+xml;q=0.8, application/n-triples;q=0.7"
                )
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read()
                response_url = response.geturl() if hasattr(response, "geturl") else document_url
                content_type = response.headers.get("Content-Type", "") if hasattr(response, "headers") else ""
                logger.info("Loaded ontology document %s via %s, content-type=%s, bytes=%d", document_url, response_url, content_type, len(data))
        except (urllib.error.URLError, TimeoutError) as e:
            logger.warning("Could not load ontology document %s: %s", document_url, e)
            ontology_graph_cache[document_url] = None
            return None
        graph_from_doc = _parse_rdf_bytes(data, response_url)
        if graph_from_doc is None:
            for rdf_url in _rdf_links_from_html(data, response_url):
                logger.info("Loading linked RDF serialization %s from ontology page %s", rdf_url, document_url)
                try:
                    with urllib.request.urlopen(rdf_url, timeout=15) as rdf_response:
                        rdf_data = rdf_response.read()
                        rdf_response_url = rdf_response.geturl() if hasattr(rdf_response, "geturl") else rdf_url
                        rdf_content_type = rdf_response.headers.get("Content-Type", "") if hasattr(rdf_response, "headers") else ""
                        logger.info("Loaded linked RDF serialization %s via %s, content-type=%s, bytes=%d", rdf_url, rdf_response_url, rdf_content_type, len(rdf_data))
                except (urllib.error.URLError, TimeoutError) as e:
                    logger.warning("Could not load RDF serialization %s linked from %s: %s", rdf_url, document_url, e)
                    continue
                graph_from_doc = _parse_rdf_bytes(rdf_data, rdf_response_url)
                if graph_from_doc is not None:
                    break
        if graph_from_doc is None:
            logger.info("No RDF graph could be extracted from ontology document %s", document_url)
        _merge_graph(server_graph, graph_from_doc)
        ontology_graph_cache[document_url] = graph_from_doc
        return graph_from_doc

    def _find_ontology_subject_graph(iri: str) -> Optional[rdflib.Graph]:
        subject_candidates = _subject_candidates(iri)
        document_urls = _ontology_document_urls(iri)
        logger.info("Ontology enrichment candidates for %s: %s", iri, document_urls)
        logger.info("Ontology subject candidates for %s: %s", iri, [str(subject) for subject in subject_candidates])
        for document_url in document_urls:
            graph_from_doc = _load_ontology_graph(document_url)
            if graph_from_doc is not None:
                for subject in subject_candidates:
                    if (subject, None, None) in graph_from_doc:
                        logger.info("Found ontology subject %s in %s", subject, document_url)
                        return _subject_subgraph(graph_from_doc, subject)
                logger.info(
                    "Ontology graph %s has %d triples but none of the subject candidates matched %s",
                    document_url,
                    len(graph_from_doc),
                    [str(subject) for subject in subject_candidates],
                )
        return None

    def _wikidata_entity_id(iri: str) -> Optional[str]:
        parsed = urllib.parse.urlparse(iri)
        host = parsed.netloc.lower()
        path = parsed.path.strip("/")
        if host == "www.wikidata.org" and path.startswith("wiki/"):
            entity_id = path.rsplit("/", 1)[-1]
        elif host == "www.wikidata.org" and path.startswith("entity/"):
            entity_id = path.rsplit("/", 1)[-1]
        elif host == "www.wikidata.org" and path.startswith("prop/direct/"):
            return None
        elif host == "www.wikidata.org":
            return None
        else:
            return None
        return entity_id if re.match(r"^Q\d+$", entity_id) else None

    def _wikidata_value_to_term(value_binding: dict):
        value = value_binding.get("value", "")
        value_type = value_binding.get("type", "")
        datatype = value_binding.get("datatype")
        if value_type == "uri":
            return rdflib.URIRef(value)
        if datatype:
            return rdflib.Literal(value, datatype=rdflib.URIRef(datatype))
        return rdflib.Literal(value)

    def _load_wikidata_graph(entity_id: str, display_iri: str) -> Optional[rdflib.Graph]:
        if entity_id in wikidata_graph_cache:
            logger.info("Using cached Wikidata entity %s: %s", entity_id, "hit" if wikidata_graph_cache[entity_id] is not None else "miss")
            return wikidata_graph_cache[entity_id]
        query = f"""SELECT ?property ?value
WHERE {{
  wd:{entity_id} ?property ?value .
  FILTER(STRSTARTS(STR(?property), "http://www.wikidata.org/prop/direct/"))
}}
LIMIT 100"""
        params = urllib.parse.urlencode({"query": query, "format": "json"})
        request = urllib.request.Request(
            f"{WIKIDATA_SPARQL_URL}?{params}",
            headers={"Accept": "application/sparql-results+json"},
        )
        logger.info("Loading Wikidata direct claims for %s", entity_id)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                results = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            logger.warning("Could not load Wikidata entity %s: %s", entity_id, e)
            wikidata_graph_cache[entity_id] = None
            return None
        graph_from_doc = rdflib.Graph()
        subject = rdflib.URIRef(display_iri)
        for row in results.get("results", {}).get("bindings", []):
            property_binding = row.get("property", {})
            value_binding = row.get("value", {})
            property_iri = property_binding.get("value")
            if not property_iri or not value_binding:
                continue
            graph_from_doc.add((subject, rdflib.URIRef(property_iri), _wikidata_value_to_term(value_binding)))
        _bind_standard_prefixes(graph_from_doc)
        _merge_graph(server_graph, graph_from_doc)
        wikidata_graph_cache[entity_id] = graph_from_doc
        logger.info("Loaded Wikidata entity %s with %d direct claims", entity_id, len(graph_from_doc))
        return graph_from_doc

    def _find_wikidata_subject_graph(iri: str) -> Optional[rdflib.Graph]:
        entity_id = _wikidata_entity_id(iri)
        if entity_id is None:
            return None
        graph_from_doc = _load_wikidata_graph(entity_id, iri)
        subject = rdflib.URIRef(iri)
        if graph_from_doc is not None and (subject, None, None) in graph_from_doc:
            return _subject_subgraph(graph_from_doc, subject)
        return None

    def _resource_format(request: Request, format: Optional[str] = None) -> str:
        if format:
            try:
                return RESOURCE_FORMAT_ALIASES[format.lower()]
            except KeyError as e:
                raise HTTPException(status_code=400, detail="Unknown resource format") from e
        accept = request.headers.get("accept", "")
        if "text/turtle" in accept or "application/x-turtle" in accept:
            return "ttl"
        if "application/ld+json" in accept:
            return "jsonld"
        if "application/n-triples" in accept or "text/plain" in accept:
            return "nt"
        if "application/rdf+xml" in accept:
            return "xml"
        if "text/html" in accept:
            return "html"
        return "html"

    def _resource_format_href(request: Request, format_key: str) -> str:
        params = dict(request.query_params)
        params["format"] = format_key
        return f"{request.url.path}?{urllib.parse.urlencode(params)}"

    def _resource_html(subject, subgraph: rdflib.Graph, request: Request) -> HTMLResponse:
        def _object_html(obj) -> str:
            object_label = _graph_label(obj, subgraph) if not isinstance(obj, rdflib.Literal) else str(obj)
            if isinstance(obj, rdflib.URIRef):
                object_href = f"/resolve?iri={urllib.parse.quote(str(obj), safe='')}"
                return f'<a href="{object_href}">{escape(object_label)}</a>'
            return escape(object_label)

        grouped_objects = {}
        for _, predicate, obj in subgraph:
            grouped_objects.setdefault(predicate, []).append(obj)
        rows = []
        for predicate in sorted(grouped_objects, key=lambda term: _graph_label(term, subgraph)):
            object_items = sorted(
                grouped_objects[predicate],
                key=lambda term: _graph_label(term, subgraph) if not isinstance(term, rdflib.Literal) else str(term),
            )
            object_html = "".join(f"<li>{_object_html(obj)}</li>" for obj in object_items)
            rows.append(
                f'<tr><td>{escape(_graph_label(predicate, subgraph))}</td><td><ul class="object-list">{object_html}</ul></td></tr>'
            )
        table = (
            '<table class="resource-table"><thead><tr><th>Predicate</th><th>Object</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
            if rows
            else '<p class="empty-result">No triples are available for this subject.</p>'
        )
        format_links = "".join(
            f'<a href="{escape(_resource_format_href(request, key))}">{escape(label)}</a>'
            for key, (_, _, label) in RDF_FORMATS.items()
        )
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(_graph_label(subject, subgraph))}</title>
  <style>
    :root {{ --bg: #f7f8fa; --panel: #fff; --text: #1f2933; --muted: #667085; --border: #d8dee6; --accent: #0b6f85; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    main {{ width: min(960px, calc(100% - 32px)); margin: 28px auto; display: grid; gap: 14px; }}
    header, section {{ padding: 16px; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; }}
    nav {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }}
    nav a, .format-links a {{ color: var(--accent); font-weight: 650; text-decoration: none; }}
    h1 {{ margin: 0 0 8px; font-size: 1.35rem; overflow-wrap: anywhere; }}
    code {{ overflow-wrap: anywhere; color: var(--muted); }}
    .format-links {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .resource-table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 8px 6px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ color: var(--muted); font-size: 0.85rem; }}
    td:first-child {{ width: 34%; color: var(--muted); }}
    .object-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }}
    .empty-result {{ color: var(--muted); }}
  </style>
</head>
<body>
<main>
  <header>
    <nav><a href="/">Files</a></nav>
    <h1>{escape(_graph_label(subject, subgraph))}</h1>
    <code>{escape(str(subject))}</code>
  </header>
  <section class="format-links">{format_links}</section>
  <section>{table}</section>
</main>
</body>
</html>
"""
        return HTMLResponse(page)

    def _external_iri_fallback_html(iri: str) -> HTMLResponse:
        iri_json = json.dumps(iri)
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>External IRI</title>
  <style>
    :root {{ --bg: #f7f8fa; --panel: #fff; --text: #1f2933; --muted: #667085; --border: #d8dee6; --accent: #0b6f85; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    main {{ width: min(760px, calc(100% - 32px)); margin: 40px auto; display: grid; gap: 14px; }}
    section {{ padding: 18px; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; }}
    h1 {{ margin: 0 0 10px; font-size: 1.35rem; }}
    p {{ margin: 8px 0; color: var(--muted); line-height: 1.5; }}
    code {{ display: block; padding: 10px; background: #eef2f6; border-radius: 6px; overflow-wrap: anywhere; color: var(--text); }}
    a.button {{ display: inline-flex; margin-top: 12px; padding: 9px 12px; border-radius: 6px; background: var(--accent); color: white; font-weight: 650; text-decoration: none; }}
  </style>
</head>
<body>
<main>
  <section>
    <h1>External IRI</h1>
    <p>No RDF description was found in the served files or configured enrichment sources. The original URL is being opened in a new tab.</p>
    <code>{escape(iri)}</code>
    <a class="button" href="{escape(iri)}" target="_blank" rel="noopener noreferrer">Open external URL</a>
  </section>
</main>
<script>
  window.open({iri_json}, "_blank", "noopener,noreferrer");
</script>
</body>
</html>
"""
        return HTMLResponse(page)

    def _resource_response(subject, subgraph: rdflib.Graph, request: Request, format: Optional[str] = None):
        format_key = _resource_format(request, format)
        if format_key == "html":
            return _resource_html(subject, subgraph, request)
        rdflib_format, media_type, _ = RDF_FORMATS[format_key]
        return PlainTextResponse(content=subgraph.serialize(format=rdflib_format), media_type=media_type)

    def _resolve_iri_response(iri: str, request: Request, format: Optional[str] = None):

        logger.info("Resolving IRI %s with requested format=%s accept=%s", iri, format, request.headers.get("accept", ""))
        subject = rdflib.URIRef(iri)
        merged_subgraph = rdflib.Graph()
        found_local_subject = False
        found_cached_subject = False
        indexed_subject = local_subject_index.get(iri)
        if indexed_subject is not None:
            _, subgraph = indexed_subject
            logger.info("Using first local subject occurrence %s from shared server graph", iri)
            _merge_graph(merged_subgraph, subgraph)
            found_local_subject = True
        elif (subject, None, None) in server_graph:
            logger.info("Using cached enriched subject %s from shared server graph", iri)
            subgraph = _subject_subgraph(server_graph, subject)
            _merge_graph(merged_subgraph, subgraph)
            found_cached_subject = True
        try:
            known_ontology_subgraph = _find_known_ontology_subject_graph(iri)
        except HTTPException:
            if found_local_subject:
                return _resource_response(subject, merged_subgraph, request, format=format)
            raise
        if known_ontology_subgraph is not None:
            for triple in known_ontology_subgraph:
                merged_subgraph.add(triple)
            for ns_prefix, namespace in known_ontology_subgraph.namespaces():
                merged_subgraph.bind(ns_prefix, namespace)
        try:
            external_subgraph = _find_zenodo_subject_graph(iri)
        except HTTPException:
            if found_local_subject:
                return _resource_response(subject, merged_subgraph, request, format=format)
            raise
        if external_subgraph is not None:
            for triple in external_subgraph:
                merged_subgraph.add(triple)
            for ns_prefix, namespace in external_subgraph.namespaces():
                merged_subgraph.bind(ns_prefix, namespace)
        ontology_subgraph = None
        if known_ontology_subgraph is None:
            ontology_subgraph = _find_ontology_subject_graph(iri)
        if ontology_subgraph is not None:
            for triple in ontology_subgraph:
                merged_subgraph.add(triple)
            for ns_prefix, namespace in ontology_subgraph.namespaces():
                merged_subgraph.bind(ns_prefix, namespace)
        wikidata_subgraph = _find_wikidata_subject_graph(iri)
        if wikidata_subgraph is not None:
            for triple in wikidata_subgraph:
                merged_subgraph.add(triple)
            for ns_prefix, namespace in wikidata_subgraph.namespaces():
                merged_subgraph.bind(ns_prefix, namespace)
        if (
            found_local_subject
            or found_cached_subject
            or known_ontology_subgraph is not None
            or external_subgraph is not None
            or ontology_subgraph is not None
            or wikidata_subgraph is not None
        ):
            logger.info("Resolved IRI %s with %d triples", iri, len(merged_subgraph))
            return _resource_response(subject, merged_subgraph, request, format=format)
        logger.info("IRI %s could not be resolved from local graph, known ontologies, Zenodo, ontology document, or Wikidata", iri)
        if _resource_format(request, format) == "html":
            logger.info("Returning external IRI fallback page for %s", iri)
            return _external_iri_fallback_html(iri)
        raise HTTPException(status_code=404, detail="Unknown RDF subject")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, resolve: Optional[str] = None, format: Optional[str] = None):
        if resolve:
            return _resolve_iri_response(resolve, request, format=format)
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
                shacl_link = f'<a class="format-link shacl-link" href="/{encoded_key}/shacl">SHACL</a>'
                file_cards.append(f"""<article class="file-card">
  <div>
    <h2>{escape(key)}</h2>
    <p>{escape(str(hdf_files[key]))}</p>
  </div>
  <div class="format-actions">{format_links}{graph_link}{query_link}{metrics_link}{shacl_link}</div>
</article>""")
            body = (
                '<section class="empty">No HDF5 files found in this directory.</section>'
                if not file_cards
                else f'<section class="file-list">{"".join(file_cards)}</section>'
            )
            combined_format_links = "".join(
                f'<a class="format-link" href="/combined/{format_key}">{escape(label)}</a>'
                for format_key, (_, _, label) in RDF_FORMATS.items()
            )
            combined_actions = (
                f'{combined_format_links}'
                '<a class="format-link graph-link" href="/combined/graph">Graph</a>'
                '<a class="format-link query-link" href="/combined/query">Query</a>'
                '<a class="format-link metrics-link" href="/combined/metrics">Metrics</a>'
                '<a class="format-link shacl-link" href="/combined/shacl">SHACL</a>'
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
    .combined-card {{
      display: grid;
      gap: 10px;
      margin-bottom: 16px;
      padding: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    .combined-card h2 {{
      margin: 0 0 4px;
      font-size: 1rem;
      font-weight: 650;
    }}
    .combined-card p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.875rem;
    }}
    .resolve-form {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
      padding: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    .resolve-form input {{
      flex: 1 1 360px;
      min-height: 36px;
      min-width: 0;
      padding: 0 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font: inherit;
    }}
    .resolve-form button {{
      min-height: 36px;
      padding: 0 14px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      font-weight: 650;
      cursor: pointer;
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
  <section class="combined-card">
    <div>
      <h2>Combined graph</h2>
      <p>All served files plus RDF enrichment loaded during browsing.</p>
    </div>
    <div class="format-actions">{combined_actions}</div>
  </section>
  <form class="resolve-form" action="/resolve" method="get">
    <input type="url" name="iri" placeholder="https://doi.org/10.5072/zenodo.403669#observable_property/T1" aria-label="IRI to resolve">
    <button type="submit">Resolve</button>
  </form>
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
        return "html"

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

    def _is_ontology_term(term) -> bool:
        text = str(term)
        ontology_prefixes = (
            "http://www.w3.org/",
            "https://www.w3.org/",
            "http://purl.org/dc/",
            "http://purl.org/dc/terms/",
            "http://xmlns.com/foaf/",
            "http://qudt.org/",
            "https://qudt.org/",
            "https://matthiasprobst.github.io/ssno",
        )
        return any(text.startswith(prefix) for prefix in ontology_prefixes)

    def _graph_data(rdf_graph: rdflib.Graph,
                    limit_nodes: Optional[int] = None,
                    limit_edges: Optional[int] = None,
                    q: Optional[str] = None,
                    include_ontology: bool = True,
                    include_isolated: bool = True,
                    focus: Optional[str] = None,
                    depth: int = 1,
                    labels: str = "auto") -> dict[str, object]:
        if labels not in {"auto", "on", "off"}:
            raise HTTPException(status_code=400, detail="labels must be one of: auto, on, off")
        depth = max(1, min(int(depth), 2))
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
        node_terms = set()
        resource_edges = []
        literal_values = {}
        degree_counts = {}
        search = (q or "").strip().lower()
        focus = (focus or "").strip()

        for subject, predicate, obj in rdf_graph:
            if not include_ontology and (_is_ontology_term(subject) or _is_ontology_term(obj)):
                continue
            node_terms.add(subject)
            if isinstance(obj, rdflib.Literal):
                literal_values.setdefault(subject, []).append((predicate, obj))
                continue
            node_terms.add(obj)
            resource_edges.append((subject, predicate, obj))
            degree_counts[subject] = degree_counts.get(subject, 0) + 1
            degree_counts[obj] = degree_counts.get(obj, 0) + 1

        if not include_isolated:
            node_terms = {node for node in node_terms if degree_counts.get(node, 0) > 0}

        if focus:
            term_by_id = {str(term): term for term in node_terms}
            focus_term = term_by_id.get(focus)
            if focus_term is None:
                matched_focus_terms = [
                    term for term in node_terms
                    if focus in str(term) or focus.lower() == _graph_label(term, rdf_graph).lower()
                ]
                focus_term = matched_focus_terms[0] if matched_focus_terms else None
            if focus_term is None:
                selected_terms = set()
            else:
                selected_terms = {focus_term}
                frontier = {focus_term}
                for _ in range(depth):
                    next_frontier = set()
                    for subject, _, obj in resource_edges:
                        if subject in frontier:
                            next_frontier.add(obj)
                        if obj in frontier:
                            next_frontier.add(subject)
                    next_frontier.difference_update(selected_terms)
                    selected_terms.update(next_frontier)
                    frontier = next_frontier
                    if not frontier:
                        break
        elif search:
            matched_nodes = {
                node for node in node_terms
                if search in str(node).lower() or search in _graph_label(node, rdf_graph).lower()
            }
            neighbor_nodes = set(matched_nodes)
            for subject, _, obj in resource_edges:
                if subject in matched_nodes or obj in matched_nodes:
                    neighbor_nodes.add(subject)
                    neighbor_nodes.add(obj)
            selected_terms = neighbor_nodes
        else:
            selected_terms = set(node_terms)

        total_nodes = len(selected_terms)
        if limit_nodes is not None and len(selected_terms) > limit_nodes:
            selected_terms = set(sorted(
                selected_terms,
                key=lambda term: (-degree_counts.get(term, 0), _graph_label(term, rdf_graph), str(term)),
            )[:limit_nodes])

        nodes = {}
        edges = []
        visible_degree_counts = {term: 0 for term in selected_terms}

        def node_group(value) -> str:
            class_label = type_by_node.get(str(value))
            if class_label:
                return f"class:{class_label}"
            return "resource" if isinstance(value, rdflib.URIRef) else "blank"

        for subject in sorted(selected_terms, key=lambda term: _graph_label(term, rdf_graph)):
            subject_id = str(subject)
            nodes.setdefault(subject_id, {
                "id": subject_id,
                "label": _graph_label(subject, rdf_graph),
                "group": node_group(subject),
                "rdf_class": type_by_node.get(subject_id, ""),
                "local_href": _local_iri_href(subject_id) if isinstance(subject, rdflib.URIRef) else "",
                "degree": degree_counts.get(subject, 0),
                "shown_neighbor_count": 0,
                "hidden_neighbor_count": 0,
                "expandable": False,
                "literals": [],
            })
            for predicate, obj in literal_values.get(subject, []):
                nodes[subject_id]["literals"].append({
                    "predicate": _graph_label(predicate, rdf_graph),
                    "value": str(obj),
                })
        total_edges = 0
        for subject, predicate, obj in resource_edges:
            if subject not in selected_terms or obj not in selected_terms:
                continue
            total_edges += 1
            visible_degree_counts[subject] = visible_degree_counts.get(subject, 0) + 1
            visible_degree_counts[obj] = visible_degree_counts.get(obj, 0) + 1
            if limit_edges is not None and len(edges) >= limit_edges:
                continue
            subject_id = str(subject)
            object_id = str(obj)
            edges.append({
                "from": subject_id,
                "to": object_id,
                "label": _graph_label(predicate, rdf_graph),
                "arrows": "to",
            })
        for subject in selected_terms:
            subject_id = str(subject)
            if subject_id not in nodes:
                continue
            shown_neighbors = visible_degree_counts.get(subject, 0)
            hidden_neighbors = max(degree_counts.get(subject, 0) - shown_neighbors, 0)
            nodes[subject_id]["shown_neighbor_count"] = shown_neighbors
            nodes[subject_id]["hidden_neighbor_count"] = hidden_neighbors
            nodes[subject_id]["expandable"] = hidden_neighbors > 0
        rendered_labels = labels
        if rendered_labels == "auto":
            rendered_labels = "off" if len(nodes) > 250 or len(edges) > 500 else "on"
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "groups": groups,
            "summary": {
                "total_nodes": total_nodes,
                "shown_nodes": len(nodes),
                "total_edges": total_edges,
                "shown_edges": len(edges),
                "truncated": len(nodes) < total_nodes or len(edges) < total_edges,
                "labels": labels,
                "rendered_labels": rendered_labels,
                "focus": focus,
                "depth": depth,
            },
        }

    def _graph_response(filename: pathlib.Path,
                        mode: str = "both",
                        file_uri: Optional[str] = None,
                        prefix: Optional[str] = None,
                        rdf_graph: Optional[rdflib.Graph] = None,
                        limit_nodes: Optional[int] = None,
                        limit_edges: Optional[int] = None,
                        q: Optional[str] = None,
                        include_ontology: bool = True,
                        include_isolated: bool = True,
                        focus: Optional[str] = None,
                        depth: int = 1,
                        labels: str = "auto") -> dict[str, object]:
        graph_file_uri = file_uri if file_uri is not None else create_app_file_uri
        if rdf_graph is None:
            structural_graph, contextual_graph = _graph_mode_flags(mode)
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
        else:
            try:
                graph_prefix = _validate_prefix(prefix)
                if graph_prefix and graph_file_uri:
                    rdf_graph.bind(graph_prefix, rdflib.URIRef(graph_file_uri), override=True, replace=True)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
        return _graph_data(
            rdf_graph,
            limit_nodes=limit_nodes,
            limit_edges=limit_edges,
            q=q,
            include_ontology=include_ontology,
            include_isolated=include_isolated,
            focus=focus,
            depth=depth,
            labels=labels,
        )

    def _graph_page(filename: pathlib.Path,
                    mode: str = "both",
                    file_uri: Optional[str] = None,
                    prefix: Optional[str] = None,
                    rdf_graph: Optional[rdflib.Graph] = None,
                    page_label: Optional[str] = None,
                    route_name: Optional[str] = None,
                    limit_nodes: Optional[int] = None,
                    limit_edges: Optional[int] = None,
                    q: Optional[str] = None,
                    include_ontology: bool = True,
                    include_isolated: bool = True,
                    labels: str = "auto") -> HTMLResponse:
        graph_file_uri = file_uri if file_uri is not None else create_app_file_uri

        display_name = page_label or filename.name
        encoded_filename = urllib.parse.quote(route_name or filename.name)
        graph_payload = _graph_response(
            filename,
            mode=mode,
            file_uri=file_uri,
            prefix=prefix,
            rdf_graph=rdf_graph,
            limit_nodes=limit_nodes,
            limit_edges=limit_edges,
            q=q,
            include_ontology=include_ontology,
            include_isolated=include_isolated,
            labels=labels,
        )
        graph_json = json.dumps(graph_payload).replace("</", "<\\/")
        graph_summary = graph_payload["summary"]
        truncation_notice = (
            f'<p class="graph-notice">Showing {graph_summary["shown_nodes"]:,} of {graph_summary["total_nodes"]:,} nodes '
            f'and {graph_summary["shown_edges"]:,} of {graph_summary["total_edges"]:,} edges. Refine the search or raise limits to see more.</p>'
            if graph_summary["truncated"]
            else ""
        )
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
        label_selected = {
            "auto": "selected" if labels == "auto" else "",
            "on": "selected" if labels == "on" else "",
            "off": "selected" if labels == "off" else "",
        }
        graph_data_url = f"/{encoded_filename}/graph-data"
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(display_name)} Graph</title>
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
    .node-link {{
      display: inline-flex;
      margin: 0 0 10px;
      color: var(--accent);
      font-size: 0.875rem;
      font-weight: 650;
      text-decoration: none;
    }}
    .graph-panel {{
      position: relative;
    }}
    .empty-graph {{
      display: none;
      color: var(--muted);
      padding: 12px;
    }}
    .graph-notice {{
      margin: 0;
      color: var(--muted);
      font-size: 0.875rem;
    }}
  </style>
</head>
<body>
<main>
  <header>
    <nav><a href="/">Files</a> {graph_nav}</nav>
    <h1>{escape(display_name)} - Graph</h1>
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
      <label>Search
        <input type="text" name="q" value="{escape(q or "")}" placeholder="label or IRI">
      </label>
      <label>Node limit
        <input type="number" name="limit_nodes" min="10" max="10000" value="{escape(str(limit_nodes or ""))}" placeholder="1000">
      </label>
      <label>Edge limit
        <input type="number" name="limit_edges" min="10" max="20000" value="{escape(str(limit_edges or ""))}" placeholder="2000">
      </label>
      <label>Labels
        <select name="labels" id="label-mode">
          <option value="auto" {label_selected["auto"]}>Auto</option>
          <option value="on" {label_selected["on"]}>On</option>
          <option value="off" {label_selected["off"]}>Off</option>
        </select>
      </label>
      <input type="hidden" name="include_ontology" value="false">
      <label class="radio-label"><input type="checkbox" name="include_ontology" value="true" {"checked" if include_ontology else ""}> Include ontology nodes</label>
      <input type="hidden" name="include_isolated" value="false">
      <label class="radio-label"><input type="checkbox" name="include_isolated" value="true" {"checked" if include_isolated else ""}> Include isolated nodes</label>
      <button type="submit">Update</button>
    </form>
    {truncation_notice}
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
  const graphDataUrl = "{graph_data_url}";
  const graphForm = document.getElementById("graph-form");
  const container = document.getElementById("network");
  const emptyGraph = document.getElementById("empty-graph");
  const nodeDetails = document.getElementById("node-details");
  const hiddenNodeToggle = document.getElementById("hidden-node-toggle");
  const hiddenNodeList = document.getElementById("hidden-node-list");
  const labelModeInput = document.getElementById("label-mode");
  const allNodes = new Map();
  const allEdges = new Map();
  const nodeSources = new Map();
  const edgeSources = new Map();
  const hiddenNodeIds = new Set();
  const expandedNodeIds = new Set();
  const nodeById = allNodes;
  let hideNode = () => {{}};
  let unhideNode = () => {{}};
  let refreshVisibleGraph = () => {{}};
  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
  const edgeKey = (edge) => `${{edge.from}}\\u0000${{edge.to}}\\u0000${{edge.label}}`;
  const renderedLabelsEnabled = () => {{
    if (labelModeInput.value === "on") {{
      return true;
    }}
    if (labelModeInput.value === "off") {{
      return false;
    }}
    return (allNodes.size <= 250 && allEdges.size <= 500);
  }};
  const visibleNode = (node) => ({{
    ...node,
    label: renderedLabelsEnabled() ? node.label : undefined,
    title: node.label
  }});
  const visibleEdge = (edge) => ({{
    ...edge,
    label: renderedLabelsEnabled() ? edge.label : undefined,
    title: edge.label
  }});
  const rememberSource = (sourceMap, id, source) => {{
    const sources = sourceMap.get(id) || new Set();
    sources.add(source);
    sourceMap.set(id, sources);
  }};
  const forgetSource = (sourceMap, id, source) => {{
    const sources = sourceMap.get(id);
    if (!sources) {{
      return false;
    }}
    sources.delete(source);
    if (sources.size === 0) {{
      sourceMap.delete(id);
      return true;
    }}
    return false;
  }};
  const addGraphPayload = (payload, source) => {{
    (payload.nodes || []).forEach((node) => {{
      allNodes.set(node.id, {{ ...(allNodes.get(node.id) || {{}}), ...node }});
      rememberSource(nodeSources, node.id, source);
    }});
    (payload.edges || []).forEach((edge) => {{
      const key = edgeKey(edge);
      allEdges.set(key, {{ ...(allEdges.get(key) || {{}}), ...edge }});
      rememberSource(edgeSources, key, source);
    }});
  }};
  addGraphPayload(graphData, "base");
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
    const hiddenNeighborText = node.hidden_neighbor_count
      ? `<p class="no-literals">${{node.hidden_neighbor_count}} more connected node(s). Double-click to expand.</p>`
      : "";
    const literalRows = literals.length
      ? `<dl>${{literals.map((literal) => `<dt>${{escapeHtml(literal.predicate)}}</dt><dd>${{escapeHtml(literal.value)}}</dd>`).join("")}}</dl>`
      : '<p class="no-literals">No literal values are available for this node.</p>';
    const localLink = node.local_href
      ? `<a class="node-link" href="${{escapeHtml(node.local_href)}}" target="_blank" rel="noopener">Open local TTL</a>`
      : "";
    nodeDetails.innerHTML = `<div class="node-details-header"><h2>${{escapeHtml(node.label)}}</h2><button type="button" class="hide-node-button">Hide</button></div>${{localLink}}${{hiddenNeighborText}}${{literalRows}}`;
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
  labelModeInput.addEventListener("change", () => {{
    refreshVisibleGraph();
  }});
  if (graphData.nodes.length === 0) {{
    emptyGraph.style.display = "block";
  }} else if (window.vis) {{
    const nodes = new vis.DataSet(Array.from(allNodes.values()).map(visibleNode));
    const edges = new vis.DataSet(Array.from(allEdges.values()).map(visibleEdge));
    const groups = graphData.groups || {{}};
    refreshVisibleGraph = () => {{
      nodes.clear();
      nodes.add(Array.from(allNodes.values())
        .filter((node) => !hiddenNodeIds.has(node.id))
        .map(visibleNode));
      edges.clear();
      edges.add(Array.from(allEdges.values())
        .filter((edge) => !hiddenNodeIds.has(edge.from) && !hiddenNodeIds.has(edge.to))
        .map(visibleEdge));
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
    const collapseNode = (nodeId) => {{
      const source = `expand:${{nodeId}}`;
      expandedNodeIds.delete(nodeId);
      for (const edgeId of Array.from(edgeSources.keys())) {{
        if (forgetSource(edgeSources, edgeId, source)) {{
          allEdges.delete(edgeId);
        }}
      }}
      for (const currentNodeId of Array.from(nodeSources.keys())) {{
        if (currentNodeId === nodeId) {{
          forgetSource(nodeSources, currentNodeId, source);
          continue;
        }}
        if (forgetSource(nodeSources, currentNodeId, source)) {{
          allNodes.delete(currentNodeId);
          hiddenNodeIds.delete(currentNodeId);
        }}
      }}
      refreshVisibleGraph();
    }};
    const expandNode = async (nodeId) => {{
      if (expandedNodeIds.has(nodeId)) {{
        collapseNode(nodeId);
        return;
      }}
      const params = new URLSearchParams(new FormData(graphForm));
      params.set("focus", nodeId);
      params.set("depth", "1");
      const response = await fetch(`${{graphDataUrl}}?${{params.toString()}}`);
      if (!response.ok) {{
        return;
      }}
      const payload = await response.json();
      expandedNodeIds.add(nodeId);
      addGraphPayload(payload, `expand:${{nodeId}}`);
      refreshVisibleGraph();
      network.selectNodes([nodeId]);
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
        navigationButtons: true,
        hideEdgesOnDrag: true,
        hideEdgesOnZoom: true
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
    network.once("stabilizationIterationsDone", () => {{
      network.setOptions({{ physics: {{ enabled: false }} }});
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
    network.on("doubleClick", (params) => {{
      if (params.nodes.length > 0) {{
        expandNode(params.nodes[0]);
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

    def _query_page(filename: pathlib.Path,
                    query: Optional[str] = None,
                    rdf_graph: Optional[rdflib.Graph] = None,
                    page_label: Optional[str] = None,
                    route_name: Optional[str] = None) -> HTMLResponse:
        sparql_query = query or DEFAULT_SPARQL_QUERY
        rdf_graph = rdf_graph if rdf_graph is not None else _load_hdf_graph(filename)
        result_text = ""
        result_html = '<p class="empty-result">Run the example query or edit it before submitting.</p>'
        if query is not None:
            result_text, result_html = _query_result(rdf_graph, sparql_query)

        display_name = page_label or filename.name
        encoded_filename = urllib.parse.quote(route_name or filename.name)
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
  <title>{escape(display_name)} Query</title>
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
    <h1>{escape(display_name)} - SPARQL Query</h1>
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

    def _shacl_result(rdf_graph: rdflib.Graph, shapes_text: str) -> tuple[str, str]:
        try:
            import pyshacl

            shapes_graph = rdflib.Graph()
            _bind_standard_prefixes(shapes_graph)
            shapes_graph.parse(data=shapes_text, format="turtle")
            conforms, results_graph, results_text = pyshacl.validate(
                rdf_graph,
                shacl_graph=shapes_graph,
                inference="rdfs",
            )
            _bind_standard_prefixes(results_graph)
            status = "Conforms" if conforms else "Does not conform"
            status_class = "valid" if conforms else "invalid"
            results_turtle = results_graph.serialize(format="turtle")
            html = (
                f'<div class="validation-status {status_class}">{status}</div>'
                f"<pre>{escape(results_turtle)}</pre>"
            )
            return results_text, html
        except Exception as e:
            return f"SHACL validation error: {e}", '<div class="validation-status invalid">Validation failed</div>'

    def _shacl_page(filename: pathlib.Path,
                    shapes: Optional[str] = None,
                    rdf_graph: Optional[rdflib.Graph] = None,
                    page_label: Optional[str] = None,
                    route_name: Optional[str] = None) -> HTMLResponse:
        shapes_text = shapes or DEFAULT_SHACL_SHAPES
        rdf_graph = rdf_graph if rdf_graph is not None else _load_hdf_graph(filename)
        result_text = ""
        result_html = '<p class="empty-result">Run the default shape or paste your own SHACL Turtle before validating.</p>'
        if shapes is not None:
            result_text, result_html = _shacl_result(rdf_graph, shapes_text)

        display_name = page_label or filename.name
        encoded_filename = urllib.parse.quote(route_name or filename.name)
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(display_name)} SHACL</title>
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
    header, .shacl-panel, .result-panel {{
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
      min-height: 240px;
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
      min-height: 140px;
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
    .validation-status {{
      display: inline-flex;
      min-height: 32px;
      align-items: center;
      margin-top: 12px;
      padding: 0 10px;
      border-radius: 6px;
      font-weight: 650;
    }}
    .validation-status.valid {{
      color: #175f2a;
      background: #dff3df;
    }}
    .validation-status.invalid {{
      color: #8a1f1f;
      background: #f8dfe1;
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
    <nav><a href="/">Files</a><a href="/{encoded_filename}/graph">Graph</a><a href="/{encoded_filename}/query">Query</a><a href="/{encoded_filename}/metrics">Metrics</a><a href="/{encoded_filename}/ttl">Turtle</a></nav>
    <h1>{escape(display_name)} - SHACL Validation</h1>
  </header>
  <section class="shacl-panel">
    <form method="get" action="/{encoded_filename}/shacl">
      <label>SHACL shapes
        <textarea id="shacl-shapes" name="shapes">{escape(shapes_text)}</textarea>
      </label>
      <button type="submit">Validate</button>
    </form>
  </section>
  <section class="result-panel">
    <label>Result
      <textarea id="shacl-result" readonly>{escape(result_text)}</textarea>
    </label>
    {result_html}
  </section>
</main>
</body>
</html>
"""
        return HTMLResponse(page)

    def _format_count(value) -> str:
        if isinstance(value, float):
            return f"{value:,.1f}"
        return f"{value:,}"

    def _count_table(rows: list[tuple[str, int]], empty_message: str) -> str:
        if not rows:
            return f'<p class="empty-result">{escape(empty_message)}</p>'
        body = "".join(
            f"<tr><td>{escape(label)}</td><td>{_format_count(count)}</td></tr>"
            for label, count in rows
        )
        return f'<table class="metric-table"><tbody>{body}</tbody></table>'

    def _percent(numerator: int, denominator: int) -> float:
        return (numerator / denominator * 100.0) if denominator else 0.0

    def _external_namespace(value) -> str:
        text = str(value)
        if "#" in text:
            return text.rsplit("#", 1)[0] + "#"
        if "/" in text:
            return text.rsplit("/", 1)[0] + "/"
        return text

    def _resource_terms(subject, predicate, obj) -> list:
        terms = []
        for term in (subject, predicate, obj):
            if isinstance(term, (rdflib.URIRef, rdflib.BNode)):
                terms.append(term)
        return terms

    def _graph_metrics(rdf_graph: rdflib.Graph,
                       compute_distances: bool = True,
                       distance_node_limit: int = COMBINED_METRICS_DISTANCE_NODE_LIMIT) -> dict[str, object]:
        return compute_graph_metrics(
            rdf_graph,
            base_namespace=create_app_file_uri,
            compute_distances=compute_distances,
            distance_node_limit=distance_node_limit,
        )

    def _combined_graph_metrics() -> dict[str, object]:
        nonlocal combined_metrics_cache
        cache_key = (server_graph_version, len(server_graph))
        if combined_metrics_cache is not None and combined_metrics_cache[:2] == cache_key:
            return combined_metrics_cache[2]
        metrics = _graph_metrics(
            server_graph,
            compute_distances=True,
            distance_node_limit=COMBINED_METRICS_DISTANCE_NODE_LIMIT,
        )
        combined_metrics_cache = (cache_key[0], cache_key[1], metrics)
        return metrics

    def _metrics_page(filename: pathlib.Path,
                      rdf_graph: Optional[rdflib.Graph] = None,
                      page_label: Optional[str] = None,
                      route_name: Optional[str] = None,
                      metrics: Optional[dict[str, object]] = None) -> HTMLResponse:
        rdf_graph = rdf_graph if rdf_graph is not None else _load_hdf_graph(filename)
        metrics = metrics if metrics is not None else _graph_metrics(rdf_graph)
        display_name = page_label or filename.name
        encoded_filename = urllib.parse.quote(route_name or filename.name)
        largest_distance_value = (
            metrics["largest_distance"]
            if metrics.get("largest_distance_computed", True)
            else "Not computed"
        )
        largest_distance_description = (
            "Largest shortest-path distance within connected components."
            if metrics.get("largest_distance_computed", True)
            else f"Skipped for graphs above {metrics.get('largest_distance_node_limit', COMBINED_METRICS_DISTANCE_NODE_LIMIT):,} resource nodes."
        )
        cards = [
            ("Total triples", metrics["triples"], "Total RDF statements in the graph."),
            ("Distinct subjects", metrics["subjects"], "Unique resources or blank nodes used as subjects."),
            ("Distinct predicates", metrics["predicates"], "Unique properties used by triples."),
            ("Distinct objects", metrics["objects"], "Unique object terms, including literals."),
            ("IRI count", metrics["iri_count"], "Unique IRI terms in subject, predicate, or object position."),
            ("Blank node count", metrics["blank_nodes"], "Unique blank nodes used as subject or object terms."),
            ("Literal count", metrics["literals"], "Triples whose object is a literal value."),
            ("Avg triples / subject", metrics["avg_triples_per_subject"], "Average description density per subject."),
            ("Distinct classes", metrics["classes"], "Unique rdf:type object classes."),
            ("Subjects without type", metrics["subjects_without_type"], "Subjects without an explicit rdf:type."),
            ("Resource nodes", metrics["resource_nodes"], "Subject and IRI/blank-node object terms used for connectivity."),
            ("Avg out-degree", metrics["avg_out_degree"], "Average outgoing resource links per resource node."),
            ("Avg in-degree", metrics["avg_in_degree"], "Average incoming resource links per resource node."),
            ("Weakly connected nodes", metrics["weakly_connected_nodes"], "Resource nodes with zero or one resource link."),
            ("Connected components", metrics["components"], "Disconnected resource groups in the graph."),
            ("Largest component", metrics["largest_component"], "Node count of the largest connected component."),
            ("Largest distance", largest_distance_value, largest_distance_description),
            ("Label coverage", f'{metrics["label_coverage"]:.1f}%', "Percentage of subjects with at least one rdfs:label."),
            ("Blank node percentage", f'{metrics["blank_node_percentage"]:.1f}%', "Blank nodes divided by all unique resource nodes."),
            ("owl:sameAs links", metrics["same_as_count"], "Explicit identity links to equivalent resources."),
        ]
        card_html = "".join(
            f'<article class="metric-card"><span>{escape(label)}</span><strong>{escape(_format_count(value) if not isinstance(value, str) else value)}</strong><p>{escape(description)}</p></article>'
            for label, value, description in cards
        )
        empty_notice = (
            '<section><p class="empty-result">No triples are available for this graph.</p></section>'
            if metrics["triples"] == 0
            else ""
        )
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(display_name)} Metrics</title>
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
    .metric-card p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.82rem;
      line-height: 1.35;
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
    <h1>{escape(display_name)} - Graph Metrics</h1>
  </header>
  <section>
    <h2>Knowledge Graph Metrics</h2>
    <p class="empty-result">Metrics are computed from the currently loaded RDF graph. Connectivity metrics use subjects and IRI or blank-node objects as graph nodes; literal objects are excluded from the resource network.</p>
  </section>
  {empty_notice}
  <section>
    <div class="metric-grid">{card_html}</div>
  </section>
  <div class="metric-sections">
    <section>
      <h2>Top Predicates</h2>
      <p class="empty-result">Most frequently used RDF properties.</p>
      {_count_table(metrics["top_predicates"], "No predicates found.")}
    </section>
    <section>
      <h2>Rare Predicates</h2>
      <p class="empty-result">Least frequent properties, including one-off predicates.</p>
      {_count_table(metrics["rare_predicates"], "No predicates found.")}
    </section>
    <section>
      <h2>Predicate Usage Distribution</h2>
      <p class="empty-result">Triple counts per predicate.</p>
      {_count_table(metrics["predicate_distribution"], "No predicates found.")}
    </section>
    <section>
      <h2>RDF Classes</h2>
      <p class="empty-result">Instances per rdf:type class.</p>
      {_count_table(metrics["top_classes"], "No RDF classes found.")}
    </section>
    <section>
      <h2>Top Nodes by Out-Degree</h2>
      <p class="empty-result">Resources that link to many other resources.</p>
      {_count_table(metrics["top_out_degree"], "No outgoing resource links found.")}
    </section>
    <section>
      <h2>Top Nodes by In-Degree</h2>
      <p class="empty-result">Resources that many other resources point to.</p>
      {_count_table(metrics["top_in_degree"], "No incoming resource links found.")}
    </section>
    <section>
      <h2>Datatype Distribution</h2>
      <p class="empty-result">Literal datatype usage.</p>
      {_count_table(metrics["datatype_distribution"], "No literals found.")}
    </section>
    <section>
      <h2>Language Tags</h2>
      <p class="empty-result">Language-tagged literal distribution.</p>
      {_count_table(metrics["language_distribution"], "No language-tagged literals found.")}
    </section>
    <section>
      <h2>Literal Quality</h2>
      {_count_table([
          ("Untyped literals", metrics["untyped_literals"]),
          ("Empty string literals", metrics["empty_literals"]),
      ], "No literals found.")}
    </section>
    <section>
      <h2>Label Readability</h2>
      {_count_table([
          ("Subjects with labels", metrics["subjects_with_labels"]),
          ("Subjects missing labels", metrics["subjects_missing_labels"]),
      ], "No subjects found.")}
    </section>
    <section>
      <h2>Data Quality</h2>
      {_count_table([
          ("Duplicate triples", metrics["duplicate_triples"]),
          ("Subjects with only one triple", metrics["subjects_with_one_triple"]),
          ("Missing type count", metrics["subjects_without_type"]),
          ("Missing label count", metrics["subjects_missing_labels"]),
      ], "No data quality metrics available.")}
    </section>
    <section>
      <h2>External Namespaces</h2>
      <p class="empty-result">IRI namespaces outside the configured file URI namespace.</p>
      {_count_table(metrics["top_external_namespaces"], "No external IRIs found.")}
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

    def _graph_formatted_response(rdf_graph: rdflib.Graph,
                                  label: str,
                                  format_key: str,
                                  raw: bool = False):
        if format_key not in RDF_FORMATS:
            raise HTTPException(status_code=404, detail="Unknown RDF format")
        rdflib_format, media_type, _ = RDF_FORMATS[format_key]
        serialized = rdf_graph.serialize(format=rdflib_format)
        if raw:
            return PlainTextResponse(content=serialized, media_type=media_type)
        return _format_controls(
            filename=label,
            format_key=format_key,
            serialized=serialized,
            structural=True,
            contextual=True,
            file_uri=None,
            prefix=None,
        )

    def _subject_response(filename: pathlib.Path,
                          resource_path: str,
                          request: Request,
                          structural: bool = True,
                          contextual: bool = True,
                          file_uri: Optional[str] = None,
                          prefix: Optional[str] = None,
                          format: Optional[str] = None):
        if not structural and not contextual:
            raise HTTPException(
                status_code=400,
                detail="At least one of structural or contextual must be True.",
            )
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

        decoded_path = urllib.parse.unquote(resource_path).strip("/")
        subject_suffix = f"{filename.name}/{decoded_path}" if decoded_path else filename.name
        candidates = [
            rdflib.BNode(subject_suffix),
            rdflib.URIRef(subject_suffix),
        ]
        if graph_file_uri:
            base = str(graph_file_uri)
            candidates.extend([
                rdflib.URIRef(f"{base}{subject_suffix}"),
                rdflib.URIRef(f"{base}{decoded_path}" if decoded_path else base.rstrip("#/")),
            ])

        subject = next((candidate for candidate in candidates if (candidate, None, None) in rdf_graph), None)
        if subject is None:
            raise HTTPException(status_code=404, detail="Unknown RDF subject")

        subgraph = _subject_subgraph(rdf_graph, subject)
        return _resource_response(subject, subgraph, request, format=format)

    @app.get("/combined/ttl")
    def get_combined_ttl(raw: bool = False):
        return _graph_formatted_response(server_graph, "combined", "ttl", raw=raw)

    @app.get("/combined/jsonld")
    def get_combined_jsonld(raw: bool = False):
        return _graph_formatted_response(server_graph, "combined", "jsonld", raw=raw)

    @app.get("/combined/nt")
    def get_combined_nt(raw: bool = False):
        return _graph_formatted_response(server_graph, "combined", "nt", raw=raw)

    @app.get("/combined/xml")
    def get_combined_xml(raw: bool = False):
        return _graph_formatted_response(server_graph, "combined", "xml", raw=raw)

    @app.get("/combined/graph")
    def get_combined_graph(mode: str = "both",
                           file_uri: Optional[str] = None,
                           prefix: Optional[str] = None,
                           limit_nodes: int = COMBINED_GRAPH_NODE_LIMIT,
                           limit_edges: int = COMBINED_GRAPH_EDGE_LIMIT,
                           q: Optional[str] = None,
                           include_ontology: bool = False,
                           include_isolated: bool = False,
                           labels: str = "auto"):
        return _graph_page(
            pathlib.Path("combined"),
            mode=mode,
            file_uri=file_uri,
            prefix=prefix,
            rdf_graph=server_graph,
            page_label="Combined graph",
            route_name="combined",
            limit_nodes=limit_nodes,
            limit_edges=limit_edges,
            q=q,
            include_ontology=include_ontology,
            include_isolated=include_isolated,
            labels=labels,
        )

    @app.get("/combined/graph-data")
    def get_combined_graph_data(mode: str = "both",
                                file_uri: Optional[str] = None,
                                prefix: Optional[str] = None,
                                limit_nodes: int = COMBINED_GRAPH_NODE_LIMIT,
                                limit_edges: int = COMBINED_GRAPH_EDGE_LIMIT,
                                q: Optional[str] = None,
                                include_ontology: bool = False,
                                include_isolated: bool = False,
                                focus: Optional[str] = None,
                                depth: int = 1,
                                labels: str = "auto"):
        return JSONResponse(_graph_response(
            pathlib.Path("combined"),
            mode=mode,
            file_uri=file_uri,
            prefix=prefix,
            rdf_graph=server_graph,
            limit_nodes=limit_nodes,
            limit_edges=limit_edges,
            q=q,
            include_ontology=include_ontology,
            include_isolated=include_isolated,
            focus=focus,
            depth=depth,
            labels=labels,
        ))

    @app.get("/combined/query")
    def get_combined_query(query: Optional[str] = None):
        return _query_page(
            pathlib.Path("combined"),
            query=query,
            rdf_graph=server_graph,
            page_label="Combined graph",
            route_name="combined",
        )

    @app.get("/combined/shacl")
    def get_combined_shacl(shapes: Optional[str] = None):
        return _shacl_page(
            pathlib.Path("combined"),
            shapes=shapes,
            rdf_graph=server_graph,
            page_label="Combined graph",
            route_name="combined",
        )

    @app.get("/combined/metrics")
    def get_combined_metrics():
        return _metrics_page(
            pathlib.Path("combined"),
            rdf_graph=server_graph,
            page_label="Combined graph",
            route_name="combined",
            metrics=_combined_graph_metrics(),
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
                       prefix: Optional[str] = None,
                       limit_nodes: Optional[int] = None,
                       limit_edges: Optional[int] = None,
                       q: Optional[str] = None,
                       include_ontology: bool = True,
                       include_isolated: bool = True,
                       labels: str = "auto"):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _graph_page(
            hdf_file,
            mode=mode,
            file_uri=file_uri,
            prefix=prefix,
            limit_nodes=limit_nodes,
            limit_edges=limit_edges,
            q=q,
            include_ontology=include_ontology,
            include_isolated=include_isolated,
            labels=labels,
        )

    @app.get("/{filename}/graph-data")
    def get_file_graph_data(filename: str,
                            mode: str = "both",
                            file_uri: Optional[str] = None,
                            prefix: Optional[str] = None,
                            limit_nodes: Optional[int] = None,
                            limit_edges: Optional[int] = None,
                            q: Optional[str] = None,
                            include_ontology: bool = True,
                            include_isolated: bool = True,
                            focus: Optional[str] = None,
                            depth: int = 1,
                            labels: str = "auto"):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return JSONResponse(_graph_response(
            hdf_file,
            mode=mode,
            file_uri=file_uri,
            prefix=prefix,
            limit_nodes=limit_nodes,
            limit_edges=limit_edges,
            q=q,
            include_ontology=include_ontology,
            include_isolated=include_isolated,
            focus=focus,
            depth=depth,
            labels=labels,
        ))

    @app.get("/{filename}/query")
    def get_file_query(filename: str, query: Optional[str] = None):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _query_page(hdf_file, query=query)

    @app.get("/{filename}/shacl")
    def get_file_shacl(filename: str, shapes: Optional[str] = None):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _shacl_page(hdf_file, shapes=shapes)

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

    @app.get("/resolve")
    def resolve_iri_query(request: Request,
                          iri: Optional[str] = None,
                          resolve: Optional[str] = None,
                          format: Optional[str] = None):
        target_iri = iri or resolve
        if not target_iri:
            raise HTTPException(status_code=400, detail="Provide an IRI with ?iri=... or ?resolve=...")
        return _resolve_iri_response(target_iri, request, format=format)

    @app.get("/resolve/{encoded_iri:path}")
    def resolve_iri(request: Request, encoded_iri: str, format: Optional[str] = None):
        iri = urllib.parse.unquote(encoded_iri)
        return _resolve_iri_response(iri, request, format=format)

    @app.get("/{filename}/{resource_path:path}")
    def get_file_subject(request: Request,
                         filename: str,
                         resource_path: str,
                         structural: bool = True,
                         contextual: bool = True,
                         file_uri: Optional[str] = None,
                         prefix: Optional[str] = None,
                         format: Optional[str] = None):
        hdf_file = hdf_files.get(filename)
        if hdf_file is None:
            raise HTTPException(status_code=404, detail="Unknown HDF5 file")
        return _subject_response(
            hdf_file,
            resource_path,
            request,
            structural=structural,
            contextual=contextual,
            file_uri=file_uri,
            prefix=prefix,
            format=format,
        )

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
               file_uri: Optional[str] = None,
               local_iri_patterns: Optional[Sequence[str]] = None,
               h5_extensions: Optional[Sequence[str]] = None):
    """Run a FastAPI/uvicorn server exposing RDF for HDF5 files."""
    if filenames is None:
        filenames = [filename] if filename is not None else None
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logger.setLevel(logging.INFO)
    app = create_app(
        filenames,
        structural=structural,
        contextual=contextual,
        file_uri=file_uri,
        local_iri_patterns=local_iri_patterns,
        h5_extensions=h5_extensions,
    )
    url = f"http://{host}:{port}/"
    logger.info("Starting h5rdmtoolbox RDF server at %s serving files %s", url, app.state.hdf_files)
    uvicorn.run(app, host=host, port=port)
