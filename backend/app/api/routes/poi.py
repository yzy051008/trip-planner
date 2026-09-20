"""POI 图片接口。"""

import threading
import time
from typing import Optional

from fastapi import APIRouter

from ...services.amap_service import get_amap_service


router = APIRouter(prefix="/poi", tags=["POI"])

_photo_semaphore = threading.BoundedSemaphore(3)
_PHOTO_MIN_INTERVAL = 0.4
_photo_last_call = 0.0
_photo_call_lock = threading.Lock()


def _rate_limited_photo_call(amap_service, name: str) -> Optional[str]:
    global _photo_last_call
    with _photo_call_lock:
        wait = _photo_last_call + _PHOTO_MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _photo_last_call = time.monotonic()
    return amap_service.get_poi_photo_by_name(name)


@router.get("/photo", summary="获取景点图片")
def get_attraction_photo(name: str):
    amap_service = get_amap_service()
    with _photo_semaphore:
        photo_url = _rate_limited_photo_call(amap_service, name)

    return {
        "success": True,
        "message": "获取图片成功",
        "data": {"name": name, "photo_url": photo_url},
    }
