import requests

from h5rdmtoolbox.repository.zenodo.tokens import get_api_token


def delete_sandbox_deposits():
    """Delete all deposits in the sandbox account."""
    depositions_url = 'https://sandbox.zenodo.org/api/deposit/depositions?'

    response = requests.get(depositions_url, params={'access_token': get_api_token(sandbox=True)}).json()
    n_unsubmitted = sum([not hit['submitted'] for hit in response])
    while n_unsubmitted > 0:
        for hit in response:
            if not hit['submitted']:
                delete_response = requests.delete(hit['links']['latest_draft'],
                                                  params={'access_token': get_api_token(sandbox=True)})
                delete_response.raise_for_status()
        response = requests.get(depositions_url, params={'access_token': get_api_token(sandbox=True)}).json()
        n_unsubmitted = sum([not hit['submitted'] for hit in response])


if __name__ == '__main__':
    delete_sandbox_deposits()
