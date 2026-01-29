from fastapi import FastAPI, HTTPException
import time

app = FastAPI()

# Start timestamp
start_time = time.time()

@app.get("/healthz")
def health_check():
    uptime = time.time() - start_time

    # After 30 seconds, simulate a logical crash
    if uptime > 30:
        raise HTTPException(status_code=500, detail="Service unhealthy (simulated failure)")

    return {"status": "ok", "uptime_seconds": int(uptime)}
