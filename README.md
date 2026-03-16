# Nexora — Intelligent Study Assistant

> **AI-powered exam preparation platform for university students**
> Grounded strictly in uploaded syllabus materials using RAG architecture.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Groq API Key** ([Get one here](https://console.groq.com/)) or **Gemini API Key** ([Get one here](https://ai.google.dev/))

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env and add your GROQ_API_KEY or GEMINI_API_KEY

# Start server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 3. Access the App

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📁 Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Pydantic settings / env config
│   ├── ingest.py                # Document ingestion CLI script
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # Environment variables (API keys)
│   ├── routes/                  # API endpoint handlers
│   │   ├── chat.py              # Chat + smart subject switching
│   │   ├── subjects.py          # Subject & unit metadata
│   │   ├── documents.py         # Document upload & management
│   │   ├── study_plan.py        # AI study plan generation
│   │   ├── study_mode.py        # 2-mark & 10-mark question modes
│   │   └── memory.py            # Student progress & welcome-back
│   ├── services/                # Business logic layer
│   │   ├── llm_service.py       # LLM integration (Groq/Gemini) + quality control
│   │   ├── rag_service.py       # RAG pipeline (ChromaDB vector search)
│   │   ├── document_service.py  # PDF/DOCX/PPTX processing
│   │   ├── memory_service.py    # Long-term memory & progress tracking
│   │   └── study_plan_service.py # Study schedule generation
│   ├── models/                  # Pydantic schemas & data models
│   ├── core/                    # Middleware & exception handlers
│   ├── data/                    # Subject metadata JSON
│   ├── documents/               # Uploaded syllabus files (per subject)
│   └── chroma_db/               # ChromaDB vector store
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root component + routing + theme
│   │   ├── main.jsx             # React entry point
│   │   ├── index.css            # Global design system (dark/light)
│   │   ├── pages/               # Full-page views
│   │   │   ├── Landing.jsx/css  # Onboarding setup form
│   │   │   ├── Dashboard.jsx/css # Subject overview
│   │   │   ├── Chat.jsx/css     # ChatGPT-style AI chat
│   │   │   ├── StudyMode.jsx/css # 2-mark & 10-mark exam prep
│   │   │   ├── StudyPlan.jsx/css # AI study planner
│   │   │   ├── Documents.jsx/css # Knowledge base manager
│   │   │   └── Settings.jsx/css # Tone, theme, about
│   │   ├── components/          # Reusable UI components
│   │   │   ├── Layout.jsx/css   # Shell with sidebar
│   │   │   ├── Sidebar.jsx/css  # Navigation panel
│   │   │   ├── ChatMessage.jsx/css # Message bubble + markdown
│   │   │   ├── ChatInput.jsx/css # Message composer
│   │   │   ├── SubjectCard.jsx/css # Subject selection card
│   │   │   └── UnitSelector.jsx/css # Unit picker
│   │   ├── hooks/
│   │   │   └── useChat.js       # Chat state + context switch logic
│   │   ├── api/
│   │   │   └── client.js        # API client (fetch wrapper)
│   │   └── utils/
│   │       └── constants.js     # Subjects, styles, app info
│   └── ...
```

---

## 🧠 System Capabilities

### 1. Chat-Based Learning (Phase 1–3)
- Natural ChatGPT-style conversational interface
- Markdown rendering (headings, bold, code blocks, lists, tables)
- Conversation history with auto-scroll
- Multi-style answer modes (2-mark, 10-mark, explanation, summary, quick revision)
- Intelligent style detection from natural language cues

### 2. Syllabus-Restricted Answers (Phase 4–6, RAG)
- Upload PDF, DOCX, PPTX, TXT syllabus materials
- ChromaDB vector store for semantic search
- Every AI answer grounded strictly in uploaded documents
- No-docs fallback: AI explicitly tells student to upload materials
- Quality control: post-generation validation with 5 automated checks

### 3. Exam Preparation Modes (Phase 5)
- **2-Mark Mode**: Definition-style questions generated from syllabus
- **10-Mark Mode**: Detailed structured exam questions
- Click any question → AI generates the answer on demand
- Progress tracking per question
- Unit-specific question generation

### 4. Study Plan Generation (Phase 7)
- AI-generated study schedules based on:
  - Available time (hours before exam)
  - Subject difficulty
  - Unit coverage
- Structured hour-by-hour plans
- Study tips and prioritization advice

### 5. Memory-Based Learning (Phase 8)
- Persistent student profile across sessions
- Tracks: subjects studied, units covered, questions asked
- Welcome-back greeting with study continuity suggestions
- Progress visualization per subject

### 6. Flexible Conversational AI (Phase 9–11)
- **Smart Subject Switching**: "I want to study OB Unit 2" → auto-switch
- **New Chat**: fresh conversation with subject/unit re-selection
- **10 Tone Modes**: Professional, Friendly, Simple, Motivational, Teacher, Exam Prep, Concise, Detailed, Supportive, Calm
- **Dark/Light Mode**: theme toggle with localStorage persistence
- **Quality Control**: 6 prompt rules + 5 post-gen checks + visual badges

---

## 📚 Supported Subjects (Semester 4, CSE)

| Code | Subject | Icon |
|------|---------|------|
| COA  | Computer Organization and Architecture | 🖥️ |
| APJ  | Advanced Programming in Java | ☕ |
| DAA  | Design and Analysis of Algorithms | ⚡ |
| DM   | Discrete Mathematics | 🔢 |
| OB   | Organizational Behaviour | 👥 |

> **Scalable**: New subjects/departments can be added by updating `data/_subjects.json` and `constants.js`.

---

## 🏗️ Architecture

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + Vite + Vanilla CSS |
| **Backend** | FastAPI (Python 3.13) |
| **LLM** | Groq (LLaMA 3.3 70B) / Google Gemini |
| **Vector DB** | ChromaDB (local persistence) |
| **State** | In-memory + localStorage |

### Quality Control Pipeline

```
Student Message → RAG Context Retrieval → Quality Reminder Injection
→ Enhanced System Prompt (6 Rules) → LLM Generation
→ Post-Generation Validation (5 Checks) → Quality Badge in UI
```

---

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/chat/start-session` | Start study session with greeting |
| `POST` | `/api/chat/message` | Send message, get AI response + quality |
| `POST` | `/api/chat/detect-switch` | Detect subject/unit switch intent |
| `GET`  | `/api/chat/sessions` | List chat sessions |
| `GET`  | `/api/subjects/` | List all subjects |
| `GET`  | `/api/subjects/{code}` | Get subject details |
| `POST` | `/api/documents/upload` | Upload syllabus document |
| `GET`  | `/api/documents/{code}` | List documents for subject |
| `POST` | `/api/study-mode/questions` | Generate exam questions |
| `POST` | `/api/study-mode/answer` | Get answer for a question |
| `POST` | `/api/study-plan/generate` | Generate study schedule |
| `GET`  | `/api/memory/progress` | Get study progress |
| `POST` | `/api/memory/profile` | Save student profile |
| `GET`  | `/api/memory/welcome-back` | Get welcome-back greeting |
| `GET`  | `/health` | Health check |

---

## 🎨 Design System

- **Theme**: Cosmic Academic Futuristic (dark/light)
- **Font**: Inter (UI) + JetBrains Mono (code)
- **Colors**: Indigo/violet accent palette with subject-specific colors
- **Effects**: Glassmorphism, subtle gradients, spring animations
- **Responsive**: Desktop-first with mobile breakpoints

---

## 🔮 Future Expansion

The modular architecture supports:
- **New departments** — add subjects via `_subjects.json`
- **New LLM providers** — extend `llm_service.py`
- **Database persistence** — swap in-memory stores for Supabase/PostgreSQL
- **Authentication** — add JWT auth middleware
- **Multi-language support** — add translation layer
- **Analytics dashboard** — aggregate memory data
- **Collaborative features** — shared study sessions

---

## 📝 Development Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Core Chat Interface | ✅ |
| 2 | Cinematic UI Design | ✅ |
| 3 | Intelligent Style Detection | ✅ |
| 4 | Document Upload System | ✅ |
| 5 | Study Mode (2/10 Mark) | ✅ |
| 6 | RAG Pipeline (ChromaDB) | ✅ |
| 7 | Study Plan Builder | ✅ |
| 8 | Long-Term Memory | ✅ |
| 9 | Chat Management System | ✅ |
| 10 | Settings System | ✅ |
| 11 | Quality Control | ✅ |

---

Built with ❤️ for university students
