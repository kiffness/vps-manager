from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Log level: DEBUG, INFO, WARNING, ERROR
    log_level: str = "INFO"

    # Base path
    base_dir: str = "/home/runner"

    api_key: str

    # SSH connection to the host VPS
    ssh_host: str = "host.docker.internal"
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_key_path: str = "/run/secrets/ssh_key"

settings = Settings()