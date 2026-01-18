from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, HttpUrl
from parser import MediaParser, ip_view_counter, VIEW_LIMIT

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class ParseRequest(BaseModel):
    url: HttpUrl

class MediaFormat(BaseModel):
    quality: str
    url: str
    type: str = 'video'

class ImageFormat(BaseModel):
    label: str
    url: str

class ParseResponse(BaseModel):
    platform: str
    title: str
    thumbnail: str
    formats: list[MediaFormat]
    images: list[ImageFormat] = []

@router.post("/parse", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_media(request: Request, data: ParseRequest):
    try:
        parser = MediaParser()
        client_ip = get_remote_address(request)
        result = await parser.parse_url(str(data.url), client_ip)
        return ParseResponse(**result)
    except ValueError as e:
        if str(e) == "LIMIT_REACHED":
            raise HTTPException(
                status_code=429, 
                detail={
                    "error": "LIMIT_REACHED",
                    "message": "Free limit reached. Please sign in to continue."
                }
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to parse media URL")

@router.get("/usage/{ip}")
async def get_usage(ip: str):
    return {
        "used": ip_view_counter.get(ip, 0),
        "limit": VIEW_LIMIT,
        "remaining": max(0, VIEW_LIMIT - ip_view_counter.get(ip, 0))
    }