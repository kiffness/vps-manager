from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Log level: DEBUG, INFO, WARNING, ERROR
    log_level: str = "INFO"

    # Base path
    base_dir: str = "/home/runner"

settings = Settings()