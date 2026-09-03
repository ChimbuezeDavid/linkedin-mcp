# Universal LinkedIn MCP Server

[![Model Context Protocol](https://img.shields.io/badge/MCP-Compatible-blue.svg)](https://modelcontextprotocol.io)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Model Context Protocol (MCP) server that empowers any AI assistant to interact with LinkedIn just like a human user—with strict safety guardrails ensuring all actions (editing, posting, searching, messaging) are performed **strictly from and within your authenticated account boundary**.

---

## 🛡️ Core Security & Guardrails

- **Strict User-Only Profile Mutations**: Profile editing tools (`update_my_headline`, `update_my_about`) **accept NO target profile parameter**. They are hardcoded and locked to `/in/me` (your profile). It is mathematically impossible for the AI to modify another person's profile.
- **Account-Bound Outreach**:
  - **Direct Messages**: Dispatched exclusively from your personal inbox as you.
  - **Searches & Profile Viewing**: Executed through your logged-in account, honoring your network degree (1st/2nd/3rd).
  - **Posts & Comments**: Authored strictly by your profile.
- **Anti-Bot Stealth Engine**:
  - Uses your computer's native **Google Chrome** instead of generic automation browser binaries.
  - Features human typing delays, realistic bezier scrolling, and automated fingerprint shielding (`navigator.webdriver` removal).
- **Session Guard**: Every single tool validates that your session is active before taking action. Unauthenticated attempts are immediately blocked.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **[uv](https://github.com/astral-sh/uv)** (fast Python package manager)
- **Google Chrome** installed on your system

### 2. Installation
Clone this repository and sync dependencies:

```bash
git clone https://github.com/<your-username>/linkedin-mcp.git
cd linkedin-mcp
uv sync
```

### 3. One-Time Interactive Login
Run the interactive authentication tool to open a dedicated Chrome window and log in to your LinkedIn account:

```bash
uv run python -c "import asyncio; from linkedin_mcp.tools.auth import linkedin_start_login; asyncio.run(linkedin_start_login())"
```

1. Log in with your email, password, and complete 2FA if prompted.
2. Once your LinkedIn home feed loads, the tool automatically verifies your identity and saves your secure session state locally to `~/.linkedin_mcp`.
3. You only need to do this once. Your session persists across restarts.

---

## 🔌 Connecting to Your AI Assistant

This server supports both **Desktop AI clients** (via local `stdio`) and **Browser-based AI clients** (via Streamable HTTP or SSE tunnels).

### Category A: Desktop AI Apps (Zero Setup, No Tunnels Needed)

Desktop apps run directly on your computer and talk to the server locally over standard input/output (`stdio`).

#### 1. Claude Desktop
Add this to your `claude_desktop_config.json` (found at `%APPDATA%\Claude\claude_desktop_config.json` on Windows or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uv",
      "args": [
        "--directory",
        "<PATH_TO_LINKEDIN_MCP>",
        "run",
        "linkedin-mcp"
      ]
    }
  }
}
```
*(Replace `<PATH_TO_LINKEDIN_MCP>` with your actual project directory path, e.g., `C:/Users/chimb/LinkedIn mcp`)*.

#### 2. Antigravity
Add the server to your Antigravity MCP settings:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uv",
      "args": [
        "--directory",
        "<PATH_TO_LINKEDIN_MCP>",
        "run",
        "linkedin-mcp"
      ]
    }
  }
}
```

#### 3. Cursor / Windsurf
Add to `.cursor/mcp.json` or global MCP settings:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uv",
      "args": [
        "--directory",
        "<PATH_TO_LINKEDIN_MCP>",
        "run",
        "linkedin-mcp"
      ]
    }
  }
}
```

#### 4. Claude Code CLI
```bash
claude mcp add linkedin uv --directory "<PATH_TO_LINKEDIN_MCP>" run linkedin-mcp
```

---

### Category B: Web-Based AI (Grok.com)

Web assistants running in the cloud cannot directly access `localhost` or your local browser profile. Therefore, they connect over an encrypted public tunnel using **Streamable HTTP** (recommended) or **SSE**.

#### 1. Grok Web (`grok.com/connectors`)

We provide a 1-click startup script that launches the MCP server in Streamable HTTP mode on port `8765` and automatically sets up a Cloudflare Tunnel:

```powershell
# In PowerShell:
powershell -ExecutionPolicy Bypass -File .\run_for_grok.ps1
```

1. Look for the public tunnel URL displayed in your terminal (e.g. `https://random-words.trycloudflare.com`).
2. Go to **[grok.com/connectors](https://grok.com/connectors)**.
3. Click **Add Custom MCP Server**:
   - **Name**: `LinkedIn MCP`
   - **URL**: `https://random-words.trycloudflare.com/mcp` *(make sure to append `/mcp` at the end)*
4. Click **Save** and start chatting!

> [!NOTE]
> **Why `/mcp`?** Cloudflare quick tunnels do not support persistent SSE streams due to proxy buffering, but fully support Streamable HTTP (`/mcp`). The server includes built-in CORS middleware to ensure seamless communication with `grok.com`.

#### 2. Using ngrok (Alternative for SSE)
If you prefer using `ngrok` with the standard SSE transport:

```bash
# Terminal 1: Start MCP server in SSE mode
uv run linkedin-mcp --transport sse --port 8765

# Terminal 2: Expose via ngrok
ngrok http 8765
```

In your AI's custom connector settings, set the URL to:
`https://<your-ngrok-subdomain>.ngrok-free.app/sse`

---

## 🛠️ Available MCP Tools

| Category | Tool Name | Parameters | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `check_login_status` | *(none)* | Checks active session health and verified user identity. |
| | `start_login` | *(none)* | Opens interactive Chrome window for 1-click login / 2FA. |
| | `logout` | *(none)* | Clears all stored session credentials and cookies. |
| **Self-Profile** | `get_my_profile` | *(none)* | Retrieves full profile details for your authenticated account. |
| *(Hard-Locked)* | `update_my_headline` | `new_headline` | Updates your headline (locked strictly to `/in/me`). |
| | `update_my_about` | `new_about` | Updates your bio/About section (locked strictly to `/in/me`). |
| **Browsing** | `search_people` | `query`, `limit` | Searches LinkedIn professionals with your network access. |
| | `view_profile` | `profile_url` | Reads any member's public/network profile details. |
| **Feed & Posts** | `get_feed` | `limit` | Reads recent posts from your personal home feed. |
| | `create_post` | `text` | Publishes a new post authored by your account. |
| | `comment_on_post` | `post_url`, `comment_text` | Comments on a post as your authenticated profile. |
| **Messaging** | `list_conversations` | `limit` | Lists recent direct message threads in your inbox. |
| | `send_message` | `recipient_name`, `message_text` | Dispatches a direct message from your account. |
| **Network** | `send_connection_request` | `profile_url`, `custom_note` | Sends a connection invitation with an optional note. |
| | `get_pending_invitations` | *(none)* | Lists incoming connection invitations received by your account. |

---

## 🧪 Running Automated Tests

Run the guardrail and boundary verification suite:

```bash
uv run python -m unittest discover tests
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
