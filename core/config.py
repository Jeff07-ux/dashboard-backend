from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cable Assembly API"
    # Column Header Configuration
    COL_CABLE_NAME: str = "Cable name"
    COL_PHASE: str = "phase"
    COL_TS: str = "TS"
    COL_TO: str = "TO"
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

settings = Settings()
