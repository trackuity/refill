PYTHON=python3.7
EXTRAS=all

.PHONY: all sync publish clean

all: venv requirements.txt dev-requirements.txt sync .git/hooks/pre-commit .git/hooks/pre-push

venv:
	$(PYTHON) -m venv venv
	venv/bin/pip install pip-tools==6.4.0 pip==21.3

requirements.txt: venv setup.py
	venv/bin/pip-compile --extra $(EXTRAS)

dev-requirements.txt: dev-requirements.in requirements.txt
	venv/bin/pip-compile dev-requirements.in

sync: requirements.txt dev-requirements.txt
	venv/bin/pip-sync requirements.txt dev-requirements.txt

.git/hooks/pre-commit: dev-requirements.txt .pre-commit-config.yaml
	venv/bin/pre-commit install -t pre-commit
	venv/bin/pre-commit run --all-files --hook-stage commit

.git/hooks/pre-push: dev-requirements.txt .pre-commit-config.yaml
	venv/bin/pre-commit install -t pre-push
	venv/bin/pre-commit run --all-files --hook-stage push

dist: sync
	venv/bin/python setup.py sdist bdist_wheel

publish: dist
	venv/bin/twine upload dist/*

clean:
	rm -rf venv dist build
