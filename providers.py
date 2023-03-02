import asyncio
from enum import StrEnum
from functools import cache

from fastapi import FastAPI

from models import Tickets

app = FastAPI()


class JsonPath(StrEnum):
    PROVIDER_A = 'data/response_a.json'
    PROVIDER_B = 'data/response_b.json'


@cache
def load_tickets(path: JsonPath) -> Tickets:
    return Tickets.parse_file(path)


async def load_tickets_coro(path: JsonPath) -> Tickets:
    # i didnt want to make code harder writing or importing package for coro caching
    return load_tickets(path)


@app.post('/provider_a/search')
async def provider_a() -> Tickets:
    res = await asyncio.gather(asyncio.sleep(30), load_tickets_coro(JsonPath.PROVIDER_A))
    return res[1]


@app.post('/provider_b/search')
async def provider_b() -> Tickets:
    res = await asyncio.gather(asyncio.sleep(60), load_tickets_coro(JsonPath.PROVIDER_B))
    return res[1]
