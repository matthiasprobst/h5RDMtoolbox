# Zenodo repository interface

The Zenodo interface supports access to production and Sandbox repositories.
Supply credentials through environment variables:

- `ZENODO_API_TOKEN` for production.
- `ZENODO_SANDBOX_API_TOKEN` for Sandbox.

Alternatively, store tokens in `UserDir['repository'] / 'zenodo.ini'`, where
`UserDir` is available from `h5rdmtoolbox.user`. The file uses a `[zenodo]` section
for production and a `[zenodo:sandbox]` section for Sandbox, each with an
`access_token` entry. Environment variables take precedence over the file.
Keep tokens and local credential files out of version control.

Validate research data explicitly with `h5rdmtoolbox.validation.validate` before
upload when required by the publication workflow. See the
[repository guide](../../../../docs/userguide/repository/index.rst) for scope and
[testing guide](../../../../tests/README.md) for live Sandbox test requirements.
