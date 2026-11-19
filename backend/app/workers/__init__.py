"""
Background Worker Processes (Backend Application Worker Tier).

Contains the entry points for work that must run outside of the API server's
process. Tracking inference is executed here so that the PyTorch / Ultralytics
memory footprint never lives inside the FastAPI application process.
"""
