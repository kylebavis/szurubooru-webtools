from pathlib import Path
from typing import Optional

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    szuru_base: Optional[AnyHttpUrl] = None
    szuru_user: str = ""
    szuru_password: str = ""
    szuru_token: str = ""
    auth_mode: str = "auto"  # basic|token|auto
    download_dir: Path = Path("/tmp/szuru-downloads")

    model_config = {
        "env_prefix": "SZURU_",
        "case_sensitive": False
    }

settings = Settings()
