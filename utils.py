"""
# decorate coroutine with redis connection
def with_connection(func: Callable):
    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        redis_ = await redis.from_url("redis://redis")
        try:
            result = await func(*args, redis=redis_, **kwargs)
        finally:
            await redis_.close()
        return result
    return wrapped

# rates = await asyncio.gather(redis.get(f'currency_rate:{cur_actual}_KZT'), redis.get(f'currency_rate:{cur_target}_KZT'))
"""
