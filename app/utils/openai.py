import json
import re
from openai import OpenAI
from app.utils.settings import settings


def ask_from_openai(
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
    1. The content MUST be valid JSON with exactly three keys: "title", "content", and "tags".
    2. "title": A creative title.
    3. "content": The story text.
    4. "tags": A list of tags related to the story.
    5. Theme: {content_theme}.
    6. STYLE: Use simple, easy-to-understand language suitable for a general audience. Avoid complex vocabulary.
    
    LENGTH CONSTRAINT:
    - Target word count: {content_size} words.
    - MAXIMUM permitted words: {int(content_size) + 20}.
    - STOP writing immediately if you are approaching this limit.
    - Shorter is better than longer.
    
    Output JSON ONLY. No markdown formatting.
    """
    
    # Calculate max tokens (approx 2 tokens per word + buffer for JSON overhead)
    # 1 word ~ 1.3 to 1.5 tokens usually, but we use 2.5 to be safe + 100 for JSON structure
    max_tokens = int(content_size * 2.5) + 100
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=ai_key)
        
        # Generate content
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4o-mini for cost efficiency
            messages=[
                {"role": "system", "content": "You are a creative writer who generates content in JSON format."},
                {"role": "user", "content": content_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        return extract_json_from_llm(response.choices[0].message.content)
    
    except Exception as e:
        # Import OpenAI exceptions
        from openai import RateLimitError, AuthenticationError, APIError, APIConnectionError
        
        # Handle specific OpenAI errors
        if isinstance(e, RateLimitError):
            raise ValueError("OpenAI API quota exceeded. Please check your plan and billing details.")
        elif isinstance(e, AuthenticationError):
            raise ValueError("Invalid OpenAI API key. Please check your API key.")
        elif isinstance(e, APIConnectionError):
            raise ValueError("Failed to connect to OpenAI API. Please check your internet connection.")
        elif isinstance(e, APIError):
            raise ValueError(f"OpenAI API error: {str(e)}")
        else:
            # Generic error
            raise ValueError(f"Error generating content with OpenAI: {str(e)}")



def extract_json_from_llm(text: str) -> dict:
    """
    Extracts JSON from markdown or plain text LLM output
    """
    if not text:
        raise ValueError("Empty LLM response")

    # Remove ```json and ``` fences if present
    cleaned = re.sub(r"^```json\s*|```$", "", text.strip(), flags=re.MULTILINE)

    return json.loads(cleaned)
