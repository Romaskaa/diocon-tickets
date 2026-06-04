import hashlib
import re

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class ETagMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app: FastAPI,
            include_paths: list[str] | None = None,
            exclude_paths: list[str] | None = None,
            weak: bool = False,
    ) -> None:
        super().__init__(app)
        self.include_patterns = [
            re.compile(path) for path in include_paths
        ] if include_paths else None
        self.exclude_patterns = [
            re.compile(path) for path in exclude_paths
        ] if exclude_paths else None
        self.weak = weak

    async def dispatch(self, request: Request, call_next):
        ...
