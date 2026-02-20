# Sarker Shop - Backend Product Requirements Document (PRD)

## 1. Project Overview

**Sarker Shop** is a robust, scalable e-commerce platform backend built with **Django** and **Django Rest Framework (DRF)**. It provides a headless API architecture to support modern frontend frameworks (React/Next.js/Mobile).

### Core Technologies

* **Framework**: Django 5.x
* **API**: Django Rest Framework (DRF) + DRF Spectacular (OpenAPI/Swagger)
* **Authentication**: JWT (JSON Web Tokens) via `rest_framework_simplejwt` + `dj_rest_auth`
* **Database**: SQLite (Dev) / PostgreSQL (Prod ready)
* **Asynchronous Tasks**: Signals for sync & automation

---

## 2. Module Breakdown

### A. Accounts & Authentication (`accounts`)

Handles user management, profiles, security, and address books.

#### Models

1. **Customer**: Extends the default User.
    * *Fields*: `phone_number`, `customer_type` (Retail/Wholesale), `avatar`, `social_avatar_url`.
    * *New*: `is_email_verified` (Boolean) - Synced with Allauth.
2. **Address**: Delivery addresses.
    * *Features*: Chained selects (Division -> District -> SubDistrict), Single Default Address logic.
3. **Location Models**: `Division`, `District`, `SubDistrict` for Bangladesh geo-data.

#### Key Features

* **Unified Auth**: Support for Email/Password and Social Login (Google/Facebook/GitHub).
* **Auto-Healing Verification**: `ResendVerificationEmailView` automatically fixes missing verification records.
* **Bidirectional Sync**: Admin changes to "Verified" status sync to the Auth system, and vice versa.
* **RBAC**: Role-Based Access Control for Staff vs Customers.

#### API Endpoints

* `POST /auth/register/`: User registration.
* `POST /auth/login/`: JWT Token obtain.
* `POST /auth/resend-verification-email/`: Self-service verification.
* `GET/PUT /customers/me/`: Manage own profile.
* `GET/POST /addresses/`: Manage address book.

---

### B. Product Catalog (`products`)

Manages the inventory, categories, and product variations.

#### Models

1. **Category**: Hierarchical (Parent/Child) structure with breadcrumb support.
2. **Brand**: Product manufacturers.
3. **Product**:
    * *Types*: `Simple` or `Variant` (e.g. Phone with Ram/Storage options).
    * *Features*: Auto-generated SKU, Auto-Slug, "SS" prefixed Product ID.
4. **ProductVariant**: Specific combinations (e.g., Red, 64GB) with unique SKUs and stock.
5. **ProductImage**: Gallery with drag-and-drop ordering support.

#### Key Features

* **Dynamic Pricing**:
  * `display_price`: Auto-calculates based on variants.
  * `wholesale_price`: Supported for wholesale customers.
* **Inventory Tracking**: Stock quantity tracked at Variant level.
* **SEO Ready**: Alt text for images, Slugs for URLs.

#### API Endpoints

* `GET /products/`: List with filters (Category, Price, Brand).
* `GET /products/{slug}/`: Detail view.
* `GET /categories/`: Category tree.

---

### C. Order Management (`orders`)

Handles the checkout lifecycle and transaction records.

#### Models

1. **Cart & CartItem**: Persistent shopping cart (Session or User based).
2. **Order**: The final transaction record.
    * *Fields*: Snapshot of Shipping Address (to prevent history loss if user changes address later).
3. **OrderItem**: Snapshot of Product Price at time of purchase.
4. **OrderStatus**: Configurable states (Pending, Shipped, Delivered).
5. **PaymentInfo**: Tracks `transaction_id`, `payment_method` (COD/Stripe), and `is_paid` status.

#### Key Features

* **Snapshotting**: Prices and Addresses are copied to the order to preserve historical accuracy.
* **Guest Checkout**: Supports orders without a user account.
* **Wholesale Logic**: Automatically applies wholesale pricing for wholesale customers.

#### API Endpoints

* `POST /cart/add/`: Add item to cart.
* `POST /orders/checkout/`: Convert Cart to Order.
* `GET /orders/`: Order history.

---

### D. User Engagement (`reviews`, `web`)

Features for community and customer support.

#### Models

1. **Review**: 1-5 Star ratings + Comments.
    * *Automation*: Updates `Product.rating` and `Product.reviews_count` on save.
2. **Question**: Q&A section for products.
3. **ContactMessage**: "Contact Us" form submissions.
4. **NewsletterSubscription**: Email marketing list.

#### API Endpoints

* `POST /reviews/`: Submit a review (Authenticated).
* `GET /reviews/?product={id}`: List reviews for a product.
* `POST /web/contact/`: Send a message.

---

## 3. Infrastructure & Automation

### Signals (Automation)

The backend uses Django Signals to decouple logic:

* **Verification Sync**: `accounts/signals.py` ensures `Customer.is_email_verified` matches `EmailAddress.verified`.
* **Profile Creation**: Automatically creates a `Customer` profile when a `User` registers.
* **Rating Aggregation**: Recalculates Product Average Rating whenever a Review is added/deleted.

### Admin Dashboard Enhancements

We have heavily customized the Django Admin:

* **Editable Verification**: "Email Verified" status uses `list_editable` in the Customer list.
* **Bulk Actions**: "Mark Verified/Unverified" actions.
* **Inline Editing**: Manage Addresses and Email Addresses directly within the User/Customer detail view.

### Security

* **JWT**: Stateless authentication with short-lived Access tokens and long-lived Refresh tokens.
* **CORS**: Configured to allow strictly defined Frontend origins (`localhost`, `ngrok`).
* **Password Validators**: Enforces strength standards.

## 4. Environment Variables

* `SECRET_KEY`: Django security key.
* `DEBUG`: `True` for Dev, `False` for Prod.
* `ALLOWED_HOSTS`: Domain allowlist.
* `CORS_ALLOWED_ORIGINS`: Frontend URLs.
* `EMAIL_BACKEND`: Switch between Console (Dev) and SMTP (Prod).

---

*Verified by Antigravity AI - 2026*
