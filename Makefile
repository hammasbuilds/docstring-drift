# One command per thing a reader wants to do.
.PHONY: demo test lint scan clean

demo:            ## run the scanner on this repo and print every finding
	python demo.py

test:            ## the full suite
	python -m pytest -q

lint:
	ruff check src tests demo.py

scan:            ## scan an installed package: make scan PKG=transformers
	python demo.py $(PKG)

clean:
	rm -rf .pytest_cache **/__pycache__
