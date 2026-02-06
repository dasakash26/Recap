# Recap

AI-powered document search with citations. Upload documents, chat with AI, get accurate answers backed by your content.

<div align="center">
  <img src="frontend/public/recap-demo.png" alt="Recap Demo" style="border-radius:1rem; box-shadow:0 4px 20px rgba(0,0,0,0.3);" />
</div>

## Features

<div align="center">

| Feature                     | Description                                                                 |
|-----------------------------|-----------------------------------------------------------------------------|
| **Context Isolation**       | Organize documents into folders for zero-noise retrieval                    |
| **Cited Answers**           | Every response links directly to source content                             |
| **Real-time Collaboration** | Share folders with your team                                                |
| **Smart Search**            | Vector-powered semantic search with LangGraph agents                        |

</div>

## Stack

<div align="center">

| Category    | Technologies                                                                 |
|-------------|------------------------------------------------------------------------------|
| **Backend** | FastAPI • Python 3.12 • LangGraph • ChromaDB • PostgreSQL • Prisma           |
| **Frontend**| Next.js 15 • React • TypeScript • Tailwind CSS • shadcn/ui                  |
| **AI**      | Google Gemini 1.5 Flash                                                     |

</div>

## How It Works

<div align="center">

```mermaid
flowchart TD
    A[1. Upload<br/>Documents are chunked and embedded] --> B[2. Store<br/>Embeddings → ChromaDB<br/>Metadata → PostgreSQL]
    B --> C[3. Query<br/>Semantic search retrieves relevant chunks]
    C --> D[4. Generate<br/>LangGraph agent + Gemini synthesizes answer]
    D --> E[5. Stream<br/>Response streams via SSE with citations]
    
    style A fill:#1e293b,stroke:#475569,color:#e2e8f0
    style B fill:#1e293b,stroke:#475569,color:#e2e8f0
    style C fill:#1e293b,stroke:#475569,color:#e2e8f0
    style D fill:#1e293b,stroke:#475569,color:#e2e8f0
    style E fill:#1e293b,stroke:#475569,color:#e2e8f0
```

</div>

## Quick Start

### Backend

```bash
git clone https://github.com/dasakash26/Recap.git
cd Recap/backend

# Install dependencies
uv sync

# Setup environment
cp .env.example .env
# Edit .env with your credentials
```

```bash
# Generate Prisma client and run migrations
uv run prisma generate
uv run prisma migrate deploy

# Start server
uv run uvicorn main:app --reload
```

Backend runs at [http://localhost:8000](http://localhost:8000) • API docs at `/docs`

</div>

### Frontend

```bash
cd ../frontend

# Install dependencies
pnpm install

# Setup environment
cp .env.example .env.local
# Edit .env.local with backend URL
```

**`.env.local` file example:**

```bash
# Start dev server
pnpm dev
```

Frontend runs at [http://localhost:3000](http://localhost:3000)

## License

MIT © 2026 Akash Das
