from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.routes import router
from pathlib import Path

app = FastAPI(title="Szuru Importer")
app.include_router(router, prefix="/api")

# Static files
static_dir = Path(__file__).parent / 'static'
if static_dir.exists():
    app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')

# Templates
templates_dir = Path(__file__).parent / 'templates'
templates = Jinja2Templates(directory=str(templates_dir))

@app.get('/health')
async def health_check():
    return {"status": "healthy", "service": "szuru-webtools"}

@app.get('/')
async def import_page(request: Request):
    return templates.TemplateResponse("import.html", {"request": request})

@app.get('/tag-tools')
async def tag_tools_page(request: Request):
    return templates.TemplateResponse("tag-tools.html", {"request": request})

@app.get('/healthz')
async def health():
    return {"status":"ok"}
