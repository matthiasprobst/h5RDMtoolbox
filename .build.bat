pip install --upgrade build
pip install --upgrade twine
python -m build
python -m twine upload dist/*