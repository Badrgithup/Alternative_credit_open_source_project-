# FinScore Platform (open source project)

## 📌 Project Overview
The **FinScore Platform** is a cutting-edge M-Marketing and Alternative Financial Scoring ecosystem tailored for Small and Medium Enterprises (SMEs / PMEs) in Tunisia, empowering local businesses to access specialized credit mapping. (open source project to encourage alternative bankinh Scoring)

The architecture features a dual portal:
- **PME Dashboard**: Enables business owners to register their enterprises, connect alternative data pipelines (RNE/CNSS), and unlock advanced financial viability insights.
- **Banker / Investor Dashboard**: Equips financial analysts with real-time AI-driven scraping and simulation modeling via a comprehensive marketplace, utilizing next-generation Machine Learning to uncover hidden investment opportunities safely and efficiently.

## 🚀 Tech Stack
- **Backend Core**: FastAPI (Python 3.11+)
- **Frontend Interface**: Next.js 14 (React, Tailwind CSS, Framer Motion)
- **Database**: SQLite (SQLAlchemy ORM) - Ready for PostgreSQL scaling
- **AI Extraction**: Groq Cloud Platform (Llama-3 70B Versatile) for deterministic data compilation.

## ⚙️ Getting Started

### 1. Requirements
- Node.js (v18+)
- Python (v3.11+)
- Git

### 2. Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd credit-risk-analysis/backend
   ```
2. Create and activate a Virtual Environment:
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up Environmental Configuration:
   Create a `.env` file referencing the `.env.example`:
   ```bash
   cp .env.example .env
   # Make sure to securely paste your Groq API Key!
   ```
5. Launch the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 3. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd credit-risk-analysis/v2-pme-frontend
   ```
2. Install npm modules:
   ```bash
   npm install
   ```
3. Launch the Next.js development server:
   ```bash
   npm run dev
   ```
   *The primary application will automatically route to `http://localhost:3000`.*

---
*Developed for optimal credit tracking integration and academic evaluation.*
