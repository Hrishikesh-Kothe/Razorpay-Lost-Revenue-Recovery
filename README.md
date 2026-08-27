# Razorpay Lost Revenue Recovery

AI-assisted payment-failure recovery PoC: Razorpay webhook → LangGraph classification/policy/recovery → merchant dashboard + email outreach.

## Quick start (Docker)

1. Ensure `backend/.env` exists (copy from `backend/.env.example`) with your Razorpay keys:

```env
RZP_KEY_ID=...
RZP_KEY_SECRET=...
DATABASE_URL=sqlite:///./recovery.db
EMAIL_SEND_LIVE=false
```

2. From the repo root:

```bash
docker compose up --build
```

3. Open:

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- Health: http://localhost:8000/

`backend/.env` is loaded by Compose and is **never** baked into images. SQLite data persists in the `backend-data` volume.

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional: copy `frontend/.env.example` to `frontend/.env.local` and set `NEXT_PUBLIC_API_URL`.

## Demo tips

1. POST a failure to `/webhooks/razorpay` (or use the seed script).
2. Open the dashboard → Live Execution → click a transaction.
3. Use **STOP recovery** in the drawer to demo opt-out guardrails.
4. Keep `EMAIL_SEND_LIVE=false` unless you intentionally want Resend to send real mail.

## Tests

```bash
cd backend
.\venv\Scripts\python.exe -m pytest -v
```

## Deployment

### Backend → Render

1. Create a **Web Service** from this repo.
2. Dockerfile path: `backend/Dockerfile` (or use root `render.yaml`).
3. Add a **PostgreSQL** database and set `DATABASE_URL` from Render.
4. Set env vars (see `backend/.env.example`):
   - `RZP_KEY_ID`, `RZP_KEY_SECRET`
   - `CORS_ORIGINS=https://YOUR_VERCEL_APP.vercel.app`
   - `EMAIL_*` as needed (`EMAIL_SEND_LIVE=false` recommended)
5. Health check: `GET /`
6. Point Razorpay webhooks to: `https://YOUR_API.onrender.com/webhooks/razorpay`

### Frontend → Vercel

1. Import the repo in Vercel.
2. Root directory: `frontend`
3. Framework: Next.js
4. Env:
   - `NEXT_PUBLIC_API_URL=https://YOUR_API.onrender.com`
5. Deploy, then update backend `CORS_ORIGINS` to the Vercel URL.

## Notes

- Do not commit `backend/.env` or `*.db`.
- Use `backend/.env.example` and `frontend/.env.example` as templates only.
- `/razorpay-test` is disabled unless `ENABLE_RAZORPAY_TEST=true`.
