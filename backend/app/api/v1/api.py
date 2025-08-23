from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, profiles, infringements, takedowns, subscriptions, dashboard, social_media, scanning, enhanced_scanning, delisting, gift_subscriptions, addons, stripe_webhooks, watermarking

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["protected-profiles"])
api_router.include_router(infringements.router, prefix="/infringements", tags=["infringements"])
api_router.include_router(takedowns.router, prefix="/takedowns", tags=["takedown-requests"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(social_media.router, prefix="/social-media", tags=["social-media-monitoring"])
api_router.include_router(scanning.router, prefix="/scanning", tags=["content-scanning"])
api_router.include_router(enhanced_scanning.router, prefix="/scanning-v2", tags=["enhanced-content-scanning"])
api_router.include_router(delisting.router, prefix="/delisting", tags=["search-engine-delisting"])
api_router.include_router(gift_subscriptions.router, prefix="/gifts", tags=["gift-subscriptions"])
api_router.include_router(addons.router, prefix="/addons", tags=["addon-services"])
api_router.include_router(stripe_webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(watermarking.router, prefix="/watermarking", tags=["content-watermarking"])