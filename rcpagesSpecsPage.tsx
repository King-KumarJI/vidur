warning: in the working copy of 'backend/app/core/ai_reasoning/ollama_client.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/backend/app/core/ai_reasoning/ollama_client.py b/backend/app/core/ai_reasoning/ollama_client.py[m
[1mindex 27f479b..7c21c60 100644[m
[1m--- a/backend/app/core/ai_reasoning/ollama_client.py[m
[1m+++ b/backend/app/core/ai_reasoning/ollama_client.py[m
[36m@@ -22,11 +22,6 @@[m [mfrom app.core.ai_reasoning.exceptions import OllamaUnavailableError[m
 [m
 logger = get_logger("ai_reasoning.ollama_client")[m
 [m
[31m-#: Request timeout (seconds) for a single Ollama call. Local inference[m
[31m-#: on a small model is expected to complete well within this window;[m
[31m-#: if it doesn't, the caller should fall back rather than hang.[m
[31m-DEFAULT_TIMEOUT_SECONDS = 30.0[m
[31m-[m
 [m
 class OllamaClient:[m
     """Minimal client for Ollama's `/api/chat` endpoint, requesting a[m
[36m@@ -36,7 +31,7 @@[m [mclass OllamaClient:[m
         self,[m
         host: Optional[str] = None,[m
         model: Optional[str] = None,[m
[31m-        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,[m
[32m+[m[32m        timeout_seconds: Optional[float] = None,[m
         transport: Optional[httpx.BaseTransport] = None,[m
     ) -> None:[m
         """`transport` is real (system default) unless injected, the[m
[36m@@ -46,7 +41,9 @@[m [mclass OllamaClient:[m
         without a live Ollama instance."""[m
         self._host = (host or settings.OLLAMA_HOST).rstrip("/")[m
         self._model = model or settings.OLLAMA_MODEL[m
[31m-        self._timeout_seconds = timeout_seconds[m
[32m+[m[32m        self._timeout_seconds = ([m
[32m+[m[32m            timeout_seconds if timeout_seconds is not None else settings.OLLAMA_TIMEOUT_SECONDS[m
[32m+[m[32m        )[m
         self._transport = transport[m
 [m
     def chat_json(self, system_prompt: str, user_prompt: str) -> str:[m
