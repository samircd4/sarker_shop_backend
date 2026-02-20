# 🚀 Redis + Celery Integration Guide for Sarker Shop

## Why We Need This

Currently, every email (order confirmation, password reset, welcome email) **blocks the API response** for 1.5–10 seconds while Django waits for the SMTP server to finish. With Celery + Redis, emails are queued and sent in the background — the user gets an instant response.

---

## ⏱️ Performance Comparison

| Action | Current | After Redis |
|---|---|---|
| Order confirmation | 1.5–3s | **~55ms** |
| Password reset | 1.5–3s | **~55ms** |
| Email verification | 1.5–3s | **~55ms** |
| Bad network day | 5–10s | **~55ms** |

---

## 🏗️ Architecture Overview

```mermaid
graph LR
    A[User Request] --> B[Django View]
    B --> C{Queue Task}
    C --> D[(Redis Broker)]
    B --> E[Instant Response ✅]
    D --> F[Celery Worker]
    F --> G[smtp.hostinger.com]
    G --> H[User's Inbox 📧]
```

---

## 📦 Step 1: Install Redis on Windows

You have three options. **Option C is the easiest to start with.**

### Option A: WSL2 (Best for Development)

1. Open PowerShell as Administrator and run:

   ```powershell
   wsl --install
   ```

2. After WSL2 is set up, open Ubuntu terminal and run:

   ```bash
   sudo apt update && sudo apt install redis-server
   sudo service redis-server start
   ```

3. Test it works: `redis-cli ping` → should return `PONG`

### Option B: Docker

```powershell
docker run -d -p 6379:6379 --name sarker-redis redis:alpine
```

### Option C: Upstash (Cloud Redis — No Installation!)

1. Go to [upstash.com](https://upstash.com) and create a free account
2. Create a new Redis database (free tier: 10,000 commands/day)
3. Copy the **Redis URL** — it looks like: `rediss://default:password@host.upstash.io:6379`
4. No installation needed — works from anywhere

> [!TIP]
> For local development, WSL2 is recommended. For production/quick start, use Upstash.

---

## 📦 Step 2: Add Python Packages

Add these to your `pyproject.toml` under `[project] dependencies`:

```toml
"celery[redis]>=5.3",
"django-celery-results>=2.5",
```

Then run:

```powershell
uv sync
```

---

## 📁 Step 3: Create `celery.py`

**New file:** `backend/ecommerce_api/celery.py`

This file initializes the Celery application and connects it to Redis.

```python
import os
from celery import Celery

# Tell Celery which Django settings to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_api.settings')

app = Celery('ecommerce_api')

# Load config from Django settings (keys starting with CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in all installed apps
app.autodiscover_tasks()
```

---

## 📁 Step 4: Update `__init__.py`

**Edit:** `backend/ecommerce_api/__init__.py`

Add these lines so Celery loads when Django starts:

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

---

## ⚙️ Step 5: Update `settings.py`

Add these lines to your `backend/ecommerce_api/settings.py`:

```python
# ========================
# Celery Configuration
# ========================
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'  # Stores results in your SQLite/Postgres DB
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Dhaka'

# Add to INSTALLED_APPS:
# 'django_celery_results',
```

Also add `'django_celery_results'` to your `INSTALLED_APPS` list.

---

## 📁 Step 6: Create `tasks.py` Files

### `backend/accounts/tasks.py` (New File)

This is where you move all email-sending logic out of views:

```python
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

@shared_task
def send_welcome_email_task(full_name, email, verify_link):
    """Send welcome email in the background."""
    html_content = render_to_string('emails/welcome_email.html', {
        'full_name': full_name,
        'verify_link': verify_link,
    })
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(
        subject="Welcome to Sarker Shop!",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=True)

@shared_task
def send_password_reset_email_task(email, reset_link):
    """Send password reset email in the background."""
    # ... same pattern as above
    pass
```

### `backend/orders/tasks.py` (New File)

```python
from celery import shared_task

@shared_task
def send_order_confirmation_email_task(order_id, customer_email):
    """Send order confirmation email in the background."""
    # Fetch order from DB and send email
    pass
```

---

## ✏️ Step 7: Update Views to Use `.delay()`

This is the **only change** to your existing view logic. It's a one-line swap.

### In `backend/accounts/views.py`

**Before (blocking):**

```python
# This blocks the response for 1.5–3 seconds
email_message.send(fail_silently=True)
return Response({"message": "Registered successfully"})
```

**After (instant):**

```python
from accounts.tasks import send_welcome_email_task

# This returns instantly — email sent in background
send_welcome_email_task.delay(full_name, email, verify_link)
return Response({"message": "Registered successfully"})
```

The `.delay()` method is the key — it pushes the task to Redis and returns immediately.

---

## 🗄️ Step 8: Run Database Migration

Since `django-celery-results` stores task results in the database:

```powershell
uv run manage.py migrate
```

---

## 🖥️ Step 9: Update `.env`

Add your Redis URL to `backend/.env`:

```bash
# For local WSL2/Docker Redis:
REDIS_URL=redis://localhost:6379/0

# For Upstash (cloud):
REDIS_URL=rediss://default:your-password@your-host.upstash.io:6379
```

---

## 🚦 Running Everything

You now need **3 terminals** running simultaneously:

### Terminal 1 — Django Server

```powershell
cd backend
uv run manage.py runserver
```

### Terminal 2 — Celery Worker

```powershell
cd backend
uv run celery -A ecommerce_api worker --loglevel=info
```

### Terminal 3 — Redis (if using WSL2)

```bash
# In WSL2 Ubuntu terminal
sudo service redis-server start
```

> [!NOTE]
> If using Upstash (cloud Redis), you don't need Terminal 3 — Redis is always running in the cloud.

---

## 📋 Summary of All Files Changed

| File | Type | Change |
|---|---|---|
| `pyproject.toml` | Modify | Add `celery[redis]` and `django-celery-results` |
| `ecommerce_api/celery.py` | **New** | Celery app initialization |
| `ecommerce_api/__init__.py` | Modify | Import Celery app |
| `ecommerce_api/settings.py` | Modify | Add Celery config + `django_celery_results` to INSTALLED_APPS |
| `backend/.env` | Modify | Add `REDIS_URL` |
| `accounts/tasks.py` | **New** | Email task functions |
| `accounts/views.py` | Modify | Replace `email.send()` with `task.delay()` |
| `orders/tasks.py` | **New** | Order email task functions |
| `orders/views.py` | Modify | Replace `email.send()` with `task.delay()` |

---

## 🔍 How to Verify It's Working

After setup, when a user registers:

1. The API response comes back **instantly** (< 100ms)
2. In your **Celery terminal**, you'll see:

   ```
   [INFO] Task accounts.tasks.send_welcome_email_task received
   [INFO] Task accounts.tasks.send_welcome_email_task succeeded in 2.3s
   ```

3. The user receives the email a few seconds later

---

## ⚠️ Important Notes

> [!IMPORTANT]
> Celery tasks must receive **simple data types** (strings, numbers, lists, dicts) — not Django model objects. Pass `user.id` or `user.email`, not the `user` object itself.

> [!WARNING]
> If the Celery worker is not running, tasks will pile up in Redis and be processed when the worker starts again. They are **not lost**.

> [!TIP]
> For production deployment (e.g., on a VPS), you'd run Celery as a systemd service so it starts automatically with the server.
