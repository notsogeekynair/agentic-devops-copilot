.PHONY: setup test run deploy

setup:
	python -m venv .venv && . ./.venv/Scripts/activate || . ./.venv/bin/activate; pip install -r requirements.txt

test:
	python -m pytest -q

run:
	# Local Lambda test (requires serverless or sam). For now, just a placeholder.
	python -c "print('Run via SAM/Serverless or integrate FastAPI for local dev')"

deploy:
	serverless deploy
