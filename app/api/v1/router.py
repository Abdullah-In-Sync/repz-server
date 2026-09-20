from fastapi import APIRouter

from app.api.v1.routes import admin, body_metrics, exercises, reports, routines, users, workouts

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(exercises.router)
api_router.include_router(routines.router)
api_router.include_router(workouts.router)
api_router.include_router(body_metrics.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
