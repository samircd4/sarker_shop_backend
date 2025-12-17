# Sarker Shop Backend

A robust, scalable e-commerce REST API built with Django and Django Rest Framework (DRF). This project provides a complete backend solution for modern e-commerce applications, featuring JWT authentication, product catalog management, shopping cart functionality, order processing, and customer reviews.

## 🚀 Key Features

- **Modular Architecture**: Organized into dedicated apps (`accounts`, `products`, `orders`, `reviews`) for maintainability.
- **Secure Authentication**: JWT-based authentication (Access & Refresh tokens) via `simplejwt`.
- **Product Catalog**: Advanced filtering, searching, and sorting capabilities.
- **Shopping Cart & Checkout**: Full cart management and order lifecycle tracking.
- **Reviews & Ratings**: User-generated reviews with automated rating aggregation.
- **Interactive Documentation**: Beautiful Swagger UI documentation with interactive testing.

## 🛠️ Tech Stack

- **Framework**: Django 5.2.8, Django Rest Framework 3.15+
- **Documentation**: drf-spectacular (Swagger UI / OpenAPI 3.0)
- **Database**: SQLite (Development), PostgreSQL (Production ready)
- **Authentication**: SimpleJWT
- **Utilities**: Django Filter, CORS Headers

## 📦 Getting Started

### Prerequisites

- Python 3.10+
- `uv` (recommended) or `pip`

### Installation

1.  **Clone the repository**

    ```bash
    git clone https://github.com/samircd4/sarker_shop_backend.git
    cd sarker_shop_backend
    ```

2.  **Install dependencies**

    ```bash
    # Using uv (Recommended)
    uv sync
    # OR using pip
    pip install -r requirements.txt
    ```

3.  **Run Migrations**

    ```bash
    python manage.py migrate
    ```

4.  **Start the Server**
    ```bash
    python manage.py runserver
    ```

The API will be available at `http://127.0.0.1:8000/api/`.

---

## 📖 Interactive API Documentation

We provide a fully interactive API documentation using **Swagger UI**. This allows you to explore endpoints, view schemas, and test requests directly from your browser.

- **Swagger UI**: [`http://127.0.0.1:8000/api/docs/`](http://127.0.0.1:8000/api/docs/)
- **Redoc**: [`http://127.0.0.1:8000/api/redoc/`](http://127.0.0.1:8000/api/redoc/)
- **OpenAPI Schema**: [`http://127.0.0.1:8000/api/schema/`](http://127.0.0.1:8000/api/schema/)

### Features
- **Visual Layout**: Organized by domain (Accounts, Catalog, Orders, Reviews).
- **Try It Out**: Execute requests against the live API directly from the docs.
- **Authentication**: Built-in support for JWT Login (click "Authorize" or use the custom Login button).

> **Note**: Access to the documentation is restricted to logged-in users for security. You will be redirected to the login page if not authenticated.

---

## 📚 API Reference Overview

All endpoints are prefixed with `/api/`.

### 1. 🔐 Authentication & Accounts

Manage user registration, login, and profiles.

| Endpoint                         | Method          | Description                              | Permissions                                 |
| :------------------------------- | :-------------- | :--------------------------------------- | :------------------------------------------ |
| **`/accounts/register/`**        | `POST`          | Register a new user account.             | **Public**                                  |
| **`/accounts/login/`**           | `POST`          | Login to obtain Access & Refresh tokens. | **Public**                                  |
| **`/accounts/refresh/`**         | `POST`          | Refresh an expired access token.         | **Public**                                  |
| **`/accounts/change-password/`** | `PUT`           | Change the current user's password.      | **Auth** (Logged in users)                  |
| **`/accounts/profile/`**         | `GET`           | List customer profiles.                  | **Auth** (View Own)<br>**Admin** (View All) |
| **`/accounts/profile/me/`**      | `GET`, `PUT`    | Retrieve or update your own profile.     | **Auth** (Owner only)                       |
| **`/accounts/addresses/`**       | `GET`, `POST`   | List or add shipping addresses.          | **Auth** (Owner only)                       |
| **`/accounts/addresses/{id}/`**  | `PUT`, `DELETE` | Update or remove an address.             | **Auth** (Owner only)                       |

### 2. 🛍️ Product Catalog

Browse, search, and filter products.

| Endpoint                     | Method          | Description                        | Permissions    |
| :--------------------------- | :-------------- | :--------------------------------- | :------------- |
| **`/products/`**             | `GET`           | List all products with pagination. | **Public**     |
| **`/products/`**             | `POST`          | Add a new product.                 | **Admin Only** |
| **`/products/{id}/`**        | `GET`           | Get detailed product info.         | **Public**     |
| **`/products/{id}/`**        | `PUT`, `DELETE` | Update or delete a product.        | **Admin Only** |
| **`/products/suggest/`**     | `GET`           | Autocomplete suggestions.          | **Public**     |
| **`/products/featured/`**    | `GET`           | List featured products.            | **Public**     |
| **`/products/bestsellers/`** | `GET`           | List bestsellers.                  | **Public**     |
| **`/categories/`**           | `GET`           | List all product categories.       | **Public**     |
| **`/categories/`**           | `POST`          | Create a new category.             | **Admin Only** |
| **`/categories/{id}/`**      | `PUT`, `DELETE` | Edit or delete a category.         | **Admin Only** |
| **`/brands/`**               | `GET`           | List all brands.                   | **Public**     |
| **`/brands/`**               | `POST`          | Add a new brand.                   | **Admin Only** |

### 3. ⭐ Reviews
