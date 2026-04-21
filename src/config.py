from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jules_api_key: str = ""
    github_token: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    default_repo_owner: str = ""
    default_repo_name: str = ""
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def load_settings() -> Settings:
    return Settings()
