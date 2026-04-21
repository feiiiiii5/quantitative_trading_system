.PHONY: run test install clean-cache

run:
	streamlit run app.py

test:
	python test_imports.py && python test_engine.py

install:
	pip install -r requirements.txt

clean-cache:
	rm -rf data/cache/*.parquet data/cache/cache_index.json
