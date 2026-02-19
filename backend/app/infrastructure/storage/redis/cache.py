import json
import redis
import hashlib
import random
import asyncio
from typing import Any, Optional, Callable, Set
from functools import wraps
from app.core.config import settings
from app.infrastructure.logging.config import logger


class CacheManager:
    """
    通用的缓存管理器，支持 Redis 和内存缓存 fallback
    包含缓存击穿、缓存穿透、缓存雪崩的防护措施
    """

    _instance: Optional["CacheManager"] = None
    _redis_client: Optional["redis.Redis"] = None
    _memory_cache: dict = {}
    
    _lock_set: Set[str] = set()
    _lock: asyncio.Lock = asyncio.Lock()
    
    _NULL_VALUE = "__NULL_CACHE__"
    _NULL_TTL = 300

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
                    decoded = json.loads(data)
                    if decoded == self._NULL_VALUE:
                        return self._NULL_VALUE
                    return decoded
            except Exception as e:
                logger.warning(f"Redis get 失败: {e}")
        
        value = self._memory_cache.get(key)
        if value == self._NULL_VALUE:
            return self._NULL_VALUE
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        if ttl is None:
            ttl = settings.REDIS_DEFAULT_TTL
        
        final_ttl = self._add_random_ttl(ttl)

        try:
            serialized = json.dumps(value, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"序列化失败: {e}")
            return False

        self._memory_cache[key] = value

        if self._redis_client:
            try:
                if final_ttl > 0:
                    self._redis_client.setex(key, final_ttl, serialized)
                else:
                    self._redis_client.set(key, serialized)
                return True
            except Exception as e:
                logger.warning(f"Redis set 失败: {e}")

        return True

    def set_null(self, key: str) -> bool:
        """
        缓存空值（防止缓存穿透）
        """
        return self.set(key, self._NULL_VALUE, self._NULL_TTL)

    def is_null_value(self, value: Any) -> bool:
        """判断是否是空值标记"""
        return value == self._NULL_VALUE

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

    def _add_random_ttl(self, base_ttl: int) -> int:
        """
        添加随机过期时间（防止缓存雪崩）
        在基础 TTL 基础上增加 ±10% 的随机偏移
        """
        if base_ttl <= 0:
            return base_ttl
        
        offset = int(base_ttl * 0.1)
        random_ttl = base_ttl + random.randint(-offset, offset)
        return max(random_ttl, 60)

    async def _acquire_lock(self, key: str) -> bool:
        """获取互斥锁（防止缓存击穿）"""
        async with self._lock:
            if key in self._lock_set:
                return False
            self._lock_set.add(key)
            return True

    async def _release_lock(self, key: str):
        """释放互斥锁"""
        async with self._lock:
            if key in self._lock_set:
                self._lock_set.remove(key)

    def cached(
        self, 
        prefix: str, 
        ttl: Optional[int] = None,
        protect_breakdown: bool = True,
        protect_penetration: bool = True,
        protect_avalanche: bool = True
    ):
        """
        装饰器：缓存函数返回值，包含完整的缓存防护
        
        Args:
            prefix: 缓存键前缀
            ttl: 过期时间（秒），None 使用默认值
            protect_breakdown: 是否开启缓存击穿防护
            protect_penetration: 是否开启缓存穿透防护
            protect_avalanche: 是否开启缓存雪崩防护
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key = self._generate_key(prefix, *args, **kwargs)
                
                cached_value = self.get(key)
                
                if cached_value is not None:
                    if protect_penetration and self.is_null_value(cached_value):
                        logger.debug(f"缓存命中空值: {prefix}")
                        return None
                    logger.debug(f"缓存命中: {prefix}")
                    return cached_value

                if protect_breakdown:
                    acquired = await self._acquire_lock(key)
                    if not acquired:
                        for _ in range(10):
                            await asyncio.sleep(0.1)
                            cached_value = self.get(key)
                            if cached_value is not None:
                                if protect_penetration and self.is_null_value(cached_value):
                                    return None
                                return cached_value
                        return None

                try:
                    result = await func(*args, **kwargs)
                    
                    if result is None or (isinstance(result, (list, dict)) and not result):
                        if protect_penetration:
                            self.set_null(key)
                        return None
                    
                    final_ttl = ttl
                    if not protect_avalanche and ttl is not None:
                        final_ttl = ttl
                    
                    self.set(key, result, final_ttl)
                    return result
                finally:
                    if protect_breakdown:
                        await self._release_lock(key)
            
            return wrapper
        return decorator


cache_manager = CacheManager()
