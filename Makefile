PYTHON=python3
PYTHON_ENV_ROOT=envs
PYTHON_PACKAGING_VENV=$(PYTHON_ENV_ROOT)/$(PYTHON)-packaging-env
PYTHON_TESTING_ENV=$(PYTHON_ENV_ROOT)/$(PYTHON)-qa-env

.PHONY: clean

# packaging environment #######################################################
$(PYTHON_PACKAGING_VENV)/.created:
	rm -rf $(PYTHON_PACKAGING_VENV) && \
	$(PYTHON) -m venv $(PYTHON_PACKAGING_VENV) && \
	. $(PYTHON_PACKAGING_VENV)/bin/activate && \
	python3 -m pip install --upgrade pip && \
	python3 -m pip install build && \
	date > $(PYTHON_PACKAGING_VENV)/.created

.PHONY: packaging-env build

packaging-env: $(PYTHON_PACKAGING_VENV)/.created

build: packaging-env
	. $(PYTHON_PACKAGING_VENV)/bin/activate && \
	rm -rf dist *.egg-info && \
	python3 -m build


# helper ######################################################################
clean:
	rm -rf $(PYTHON_ENV_ROOT)

envs: env packaging-env


# testing #####################################################################
$(PYTHON_TESTING_ENV)/.created:
	rm -rf $(PYTHON_TESTING_ENV) && \
	$(PYTHON) -m venv $(PYTHON_TESTING_ENV) && \
	. $(PYTHON_TESTING_ENV)/bin/activate && \
	python3 -m pip install pip --upgrade && \
	python3 -m pip install ruff codespell && \
	date > $(PYTHON_TESTING_ENV)/.created

.PHONY: qa qa-codespell qa-codespell-fix qa-ruff qa-ruff-fix

qa: qa-codespell qa-ruff

qa-codespell: $(PYTHON_TESTING_ENV)/.created
	. $(PYTHON_TESTING_ENV)/bin/activate && \
	codespell

qa-codespell-fix: $(PYTHON_TESTING_ENV)/.created
	. $(PYTHON_TESTING_ENV)/bin/activate && \
	codespell -w

qa-ruff: $(PYTHON_TESTING_ENV)/.created
	. $(PYTHON_TESTING_ENV)/bin/activate && \
	ruff format --check --diff && ruff check

qa-ruff-fix: $(PYTHON_TESTING_ENV)/.created
	. $(PYTHON_TESTING_ENV)/bin/activate && \
	ruff format && ruff check --fix
