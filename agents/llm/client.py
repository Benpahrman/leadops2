"""
agents/llm/client.py - Core inference engine client and LLM provider gateway.
Supports Groq (Llama 3.3 70B), Nvidia NIM, Azure AI Foundry, Gemini, and Local Ollama fallback.
"""
import json
import os
import re
from typing import Any, Optional, Dict, List
import httpx
from openai import OpenAI
from ..logging_config import get_logger

logger = get_logger("llm_client")

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as _dotenv_ex:
    logger.debug(f"Optional dotenv load skipped: {_dotenv_ex}")


class LLMClientBase:
    """Base LLM Gateway for provider initialization and completion execution."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        nvidia_key = os.environ.get("NVIDIA_API_KEY", "").strip()
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

        detected_local_url = None
        for candidate in ["http://localhost:11435/v1", "http://127.0.0.1:11435/v1"]:
            try:
                with httpx.Client(timeout=0.3) as http_client:
                    r = http_client.get(f"{candidate}/models")
                    if r.status_code == 200:
                        detected_local_url = candidate
                        break
            except Exception:
                continue

        azure_foundry_endpoint = os.environ.get(
            "AZURE_AI_FOUNDRY_ENDPOINT",
            "https://christopherbenpahrman-1055-resou.services.ai.azure.com/openai/v1"
        )
        azure_foundry_primary = os.environ.get("PROVIDER") == "azure_foundry" or os.environ.get("AZURE_AI_FOUNDRY_PRIMARY") == "true"

        # Priority 1: Explicit base_url passed
        if base_url:
            self.provider = "custom"
            self.base_url = base_url
            self.api_key = api_key or "custom"
            self.model = model or "gpt-oss:latest"
        # Priority 2: Azure AI Foundry when explicitly configured as primary
        elif azure_foundry_primary:
            self.provider = "azure_foundry"
            self.base_url = azure_foundry_endpoint
            self.api_key = api_key or os.environ.get("AZURE_AI_FOUNDRY_API_KEY") or os.environ.get("AZURE_API_KEY", "azure_token")
            self.model = model or os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-5-mini")
        # Priority 3: Fast cloud inference (Groq - sub-second latency)
        elif groq_key:
            self.provider = "groq"
            self.base_url = "https://api.groq.com/openai/v1"
            self.api_key = api_key or groq_key
            self.model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        # Priority 4: Nvidia Nemotron / Llama
        elif nvidia_key:
            self.provider = "nvidia"
            self.base_url = "https://integrate.api.nvidia.com/v1"
            self.api_key = api_key or nvidia_key
            self.model = model or os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
        # Priority 5: Gemini Flash
        elif gemini_key:
            self.provider = "gemini"
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            self.api_key = api_key or gemini_key
            self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        # Priority 6: Local Ollama
        elif detected_local_url:
            self.provider = "ollama"
            self.base_url = detected_local_url
            self.api_key = api_key or "ollama"
            self.model = model or "qwen2.5:3b"
        else:
            self.provider = "ollama"
            self.base_url = "http://localhost:11435/v1"
            self.api_key = api_key or "ollama"
            self.model = model or "qwen2.5:3b"

        self._client: Optional[OpenAI] = None
        logger.info(f"⚡ [LLM ENGINE INITIALIZED] Provider: {self.provider} | Model: '{self.model}' | Endpoint: {self.base_url}")

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if self.provider == "azure_foundry":
                self._client = self._get_azure_foundry_client() or OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    default_headers={"api-key": self.api_key} if self.api_key else None,
                    max_retries=0,
                )
            else:
                self._client = OpenAI(base_url=self.base_url, api_key=self.api_key, max_retries=0)
        return self._client

    def _get_azure_foundry_client(self) -> Optional[OpenAI]:
        """Initialize Azure AI Foundry OpenAI client with direct API key or DefaultAzureCredential."""
        endpoint = os.environ.get(
            "AZURE_AI_FOUNDRY_ENDPOINT",
            "https://christopherbenpahrman-1055-resou.services.ai.azure.com/openai/v1"
        )
        scope = os.environ.get("AZURE_AI_FOUNDRY_SCOPE", "https://ai.azure.com/.default")
        azure_key = os.environ.get("AZURE_AI_FOUNDRY_API_KEY") or os.environ.get("AZURE_API_KEY", "").strip()

        # Step 1: Direct API key for instantaneous connection without IMDS delay
        if azure_key:
            try:
                return OpenAI(
                    base_url=endpoint,
                    api_key=azure_key,
                    default_headers={"api-key": azure_key}
                )
            except Exception as e_key:
                logger.warning(f"Azure API key client init warning: {e_key}")

        if getattr(self, "_azure_credential_failed", False):
            return None

        # Step 2: Fallback to Bearer token provider via DefaultAzureCredential
        try:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            token_provider = get_bearer_token_provider(cred, scope)
            return OpenAI(base_url=endpoint, api_key=token_provider)
        except Exception as e_tok:
            self._azure_credential_failed = True
            logger.debug(f"Azure token provider initialization info: {e_tok}")

        return None

    def _call_azure_foundry(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1500,
    ) -> str:
        """Execute completion on Azure AI Foundry (gpt-5-mini) with automatic failover."""
        deployment_name = os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-5-mini")
        client = self._get_azure_foundry_client()
        if not client:
            return ""

        effective_max = max(max_tokens, 1500)

        # Step 1: chat.completions.create with max_completion_tokens (optimized for gpt-5 reasoning)
        try:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.append({"role": "user", "content": user_prompt})
            chat_resp = client.chat.completions.create(
                model=deployment_name,
                messages=msgs,
                max_completion_tokens=effective_max,
                timeout=30.0,
            )
            msg = chat_resp.choices[0].message
            content = msg.content or ""
            if not content and getattr(msg, "reasoning", None):
                content = msg.reasoning or ""
            if "<think>" in content:
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
            if content.strip():
                logger.info(f"✓ [AZURE AI FOUNDRY CHAT] Generated {len(content)} chars via {deployment_name}")
                return content.strip()
        except Exception as e_chat:
            logger.debug(f"Azure chat completions fallback to responses: {e_chat}")

        # Step 2: Attempt Azure AI Foundry Responses API if chat didn't return text
        try:
            combined_input = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
            resp = client.responses.create(
                model=deployment_name,
                input=combined_input,
                timeout=30.0,
            )
            text = getattr(resp, "output_text", None)
            if not text and hasattr(resp, "output"):
                for item in resp.output:
                    if getattr(item, "type", "") == "message" and hasattr(item, "content"):
                        for c in item.content:
                            t = getattr(c, "text", "")
                            if t:
                                text = t
                                break
            if text:
                if "<think>" in text:
                    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
                logger.info(f"✓ [AZURE AI FOUNDRY RESPONSES] Generated {len(text)} chars via {deployment_name}")
                return text.strip()
        except Exception as e_resp:
            logger.error(f"❌ [AZURE AI FOUNDRY FAILED] {e_resp}")

        return ""

    def is_available(self) -> bool:
        """Check if LLM backend is available."""
        if os.environ.get("MOCK_LLM") == "true":
            return False
        if self.provider in ("groq", "nvidia", "gemini", "azure_foundry") and bool(self.api_key):
            return True
        if bool(os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")) or bool(os.environ.get("AZURE_AI_FOUNDRY_API_KEY")):
            return True
        try:
            with httpx.Client(timeout=0.6) as http_client:
                r = http_client.get(f"{self.base_url}/models")
                return r.status_code == 200
        except Exception:
            return False

    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> str:
        """Execute a live LLM completion request with clean reasoning stripping."""
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("MOCK_LLM") == "true" or not self.is_available():
            return ""

        logger.info(f"🧠 [LLM PROMPT DISPATCH] Provider: {self.provider} | Model: {self.model}")
        if self.provider == "azure_foundry":
            azure_res = self._call_azure_foundry(system_prompt, user_prompt, max_tokens)
            if azure_res:
                return azure_res

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=45.0,
            )
            msg = response.choices[0].message
            content = msg.content or ""
            if not content and getattr(msg, "reasoning", None):
                content = msg.reasoning or ""
            if "<think>" in content:
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
            content = content.strip()
            logger.info(f"✓ [LLM COMPLETION RECEIVED] Generated {len(content)} chars")
            return content
        except Exception as e:
            logger.warning(f"⚠️ [LLM NOTICE] Provider error ({type(e).__name__}: {e}). Trying fallback...")

            # Fallback 1: Google Gemini 3.6 Flash (High Throughput, Ultra-Fast & Extremely Reliable)
            gemini_key = os.environ.get("GEMINI_API_KEY")
            if gemini_key:
                try:
                    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
                    fb_gemini = OpenAI(
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                        api_key=gemini_key,
                        max_retries=1,
                    )
                    g_resp = fb_gemini.chat.completions.create(
                        model=gemini_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=25.0,
                    )
                    c = g_resp.choices[0].message.content or ""
                    if "<think>" in c:
                        c = re.sub(r"<think>.*?</think>", "", c, flags=re.DOTALL)
                    if c.strip():
                        logger.info(f"✓ [GEMINI FALLBACK SUCCESS] Generated {len(c)} chars via {gemini_model}")
                        return c.strip()
                except Exception as g_err:
                    logger.warning(f"Gemini fallback warning: {g_err}")

            # Fallback 2: Nvidia Nemotron if configured (30s timeout)
            if os.environ.get("NVIDIA_API_KEY"):
                try:
                    fallback_client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=os.environ["NVIDIA_API_KEY"])
                    fb_resp = fallback_client.chat.completions.create(
                        model=os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b"),
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=30.0,
                    )
                    c = fb_resp.choices[0].message.content or ""
                    if "<think>" in c:
                        c = re.sub(r"<think>.*?</think>", "", c, flags=re.DOTALL)
                    if c.strip():
                        logger.info(f"✓ [NVIDIA FALLBACK SUCCESS] Generated {len(c)} chars via Nemotron")
                        return c.strip()
                except Exception as fb_err:
                    logger.warning(f"Nvidia fallback error: {fb_err}")

            # Fallback 3: Alternative Groq Model if rate-limited on primary model
            if os.environ.get("GROQ_API_KEY") and ("rate_limit" in str(e).lower() or "429" in str(e)):
                for alt_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                    try:
                        groq_alt = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"])
                        alt_resp = groq_alt.chat.completions.create(
                            model=alt_model,
                            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                            temperature=temperature,
                            max_tokens=max_tokens,
                            timeout=20.0,
                        )
                        c = alt_resp.choices[0].message.content or ""
                        if "<think>" in c:
                            c = re.sub(r"<think>.*?</think>", "", c, flags=re.DOTALL)
                        if c.strip():
                            logger.info(f"✓ [GROQ ALT MODEL SUCCESS] Generated {len(c)} chars via {alt_model}")
                            return c.strip()
                    except Exception as alt_err:
                        logger.debug(f"Groq alt model {alt_model} failed: {alt_err}")

            # Fallback 4: Azure AI Foundry (gpt-5-mini)
            if not getattr(self, "_azure_credential_failed", False):
                try:
                    azure_res = self._call_azure_foundry(system_prompt, user_prompt, max_tokens)
                    if azure_res:
                        return azure_res
                except Exception as azure_err:
                    logger.warning(f"Azure AI Foundry fallback error: {azure_err}")

            return ""

    def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> dict[str, Any]:
        """Generate completion and extract robust JSON object response."""
        res = self.generate_completion(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens)
        if not res:
            return {}
        if "{" in res and "}" in res:
            start = res.find("{")
            end = res.rfind("}") + 1
            try:
                return json.loads(res[start:end])
            except Exception as ex:
                logger.debug(f"JSON parsing fallback for structured JSON generation: {ex}")
        return {}

    def generate_completion_with_tools(

        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tool_turns: int = 3,
        temperature: float = 0.2,
    ) -> str:
        """Execute multi-turn LLM reasoning loop with active tool calling (search, fetch, WAF probe, DOM prune)."""
        from agents.tools.ai_tools_registry import AI_TOOL_DEFINITIONS, execute_tool_call

        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("MOCK_LLM") == "true" or not self.is_available():
            return ""

        active_tools = tools or AI_TOOL_DEFINITIONS
        current_messages = list(messages)

        for turn in range(max_tool_turns):
            try:
                logger.info(f"🧠 [LLM AGENT TURN {turn + 1}] Dispatching with {len(active_tools)} tools")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=current_messages,
                    tools=active_tools,
                    temperature=temperature,
                    timeout=120.0,
                )
                choice = response.choices[0]
                msg = choice.message
                current_messages.append(msg)

                # If model requested tool calls, execute them and feed results back
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        func_name = tool_call.function.name
                        try:
                            args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            args = {}
                        
                        tool_result = execute_tool_call(func_name, args)
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result, default=str),
                        })
                else:
                    # Final response generated
                    return msg.content or ""
            except Exception as e:
                logger.warning(f"Tool calling turn {turn + 1} error: {e}")
                break

        return current_messages[-1].get("content", "") if current_messages else ""
