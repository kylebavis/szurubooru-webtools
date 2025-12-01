from pathlib import Path
from typing import Optional

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    base: Optional[AnyHttpUrl] = None
    user: str = ""
    password: str = ""
    token: str = ""
    auth_mode: str = "auto"  # basic|token|auto
    download_dir: Path = Path("/tmp/szuru-downloads")

    model_config = {
        "env_prefix": "SZURU_",
        "case_sensitive": False
    }

settings = Settings()
