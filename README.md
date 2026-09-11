# Secure Mail Dispatch Microservice

An enterprise-grade, asynchronous email dispatch microservice built with **Python** and **Flask**. Originally developed during an Accenture Security Team internship, the architecture decouples high-speed API ingestion from high-latency SMTP network execution — ensuring fault tolerance, concurrent processing, and strict Machine-to-Machine (M2M) security.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Key Engineering Features](#key-engineering-features)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Running the Service](#running-the-service)
- [API Documentation](#api-documentation)
- [Testing Concurrency (Load Simulation)](#testing-concurrency-load-simulation)

---

## System Architecture

The system uses a decoupled **Controller-Service** layered architecture, splitting responsibilities across three components:

| Component | Responsibility |
|---|---|
| **Flask API Gateway** | Intercepts multipart POST requests, authenticates the calling machine via JWT, sanitizes incoming file attachments to prevent path traversal, and writes job metadata to a MySQL database. |
| **MySQL Message Queue** | Acts as a durable, persistent buffer — pending emails survive a server crash since they're never held only in memory. |
| **Parallel Worker Engine** | A background process using a `ThreadPoolExecutor` that continuously polls the database for `Queued` jobs, fetches batches concurrently, constructs the MIME multi-part payload, and dispatches via SMTP over TLS. |

---

## Key Engineering Features

- **Pessimistic Row Locking (`FOR UPDATE SKIP LOCKED`)** — Prevents race conditions during parallel processing by placing an exclusive write-lock on fetched rows, forcing concurrent threads to grab the next available batch without duplicate dispatches.
- **M2M JWT Authentication** — Enforces strict access control; the API requires the symmetric HS256 algorithm during decoding to prevent algorithm confusion attacks.
- **File Name Sanitization** — Defends against directory traversal and naming collisions by stripping dangerous characters and appending unique UUIDs to all temporarily buffered attachments.
- **Zombie Job Reclamation** — A self-healing timeout mechanism that detects jobs stuck in `Processing` due to mid-execution thread crashes and resets them to `Failed` for automatic retry.
- **Synchronous Chunking** — Limits memory exhaustion (OOM) by ensuring the main polling loop only fetches as many jobs as there are idle threads in the pool.

---

## Prerequisites

- Python 3.9+
- MySQL Server 8.0+
- A Gmail account with 2-Step Verification enabled (to generate an App Password)

---

## Setup & Installation

### 1. Clone the repository and initialize the virtual environment

```bash
git clone https://github.com/yourusername/mail-dispatch-service.git
cd mail-dispatch-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database configuration

Open your MySQL client (e.g., MySQL Workbench) and create the dedicated database:

```sql
CREATE DATABASE mail_dispatch_db;
```

### 3. Environment variables

Create a `.env` file in the root directory. **Never commit this file to version control.**

```env
# Flask Core
FLASK_APP=run_api.py
FLASK_ENV=development
MAX_CONTENT_LENGTH_MB=16

# Security
JWT_SECRET=your_super_secret_master_key

# MySQL Database
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=mail_dispatch_db

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_dummy_email@gmail.com
SMTP_APP_PASSWORD=your_16_character_app_password
```

---

## Running the Service

The microservice requires the API and the Worker engine to run **simultaneously in separate OS processes**.

**Terminal 1 — Start the API Gateway**

```bash
python run_api.py
```
> On first run, `init_db()` automatically connects to MySQL and builds the `Dispatch_Audit_Log` schema.

**Terminal 2 — Start the Parallel Worker Engine**

```bash
python run_worker.py
```
> You'll see the orchestrator boot up the thread pool and begin sleep-polling the database.

**Terminal 3 — Generate an Authentication Token**

Because this is an M2M service, there is no login endpoint — you must generate a secure token to authenticate requests.

```bash
python generate_token.py
```
Copy the `Bearer <token>` string output to your clipboard.

---

## API Documentation

### `POST /api/v1/mail/dispatch`

Ingests an email job into the asynchronous queue.

**Headers**

| Header | Value |
|---|---|
| `Authorization` | `Bearer <your_jwt_token>` |
| `Content-Type` | `multipart/form-data` |

**Form-Data Body**

| Key | Type | Description | Required |
|---|---|---|---|
| `to` | Text | Recipient email address | Yes |
| `subject` | Text | Email subject line | Yes |
| `body` | Text | HTML or plain text email body | No |
| `attachments` | File | Files to attach (PDF, JPG, TXT, CSV). Max 16MB total. | No |

**Success Response — `202 Accepted`**

```json
{
  "status": "queued",
  "job_id": 14,
  "message": "Email job successfully ingested into the dispatch queue."
}
```

---

## Testing Concurrency (Load Simulation)

To observe pessimistic locking and parallel threads in action, use the included load generator script. Ensure both `run_api.py` and `run_worker.py` are active.

```bash
python simulate_clients.py
```

**What to look for:**

1. The script instantly fires 15 concurrent POST requests to the API.
2. The Flask terminal shows 15 rapid `HTTP 202 Accepted` responses.
3. The Worker terminal shows the thread pool grab batches of 5 distinct jobs simultaneously, process SMTP handshakes out-of-order (based on network latency), and clean up temporary files — with zero duplicate dispatches.
