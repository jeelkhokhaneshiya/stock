# Deployment Guide

This document outlines the deployment process for the AI Investment System.

## **CRITICAL SAFETY WARNING: READ-ONLY SYSTEM**
> **This system is explicitly configured for READ-ONLY operations with Angel One.**
> **Live trading is strictly DISABLED at the architecture level.**
> Do NOT change safety flags in production to enable trading.
> Buy/Sell/Modify/Cancel functionalities do not exist and must not be forced.

---

## 1. Backend Deployment Requirements

The backend is a FastAPI application that requires Python 3.10+.
It can be deployed to services like Render, Heroku, AWS ECS, or a simple VPS.

### Server Configuration
- The backend should be started using `uvicorn`.
- Do not hardcode ports; use the `PORT` environment variable provided by your host.
- Startup Command:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

### PostgreSQL Database Configuration
In development, SQLite is used. For production, you **MUST** provide a valid PostgreSQL connection string.
- Environment Variable: `DATABASE_URL`
- Format: `postgresql://username:password@hostname:port/database_name`

### CORS Configuration
In production, you must restrict CORS to your exact frontend domain to prevent unauthorized clients from interacting with the backend.
- Environment Variable: `FRONTEND_ORIGIN`
- Example: `FRONTEND_ORIGIN=https://my-dashboard-app.com`

---

## 2. Frontend Deployment Requirements

The frontend is a React application built with Vite. It requires Node.js for building the static assets.
It can be deployed to static hosting services like Vercel, Netlify, or AWS S3.

### Production API Configuration
In development, Vite proxies requests to the local backend. In production, the static assets need to know the absolute URL of the backend.
- Environment Variable: `VITE_API_BASE_URL`
- Example: `VITE_API_BASE_URL=https://api.my-dashboard-app.com/api/v1`

### Build Command
```bash
npm install
npm run build
```
The output will be generated in the `dist/` directory, which can be served by any static web server (NGINX, Caddy, Apache).

---

## 3. Required Environment Variables

Below is the complete list of variables required to run the backend in production. You must set these in your hosting provider's dashboard or via a `.env` file for Docker.

| Variable Name | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `FRONTEND_ORIGIN` | Allowed origin for CORS | `https://my-dashboard-app.com` |
| `SECRET_KEY` | High-entropy random string for JWTs | `(use a secure 256-bit random string)` |
| `PORT` | The port the server binds to | `8000` |

### Angel One Environment Variables
To authenticate with the Angel One SmartAPI, provide the following variables securely:
| Variable Name | Description |
|---|---|
| `ANGEL_ONE_API_KEY` | SmartAPI Key |
| `ANGEL_ONE_CLIENT_ID` | Client Code / User ID |
| `ANGEL_ONE_PASSWORD` | Account Password (PIN) |
| `ANGEL_ONE_TOTP_SECRET` | TOTP authenticator secret string |

---

## 4. Health and Readiness Checks

For load balancers or container orchestrators (like Kubernetes), configure the following probes:

- **Liveness Probe**: `GET /api/v1/health`
  - Returns HTTP 200 `{"status": "ok", "database": "connected"}` if the server is up and the DB is reachable.
  - Returns HTTP 503 if the database drops.

- **Readiness Probe**: `GET /api/v1/ready`
  - Returns HTTP 200 `{"status": "ready"}`.
  - Returns HTTP 503 if the mandatory safety flags have been tampered with or if dependencies are offline.

---

## 5. Security Requirements
1. **Never commit `.env` or `local_dev.db` to Git.** A strict `.gitignore` is provided.
2. **Security Headers** (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`) are natively enforced by the backend middleware.
3. **Secret Non-Exposure:** The backend strictly isolates all Angel One secrets. The frontend communicates entirely using application-level JWTs. No broker keys are sent over the wire to the browser.
