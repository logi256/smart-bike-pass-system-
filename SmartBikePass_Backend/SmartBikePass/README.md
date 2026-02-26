# 🚲 Smart Bike Pass System — Backend

A full-stack digital bike pass approval system built with **Python Flask + SQLite**.

---

## 📁 Project Structure

```
SmartBikePass/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── instance/
│   └── smartbike.db        # SQLite database (auto-created on first run)
├── uploads/                # Uploaded documents (auto-created)
└── templates/
    ├── base.html           # Shared layout
    ├── index.html          # Home page
    ├── apply.html          # Student application form
    ├── status.html         # Application status tracker
    ├── login.html          # Staff login page
    ├── transport.html      # Transport in-charge dashboard
    ├── principal.html      # Principal approval dashboard
    ├── admin.html          # Admin dashboard
    ├── approved.html       # Approved pass with QR code
    └── not_found.html      # 404 page
```

---

## ⚙️ Setup & Run

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the server
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## 🔐 Default Credentials

| Role              | Username   | Password       |
|-------------------|------------|----------------|
| Transport In-Charge | transport  | transport123   |
| Principal          | principal  | principal123   |
| Admin              | admin      | admin123       |

> ⚠️ Change these passwords before deploying to production!

---

## 🌊 Approval Workflow

```
Student Applies → Transport Reviews → Principal Approves → QR Pass Issued
     (pending)    (transport_verified)      (approved)
```

| Status                | Meaning                              |
|-----------------------|--------------------------------------|
| `pending`             | Submitted, awaiting transport review |
| `transport_verified`  | Verified by transport, awaiting principal |
| `transport_rejected`  | Rejected by transport                |
| `approved`            | Fully approved, pass issued          |
| `principal_rejected`  | Rejected by principal                |

---

## 📡 API Endpoints

### Public
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/apply` | Submit bike pass application |
| GET | `/api/status/<pass_id>` | Check application status |
| POST | `/api/login` | Staff login |
| GET | `/api/logout` | Logout |

### Transport (Authenticated)
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/transport/applications` | Get pending applications |
| POST | `/api/transport/review/<pass_id>` | Verify or reject |

### Principal (Authenticated)
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/principal/applications` | Get transport-verified applications |
| POST | `/api/principal/review/<pass_id>` | Approve or reject |

### Admin (Authenticated)
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/admin/all` | All applications |
| GET | `/api/admin/stats` | Application statistics |
| GET | `/api/admin/log` | Audit log |

---

## 🗄️ Database Schema

**applications** — All bike pass applications  
**users** — Staff accounts (transport / principal / admin)  
**audit_log** — Full action history for compliance

---

## 🚀 Production Deployment

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

For production, also:
- Set a strong `app.secret_key`
- Use environment variables for credentials
- Use a proper web server (Nginx) as reverse proxy
- Consider migrating to PostgreSQL for scale
