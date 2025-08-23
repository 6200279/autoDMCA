#!/usr/bin/env python3
"""
Minimal test backend for local validation
Provides basic health checks and database connectivity tests
"""

import json
import asyncio
import os
from typing import Dict, Any
import asyncpg
import redis
from datetime import datetime

async def test_postgres():
    """Test PostgreSQL connection"""
    try:
        conn = await asyncpg.connect(
            host="postgres",
            port=5432,
            database="contentprotection", 
            user="postgres",
            password="localtest123"
        )
        
        result = await conn.fetchrow("SELECT version()")
        await conn.close()
        
        return {
            "status": "connected",
            "version": result[0] if result else "unknown"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def test_redis():
    """Test Redis connection"""
    try:
        r = redis.Redis(
            host="redis",
            port=6379,
            password="localredis123",
            decode_responses=True
        )
        
        # Test basic operations
        test_key = f"test:{datetime.now().timestamp()}"
        r.set(test_key, "test_value")
        value = r.get(test_key)
        r.delete(test_key)
        
        return {
            "status": "connected",
            "test_successful": value == "test_value"
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e)
        }

async def health_check():
    """Comprehensive health check"""
    postgres_status = await test_postgres()
    redis_status = test_redis()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "postgres": postgres_status,
            "redis": redis_status
        }
    }

async def main():
    """Simple HTTP server for testing"""
    from aiohttp import web, web_response
    
    async def handle_health(request):
        result = await health_check()
        return web_response.json_response(result)
    
    async def handle_root(request):
        return web_response.json_response({
            "message": "Content Protection Platform - Test Backend",
            "status": "running",
            "endpoints": [
                "/health",
                "/test/postgres", 
                "/test/redis"
            ]
        })
    
    async def handle_test_postgres(request):
        result = await test_postgres()
        return web_response.json_response(result)
    
    async def handle_test_redis(request):
        result = test_redis()
        return web_response.json_response(result)
    
    # Enable CORS for local testing
    async def cors_handler(request, handler):
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    app = web.Application(middlewares=[cors_handler])
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/test/postgres', handle_test_postgres)
    app.router.add_get('/test/redis', handle_test_redis)
    
    # Handle OPTIONS for CORS
    async def handle_options(request):
        return web_response.Response(
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    
    app.router.add_route('OPTIONS', '/{path:.*}', handle_options)
    
    print("Starting test backend server on http://0.0.0.0:8000")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    
    print("Test backend is ready!")
    print("Available endpoints:")
    print("  GET /health - Health check with database tests")
    print("  GET /test/postgres - Test PostgreSQL connection")
    print("  GET /test/redis - Test Redis connection")
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())