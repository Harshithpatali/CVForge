import json
import re
from openai import OpenAI
from app.core.config import settings

def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.S)
        if not match:
            raise ValueError('Grok did not return valid JSON.')
        return json.loads(match.group(0))

def generate_resume(prompt: str) -> dict:
    if not settings.xai_api_key:
        raise RuntimeError('XAI_API_KEY is not configured.')
    client = OpenAI(api_key=settings.xai_api_key, base_url=settings.xai_base_url)
    response = client.chat.completions.create(
        model=settings.xai_model,
        messages=[
            {'role': 'system', 'content': 'You are a production resume generation engine. Return JSON only.'},
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content or ''
    return _extract_json(content)
