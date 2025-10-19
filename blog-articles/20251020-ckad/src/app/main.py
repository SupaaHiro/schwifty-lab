from fastapi import FastAPI
import json
import uvicorn

app = FastAPI()

def load_metadata():
    try:
        with open("metadata.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"version": "unknown", "build": "n/a", "commit": "n/a"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/version")
async def version():
    return load_metadata()

if __name__ == "__main__":
    uvicorn.run("app:app", port=8000, reload=True)