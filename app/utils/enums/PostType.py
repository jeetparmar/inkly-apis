from enum import Enum


class PostType(str, Enum):
    story = "story"
    joke = "joke"
    poem = "poem"
    quote = "quote"
    fact = "fact"
    riddle = "riddle"
    article = "article"
