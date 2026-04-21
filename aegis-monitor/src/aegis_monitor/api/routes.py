"""HTTP routes for the monitor agent.

Address-management endpoints only at this stage — flag query + WS stream
arrive in later tasks as the persistence and rule pipeline come online.

The `AddressManager` instance lives on `app.state.addrs`, populated by
the lifespan handler in `aegis_monitor.main`. Endpoints pull it via
`Request.app.state` rather than FastAPI's `Depends` to keep the wiring
obvious.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ValidationError

from ..address_manager import AddressManager
from ..schemas import MonitorRequest

router = APIRouter()


class MonitorItem(BaseModel):
    address: str
    active: bool


class MonitorList(BaseModel):
    addresses: list[str]


def _addrs(request: Request) -> AddressManager:
    mgr = getattr(request.app.state, "addrs", None)
    if mgr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="address manager not initialised",
        )
    return mgr


@router.post(
    "/monitor",
    status_code=status.HTTP_201_CREATED,
    response_model=MonitorItem,
)
async def add_monitor(body: MonitorRequest, request: Request) -> MonitorItem:
    await _addrs(request).add(body.address)
    return MonitorItem(address=body.address, active=True)


@router.delete("/monitor/{address}", response_model=MonitorItem)
async def remove_monitor(address: str, request: Request) -> MonitorItem:
    # Validate address format by round-tripping through MonitorRequest so we
    # stay DRY with the POST handler's validator.
    try:
        normalised = MonitorRequest(address=address).address
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="address must be a 0x-prefixed 40-hex-char string",
        ) from None
    removed = await _addrs(request).remove(normalised)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="address is not being monitored",
        )
    return MonitorItem(address=normalised, active=False)


@router.get("/monitor", response_model=MonitorList)
async def list_monitored(request: Request) -> MonitorList:
    return MonitorList(addresses=await _addrs(request).list_active())
