FROM nikolaik/python-nodejs:python3.12-nodejs22

# Primary backend for the whole system is now llama.cpp (OpenAI compatible) on host :8080.
# The container itself talks to it via host.docker.internal when used as OpenHands controller.
# We keep some langchain-ollama only for optional legacy paths / future experiments.
# Install torch CPU-only FIRST to avoid pulling NVIDIA CUDA wheels/packages during pip (user has AMD GPU, no need for CUDA in the Linux sandbox image)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    requests web3 moralis python-dotenv fastmcp loguru \
    langgraph langchain-core langchain-ollama pydantic \
    openai \
    ruff bandit mypy pytest pyflakes pip-audit \
    pypdf pdfplumber pymupdf pytesseract easyocr \
    "unstructured[pdf]" pdf2image  # analyzers (ruff/bandit/mypy/pyflakes/pip-audit) power code_intelligence + analyze_folder inside OpenHands; unstructured/pdf2image for document parsing/OCR

# Note (2026-06): See requirements-core.txt + requirements-agentic.txt at project root for the split used by the host env.
# The image preloads the skills + v2 agents so sandboxes and the mcp-skills sidecar have them available.

# tesseract-ocr (system) + poppler-utils for pdf2image
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils && rm -rf /var/lib/apt/lists/*

# Copy skills so they are available in the image (for import in code execution)
COPY openhands_skills /opt/openhands_skills
COPY openhands_multiagent_v2 /opt/openhands_multiagent_v2

# Python path for baked imports in sandboxes
ENV PYTHONPATH="/opt"

RUN echo "Custom runtime with skills preloaded. Primary LLM = llama.cpp (gemma-4-26b-qat). Full document support: pymupdf + unstructured[pdf] + pdf2image + tesseract/easyocr (CPU torch to avoid NVIDIA)."

WORKDIR /workspace
