import json
import re

from openai import OpenAI

from app.core.config import settings


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r'^\s*\`\`\`(?:json)?\s*', '', text)
    text = re.sub(r'\s*\`\`\`\s*$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.S)
        if not match:
            raise ValueError('Groq did not return valid JSON.')
        return json.loads(match.group(0))


def generate_resume(prompt: str) -> dict:
    if not settings.groq_api_key:
        raise RuntimeError('GROQ_API_KEY is not configured.')

    client = OpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                'role': 'system',
                'content': (
                    'You are a production resume generation engine. '
                    'Return valid JSON only. Do not invent candidate facts.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.2,
        response_format={'type': 'json_object'},
    )
    content = response.choices[0].message.content or ''
    return _extract_json(content)
