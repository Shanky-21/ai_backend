from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def health():
    return {"status": "ok", "message": "Hackathon backend is running"}
