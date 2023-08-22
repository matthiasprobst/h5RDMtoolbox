@echo off
pytest --cov --cov-report html
@REM pylint h5rdmtoolbox --output=.pylint