from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, profiles, infringements, takedowns, subscriptions, dashboard, social_media

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["protected-profiles"])
api_router.include_router(infringements.router, prefix="/infringements", tags=["infringements"])
api_router.include_router(takedowns.router, prefix="/takedowns", tags=["takedown-requests"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(social_media.router, prefix="/social-media", tags=["social-media-monitoring"])