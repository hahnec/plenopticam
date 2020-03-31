#!/usr/bin/env bash

# upgrade twine
pip3 install --upgrade twine

# bundle pypi package
python3 setup.py sdist bdist_wheel

# test upload and download
python3 -m twine upload --repository testpypi dist/*
python3 -m pip install --index-url https://test.pypi.org/simple/ plenopticam

# production upload and download
#python3 -m twine upload dist/*
#python3 -m pip install plenopticam
