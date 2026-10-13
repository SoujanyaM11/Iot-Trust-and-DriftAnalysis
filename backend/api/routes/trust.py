from fastapi import APIRouter, Request, Depends
from typing import Optional

from ...auth_utils import get_current_user, TokenData

router = APIRouter()


def _get_user_from_token(current_user: TokenData) -> str:
    if not current_user or not current_user.email:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail='Not authenticated')
    return current_user.email


@router.get('/scores')
async def all_scores(request: Request, current_user: TokenData = Depends(get_current_user)):
    user = _get_user_from_token(current_user)
    return {'scores': request.app.state.trust_engine.get_all_scores(user)}


@router.get('/health')
async def network_health(request: Request, current_user: TokenData = Depends(get_current_user)):
    user = _get_user_from_token(current_user)
    return request.app.state.trust_engine.get_network_health(user)


@router.get('/history/{device_id}')
async def score_history(device_id: str, request: Request, current_user: TokenData = Depends(get_current_user)):
    user = _get_user_from_token(current_user)
    return {'device_id': device_id, 'history': request.app.state.trust_engine.get_history(user, device_id)}
