import hashlib
import os
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from typing import Dict, Tuple, Iterator, List
from urllib.parse import urlparse, unquote
from urllib.request import url2pathname

import pandas as pd
import rdflib
import requests
from pydantic import FileUrl
from pydantic.v1 import HttpUrl
from rdflib import Graph

from .. import logger

# --- minimal caster for common XSD datatypes ---
_XSD = "http://www.w3.org/2001/XMLSchema#"
_NUM_DT = {
    _XSD + "integer", _XSD + "int", _XSD + "long", _XSD + "short",
    _XSD + "byte", _XSD + "nonNegativeInteger", _XSD + "nonPositiveInteger",
    _XSD + "positiveInteger", _XSD + "negativeInteger"
}
_FLOAT_DT = {_XSD + "float", _XSD + "double"}
_DEC_DT = {_XSD + "decimal"}


def file_uri_or_path_to_path(value) -> pathlib.Path:
    # Keep behavior close to your code
    if isinstance(value, pathlib.Path):
        return value

    # Your custom type
    if "FileUrl" in globals() and isinstance(value, FileUrl):
        value = str(value)

    if not isinstance(value, str):
        raise TypeError(f"Expected str/Path, got {type(value)!r}")

    parsed = urlparse(value)

    # Not a URI -> treat as normal filesystem path
    if parsed.scheme != "file":
        return pathlib.Path(value)

    # File URI -> convert to OS path
    # parsed.path is already the URI path part, still percent-encoded
    path = url2pathname(unquote(parsed.path))

    # Handle file://localhost/... (same as local)
    netloc = parsed.netloc
    if netloc and netloc not in ("localhost",):
        # UNC style (mostly Windows): file://server/share/file.txt
        if os.name == "nt":
            path = f"\\\\{netloc}{path}"
        else:
            # Rare on POSIX; best effort
            path = f"/{netloc}{path}"

    return pathlib.Path(path)


def sparql_query_to_jsonld(graph: Graph, query: str) -> dict:
    results = graph.query(query)

    jsonld = {
        "@context": {},
        "@graph": []
    }

    for row in results:
        item = {}
        for var, value in row.asdict().items():
            if value is not None:
                if hasattr(value, 'n3'):
                    val_str = value.n3(graph.namespace_manager)
                else:
                    val_str = str(value)

                item[var] = val_str

                # Add simple context mapping
                if isinstance(value, (str, int, float)):
                    jsonld["@context"][var] = None
                elif value.__class__.__name__ == 'URIRef':
                    jsonld["@context"][var] = str(value)

        if item:
            jsonld["@graph"].append(item)

    return jsonld


def _cast_cell(cell, cast_literals: bool):
    """cell is a SPARQL JSON binding object like {'type': 'literal', 'value': '42', 'datatype': '...'}"""
    if cell is None:
        return None
    t = cell.get("type")
    v = cell.get("value")
    if not cast_literals:
        return v
    if t == "literal":
        dt = cell.get("datatype")
        if dt in _NUM_DT:
            try:
                return int(v)
            except Exception:
                return v
        if dt in _FLOAT_DT:
            try:
                return float(v)
            except Exception:
                return v
        if dt in _DEC_DT:
            try:
                return Decimal(v)
            except Exception:
                return v
        if dt == _XSD + "boolean":
            return v.lower() == "true"
        if dt == _XSD + "dateTime":
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                return v
        if dt == _XSD + "date":
            try:
                return date.fromisoformat(v)
            except Exception:
                return v
        if dt == _XSD + "time":
            try:
                return time.fromisoformat(v)
            except Exception:
                return v
        # language-tagged literal like {"xml:lang": "en"}
        # fall through to string value
        return v
    # URIs / bnodes: just return string
    return v


def sparql_json_to_dataframe(results_json: dict, cast_literals: bool = True) -> pd.DataFrame:
    """
    Turn a SPARQL SELECT JSON result into a pandas DataFrame.
    Columns are exactly results['head']['vars'] and missing bindings become None.
    """
    vars_ = results_json.get("head", {}).get("vars", [])
    rows = []
    for b in results_json.get("results", {}).get("bindings", []):
        row = {var: _cast_cell(b.get(var), cast_literals) for var in vars_}
        rows.append(row)
    return pd.DataFrame(rows, columns=vars_)


