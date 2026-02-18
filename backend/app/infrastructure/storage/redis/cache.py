import json
import redis
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
from app.core.config import settings
from app.infrastructure.logging.config import logger


class CacheManager:
    """通用的缓存管理器，支持 Redis 和内存缓存 fallback"""

    _instance: Optional["CacheManager"] = None
    _redis_client: Optional["redis.Redis"] = None
    _memory_cache: dict = {}

    def __new__(cls) -> "CacheManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化缓存管理器"""
        try:
            self._redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=10
            )
            # 测试连接
            self._redis_client.ping()
            logger.info(f"Redis 缓存已连接: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis 连接失败，使用内存缓存: {e}")
            self._redis_client = None

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [prefix]
        if args:
            key_parts.append(str(args))
        if kwargs:
            # 排序 kwargs 以确保相同参数生成相同的 key
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(str(sorted_kwargs))
        
        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if self._redis_client:
            try:
                data = self._redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get 失败: {e}")
                # 回退到内存缓存
        return self._memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        if ttl is None:
            ttl = settings.REDIS_DEFAULT_TTL

        try:
            serialized = json.dumps(value, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"序列化失败: {e}")
            return False

        # 先存内存缓存
        self._memory_cache[key] = value

        if self._redis_client:
            try:
                if ttl > 0:
                    self._redis_client.setex(key, ttl, serialized)
                else:
                    self._redis_client.set(key, serialized)
                return True
            except Exception as e:
                logger.warning(f"Redis set 失败: {e}")

        return True

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self._memory_cache:
            del self._memory_cache[key]

        if self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete 失败: {e}")

        return True

    def clear(self, pattern: Optional[str] = None) -> bool:
        """清空缓存（可选按 pattern 匹配）"""
        if pattern:
            keys_to_delete = [k for k in self._memory_cache if pattern in k]
            for k in keys_to_delete:
                del self._memory_cache[k]
        else:
            self._memory_cache.clear()

        if self._redis_client:
            try:
                if pattern:
                    keys = self._redis_client.keys(pattern)
                    if keys:
                        self._redis_client.delete(*keys)
                else:
                    self._redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Redis clear 失败: {e}")

        return True

    def cached(self, prefix: str, ttl: Optional[int] = None):
        """
        装饰器：缓存函数返回值
        
        Args:
            prefix: 缓存键前缀
            ttl: 过期时间（秒），None 使用默认值
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key = self._generate_key(prefix, *args, **kwargs)
                cached_value = self.get(key)
                if cached_value is not None:
                    logger.debug(f"缓存命中: {prefix}")
                    return cached_value

                result = await func(*args, **kwargs)
                self.set(key, result, ttl)
                return result
            return wrapper
        return decorator


cache_manager = CacheManager()
