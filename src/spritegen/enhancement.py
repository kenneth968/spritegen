"""Provider-backed prompt enhancement for project assets."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


ENHANCEMENT_TIMEOUT_SECONDS = 45


class PromptEnhancementError(Exception):
    pass


class PromptEnhancer:
    def enhance(
        self,
        brief: str,
        provider: str,
        model: str,
        api_key: str | None = None,
    ) -> str:
        if provider == "mock":
            return self._enhance_mock(brief)
        if provider == "pollinations":
            return self._enhance_pollinations(brief)
        if provider == "openai":
            return self._enhance_openai(brief, model, api_key)
        if provider == "openrouter":
            return self._enhance_openrouter(brief, model, api_key)
        raise PromptEnhancementError(f"Unsupported prompt provider: {provider}")

    def _enhance_mock(self, brief: str) -> str:
        raw_marker = "Raw asset idea:"
        detail_marker = "Extra details:"
        raw = self._line_after_marker(brief, raw_marker) or "game asset"
        details = self._line_after_marker(brief, detail_marker)
        parts = [
            raw,
            details,
            "game-ready asset, coherent project style, clean silhouette",
            "consistent palette, readable at small size, isolated on plain background",
        ]
        return ", ".join(part for part in parts if part)

    def _enhance_pollinations(self, brief: str) -> str:
        encoded = urllib.parse.quote(brief)
        url = f"https://text.pollinations.ai/{encoded}?model=openai"
        try:
            with urllib.request.urlopen(url, timeout=ENHANCEMENT_TIMEOUT_SECONDS) as resp:
                return resp.read().decode("utf-8").strip()
        except Exception as exc:
            raise PromptEnhancementError(f"Pollinations enhancement failed: {exc}") from exc

    def _enhance_openai(
        self,
        brief: str,
        model: str,
        api_key: str | None,
    ) -> str:
        token = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not token:
            raise PromptEnhancementError("OPENAI_API_KEY is required for prompt enhancement")

        payload = {
            "model": model,
            "input": brief,
        }
        result = self._post_json(
            url="https://api.openai.com/v1/responses",
            payload=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        text = self._extract_openai_text(result)
        if not text:
            raise PromptEnhancementError("OpenAI response did not include text output")
        return text.strip()

    def _enhance_openrouter(
        self,
        brief: str,
        model: str,
        api_key: str | None,
    ) -> str:
        token = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not token:
            raise PromptEnhancementError("OPENROUTER_API_KEY is required for prompt enhancement")

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": brief,
                }
            ],
        }
        result = self._post_json(
            url="https://openrouter.ai/api/v1/chat/completions",
            payload=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "HTTP-Referer": "https://github.com/spritegen",
            },
        )
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PromptEnhancementError("OpenRouter response did not include text output") from exc
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        text = str(content).strip()
        if not text:
            raise PromptEnhancementError("OpenRouter response did not include text output")
        return text

    def _post_json(
        self,
        url: str,
        payload: dict,
        headers: dict[str, str],
    ) -> dict:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                **headers,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=ENHANCEMENT_TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise PromptEnhancementError(f"Request failed: {exc}") from exc

    def _extract_openai_text(self, result: dict) -> str:
        if isinstance(result.get("output_text"), str):
            return result["output_text"]

        texts: list[str] = []
        for item in result.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
        return "\n".join(texts)

    def _line_after_marker(self, text: str, marker: str) -> str:
        for line in text.splitlines():
            if line.startswith(marker):
                return line.split(marker, 1)[1].strip()
        return ""
