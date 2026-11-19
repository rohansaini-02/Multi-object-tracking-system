"""
MOT17 Benchmark API Presentation Router (Backend API Layer Tier).

Exposes HTTP REST endpoints to discover available MOT17 sequences, execute CLEAR-MOT
evaluations against the ground truth annotations, and read the persisted evaluation
history used by the frontend benchmark dashboard.

Architectural Role:
- Enforces authentication checks on every endpoint via `get_current_user`.
- Delegates evaluation execution to `benchmark_service` which wraps the existing
  `MOTEvaluator` implementation.
- Keeps long-running metric computation off the event loop via `asyncio.to_thread`.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_db_session
from backend.app.models.user import User
from backend.app.repositories.tracking_job_repository import TrackingJobRepository
from backend.app.repositories.track_result_repository import TrackResultRepository
from backend.app.repositories.video_repository import VideoRepository
from backend.app.schemas.benchmark import (
    BenchmarkEvaluateRequest,
    BenchmarkMetrics,
    BenchmarkResultsResponse,
    BenchmarkSequencesResponse,
)
from backend.app.services import benchmark_service
from backend.app.services.job_service import JobService

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.get("/sequences", response_model=BenchmarkSequencesResponse)
async def list_benchmark_sequences(
    current_user: User = Depends(get_current_user),
) -> BenchmarkSequencesResponse:
    """
    Discover the MOT17 sequences that can be evaluated on this deployment.

    Args:
        current_user: Authenticated User entity resolved from JWT bearer token dependency.

    Returns:
        BenchmarkSequencesResponse with locally installed sequences, the standard
        MOT17 catalog and the resolved ground truth directory.
    """
    return benchmark_service.list_sequences()


@router.get("/results", response_model=BenchmarkResultsResponse)
async def list_benchmark_results(
    current_user: User = Depends(get_current_user),
) -> BenchmarkResultsResponse:
    """
    Retrieve the persisted benchmark evaluation history (newest first).

    Args:
        current_user: Authenticated User entity resolved from JWT bearer token dependency.

    Returns:
        BenchmarkResultsResponse containing every stored evaluation record.
    """
    results = benchmark_service.list_evaluations()
    return BenchmarkResultsResponse(count=len(results), results=results)


@router.post("/evaluate", response_model=BenchmarkMetrics)
async def evaluate_benchmark_sequence(
    req: BenchmarkEvaluateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BenchmarkMetrics:
    """
    Run a MOT17 CLEAR-MOT evaluation for a single sequence using the existing MOTEvaluator.

    Args:
        req: Evaluation request containing the sequence name and optional results source.
        current_user: Authenticated User entity resolved from JWT bearer token dependency.
        session: Injected async database session transaction context.

    Returns:
        BenchmarkMetrics DTO with the measured MOTA / IDF1 / IDSW / precision / recall.

    Raises:
        HTTPException 404: If the ground truth or the predicted results file is missing.
        HTTPException 400: If the linked tracking job does not belong to the current user.
        HTTPException 503: If the py-motmetrics dependency is unavailable.
    """
    job_mot_path = None

    if req.job_id:
        job_repo = TrackingJobRepository(session)
        video_repo = VideoRepository(session)
        service = JobService(job_repo, video_repo, TrackResultRepository(session))
        artifacts = await service.get_job_artifacts(req.job_id, current_user.id)
        job_mot_path = artifacts["paths"]["output_mot_path"]

    try:
        metrics = await asyncio.to_thread(
            benchmark_service.evaluate_sequence, req, job_mot_path
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"py-motmetrics is not available on the server: {exc}",
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation input could not be parsed: {exc}",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Evaluation input could not be parsed: {exc}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark evaluation failed: {exc}",
        )

    return metrics
