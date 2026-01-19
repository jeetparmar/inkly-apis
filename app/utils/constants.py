VALID_PLATFORMS = {"ios", "android"}
INTERESTS_DATA = [
    # Stories
    {"title": "Horror Stories", "icon": "skull"},
    {"title": "Mystery Stories", "icon": "search"},
    {"title": "Romantic Stories", "icon": "heart"},
    {"title": "Sci-Fi Stories", "icon": "planet"},
    
    # Jokes
    {"title": "Funny Jokes", "icon": "happy"},
    {"title": "Dark Humor", "icon": "moon"},
    {"title": "Sarcastic Jokes", "icon": "invert-mode"},
    
    # Poetry
    {"title": "Classic Poetry", "icon": "feather"},
    {"title": "Modern Verse", "icon": "brush"},
    {"title": "Haikus", "icon": "leaf"},
    
    # Quotes
    {"title": "Inspirational Quotes", "icon": "star"},
    {"title": "Motivational Quotes", "icon": "rocket"},
    {"title": "Philosophical Quotes", "icon": "infinite"},
    
    # Facts
    {"title": "Science Facts", "icon": "flask"},
    {"title": "History Facts", "icon": "library"},
    {"title": "Nature Facts", "icon": "earth"},
    
    # Riddles
    {"title": "Logic Riddles", "icon": "extension-puzzle"},
    {"title": "Brain Teasers", "icon": "bulb"},
    {"title": "Mystery Riddles", "icon": "help-buoy"},
    
    # Articles
    {"title": "Tech Articles", "icon": "code-slash"},
    {"title": "Health Articles", "icon": "medkit"},
    {"title": "Business Articles", "icon": "briefcase"},
]
CONTENT_CONFIGS_DATA = [
    {
        "type": "story",
        "emoji": "📚",
        "label": "Story",
        "sizes": [
            {
                "id": 300,
                "label": "Short (≈300 words)"
            },
            {
                "id": 600,
                "label": "Medium (≈600 words)"
            },
            {
                "id": 1000,
                "label": "Long (≈1000 words)"
            }
        ],
        "themes": [
            {
                "id": "adventure",
                "label": "🗺️ Adventure"
            },
            {
                "id": "mystery",
                "label": "🔍 Mystery"
            },
            {
                "id": "romance",
                "label": "💕 Romance"
            },
            {
                "id": "fantasy",
                "label": "🧙 Fantasy"
            },
            {
                "id": "sci-fi",
                "label": "🚀 Sci-Fi"
            },
            {
                "id": "horror",
                "label": "👻 Horror"
            },
            {
                "id": "drama",
                "label": "🎭 Drama"
            }
        ],
        "placeholder": "Write your captivating story here...",
        "prompt_placeholder": "e.g., \"magical forest adventure\", \"time traveling detective\"...",
        "field_label": "Your Story",
        "button_text": "Publish Story",
        "points": 50,
        "icon": "📚",
        "stats_field": "total_stories"
    },
    {
        "type": "joke",
        "emoji": "😂",
        "label": "Joke",
        "sizes": [
            {
                "id": 50,
                "label": "Short (≈50 words)"
            },
            {
                "id": 80,
                "label": "Medium (≈80 words)"
            },
            {
                "id": 100,
                "label": "Long (≈100 words)"
            }
        ],
        "themes": [
            {
                "id": "puns",
                "label": "🎯 Puns"
            },
            {
                "id": "one-liner",
                "label": "⚡ One-Liner"
            },
            {
                "id": "observational",
                "label": "👀 Observational"
            },
            {
                "id": "dark-humor",
                "label": "🌑 Dark Humor"
            },
            {
                "id": "wordplay",
                "label": "📝 Wordplay"
            },
            {
                "id": "slapstick",
                "label": "🤡 Slapstick"
            }
        ],
        "placeholder": "Share your funniest joke...",
        "prompt_placeholder": "e.g., \"programmers\", \"coffee addiction\", \"cats vs dogs\"...",
        "field_label": "Your Joke",
        "button_text": "Share Joke",
        "points": 40,
        "icon": "😂",
        "stats_field": "total_jokes"
    },
    {
        "type": "poetry",
        "emoji": "🎭",
        "label": "Poetry",
        "sizes": [
            {
                "id": 50,
                "label": "Short (≈50 words)"
            },
            {
                "id": 100,
                "label": "Medium (≈100 words)"
            },
            {
                "id": 150,
                "label": "Long (≈150 words)"
            }
        ],
        "themes": [
            {
                "id": "romantic",
                "label": "💖 Romantic"
            },
            {
                "id": "nature",
                "label": "🌿 Nature"
            },
            {
                "id": "melancholic",
                "label": "🌧️ Melancholic"
            },
            {
                "id": "inspirational",
                "label": "✨ Inspirational"
            },
            {
                "id": "haiku",
                "label": "🎋 Haiku"
            },
            {
                "id": "free-verse",
                "label": "🎨 Free Verse"
            }
        ],
        "placeholder": "Express your poetry and verses...",
        "prompt_placeholder": "e.g., \"nature\", \"love\", \"dreams\", \"seasons\"...",
        "field_label": "Your Poetry",
        "button_text": "Share Poetry",
        "points": 40,
        "icon": "🎭",
        "stats_field": "total_poetry"
    },
    {
        "type": "quote",
        "emoji": "💭",
        "label": "Quote",
        "sizes": [
            {
                "id": 20,
                "label": "Short (≈20 words)"
            },
            {
                "id": 30,
                "label": "Medium (≈30 words)"
            },
            {
                "id": 50,
                "label": "Long (≈50 words)"
            }
        ],
        "themes": [
            {
                "id": "motivational",
                "label": "💪 Motivational"
            },
            {
                "id": "inspirational",
                "label": "✨ Inspirational"
            },
            {
                "id": "philosophical",
                "label": "🤔 Philosophical"
            },
            {
                "id": "life-lessons",
                "label": "📖 Life Lessons"
            },
            {
                "id": "success",
                "label": "🏆 Success"
            },
            {
                "id": "wisdom",
                "label": "🦉 Wisdom"
            }
        ],
        "placeholder": "Share an inspiring quote...",
        "prompt_placeholder": "e.g., \"success\", \"friendship\", \"courage\", \"life\"...",
        "field_label": "Your Quote",
        "button_text": "Share Quote",
        "points": 40,
        "icon": "💭",
        "stats_field": "total_quotes"
    },
    {
        "type": "fact",
        "emoji": "🧠",
        "label": "Fact",
        "sizes": [
            {
                "id": 30,
                "label": "Short (≈30 words)"
            },
            {
                "id": 60,
                "label": "Medium (≈60 words)"
            },
            {
                "id": 90,
                "label": "Long (≈90 words)"
            }
        ],
        "themes": [
            {
                "id": "science",
                "label": "🔬 Science"
            },
            {
                "id": "history",
                "label": "📜 History"
            },
            {
                "id": "nature",
                "label": "🌍 Nature"
            },
            {
                "id": "technology",
                "label": "💻 Technology"
            },
            {
                "id": "space",
                "label": "🌌 Space"
            },
            {
                "id": "animals",
                "label": "🦁 Animals"
            }
        ],
        "placeholder": "Share an interesting fact...",
        "prompt_placeholder": "e.g., \"space\", \"animals\", \"history\", \"science\"...",
        "field_label": "Your Fact",
        "button_text": "Share Fact",
        "points": 40,
        "icon": "🧠",
        "stats_field": "total_facts"
    },
    {
        "type": "riddle",
        "emoji": "🧩",
        "label": "Riddle",
        "sizes": [
            {
                "id": 30,
                "label": "Short (≈30 words)"
            },
            {
                "id": 60,
                "label": "Medium (≈60 words)"
            },
            {
                "id": 90,
                "label": "Long (≈90 words)"
            }
        ],
        "themes": [
            {
                "id": "logic",
                "label": "🧩 Logic"
            },
            {
                "id": "wordplay",
                "label": "📝 Wordplay"
            },
            {
                "id": "math",
                "label": "🔢 Math"
            },
            {
                "id": "lateral-thinking",
                "label": "💡 Lateral Thinking"
            },
            {
                "id": "mystery",
                "label": "🔍 Mystery"
            },
            {
                "id": "tricky",
                "label": "😏 Tricky"
            }
        ],
        "placeholder": "Create a challenging riddle...",
        "prompt_placeholder": "e.g., \"mystery\", \"logic\", \"wordplay\", \"nature\"...",
        "field_label": "Your Riddle",
        "button_text": "Share Riddle",
        "points": 40,
        "icon": "🧩",
        "stats_field": "total_riddles"
    },
    {
        "type": "article",
        "emoji": "📰",
        "label": "Article",
        "sizes": [
            {
                "id": 80,
                "label": "Short (≈80 words)"
            },
            {
                "id": 150,
                "label": "Medium (≈150 words)"
            },
            {
                "id": 250,
                "label": "Long (≈250 words)"
            }
        ],
        "themes": [
            {
                "id": "technology",
                "label": "💻 Technology"
            },
            {
                "id": "health",
                "label": "🏥 Health"
            },
            {
                "id": "lifestyle",
                "label": "🌟 Lifestyle"
            },
            {
                "id": "education",
                "label": "📚 Education"
            },
            {
                "id": "business",
                "label": "💼 Business"
            },
            {
                "id": "opinion",
                "label": "💭 Opinion"
            }
        ],
        "placeholder": "Write your informative article...",
        "prompt_placeholder": "e.g., \"technology\", \"health\", \"education\", \"lifestyle\"...",
        "field_label": "Your Article",
        "button_text": "Publish Article",
        "points": 40,
        "icon": "📰",
        "stats_field": "total_articles"
    }
]
MAIL_SUBJECT = "Here is your Login OTP from Inkly."
MAIL_SMTP_HOST = "smtp.gmail.com"
MAIL_SMTP_PORT = 587
MAIL_SMTP_USER = "jeetparmar33@gmail.com"
MAIL_SMTP_PASSWORD = "ndunfilkieiqghib"
OTP_EMAIL_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Email</title>
            <style>
                body {
                    background-color: #f4f4f7;
                    font-family: Arial, Helvetica, sans-serif;
                    margin: 0;
                    padding: 0;
                }
                .email-wrapper {
                    width: 100%;
                    background-color: #f4f4f7;
                    padding: 20px 0;
                }
                .email-content {
                    max-width: 600px;
                    margin: auto;
                    background: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 3px 8px rgba(0,0,0,0.05);
                }
                .header {
                    background: #4f46e5;
                    color: #ffffff;
                    padding: 20px;
                    text-align: center;
                    font-size: 24px;
                    font-weight: bold;
                }
                .body {
                    padding: 30px;
                    color: #333333;
                    font-size: 16px;
                    line-height: 1.5;
                }
                .otp-box {
                    display: block;
                    margin: 30px auto;
                    padding: 15px 25px;
                    background: #4f46e5;
                    color: white;
                    font-size: 28px;
                    font-weight: bold;
                    border-radius: 6px;
                    letter-spacing: 4px;
                    text-align: center;
                    width: fit-content;
                }
                .footer {
                    text-align: center;
                    color: #6b7280;
                    font-size: 13px;
                    padding: 25px;
                }
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <div class="email-content">
                    <div class="header">
                        Verification Required
                    </div>
                    <div class="body">
                        <p>Dear User,</p>
                        <p>You are trying to perform the following process:</p>
                        <p style="font-size:18px; font-weight:bold; color:#111;">
                            {{process_type}}
                        </p>
                        <p>To complete this action, please use the One-Time Password (OTP) below:</p>
                        <div class="otp-box">
                            {{one_time_password}}
                        </div>
                        <p>
                            This OTP is valid for the next <strong>10 minutes</strong>.  
                            Please do not share this code with anyone.
                        </p>
                        <p>If you did not request this process, please ignore this email.</p>
                        <p>Thank you,<br/>Team Inkly</p>
                    </div>
                    <div class="footer">
                        © 2025 Your Company. All rights reserved.
                    </div>
                </div>
            </div>
        </body>
    </html>
"""
