"""Manually remove explicitly selected Zenodo Sandbox depositions."""

import argparse

import requests


def delete_sandbox_deposits(deposition_ids):
    """Delete only the supplied positive integer IDs; never enumerate an account.

    All IDs are checked before any requests are made. Duplicate IDs are deleted
    once. Missing credentials and HTTP errors stop the operation immediately.
    """
    if isinstance(deposition_ids, (str, bytes)):
        raise TypeError('Supply an iterable of integer deposition IDs.')
    ids = list(deposition_ids)
    if not ids or any(type(value) is not int or value <= 0 for value in ids):
        raise ValueError('Supply one or more positive integer deposition IDs.')

    from h5rdmtoolbox.repository.zenodo.tokens import get_api_token

    token = get_api_token(sandbox=True)
    if not token:
        raise ValueError('A Zenodo Sandbox API token is required.')
    for deposition_id in dict.fromkeys(ids):
        response = requests.delete(
            f'https://sandbox.zenodo.org/api/deposit/depositions/{deposition_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        response.raise_for_status()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deposition_ids', nargs='+', type=int, help='Sandbox IDs to delete')
    delete_sandbox_deposits(parser.parse_args().deposition_ids)
