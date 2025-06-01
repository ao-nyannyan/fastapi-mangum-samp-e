# FastAPI + Mangum + SQLAlchemy Template for AWS Lambda (Aurora MySQL via RDS Proxy)

This repository is a **starter kit** for building serverless REST APIs on AWS Lambda & API Gateway
using **FastAPI**, **Mangum**, **SQLAlchemy**, and **Pydantic**.  
It is aimed at small‑to‑medium projects with multiple developers.

## Highlights

* **Modular architecture** (routers → services → repositories)  
* **Multiple Lambda functions** – each resource can be deployed independently  
* **Async SQLAlchemy** talking to **Aurora MySQL** through **RDS Proxy**  
* **Docker‑first** local development & testing  
* **CI** example with GitHub Actions  
* **Pytest** suite runnable locally or in CI  

---

## Quick Start

```bash
# clone and cd
cp .env.example .env  # edit DB creds

# start MySQL & app with hot‑reload
docker compose up --build
```

The API will be available at **http://localhost:8000** with docs at **/docs**.

## Project layout

```
.
├── app/                 # business logic
│   ├── handlers/        # AWS Lambda entry points (Mangum)
│   ├── routers/         # FastAPI routers (HTTP layer)
│   ├── services/        # domain logic
│   ├── repositories/    # DB access
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   └── util/            # shared helpers & dependencies
├── tests/               # pytest
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Deploying to AWS

This template is agnostic to the deployment framework.  
Common options:

* AWS SAM           (`sam build && sam deploy`)  
* Serverless Framework (`sls deploy`)  
* Terraform + Lambda layers

Each Lambda needs a handler module from **`app/handlers`**; map them individually in your
infrastructure templates.

---

Made with 💜  — feel free to extend!
