import asyncio
from pathlib import Path

import aiofiles
import httpx
from loguru import logger

from src.core.config import settings
from src.tools.browser import analyze_page_visual, get_page_content

TOOL_TIMEOUT = 30

# --- Anthropic tool schemas ---

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for information using DuckDuckGo. Returns a summary of the top results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file from the workspace sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path inside the workspace."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the workspace sandbox. Creates parent directories if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path inside the workspace."},
                "content": {"type": "string", "description": "The content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "execute_shell",
        "description": "Run a shell command inside the workspace sandbox. Returns stdout and stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "get_page_content",
        "description": "Visit a URL with a real browser and return the page content as Markdown. Fast and cheap — use this for reading articles, docs, or any text-heavy page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to visit."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "analyze_page_visual",
        "description": "Take a screenshot of a URL and visually analyze it with the LLM. Use this when you need to understand page layout, charts, images, or visual elements that text extraction would miss.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to screenshot."},
                "query": {"type": "string", "description": "What to look for or analyze in the screenshot."},
            },
            "required": ["url", "query"],
        },
    },
]


def _safe_path(relative: str) -> Path:
    """Resolve a relative path inside the workspace, rejecting escapes."""
    workspace = Path(settings.WORKSPACE_DIR).resolve()
    target = (workspace / relative).resolve()
    if not str(target).startswith(str(workspace)):
        raise ValueError(f"Path escapes sandbox: {relative}")
    return target


async def web_search(query: str) -> str:
    logger.info(f"[tool] web_search: {query}")
    try:
        api_url = f"{settings.DDGS_API_URL}/search"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(api_url, params={"q": query, "max_results": 5})
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return "No results found."

        lines = []
        for r in data:
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"**{title}**\n{body}\n{href}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"


async def read_file(path: str) -> str:
    logger.info(f"[tool] read_file: {path}")
    target = _safe_path(path)
    if not target.exists():
        return f"File not found: {path}"
    async with aiofiles.open(target, "r") as f:
        return await f.read()


async def write_file(path: str, content: str) -> str:
    logger.info(f"[tool] write_file: {path}")
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(target, "w") as f:
        await f.write(content)
    return f"Written {len(content)} bytes to {path}"


async def execute_shell(command: str) -> str:
    logger.info(f"[tool] execute_shell: {command}")
    workspace = Path(settings.WORKSPACE_DIR).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TOOL_TIMEOUT)
        parts = []
        if stdout:
            parts.append(f"stdout:\n{stdout.decode(errors='replace')}")
        if stderr:
            parts.append(f"stderr:\n{stderr.decode(errors='replace')}")
        if not parts:
            parts.append(f"(exit code {proc.returncode})")
        return "\n".join(parts)
    except asyncio.TimeoutError:
        proc.kill()
        return "Command timed out after 30s."


# Dispatch map
DISPATCH = {
    "web_search": web_search,
    "read_file": read_file,
    "write_file": write_file,
    "execute_shell": execute_shell,
    "get_page_content": get_page_content,
    "analyze_page_visual": analyze_page_visual,
}


async def run_tool(name: str, args: dict) -> str:
    fn = DISPATCH.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    try:
        return await fn(**args)
    except Exception as e:
        logger.error(f"[tool] {name} failed: {e}")
        return f"Tool error: {e}"
