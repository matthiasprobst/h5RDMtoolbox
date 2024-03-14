# Testing

Go to the repository directory. For running all tests call

    pytest

To get a coverage report run (you need the package `pytest-cov`):

    pytest --cov --cov-report html

This will create a folder `covhtml/` with an `index.html` file in it.

Also, you might want to run `pylint` (static code analysis):

    pylint h5rdmtoolbox --output=.pylint

Please request testdata from the author as long it is not shipped with the repo.

For a full test run in anaconda starting from cloning the repo, copy the following to your prompt:

```bash
git clone https://github.com/matthiasprobst/h5RDMtoolbox
conda create -n h5rdmtoolbox-tests -y python=3.8
conda activate h5rdmtoolbox-tests
pip install h5rdmtoolbox[complete]
pytest --cov --cov-report html
conda deactivate
conda env remove -n h5rdmtoolbox-tests
```

## Notes about Zenodo

To test the zenodo repo, you need the environment variable `ZENODO_SANDBOX_API_TOKEN`:
under linux:

```bash
export ZENODO_SANDBOX_API_TOKEN=your_token
```

under windows:

```bash
set ZENODO_SANDBOX_API_TOKEN=your_token
```

Or add the zenodo.ini file in the local directory (`pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'zenodo.ini'`)
with the following content:

```ini
[zenodo]
api_token = your_token

[zenodo:sandbox]
api_token = your_token
```

