from enum import StrEnum
from typing import List, Optional, Self

from pydantic import BaseModel


# Data model
class PlaceNTime(BaseModel):
    at: str
    airport: str


class Segment(BaseModel):
    operating_airline: str
    marketing_airline: str
    flight_number: int
    equipment: Optional[str]
    dep: PlaceNTime
    arr: PlaceNTime
    baggage: Optional[str]


class Flight(BaseModel):
    duration: int
    segments: List[Segment]


class Pricing(BaseModel):
    total: float
    base: float
    taxes: float
    currency: str  # in future probably should be Enum with validation and error handling


class Ticket(BaseModel):
    flights: List[Flight]
    refundable: bool
    validating_airline: str
    pricing: Pricing


class Amount(BaseModel):
    amount: float
    currency: str


class Tickets(BaseModel):
    __root__: List[Ticket]

    def __add__(self, other: Self) -> Self:
        res = Tickets(__root__=self.__root__ + other.__root__)
        return res


class TicketResult(Ticket):
    price: Amount


class TicketsWithPrice(BaseModel):
    __root__: List[TicketResult]


# I like APIs not tied up with http protocol with all post, 200 responses
# with body according to model below, but for this task I dont want to tune all FastAPI for this standart
# class BasicAPIResponse(BaseModel):
#     result: Any
#     success: bool
#     errors: List[Tuple[int, str]]


class AirflowSearchResponse(BaseModel):
    search_id: str


class Status(StrEnum):
    COMPLITED = "COMPLETED"
    PENDING = "PENDING"


class AirflowResultResponse(BaseModel):
    search_id: str
    status: Status
    items: Optional[TicketsWithPrice]
