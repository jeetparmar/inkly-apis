from enum import Enum

class PostDuration(str, Enum):
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    ALL_TIME = "all"

class PostSortBy(str, Enum):
    NEWEST = "newest"
    MOST_VIEWED = "most_viewed"
    MOST_HEARTED = "most_hearted"
    MOST_COMMENTED = "most_commented"

class PostFilter(str, Enum):
    FOLLOWING = "following"
    FOLLOWERS = "followers"
    NONE = "none"
