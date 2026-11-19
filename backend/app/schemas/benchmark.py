"""
MOT17 Benchmark API Pydantic Schemas for Request & Response DTO Serialization.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BenchmarkEvaluateRequest(BaseModel):
    """
    Request payload triggering a MOT17 CLEAR-MOT evaluation.

    Attributes:
        sequence_name: MOT17 sequence identifier (e.g. 'MOT17-04-FRCNN').
        results_file: Optional explicit path to the predicted MOT results text file.
        job_id: Optional tracking job whose MOT artifact should be evaluated.
    """

    sequence_name: str = Field(..., description="MOT17 sequence identifier to evaluate.")
    results_file: Optional[str] = Field(
        None, description="Optional explicit path to the predicted MOT results text file."
    )
    job_id: Optional[str] = Field(
        None, description="Optional tracking job whose MOT artifact should be evaluated."
    )


class BenchmarkMetrics(BaseModel):
    """
    Measured CLEAR-MOT metrics for a single benchmarked sequence.

    All ratio metrics (mota, idf1, precision, recall) are expressed as fractions
    between 0.0 and 1.0, matching the py-motmetrics output convention.
    """

    sequence_id: str
    mota: float
    idf1: float
    num_switches: int
    precision: float
    recall: float
    mostly_tracked: int
    mostly_lost: int
    evaluated_at: datetime
    status: str = "COMPLETED"
    error_message: Optional[str] = None


class BenchmarkSequenceInfo(BaseModel):
    """
    Availability and metadata description of a single MOT17 benchmark sequence.
    """

    sequence_id: str
    env_tag: str
    description: str
    gt_available: bool
    results_available: bool
    results_file: Optional[str] = None
    last_evaluation: Optional[BenchmarkMetrics] = None


class BenchmarkSequencesResponse(BaseModel):
    """
    Discovery payload listing locally installed sequences and the standard catalog.
    """

    mot17_dir: str
    dataset_available: bool
    sequences: List[BenchmarkSequenceInfo]
    catalog: List[str]


class BenchmarkResultsResponse(BaseModel):
    """
    Payload listing every persisted benchmark evaluation record.
    """

    count: int
    results: List[BenchmarkMetrics]
