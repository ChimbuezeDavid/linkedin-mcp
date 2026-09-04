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

## 🚀 Quickstart (Zero-Clone Setup)

You do **not** need to clone this repository to use the LinkedIn MCP server. As long as you have **[uv](https://github.com/astral-sh/uv)** and **Google Chrome** installed, your AI assistant can run it directly via `uvx`.

### 1. One-Time Interactive Sign-In
Before connecting to an AI assistant, authenticate your LinkedIn session once:

```bash
uvx --from git+https://github.com/ChimbuezeDavid/linkedin-mcp python -c "import asyncio; from linkedin_mcp.tools.auth import linkedin_start_login; asyncio.run(linkedin_start_login())"
```

1. A dedicated Google Chrome window will open.
2. Sign in with your LinkedIn credentials (and complete 2FA if prompted).
3. Once your home feed loads, the tool verifies your account and securely saves your session state to `~/.linkedin_mcp`. Your session persists across restarts with sliding window keep-alive protection.

---

## 🔌 Connecting to Your AI Assistant

### Category A: Desktop AI Clients (Zero-Clone via `uvx`)

Add the LinkedIn MCP server directly to your AI client's configuration file:

#### 1. Claude Desktop
Add to your `claude_desktop_config.json` (`%APPDATA%\Claude\claude_desktop_config.json` on Windows or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ChimbuezeDavid/linkedin-mcp",
        "linkedin-mcp"
      ]
    }
  }
}
```

#### 2. Antigravity
Add to your Antigravity MCP settings:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ChimbuezeDavid/linkedin-mcp",
        "linkedin-mcp"
      ]
    }
  }
}
```

#### 3. Cursor / Windsurf
Add to `.cursor/mcp.json` or your global MCP settings:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ChimbuezeDavid/linkedin-mcp",
        "linkedin-mcp"
      ]
    }
  }
}
```

#### 4. Claude Code CLI
```bash
claude mcp add linkedin uvx --from git+https://github.com/ChimbuezeDavid/linkedin-mcp linkedin-mcp
```

---

### Local Development / Contributing
If you want to modify or contribute to the codebase:

```bash
git clone https://github.com/ChimbuezeDavid/linkedin-mcp.git
cd linkedin-mcp
uv sync
```

To run locally against your local files:
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

## 🛠️ Available MCP Tools (29 Tools)

| Category | Tool Name | Parameters | Description |
| :--- | :--- | :--- | :--- |
| **Auth & Keep-Alive** | `check_login_status` | *(none)* | Checks session health, verified identity, and sliding window telemetry. |
| | `start_login` | `timeout_seconds` | Opens interactive Chrome window for 1-click login / 2FA. |
| | `logout` | *(none)* | Clears all stored session credentials, cookies, and local cache. |
| | `refresh_session` | *(none)* | Performs a silent heartbeat to extend the 30-day session sliding window. |
| **Self-Profile** | `get_my_profile` | *(none)* | Retrieves full profile details for your authenticated account. |
| *(Hard-Locked)* | `update_my_headline` | `headline` | Updates your headline (locked strictly to `/in/me`). |
| | `update_my_about` | `summary` | Updates your bio/About section (locked strictly to `/in/me`). |
| | `add_education` | `school`, `degree`, `field_of_study`, ... | Adds an academic credential to your profile. |
| | `add_experience` | `title`, `company`, `employment_type`, ... | Adds a job or role to your Experience section. |
| | `add_skill` | `skill_name` | Adds a skill to your Skills section (with auto-suggestion). |
| | `add_project` | `title`, `description`, `url`, ... | Adds a project to your Projects section. |
| | `update_job_preferences` | `job_titles`, `location_types`, ... | Configures "Open to work" career preferences. |
| | `update_my_services` | `services_to_add`, `services_to_remove`, ... | Updates client services and offerings on your profile. |
| **Browsing** | `search_people` | `keywords`, `location`, `company`, `limit` | Searches LinkedIn professionals with your network access. |
| | `view_profile` | `profile_url` | Reads any member's public/network profile details. |
| **Feed, Posts & Polls** | `get_feed` | `limit` | Reads recent posts from your personal home feed. |
| | `create_post` | `text`, `media_path` *(optional)* | Publishes a post authored by your account, optionally with image/PDF. |
| | `create_poll` | `question`, `options`, `duration` | Publishes an interactive poll to your feed (2-4 options). |
| | `comment_on_post` | `post_url`, `comment_text` | Comments on a post as your authenticated profile. |
| **Analytics & Insights**| `get_post_analytics` | `limit` | Retrieves impressions, reactions, and comments for your recent posts. |
| | `get_profile_views` | *(none)* | Retrieves private profile view counts and viewer demographics. |
| **Direct Messaging** | `list_conversations` | `limit` | Lists recent direct message threads in your inbox. |
| | `get_conversation_messages` | `recipient_name`, `limit` | Reads complete message history and replies for a specific thread. |
| | `send_message` | `recipient_profile_url`, `message_text` | Dispatches a direct message from your account. |
| **Network & Growth** | `send_connection_request` | `profile_url`, `custom_note` | Sends a connection invitation with an optional note. |
| | `get_pending_invitations` | *(none)* | Lists incoming connection invitations received by your account. |
| | `manage_invitation` | `sender_name`, `action` | Accepts or ignores a pending connection invitation. |
| **Agentic Skills** | `get_network_briefing` | `limit` | Generates a daily executive digest: inbox, invitations, analytics & feed. |
| | `analyze_profile_strength` | *(none)* | Audits completeness across 6 sections and gives actionable score & tips. |

---

## 🧪 Running Automated Tests

Run the guardrail and boundary verification suite:

```bash
uv run python -m unittest discover tests
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
