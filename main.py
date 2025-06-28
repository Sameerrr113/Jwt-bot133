from fastapi import FastAPI, Request, HTTPException
import httpx, os, json, jwt, time, logging

app = FastAPI()
log = logging.getLogger("uvicorn.error")

BOT_TOKEN  = os.getenv("BOT_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY")

if not BOT_TOKEN or not SECRET_KEY:
    raise RuntimeError("BOT_TOKEN and SECRET_KEY must be set as Vercel environment variables.")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def make_jwt(payload: dict) -> str:
    payload = dict(payload)
    payload.setdefault("iat", int(time.time()))
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

async def send(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{TG_API}/sendMessage", json={"chat_id": chat_id, "text": text})
        resp.raise_for_status()

@app.post("/")
async def webhook(req: Request):
    try:
        update = await req.json()
    except Exception as e:
        log.error("Invalid JSON from Telegram: %s", e)
        raise HTTPException(status_code=400, detail="Bad request")

    message = update.get("message") or {}
    chat_id = message.get("chat", {}).get("id")
    text    = message.get("text", "")

    if not chat_id:
        return {"ok": True}

    if text.lower().startswith(("/start", "/help")):
    await send(
        chat_id,
        (
            "👋 JWT Generator Bot\n"
            "Send me any valid JSON and I'll return a signed JWT.\n"
            "Example:\n"
            '{"uid": "123", "role": "tester"}'
        )
    )
    return {"ok": True}

    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").split("\n", 1)[-1]

    try:
        payload = json.loads(stripped)
        token   = make_jwt(payload)
        await send(chat_id, f"`{token}`")
    except json.JSONDecodeError:
        await send(chat_id, "❌ *Invalid JSON.* Please send a proper JSON object.")
    except Exception as exc:
        log.error("Unexpected error: %s", exc)
        await send(chat_id, "⚠️ *Internal error.* Please try again later.")
    return {"ok": True}