def parse_literal(literal):
    if isinstance(literal, rdflib.Literal):
        return literal.value
    if isinstance(literal, rdflib.URIRef):
        return str(literal)
    return literal


@dataclass
class DownloadStatus:
    record_id: str
    filename: pathlib.Path
    ok: bool
    message: str


def extract_record_id(value: str) -> str:
    """
    Accepts either a bare record ID like '1234567' or a Zenodo URL
    and returns the numeric record ID as a string.
    """
    # If it's just digits, assume it's already the ID
    if value.isdigit():
        return value

    # Try to pull the last number sequence from the string (e.g. URL)
    match = re.search(r'(\d+)/?$', value.strip())
    if match:
        return match.group(1)

    raise ValueError(f"Could not extract a numeric record ID from '{value}'")


def get_file_metadata(record: str, sandbox: bool = False) -> Iterator[Tuple[str, Dict]]:
    """
    Fetch the Zenodo record JSON and yield (filename, file-metadata-dict) tuples.
    """
    record_id = extract_record_id(record)
    base_url = "https://sandbox.zenodo.org/api/records" if sandbox else "https://zenodo.org/api/records"
    url = f"{base_url}/{record_id}"

    resp = requests.get(url)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch record {record_id}: HTTP {resp.status_code} - {resp.text}"
        )

    data = resp.json()

    # Zenodo records normally have 'files' at the top level
    files = data.get("files", [])

    if not files:
        # Some records may store file info differently; handle gracefully
        raise RuntimeError(f"No files found in record {record_id} (or unexpected schema).")

    for f in files:
        # Common fields in Zenodo API
        name = f.get("key") or f.get("filename") or "<unknown>"
        yield name, f


def _is_sandbox_doi(doi: str) -> bool:
    """Return True if the provided doi string looks like a sandbox URL/DOI."""
    if "10.5281/zenodo" in doi:
        return True
    return False


