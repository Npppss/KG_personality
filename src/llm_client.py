import json
import os
import time
from typing import Any, Dict
from openai import OpenAI
import google.generativeai as genai
from .config import load_config

class LLMClient:
    def __init__(self):
        cfg = load_config()
        self.provider = cfg["llm_provider"]
        self.temperature = cfg["temperature"]
        self.session_logs = []  # store prompts/responses
        
        print(f"🔧 Initializing LLMClient with provider: {self.provider}")
        
        if self.provider == "openai":
            self.model = cfg["openai_model"]
            self.client = OpenAI(api_key=cfg["openai_api_key"])
            print(f"✅ OpenAI client initialized with model: {self.model}")
        elif self.provider == "gemini":
            self.model = cfg["gemini_model"]
            genai.configure(api_key=cfg["gemini_api_key"])
            # Try different model variants for Gemini
            model_variants = [
                "models/gemini-1.5-flash-latest",
                "models/gemini-1.5-pro-latest", 
                "models/gemini-pro",
                self.model
            ]
            
            self.client = None
            for variant in model_variants:
                try:
                    self.client = genai.GenerativeModel(variant)
                    self.model = variant
                    print(f"✅ Gemini client initialized with model: {variant}")
                    break
                except Exception as e:
                    print(f"❌ Failed to load {variant}: {str(e)[:50]}...")
                    continue
            
            if self.client is None:
                raise ValueError("No working Gemini model found")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def complete_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if self.provider == "openai":
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = resp.choices[0].message.content
        elif self.provider == "gemini":
            prompt = f"{system_prompt}\n\n{user_prompt}\n\nPlease respond with valid JSON only."
            resp = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                )
            )
            content = resp.text
        
        self.session_logs.append({
            "timestamp": time.time(),
            "system": system_prompt,
            "user": user_prompt,
            "assistant": content,
        })
        return json.loads(content)

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "openai":
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = resp.choices[0].message.content
        elif self.provider == "gemini":
            prompt = f"{system_prompt}\n\n{user_prompt}"
            resp = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                )
            )
            content = resp.text
        
        self.session_logs.append({
            "timestamp": time.time(),
            "system": system_prompt,
            "user": user_prompt,
            "assistant": content,
        })
        return content
    
    def save_session(self, filepath: str):
        """Save session logs to file"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.session_logs, f, ensure_ascii=False, indent=2)

    def save_session(self, out_dir: str) -> str:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"session-{int(time.time())}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.session_logs, f, ensure_ascii=False, indent=2)
        return path