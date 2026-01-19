from enum import Enum


class PostType(str, Enum):
    story = "story"
    joke = "joke"
    poetry = "poetry"
    quote = "quote"
    fact = "fact"
    riddle = "riddle"
    article = "article"
