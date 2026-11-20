PY  = backend/.venv/bin/python

setup:            ## create the venv and install everything
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install -r backend/requirements-dev.txt
	cd frontend && npm install

setup-live:       ## extra deps for real scrapers (Playwright + Chromium)
	backend/.venv/bin/pip install -r backend/requirements-live.txt
	backend/.venv/bin/playwright install chromium

backend:          ## API on http://127.0.0.1:8000 (also runs the background crawler)
	cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:         ## UI dev server on http://127.0.0.1:5173
	cd frontend && npm run dev

dev:              ## backend + frontend together
	$(MAKE) -j2 backend frontend

build:            ## build the UI so the backend serves it at http://127.0.0.1:8000
	cd frontend && npm run build

crawl:            ## one crawl in the foreground, e.g. make crawl AIRLINES=UA,WN
	cd backend && .venv/bin/python -m app.cli crawl $(if $(AIRLINES),--airlines $(AIRLINES))

test:
	cd backend && .venv/bin/pytest -q

.PHONY: setup setup-live backend frontend dev build crawl test