def download_and_verify_file(file_meta: Dict, dest_dir: pathlib.Path) -> Tuple[pathlib.Path, bool, str, str]:
    """
    Download a single file described by file_meta into dest_dir and verify its checksum.

    Returns: (path, ok, expected_checksum, computed_checksum)
    """
    links = file_meta.get("links", {})
    url = links.get("self") or links.get("download")
    if not url:
        raise RuntimeError("No download link found for file metadata")

    filename = pathlib.Path(file_meta.get("key") or file_meta.get("filename") or "download.bin").name
    dest_path = dest_dir / filename

    # Stream download and compute md5 on the fly
    md5 = hashlib.md5()
    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to download {url}: HTTP {resp.status_code}")

    with open(dest_path, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            if not chunk:
                continue
            fh.write(chunk)
            md5.update(chunk)

    computed = md5.hexdigest()
    expected_raw = file_meta.get("checksum", "")

    # expected_raw is usually like 'md5:abcdef...'
    if ":" in expected_raw:
        algo, expected = expected_raw.split(":", 1)
    else:
        algo, expected = "md5", expected_raw

    if algo.lower() != "md5":
        # we only compute md5 here; report mismatch of algorithm instead of trying to compute another
        return dest_path, False, expected_raw, f"computed(md5)={computed}"

    ok = computed.lower() == expected.lower()
    return dest_path, ok, expected, computed


from dataclasses import dataclass


@dataclass
class WebResource:
    download_url: HttpUrl
    checksum: str
    title: str
    identifier: str
    mediaType: str


def compute_md5_of_file(path: pathlib.Path) -> str:
    """Return hex md5 of file at path."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize_filename(name: str) -> str:
    """Return a filesystem-safe filename (very small sanitizer)."""
    # remove path separators and control chars
    name = str(name)
    name = name.replace("/", "_").replace("\\\\", "_")
    # simple collapse of problematic characters
    return re.sub(r"[^\w\-.()\[\] ]+", "_", name)


def parse_checksum(raw: str) -> Tuple[str, str]:
    """Parse checksum string like 'md5:abcd' or just 'abcd' -> (algo, hex)"""
    if not raw:
        return "md5", ""
    s = str(raw)
    if ":" in s:
        algo, val = s.split(":", 1)
    else:
        algo, val = "md5", s
    return algo.lower(), val.lower()


def download(download_directory: pathlib.Path, web_resources: List[WebResource]) -> List[DownloadStatus]:
    """Download and verify a list of WebResource items.

    For each resource:
    - determine a record id (using extract_record_id when possible) and create a subfolder
    - skip download if a file with the expected checksum already exists
    - stream-download into a .tmp file while computing md5
    - on success move the .tmp to final filename; on checksum mismatch rename with conflict suffix
    - append status entries to the overall list and print progress

    Returns a list of DownloadStatus entries.
    """
    overall = []
    download_directory.mkdir(parents=True, exist_ok=True)

    for web_resource in web_resources:
        doi = web_resource.identifier
        # normalize DOI-like URLs
        if isinstance(doi, str) and (doi.startswith("http://doi.org/") or doi.startswith("https://doi.org/")):
            doi = doi.split("doi.org/", 1)[-1]

        # try to extract numeric record id; otherwise fall back to sanitized doi string
        try:
            rec_id = extract_record_id(str(doi))
        except Exception:
            rec_id = str(doi).replace("/", "_")

        record_dir = download_directory / str(rec_id)
        record_dir.mkdir(parents=True, exist_ok=True)

        url = str(web_resource.download_url)
        title = str(web_resource.title) if web_resource.title is not None else ""
        title = title.replace(".", "_")
        if web_resource.mediaType == "text/turtle":
            expected_suffix = ".ttl"
        elif web_resource.mediaType == "application/ld+json":
            expected_suffix = ".jsonld"
        elif web_resource.mediaType == "application/json":
            expected_suffix = ".json"
        elif web_resource.mediaType == "application/rdf+xml":
            expected_suffix = ".rdf"
        elif web_resource.mediaType == "application/x+hdf5":
            expected_suffix = ".hdf"
        else:
            expected_suffix = None

        # determine filename: prefer title, else last segment of URL
        if url.endswith("/content"):
            _url = url.rsplit("/", 2)[-2]  # remove trailing /content for Zenodo URLs
            _fname = _url.rsplit("/", 1)[-1]
        else:
            _fname = url.rsplit("/", 1)[-1]

        if pathlib.Path(_fname).suffix == "":
            if title != "":
                filename = sanitize_filename(title)
            else:
                if expected_suffix:
                    filename = f"download{expected_suffix}"
                else:
                    filename = "download.bin"
        else:
            filename = sanitize_filename(_fname)
        filename = filename.replace(" ", "_")
        dest_path = record_dir / filename
        if dest_path.suffix == "" and expected_suffix:
            dest_path = dest_path.with_suffix(expected_suffix)

        if web_resource.checksum is None:
            if dest_path.exists():
                logger.debug(f" > SKIP (exists, no checksum provided): {filename} -> {dest_path}")
                overall.append(DownloadStatus(rec_id, dest_path, True, "exists, no checksum provided"))
                continue

        expected_algo, expected_val = parse_checksum(web_resource.checksum)

        # If destination exists and matches expected checksum, skip
        if dest_path.exists() and expected_val:
            try:
                existing_md5 = compute_md5_of_file(dest_path)
                if expected_algo == "md5" and existing_md5.lower() == expected_val.lower():
                    logger.debug(f" > SKIP (exists & checksum ok): {filename} -> {dest_path}")
                    overall.append(DownloadStatus(rec_id, dest_path, True, f"exists, checksum matches"))
                    continue
            except Exception:
                # fall through to re-download
                pass

        # stream download to tmp file while computing md5
        tmp_path = record_dir / (filename + ".tmp")
        try:
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()

            md5 = hashlib.md5()
            with open(tmp_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    md5.update(chunk)

            computed = md5.hexdigest()

            # verify
            ok = False
            message = ""
            if expected_algo == "md5":
                if expected_val:
                    ok = computed.lower() == expected_val.lower()
                    if ok:
                        # move tmp to final
                        tmp_path.replace(dest_path)
                        message = f"saved to {dest_path}"
                        print(f" > OK: {filename} -> {dest_path} (md5 matches)")
                    else:
                        # conflict: keep both, rename new file with record id + short hash
                        new_name = f"{pathlib.Path(filename).stem}__{rec_id}__{computed[:8]}{pathlib.Path(filename).suffix}"
                        new_path = record_dir / new_name
                        tmp_path.replace(new_path)
                        message = f"checksum mismatch: expected={expected_val}, computed={computed}; saved as {new_path}"
                        print(
                            f" > MISMATCH: {filename} -> {new_path} (expected md5: {expected_val}, computed md5: {computed})")
                else:
                    # no expected checksum provided — accept and move
                    tmp_path.replace(dest_path)
                    ok = True
                    message = f"saved to {dest_path} (no expected checksum)"
                    print(f" > SAVED (no expected checksum): {filename} -> {dest_path}")
            else:
                # unsupported algorithm: save file but mark as not-verified
                tmp_path.replace(dest_path)
                ok = False
                message = f"saved to {dest_path} (unsupported checksum algorithm: {expected_algo})"
                print(f" > SAVED (unsupported checksum alg '{expected_algo}'): {filename} -> {dest_path}")

            overall.append(DownloadStatus(rec_id, dest_path, ok, message))

        except Exception as exc:
            # cleanup tmp file when exists
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            print(f" > ERROR downloading {filename}: {exc}")
            overall.append(DownloadStatus(rec_id, dest_path, False, str(exc)))

    # summary
    total = len(overall)
    ok_count = sum(1 for o in overall if o.ok)
    print(f"Summary: {ok_count}/{total} files verified successfully")

    return overall


def get_rdf_format_from_filename(filename: pathlib.Path) -> str:
    """Return rdflib format string based on filename suffix."""
    filename = pathlib.Path(filename)
    if filename.suffix == ".ttl":
        return "turtle"
    elif filename.suffix == ".jsonld":
        return "json-ld"
    else:
        return filename.suffix.split(".")[-1]


def database_initialization(
        config_filename: pathlib.Path,
        download_directory: pathlib.Path
) -> List[DownloadStatus]:
    """Initialize the database by downloading metadata files as specified in the config TTL file.

    Parameters
    ----------
    config_filename : pathlib.Path
        Path to the RDF configuration file (TTL or JSON-LD) describing datasets.
    download_directory : pathlib.Path, optional
        Directory where downloaded files will be stored.

    Returns
    -------
    List[DownloadStatus]
        A list of DownloadStatus entries indicating the result of each download.
    """
    config_filename = pathlib.Path(config_filename)
    if not pathlib.Path(download_directory).exists():
        raise ValueError(f"Download directory does not exist: {download_directory}")
    if not pathlib.Path(download_directory).is_dir():
        raise ValueError(f"Download directory is not a directory: {download_directory}")
    g = rdflib.Graph()
    g.parse(
        config_filename,
        format=get_rdf_format_from_filename(config_filename)
    )
    # get all dcat:Dataset entries:
    query = """
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX spdx: <http://spdx.org/rdf/terms#>

        SELECT ?dataset ?identifier ?download ?title ?checksumValue WHERE {
            ?dataset a dcat:Dataset ;
                     dcterms:identifier ?identifier ;
                     dcat:distribution ?dist .

            ?dist dcat:downloadURL ?download ;
                  dcterms:title ?title ;
                  dcat:mediaType ?media .

            OPTIONAL {
                ?dist spdx:checksum ?ck .
                ?ck spdx:checksumValue ?checksumValue .
            }

            FILTER(
                CONTAINS(LCASE(STR(?media)), "text/turtle") ||
                CONTAINS(LCASE(STR(?media)), "application/ld+json")
            )
        }
        """
    results = g.query(query)
    list_of_ttl_web_resources = [WebResource(
        download_url=row.download,
        checksum=row.checksumValue,
        title=row.title,
        identifier=row.identifier,
        mediaType="text/turtle"
    ) for row in results]

    print(
        f"Found {len(list_of_ttl_web_resources)} TTL web resources to download. Downloading to {download_directory}...")
    return download(
        download_directory=download_directory,
        web_resources=list_of_ttl_web_resources
    )


def sparql_result_to_df(bindings):
    return pd.DataFrame([{str(k): v for k, v in binding.items()} for binding in bindings])
