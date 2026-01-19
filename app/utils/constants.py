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
