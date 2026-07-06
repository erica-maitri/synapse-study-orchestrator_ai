import os
from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm

# Load root-level .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

# Set environment variables for LiteLLM to point to local Ollama
os.environ["OPENAI_API_BASE"] = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "ollama")

# Define the models
# Planner uses llama3.2 (3B)
planner_model = LiteLlm(model="openai/llama3.2:latest")

# Subagents use qwen2.5:1.5b
subagent_model = LiteLlm(model="openai/qwen2.5:1.5b")

print(f"[Agents] Initialized models. OpenAI Base: {os.environ['OPENAI_API_BASE']}")
