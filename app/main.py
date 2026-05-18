from fastapi import FastAPI

app = FastAPI()

VERSION = "1.0.0"


@app.get("/")
def root():
    return {"message": "Hello from ArgoCD demo!", "version": VERSION}


@app.get("/health")
def health():
    return {"status": "ok"}
