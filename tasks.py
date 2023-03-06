import time
import xml.etree.ElementTree as ET
from datetime import date
from typing import Callable, Iterable, Optional

import httpx
from gevent import monkey
from huey import RedisHuey, crontab

from models import Ticket, Tickets

monkey.patch_all()


huey = RedisHuey(host='redis', results=True)


# flexible filtering and sorting
def filter_and_sort_tickets(tickets: Tickets,
                            filters: Optional[Iterable[Callable]] = None,
                            sorts: Optional[Iterable[Callable]] = None,
                            **filter_kwargs: dict) -> Tickets:
    # to sort more efficiently, we make one function for filtering and one for sorting
    if filters:
        filter_function = lambda ticket: all([f(ticket, **filter_kwargs) for f in filters])
        tickets.__root__ = list(filter(filter_function, tickets.__root__))
    if sorts:
        sort_function = lambda ticket: tuple([s(ticket) for s in sorts])
        tickets.__root__ = sorted(tickets.__root__, key=sort_function)
    return tickets


@huey.task(retries=3, retry_delay=10)
def search(dep: Optional[str] = None, arr: Optional[str] = None) -> Tickets:
    a_res = resolve_provider_a()
    b_res = resolve_provider_b()
    # tasks is scheduled, wait for them to be finished
    while a_res(preserve=True) is None or b_res(preserve=True) is None:
        time.sleep(0.1)
    res = a_res() + b_res()

    # check if first flight from departure airport and last is too arrival
    def dep_arr_filter(ticket: Ticket, dep: str, arr: str) -> bool:
        return ticket.flights[0].segments[0].dep.airport == dep and ticket.flights[-1].segments[-1].arr.airport == arr

    filters = (dep_arr_filter, ) if dep and arr else ()
    res = filter_and_sort_tickets(res, filters, dep=dep, arr=arr)  # type: ignore

    return res


# probably should be cached but we will not cache for clear experement
@huey.task(retries=3, retry_delay=10)
def resolve_provider_a() -> Tickets:
    # httpx request to provider a
    resp = httpx.post('http://providers/provider_a/search', timeout=120)
    return Tickets.parse_raw(resp.text)


# probably should be cached but we will not cache for clear experement
@huey.task(retries=3, retry_delay=10)
def resolve_provider_b() -> Tickets:
    # httpx request to provider b
    resp = httpx.post('http://providers/provider_b/search', timeout=120)
    return Tickets.parse_raw(resp.text)


@huey.periodic_task(crontab(hour='6', minute='0'), retries=3, retry_delay=10)
def load_currency_rates():
    # load currency rates
    date_ = date.today().strftime('%d.%m.%Y')
    resp = httpx.get(f'https://www.nationalbank.kz/rss/get_rates.cfm?fdate={date_}', timeout=5)
    tree = ET.fromstring(resp.text)

    # parse currency rates and put them to redis
    data = {}
    for cur_data in tree.iter('item'):
        cur = cur_data.find('title').text  # type: ignore
        value = float(cur_data.find('description').text)  # type: ignore
        quant = float(cur_data.find('quant').text)  # type: ignore
        data[f'currency_rate:{cur}_KZT'] = value / quant

    # reuse huey redis connection
    huey.storage.conn.mset(data)  # type: ignore
