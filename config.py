from stor.util.default_root import DEFAULT_ROOT_PATH
from stor.util.config import load_config

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


STOR_ROOT_PATH = DEFAULT_ROOT_PATH
STOR_CONFIG = load_config(STOR_ROOT_PATH, "config.yaml")
