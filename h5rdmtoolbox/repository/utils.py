import hashlib
import logging
import pathlib
import uuid
import warnings
from typing import Optional, Union, Dict

import requests

logger = logging.getLogger('h5rdmtoolbox')


def download_file(file_url,
                  filename: str,
                  target_folder: Union[str, pathlib.Path] = None,
                  access_token: Optional[str] = None,
                  checksum: Optional[str] = None,
                  checksum_algorithm: Optional[str] = None,
                  headers: Optional[Dict] = None) -> pathlib.Path:
    logger.debug(f'Attempting to provide file from URL (download or return from cache): {file_url}')

    from ..utils import DownloadFileManager
    dfm = DownloadFileManager()

    existing_filename = dfm.get(checksum=checksum, filename=filename)
    if existing_filename:
        # checksum has been verified before because file is in cache
        return existing_filename

    if target_folder is None:
        from ..user import CACHE_DIR
        target_folder = CACHE_DIR
    else:
        logger.debug(f'A target folder was specified. Downloading file to this folder: {target_folder}')
        target_folder = pathlib.Path(target_folder)

    if checksum:
        target_filename = target_folder / checksum / filename
    else:
        target_filename = target_folder / f"{uuid.uuid4().hex}" / filename

    if not target_filename.parent.exists():
        target_filename.parent.mkdir(exist_ok=True, parents=True)

    # ---- helpers: session w/ retry, auth headers, resolve Zenodo links.content ----
    def _make_session() -> requests.Session:
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry = Retry(
            total=8,
            connect=4,
            read=4,
            status=8,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD"]),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        sess = requests.Session()
        adapter = HTTPAdapter(max_retries=retry)
        sess.mount("https://", adapter)
        sess.mount("http://", adapter)
        return sess

    def _merge_headers(headers_in: Optional[Dict], token: Optional[str]) -> Dict:
        h = dict(headers_in or {})
        # Zenodo-recommended style; still keep query-param fallback below.
        if token and "Authorization" not in h:
            h["Authorization"] = f"Bearer {token}"
        if "User-Agent" not in h:
            h["User-Agent"] = "download_file/1.0"
        return h

    def _get_with_fallback(sess: requests.Session, url: str, stream: bool, h: Dict):
        # timeouts: (connect timeout, read timeout)
        timeout = (15, 120)

        # 1) try with headers (Authorization if available)
        r = sess.get(url, stream=stream, headers=h, timeout=timeout, allow_redirects=True)

        # 2) if forbidden/unauthorized and we have a token, try query param fallback
        if r.status_code in (401, 403) and access_token:
            r.close()
            r = sess.get(
                url,
                stream=stream,
                params={"access_token": access_token},
                headers=h,
                timeout=timeout,
                allow_redirects=True,
            )
        return r

    def _resolve_content_url(sess: requests.Session, url: str, h: Dict) -> str:
        """
        If url points to Zenodo JSON (record/metadata), and it contains links.content,
        download from that content link instead.
        """
        try:
            r = _get_with_fallback(sess, url, stream=False, h=h)
            # don't raise here; we only want to resolve if it is JSON and valid
            ctype = (r.headers.get("Content-Type") or "").lower()
            if r.ok and "application/json" in ctype:
                try:
                    j = r.json()
                except Exception:
                    return url
                if isinstance(j, dict):
                    links_content = (j.get("links") or {}).get("content")
                    if links_content:
                        return links_content
            return url
        finally:
            try:
                r.close()
            except Exception:
                pass

    sess = _make_session()
    h = _merge_headers(headers, access_token)

    # ---- checksum handling ----
    hasher = None
    expected_checksum_value = None

    if checksum is not None:
        if checksum_algorithm is None:
            if ":" in checksum:
                checksum_algorithm = checksum.split(":", 1)[0].strip().lower()
            else:
                checksum_algorithm = "md5"

        # If checksum has algo:value, compare only to value
        if ":" in checksum:
            _, expected_checksum_value = checksum.split(":", 1)
            expected_checksum_value = expected_checksum_value.strip().lower()
        else:
            expected_checksum_value = checksum.strip().lower()

        try:
            hasher = hashlib.new(checksum_algorithm)
        except ValueError:
            raise ValueError(f"Unsupported checksum algorithm: {checksum_algorithm}")

    # ---- always resolve to content URL if needed; then stream download ----
    content_url = _resolve_content_url(sess, file_url, h)

    # Use a temp file then atomic replace to avoid partial files in cache on failures
    tmp_filename = target_filename.with_suffix(target_filename.suffix + ".part")

    try:
        with _get_with_fallback(sess, content_url, stream=True, h=h) as response:
            response.raise_for_status()

            chunk_size = 1024 * 1024  # 1 MiB

            with open(tmp_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    if hasher:
                        hasher.update(chunk)

        # Move into place only after success
        tmp_filename.replace(target_filename)

        assert target_filename.exists(), f"File {target_filename} does not exist."
        logger.debug("Download successful.")

        if hasher:
            file_checksum = hasher.hexdigest().lower()
            if expected_checksum_value and file_checksum != expected_checksum_value:
                warnings.warn(
                    f"Checksum mismatch for {target_filename}: expected {expected_checksum_value}, got {file_checksum}",
                    RuntimeWarning
                )
                logger.error(
                    f"Checksum mismatch for {target_filename}: expected {expected_checksum_value}, got {file_checksum}"
                )
            else:
                logger.debug("Checksum verification successful.")

    finally:
        # Cleanup partial file if it exists
        try:
            if tmp_filename.exists():
                tmp_filename.unlink()
        except Exception:
            pass

    dfm.add(checksum=checksum,
            url=file_url,
            filepath=target_filename,
            filename=filename)
    return target_filename

