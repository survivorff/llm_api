"""FastAPI 依赖：获取共享服务、当前 principal。"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.state import AppServices
from ..db.base import get_session
from ..domain.auth import AuthError, Principal


def get_services(request: Request) -> AppServices:
    return request.app.state.services


async def get_principal(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
) -> Principal:
    try:
        return await services.auth.resolve(request, session)
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


def require_admin(request: Request, services: AppServices = Depends(get_services)) -> None:
    try:
        services.auth.verify_admin(request)
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
