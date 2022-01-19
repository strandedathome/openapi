from rolls.util.default_root import DEFAULT_ROOT_PATH
from rolls.util.config import load_config

CACHE_CONFIG = {
    'default': {
        'cache': "aiocache.SimpleMemoryCache",
    },
    # use redis, uncomment next
    # 'default': {
    #     'cache': "aiocache.RedisCache",
    #     'endpoint': "",
    #     'port': 6379,
    #     'password': '',
    # }
}


ROLLS_ROOT_PATH = DEFAULT_ROOT_PATH
ROLLS_CONFIG = load_config(ROLLS_ROOT_PATH, "config.yaml")
