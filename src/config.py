from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/exportaciones"
    data_dir: Path = Path("../")
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    ml_models_dir: Path = Path("./ml_models")

    # ETL chunk size para archivos grandes (629K rows total las de los excel)
    etl_chunk_size: int = 10_000

    @property
    def xlsx_glob_pattern(self) -> str:
        return str(self.data_dir / "**" / "*.xlsx")


settings = Settings()
