import json
import re
import google.generativeai as genai
from app.utils.settings import settings


def ask_from_gemini(
    ai_key: str,
    content_type="story",
    content_about="a little boy",
    content_size=300,
    content_language="english",
    content_theme="fantasy",
) -> dict:
    content_prompt = f"""
    Write a {content_theme} {content_type} about {content_about}.
    The story should be approximately {content_size} words and written in {content_language}.

    Requirements:
    - Include a creative and relevant title.
    - Maintain a fantasy theme throughout the story.
    - The response MUST be valid JSON.
    - Use exactly two keys in the JSON:
    - "title": the story title
    - "content": the full story text
    - Do NOT include any explanation, markdown, or text outside the JSON object.
    """
    # 3. Configure Gemini API key
    genai.configure(api_key=ai_key)
    # Use a text-capable Gemini model
    model = genai.GenerativeModel(settings.gemini_model)

    # Generate content
    response = model.generate_content(content_prompt)
    return extract_json_from_llm(response.text)


def extract_json_from_llm(text: str) -> dict:
    """
    Extracts JSON from markdown or plain text LLM output
    """
    if not text:
        raise ValueError("Empty LLM response")

    # Remove ```json and ``` fences if present
    cleaned = re.sub(r"^```json\s*|```$", "", text.strip(), flags=re.MULTILINE)

    return json.loads(cleaned)
