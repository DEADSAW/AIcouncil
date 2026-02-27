"""
config.py — Default agent configurations, provider configs, and constants.
"""

# ---------------------------------------------------------------------------
# Provider definitions
# Each provider entry describes how to call the API.
# ---------------------------------------------------------------------------
PROVIDERS = {
    "groq": {
        "name": "Groq",
        "type": "openai_compatible",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        # Free-tier rate limits (approximate)
        "rate_limit_rpm": 30,
        "rate_limit_rpd": 14400,
    },
    "google": {
        "name": "Google AI Studio",
        "type": "google",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models",
        "env_key": "GOOGLE_API_KEY",
        "default_model": "gemini-2.0-flash",
        "models": [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        "rate_limit_rpm": 15,
        "rate_limit_rpd": 1500,
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "openai_compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "mistralai/mistral-7b-instruct:free",
        "models": [
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemma-3-4b-it:free",
            "deepseek/deepseek-r1:free",
        ],
        "rate_limit_rpm": 20,
        "rate_limit_rpd": 200,
    },
    "cerebras": {
        "name": "Cerebras",
        "type": "openai_compatible",
        "base_url": "https://api.cerebras.ai/v1",
        "env_key": "CEREBRAS_API_KEY",
        "default_model": "llama3.1-70b",
        "models": [
            "llama3.1-70b",
            "llama3.1-8b",
        ],
        "rate_limit_rpm": 30,
        "rate_limit_rpd": 1000,
    },
    "cohere": {
        "name": "Cohere",
        "type": "cohere",
        "env_key": "COHERE_API_KEY",
        "default_model": "command-r-plus",
        "models": [
            "command-r-plus",
            "command-r",
            "command",
        ],
        "rate_limit_rpm": 20,
        "rate_limit_rpd": 1000,
    },
}

# ---------------------------------------------------------------------------
# Agent role definitions
# ---------------------------------------------------------------------------
ROLES = {
    "thinker": {
        "label": "Thinker",
        "color": "#28a745",      # green
        "icon": "💡",
        "system_prompt": (
            "You are a creative and analytical thinker. Your job is to propose "
            "thoughtful, well-reasoned solutions to the question. Be specific, "
            "practical, and clear. Structure your answer with clear headings "
            "when appropriate."
        ),
    },
    "critic": {
        "label": "Critic",
        "color": "#ffc107",      # yellow/amber
        "icon": "🔍",
        "system_prompt": (
            "You are a rigorous critic and challenger. Your job is to find flaws, "
            "weaknesses, and oversights in proposed solutions. Propose better "
            "alternatives where possible. Be constructive but direct."
        ),
    },
    "judge": {
        "label": "Judge",
        "color": "#6f42c1",      # purple
        "icon": "⚖️",
        "system_prompt": (
            "You are an impartial judge reviewing a debate. Analyse both sides "
            "fairly. Score each participant 1–10, declare a winner or consensus, "
            "and give a concise final verdict with the best answer synthesised "
            "from the debate."
        ),
    },
    "researcher": {
        "label": "Researcher",
        "color": "#17a2b8",      # teal
        "icon": "🔬",
        "system_prompt": (
            "You are a thorough researcher. Your job is to provide relevant "
            "background information, cite known facts, and surface edge cases "
            "or considerations that others may have missed."
        ),
    },
    "security_auditor": {
        "label": "Security Auditor",
        "color": "#dc3545",      # red
        "icon": "🛡️",
        "system_prompt": (
            "You are a security auditor. Analyse proposed solutions for security "
            "vulnerabilities, privacy concerns, and potential abuse vectors. "
            "Suggest mitigations for any issues you find."
        ),
    },
}

# ---------------------------------------------------------------------------
# Default council configuration
# ---------------------------------------------------------------------------
DEFAULT_AGENTS = [
    {
        "id": "thinker1",
        "name": "Thinker 1",
        "role": "thinker",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
    },
    {
        "id": "thinker2",
        "name": "Thinker 2 (Critic)",
        "role": "critic",
        "provider": "google",
        "model": "gemini-2.0-flash",
    },
    {
        "id": "judge",
        "name": "Judge",
        "role": "judge",
        "provider": "openrouter",
        "model": "mistralai/mistral-7b-instruct:free",
    },
]

# Debate settings
MAX_REVISION_ROUNDS = 2
VOTE_OPTIONS = ["APPROVE", "REJECT", "NEEDS REVISION"]

# File upload settings
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {".txt", ".py", ".js", ".ts", ".md", ".json", ".csv", ".pdf",
                      ".html", ".css", ".yaml", ".yml", ".sh", ".go", ".rs", ".java",
                      ".c", ".cpp", ".h"}
