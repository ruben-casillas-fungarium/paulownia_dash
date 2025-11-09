test:
	pytest -q

run:
	streamlit run app.py

zip:
	python scripts/make_zip.py