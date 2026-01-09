# True Spark APIs

A FastAPI-based backend service for the **True Spark** platform.
This service provides REST APIs with Swagger documentation, MongoDB integration, and Docker support.

---

## 🚀 Tech Stack

- **Python 3.9+**
- **FastAPI**
- **Uvicorn**
- **MongoDB**
- **Docker**

---

Open README.md in VS Code

## 📁 Project Setup (Local Development)

### 1️⃣ Create Virtual Environment

```bash
python3 -m venv .venv
```

### 2️⃣ Activate Virtual Environment

```bash
source .venv/bin/activate
```

### 3️⃣ Upgrade pip

```bash
pip install --upgrade pip
```

### 4️⃣ Install Dependencies

```bash
pip install --no-cache-dir -r requirements.txt
```

---

## ▶️ Run the Application (Local)

```bash
uvicorn main:app --port 8000 --reload
```

### ⚠️ Troubleshooting

If the application fails to start:

1. Restart your IDE
2. Ensure **MongoDB** is installed and running locally
3. Create a MongoDB database named:

```text
true_spark_db
```

---

## 📘 API Documentation (Swagger)

Once the app is running, access Swagger UI at:

```text
http://localhost:9000/ts_api_docs
```

---

## ☁️ Run on Linode / Production Server

```bash
uvicorn main:app --host 0.0.0.0 --port 80
```

---

## 🐳 Docker Support

### Build Docker Image

```bash
docker build -t ts_apis .
```

### Run Docker Container

```bash
docker run -p 80:80 ts_apis
```

---

## 🗄️ Database

- **MongoDB**
- Default database name: `true_spark_db`

Make sure MongoDB is accessible from the application environment.

---

## ✅ Health Check

After startup, verify the service is running by opening Swagger UI or calling any API endpoint.

---

## 📌 Notes

- Ensure port **80** is open on your server (Linode / Cloud VM)
- Use a process manager like **PM2**, **Supervisor**, or **Docker** for production stability

---

## 📄 License

This project is proprietary to **True Spark**.

# True Spark APIs

A FastAPI-based backend service for the **True Spark** platform.
This service provides REST APIs with Swagger documentation, MongoDB integration, and Docker support.

---

## 🚀 Tech Stack

- **Python 3.9+**
- **FastAPI**
- **Uvicorn**
- **MongoDB**
- **Docker**

---

## 📁 Project Setup (Local Development)

### 1️⃣ Create Virtual Environment

```bash
python3 -m venv .venv
```

### 2️⃣ Activate Virtual Environment

```bash
source .venv/bin/activate
```

### 3️⃣ Upgrade pip

```bash
pip install --upgrade pip
```

### 4️⃣ Install Dependencies

```bash
pip install --no-cache-dir -r requirements.txt
```

---

## ▶️ Run the Application (Local)

```bash
uvicorn main:app --port 8000 --reload
```

### ⚠️ Troubleshooting

If the application fails to start:

1. Restart your IDE
2. Ensure **MongoDB** is installed and running locally
3. Create a MongoDB database named:

```text
true_spark_db
```

---

## 📘 API Documentation (Swagger)

Once the app is running, access Swagger UI at:

```text
http://localhost:9000/ts_api_docs
```

---

## ☁️ Run on Linode / Production Server

```bash
uvicorn main:app --host 0.0.0.0 --port 80
```

---

## 🐳 Docker Support

### Build Docker Image

```bash
docker build -t ts_apis .
```

### Run Docker Container

```bash
docker run -p 80:80 ts_apis
```

---

## 🗄️ Database

- **MongoDB**
- Default database name: `true_spark_db`

Make sure MongoDB is accessible from the application environment.

---

## ✅ Health Check

After startup, verify the service is running by opening Swagger UI or calling any API endpoint.

---

## 📌 Notes

- Ensure port **80** is open on your server (Linode / Cloud VM)
- Use a process manager like **PM2**, **Supervisor**, or **Docker** for production stability

---

## 📄 License

This project is proprietary to **True Spark**.
