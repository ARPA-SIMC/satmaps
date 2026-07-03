PYTHON_ENVIRONMENT := PYTHONASYNCDEBUG=1 PYTHONDEBUG=1

check: flake8 mypy

format: pyupgrade autoflake isort black 

pyupgrade:
	pyupgrade --exit-zero-even-if-changed --py312-plus $(shell find satmaps -name "*.py")

black:
	black satmaps

autoflake:
	autoflake --in-place --recursive satmaps

isort:
	isort satmaps

flake8:
	flake8 satmaps

mypy:
	mypy

unittest:
	$(PYTHON_ENVIRONMENT) pytest

coverage:
	$(PYTHON_ENVIRONMENT) pytest --cov=egtlib --cov-report html 

.PHONY: check pyupgrade black mypy unittest coverage
