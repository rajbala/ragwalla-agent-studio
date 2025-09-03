# Ragwalla Agent Studio

A simplified chat interface for Ragwalla AI agents with WebSocket support and conversation persistence.

## Quick Start

### 1. Prerequisites

- Python 3.12 or higher
- UV package manager (recommended) or pip

### 2. Installation

Clone the repository:
```bash
git clone <repository-url>
cd ragwalla-agent-studio
```

### 3. Configuration

Copy the example environment file and add your Ragwalla API credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
# REQUIRED: Your Ragwalla API Configuration
AGENT_BASE_URL=https://api.ragwalla.com
RAGWALLA_API_KEY=your_actual_api_key_here
```

### 4. Run the Application

Using UV (recommended):
```bash
uv run app.py
```

Or using Python directly:
```bash
python app.py
```

The application will start on http://localhost:8000

## Features

- Real-time chat with Ragwalla AI agents
- WebSocket-based streaming responses
- Persistent conversation history
- Clean, modern UI with iMessage-style design
- Support for multiple agents
- Session management

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `AGENT_BASE_URL` | Yes | Your Ragwalla API endpoint | - |
| `RAGWALLA_API_KEY` | Yes | Your Ragwalla API key | - |
| `HOST` | No | Server host | `0.0.0.0` |
| `PORT` | No | Server port | `8000` |

## Usage

1. Open http://localhost:8000 in your browser
2. Select an agent from the dropdown
3. Start chatting!

## Deployment

This application is designed to be easily deployed with just environment configuration:

1. Set your `AGENT_BASE_URL` and `RAGWALLA_API_KEY` in the environment
2. Run the application
3. No additional configuration needed

## Database

The application uses a local SQLite database (`ragwalla_agent_studio.db`) to store:
- Chat sessions
- Message history

The database is created automatically on first run.

## Requirements

All Python dependencies are managed inline using PEP 723 script metadata. No separate requirements.txt file is needed.

## Support

For issues with the Ragwalla API, contact your Ragwalla support team.
For application issues, please create an issue in the repository.