cd ..
pytest --cov=h5rdmtoolbox --cov-report=html

cd tests

start ../htmlcov/index.html
