PYTHON=python3.7
EXTRAS=all

.PHONY: all sync clean

all: venv requirements.txt dev-requirements.txt sync .git/hooks/pre-commit .git/hooks/pre-push

venv:
	$(PYTHON) -m venv venv
	venv/bin/pip install pip-tools==6.4.0 pip==21.3

requirements.txt: setup.py
	venv/bin/pip-compile --extra $(EXTRAS)

dev-requirements.txt: dev-requirements.in requirements.txt
	venv/bin/pip-compile dev-requirements.in

sync: venv requirements.txt dev-requirements.txt
	venv/bin/pip-sync requirements.txt dev-requirements.txt

.git/hooks/pre-commit: .pre-commit-config.yaml
	venv/bin/pre-commit install -t pre-commit
	venv/bin/pre-commit run --all-files --hook-stage commit

.git/hooks/pre-push: .pre-commit-config.yaml
	venv/bin/pre-commit install -t pre-push
	venv/bin/pre-commit run --all-files --hook-stage push

clean:
	rm -rf venv
