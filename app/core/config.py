from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    szuru_base: AnyHttpUrl = ""
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
