DEFAULT_USERNAME = "true_spark_{data}"
INVALID_TOKEN_NO_SUBJECT = "invalid token: no subject"
INVALID_TOKEN = "invalid or expired token"
USER_FOUND = "user found"
IS_REQUIRED = "{data} is required"
CREATED_SUCCESS = "{data} created successfully"
INVALID_DATA = "invalid {data}"
SELECT_REQUIRED = "plase select {data}"
ALREADY_EXISTS_FIELD = "a user with this {data} already exists."
FETCHED_SUCCESS = "{data} fetched successfully"
ALREADY_LOGOUT = "user already logged out"
LOGOUT_SUCCESS = "user logged out successfully"
NOT_FOUND = "{data} not found"
OTP_VERIFIED = "otp verified"
NO_PREFERENCE = "no preference saved yet"
SOME_ERROR = "something went wrong, Please contact"
ALREADY_EXISTS = "already {data}"
ACTION_SUCCESS = "{data} successfully"
OTP_SENT = "otp sent to {email}"
SAVED_SUCCESS = "{data} saved successfully"
REFERRAL_CODE_GENERATED = "{data} referral codes generated successfully"
REFERRAL_CODE_REDEEMED = "referral code redeemed successfully"
REFERRAL_CODE_INVALID = "invalid or used referral code"

PROMPT_FOR_FETCH_TAGS_HASHTAGS = f"""
Prompt:
    Read the following story and generate two lists:

Hashtags – 8–12 concise, relevant hashtags that capture the main themes, characters, settings, emotions, and plot elements. Use camelCase or underscores for multi-word hashtags (e.g., #AbandonedLighthouse).

Emoji Keywords – 8–12 relevant keywords or short phrases with a matching emoji or icon that visually represents the concept.

Avoid generic words like 'story' or 'fiction'. Format the output as two separate bullet lists under the headings 'Hashtags' and 'Emoji Keywords'.

Story:
    {{story}}"""

PROMPT_FOR_STORY = f"""Write a short {{language}} story titled {{title}}. The story should include exactly {{words_count}} words, each with distinct personalities, roles, and motivations. Ensure that the characters interact meaningfully and contribute to the progression of the story. The tone should be engaging, the plot should have a clear beginning, middle, and end, and the title should feel relevant to the theme of the story."""
