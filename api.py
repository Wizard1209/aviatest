from typing import Optional

import redis as redis_
from fastapi import FastAPI
from tasks import search, load_currency_rates, huey
from models import AirflowSearchResponse, Status, AirflowResultResponse, Amount, TicketResult, TicketsWithPrice


redis = redis_.Redis(host='redis')

core_app = FastAPI(debug=True)


# could be cached with cache clear if last cache was done before 12 a.m.
def get_currency_rate(cur_actual: str, cur_target: str) -> float:
    if cur_actual == cur_target:
        return 1.0
    kzt_rate_actual = 1.0 if cur_actual == 'KZT' else redis.get(f'currency_rate:{cur_actual}_KZT')
    kzt_rate_target = 1.0 if cur_target == 'KZT' else redis.get(f'currency_rate:{cur_target}_KZT')
    if not kzt_rate_actual or not kzt_rate_target:
        raise RuntimeError('currency rate not found')
    return float(kzt_rate_actual) / float(kzt_rate_target)


@core_app.on_event("startup")
async def startup_load_currency_rates():
    try:
        get_currency_rate('KZT', 'USD')
    except RuntimeError:
        load_currency_rates()


@core_app.post("/search")
async def search_api(dep: Optional[str] = None, arr: Optional[str] = None) -> AirflowSearchResponse:
    res = search(dep, arr)
    return AirflowSearchResponse(search_id=res.id)


@core_app.get("/results/{search_id}/{currency}")
async def search_result_api(search_id: str, currency: str):
    search_result = huey.result(search_id, preserve=True)
    if search_result is None:
        return AirflowResultResponse(search_id=search_id, status=Status.PENDING, items=None)
    tickets = search_result

    # convert currency
    rate = {}
    res = []
    for ticket in tickets.__root__:  # type: ignore
        if ticket.pricing.currency not in rate:
            rate[ticket.pricing.currency] = get_currency_rate(ticket.pricing.currency, currency)

        amount = ticket.pricing.total * rate[ticket.pricing.currency]
        pr = Amount(amount=amount, currency=currency)
        res.append(TicketResult(**ticket.dict(), price=pr))

    res = sorted(res, key=lambda t: t.price.amount)  # type: ignore
    return AirflowResultResponse(search_id=search_id, status=Status.COMPLITED, items=TicketsWithPrice(__root__=res))
