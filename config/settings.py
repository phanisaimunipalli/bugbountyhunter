from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    agentfield_api_key: str = "mock"
    bright_data_api_key: str = "mock"
    bright_data_host: str = "brd.superproxy.io"
    bright_data_port: int = 22225
    actionbook_api_key: str = "mock"
    qwen_api_key: str = "mock"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    zai_api_key: str = "mock"
    zai_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    qoder_api_key: str = "mock"
    qoder_base_url: str = "https://api.qoder.ai/v1"
    tokenrouter_api_key: str = "mock"
    tokenrouter_base_url: str = "https://api.tokenrouter.com/v1"
    evermind_api_key: str = "mock"
    evermind_base_url: str = "https://api.evermind.ai/v1"
    nosana_api_key: str = "mock"
    nosana_base_url: str = "https://api.nosana.io/v1"
    github_token: str = "mock"
    github_username: str = "mock"
    zeabur_api_key: Optional[str] = None
    zeabur_project_id: Optional[str] = None
    butterbase_api_key: Optional[str] = None
    butterbase_base_url: str = "https://api.butterbase.ai/v1"
    mock_mode: bool = False
    log_level: str = "INFO"
    port: int = 8080
    terminal_url: str = "https://bounty-hunter.zeabur.app"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
