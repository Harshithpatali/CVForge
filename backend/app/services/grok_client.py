import json
from openai import OpenAI
from app.core.config import settings
from app.schemas.resume import GeneratedResume

class GrokClient:
    def __init__(self):
        if not settings.xai_api_key:
            raise RuntimeError("XAI_API_KEY is not configured")
        self.client=OpenAI(api_key=settings.xai_api_key,base_url="https://api.x.ai/v1")

    def generate(self, system_prompt: str, candidate: dict, job: dict, answers: dict) -> GeneratedResume:
        payload={"candidate":candidate,"job":job,"candidate_answers":answers}
        schema=GeneratedResume.model_json_schema()
        response=self.client.responses.create(
            model=settings.xai_model,
            input=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":json.dumps(payload,ensure_ascii=False)},
            ],
            response_format={"type":"json_schema","json_schema":{"name":"generated_resume","schema":schema,"strict":True}},
        )
        return GeneratedResume.model_validate_json(response.output_text)
