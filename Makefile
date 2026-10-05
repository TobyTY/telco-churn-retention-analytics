# Rebuild everything from the raw download: `make all`. Each step can also run alone.
# Uses .venv if present, otherwise the python on PATH.

ifneq (,$(wildcard .venv/Scripts/python.exe))
PY ?= .venv/Scripts/python.exe
else ifneq (,$(wildcard .venv/bin/python))
PY ?= .venv/bin/python
else
PY ?= python
endif

CHECK_FILES = README.md reports/executive_summary.md reports/insights_and_recommendations.md \
              docs/interview_talking_points.md docs/assumptions.md docs/model_card.md docs/project_brief.md data/README.md dashboard/index.html

.PHONY: all data warehouse audit cleaning eda analysis model excel dashboard screenshots powerbi reports notebooks test check clean distclean

all: data warehouse audit cleaning eda analysis model excel dashboard screenshots reports notebooks test check

data:
	$(PY) -m src.download

warehouse:
	$(PY) -m src.warehouse

audit:
	$(PY) -m src.audit

cleaning:
	$(PY) -m src.clean

eda:
	$(PY) -m src.eda

analysis:
	$(PY) -m src.analysis

model:
	$(PY) -m src.model

excel:
	$(PY) -m src.excel_build
	$(PY) -m src.excel_verify

dashboard:
	$(PY) -m src.dashboard_build

screenshots:
	$(PY) tools/screenshot.py dashboard/index.html reports/figures/dashboard

powerbi:
	$(PY) -m src.powerbi_export

reports:
	$(PY) -m src.report_build

notebooks:
	$(PY) -m src.notebooks_build

test:
	$(PY) -m pytest -q

check:
	$(PY) tools/check_numbers.py --facts reports/facts.json --files $(CHECK_FILES)

# Remove everything the pipeline generates (keeps the downloaded raw data).
clean:
	rm -rf data/warehouse.duckdb data/warehouse.duckdb.wal data/processed/*.parquet reports/facts.json reports/*.csv reports/*.json \
	       reports/sql_outputs/*.csv reports/figures/*.png reports/executive_summary.md reports/insights_and_recommendations.md \
	       excel/*.xlsx dashboard/index.html docs/index.html notebooks/*.ipynb powerbi/export .pytest_cache

# Also remove the raw download.
distclean: clean
	rm -rf data/raw/*.csv data/raw/_source.json
