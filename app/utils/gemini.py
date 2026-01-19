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
    You are a creative writer.
    
    Task: Write a {content_theme} {content_type} about {content_about}.
    Language: {content_language}.

    Requirements:
    1. The content MUST be valid JSON with exactly two keys: "title" and "content".
    2. "title": A creative title.
    3. "content": The story text.
    4. Theme: {content_theme}.
    5. STYLE: Use simple, easy-to-understand language suitable for a general audience. Avoid complex vocabulary.
    
    LENGTH CONSTRAINT:
    - Target word count: {content_size} words.
    - MAXIMUM permitted words: {int(content_size) + 20}.
    - STOP writing immediately if you are approaching this limit.
    - Shorter is better than longer.
    
    Output JSON ONLY. No markdown formatting.
    """
    # 3. Configure Gemini API key
    genai.configure(api_key=ai_key)
    
    # Calculate max tokens (approx 2 tokens per word + buffer for JSON overhead)
    # 1 word ~ 1.3 to 1.5 tokens usually, but we use 2.5 to be safe + 100 for JSON structure
    max_tokens = int(content_size * 2.5) + 100
    
    generation_config = genai.GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=0.7,
        response_mime_type="application/json"
    )

    # Use a text-capable Gemini model
    model = genai.GenerativeModel(settings.gemini_model)

    # Generate content
    response = model.generate_content(content_prompt, generation_config=generation_config)
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
