# 🚀 RepoPilot

**AI-powered GitHub repository analyzer and live demo launcher.**

RepoPilot takes a public GitHub repository, analyzes its structure and technology stack, then launches the application inside an isolated Docker sandbox and provides a live preview URL.

---

## ✨ Features

* 🔗 **GitHub Repository Analysis**

  * Detects project runtime
  * Detects frameworks and libraries
  * Detects programming languages
  * Detects package managers
  * Detects application ports
  * Detects build and start commands
  * Detects entry points
  * Detects package files and dependencies
  * Analyzes project structure

* 🐳 **Isolated Docker Sandbox**

  * Each repository runs in its own sandbox environment
  * Applications are isolated from the host environment
  * Automatically maps application ports

* ⚡ **Live Preview**

  * Launch a repository and receive a preview URL
  * Monitor sandbox status while the application starts

* 🔐 **Authentication**

  * User login
  * JWT-based authentication
  * Protected repository analysis and sandbox endpoints

* 🎨 **Modern Dashboard**

  * Repository URL input
  * Sandbox status monitoring
  * Repository intelligence dashboard
  * Dependency and package inspection
  * Project structure visualization
  * Responsive UI

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │      GitHub Repo    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      RepoPilot      │
                    │      Dashboard      │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
       ┌─────────────────┐          ┌─────────────────┐
       │ Repository      │          │ Sandbox         │
       │ Analyzer        │          │ Manager         │
       └────────┬────────┘          └────────┬────────┘
                │                            │
                ▼                            ▼
       ┌─────────────────┐          ┌─────────────────┐
       │ Framework       │          │ Docker          │
       │ Runtime         │          │ Container       │
       │ Dependencies    │          │                 │
       │ Ports           │          │                 │
       └─────────────────┘          └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Live Preview    │
                                    │ URL             │
                                    └─────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend

* React
* Vite
* JavaScript / JSX
* Axios
* React Router
* Lucide React
* CSS

### Backend

* Python
* FastAPI
* Uvicorn
* JWT Authentication
* Docker integration

### Sandbox

* Docker
* Isolated application containers
* Dynamic port mapping

---

## 📁 Project Structure

```text
RepoPilot/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── repository.py
│   │   │   ├── sandbox.py
│   │   │   └── ...
│   │   │
│   │   ├── services/
│   │   │   ├── repository_analyzer.py
│   │   │   ├── sandbox_manager.py
│   │   │   └── ...
│   │   │
│   │   └── main.py
│   │
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Login.jsx
│   │   │   └── ...
│   │   │
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── ...
│   │
│   └── ...
│
└── README.md
```

---

## 🔍 Repository Analysis

RepoPilot analyzes repositories before launching them.

The analyzer can identify:

| Category        | Detection                                       |
| --------------- | ----------------------------------------------- |
| Runtime         | Node.js, Python, etc.                           |
| Framework       | React, Vite, Express, Prisma, FastAPI, etc.     |
| Languages       | TypeScript, JavaScript, Python, CSS, HTML, etc. |
| Package Manager | npm, Yarn, pnpm, Bun                            |
| Ports           | Common application ports                        |
| Applications    | Frontend / backend applications                 |
| Dependencies    | Project dependencies                            |
| Packages        | `package.json` files                            |
| Entry Points    | Main application entry files                    |
| Commands        | Build and start commands                        |
| Structure       | Repository directories and files                |

---

## 🐳 Sandbox Workflow

When a repository is launched:

```text
GitHub URL
    │
    ▼
Clone Repository
    │
    ▼
Analyze Repository
    │
    ▼
Detect Runtime / Framework / Port
    │
    ▼
Generate Docker Environment
    │
    ▼
Build Application
    │
    ▼
Start Container
    │
    ▼
Monitor Container
    │
    ▼
Expose Preview Port
    │
    ▼
Live Preview URL
```

---

## ⚙️ Local Development

### Prerequisites

Make sure you have:

* Python 3.12+
* Node.js
* npm
* Docker
* Git

### Clone

```bash
git clone <your-repository-url>
cd RepoPilot
```

---

## 🔧 Backend

Navigate to the backend:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

---

## 🎨 Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start Vite:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

---

## 🔐 Environment Variables

Create a `.env` file for local configuration.

Example:

```env
JWT_SECRET=your-secret-key
```

Do not commit secrets or environment files to Git.

---

## 🧪 Useful Commands

### Frontend

```bash
npm run dev
```

```bash
npm run build
```

```bash
npm run lint
```

### Backend

```bash
uvicorn app.main:app --reload --port 8000
```

### Git

```bash
git status
```

```bash
git add .
```

```bash
git commit -m "your message"
```

```bash
git push origin main
```

---

## 🔌 API Overview

### Repository Analysis

```http
POST /api/repository/analyze
```

Example request:

```json
{
  "url": "https://github.com/username/repository"
}
```

The endpoint returns repository intelligence including framework, runtime, languages, dependencies, applications, ports, commands, packages, entry points, and project structure.

### Sandbox Launch

```http
POST /api/sandbox/launch
```

Example request:

```json
{
  "url": "https://github.com/username/repository"
}
```

### Sandbox Status

```http
GET /api/sandbox/{sandbox_id}
```

The dashboard polls this endpoint to monitor the container.

---

## 🔒 Security Considerations

RepoPilot executes external repositories inside Docker containers.

For production deployment, additional security controls should be considered, including:

* CPU limits
* Memory limits
* Process limits
* Network restrictions
* Container isolation
* Read-only host mounts
* Execution timeouts
* Resource quotas
* Repository validation
* Secret isolation
* Container cleanup

Never run untrusted repositories directly on the host system.

---

## 🚧 Current Limitations

RepoPilot is currently designed primarily for public GitHub repositories.

Some repositories may require additional configuration when they use:

* Custom build systems
* Non-standard ports
* Private dependencies
* External services
* Databases
* Environment-specific configuration
* Complex multi-service architectures

---

## 🗺️ Future Improvements

Potential improvements include:

* 🤖 AI-powered repository debugging
* 🔧 Automatic Dockerfile generation
* 🧠 Smarter framework detection
* 🔌 Multi-service application support
* 📦 Automatic dependency repair
* 🐛 Build error detection and fixing
* 📊 Resource monitoring
* 🌐 Network isolation
* 💾 Persistent sandbox sessions
* 🔄 Automatic rebuilds
* 📝 AI-generated project documentation
* 🔍 Code quality analysis
* 🚀 Production deployment support

---

## 🎯 Project Goal

RepoPilot aims to make it easier to **understand, run, and demonstrate unfamiliar GitHub repositories without manually configuring their development environments.**

Instead of:

```text
Clone → Read README → Install dependencies → Fix errors → Configure ports → Run
```

RepoPilot aims for:

```text
Paste GitHub URL → Analyze → Launch → Preview
```

---

## 👨‍💻 Author

**Ninaad Mhadalkar**

Built as a developer-focused project exploring:

* Full-stack development
* Repository analysis
* Docker sandboxing
* Backend automation
* Developer tooling
* AI-assisted development

---

## 📄 License

This project is currently intended for educational and portfolio purposes.
