def recid_from_doi_or_redid(doi_or_recid: str) -> int:
    """Returns the recid from a doi or recid"""
    if isinstance(doi_or_recid, int):
        rec_id = doi_or_recid
    elif isinstance(doi_or_recid, str):
        if '/' in doi_or_recid:
            _tmp = doi_or_recid.rsplit('/', 1)[-1]
            if _tmp.startswith('zenodo'):
                rec_id = int(_tmp.split('.')[-1])
            else:
                rec_id = int(_tmp)
        else:
            rec_id = int(doi_or_recid)
    else:
        raise TypeError(f'Expected int or str, got {type(doi_or_recid)}')
    return rec_id
