import requests

from h5rdmtoolbox.repository.zenodo.tokens import get_api_token


def delete_sandbox_deposits():
    """Delete all deposits in the sandbox account."""
    r = requests.get(
        'https://sandbox.zenodo.org/api/deposit/depositions',
        params={'access_token': get_api_token(sandbox=True)}
    )
    r.raise_for_status()
    for deposit in r.json():
        try:
            # if deposit['title'].startswith('[test]'):
            if not deposit['submitted']:
                if deposit['title'].startswith('[test]'):
                    print(f'deleting deposit {deposit["title"]} with id {deposit["id"]}')
                    r = requests.delete(
                        'https://sandbox.zenodo.org/api/deposit/depositions/{}'.format(deposit['id']),
                        params={'access_token': get_api_token(sandbox=True)}
                    )
            else:
                print(
                    f'Cannot delete {deposit["title"]} with id {deposit["id"]} because it is already published."'
                )
        except Exception as e:
            pass


if __name__ == '__main__':
    delete_sandbox_deposits()
