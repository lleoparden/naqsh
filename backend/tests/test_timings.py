"""Timings: total_ms is wall time, stage_ms_sum keeps the (overlapping) stage sum."""

from app.pipeline.types import PageJob


def test_total_ms_is_wall_time_when_elapsed_is_known() -> None:
    job = PageJob(id="x", register="egyptian", width=10, height=10)
    job.add_stage("segment", 10_000, 0.0)
    job.add_stage("clean_plate", 20_000, 0.0)
    job.elapsed_ms = 21_500
    data = job.to_dict()
    assert data["total_ms"] == 21_500
    assert data["stage_ms_sum"] == 30_000


def test_total_ms_falls_back_to_stage_sum_when_elapsed_is_missing() -> None:
    job = PageJob(id="x", register="egyptian", width=10, height=10)
    job.add_stage("read", 1_000, 0.0)
    job.add_stage("typeset", 200, 0.0)
    data = job.to_dict()
    assert data["total_ms"] == 1_200
    assert data["stage_ms_sum"] == 1_200
