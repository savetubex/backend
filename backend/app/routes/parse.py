from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, HttpUrl
from app.services.parser import MediaParser

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
@limiter.limit("10/minute")  # Increased rate limit
async def parse_media(request: Request, data: ParseRequest):
    """Parse public media URLs for metadata only.
    
    DISCLAIMER: This service only extracts publicly available metadata.
    Users are responsible for complying with platform terms of service.
    """
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
    """Get current usage count for an IP"""
    from app.services.parser import ip_view_counter, VIEW_LIMIT
    return {
        "used": ip_view_counter.get(ip, 0),
        "limit": VIEW_LIMIT,
        "remaining": max(0, VIEW_LIMIT - ip_view_counter.get(ip, 0))
    }