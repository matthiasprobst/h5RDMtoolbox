"""

# Downloading Metadata files from Zenodo Sandbox

This script shows how to download metadata files from the Zenodo sandbox environment for testing purposes.
It reads a mapping of dataset names to their corresponding DOIs and downloads the relevant files into a specified
directory.

"""
import pathlib
from typing import List

import rdflib

from .utils import DownloadStatus, download, WebResource, get_rdf_format_from_filename

__this_dir__ = pathlib.Path(__file__).parent


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
        web_resources=list_of_ttl_web_resources,
        use_agent_header=True
    )
