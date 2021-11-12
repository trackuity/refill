.PHONY: all sync clean

all: venv requirements.txt dev-requirements.txt sync

venv:
	python3.7 -m venv venv
	venv/bin/pip install pip-tools==6.4.0 pip==21.3

requirements.txt: setup.py
	venv/bin/pip-compile

dev-requirements.txt: dev-requirements.in requirements.txt
	venv/bin/pip-compile dev-requirements.in

sync: venv requirements.txt dev-requirements.txt
	venv/bin/pip-sync requirements.txt dev-requirements.txt

clean:
	rm -rf venv
