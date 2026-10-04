from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://verdustry:verdustry@127.0.0.1:5432/verdustry"
    jwt_secret: str = "verdustry-secret-change-me-min-32-characters!!"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM (Groq, ou tout autre fournisseur compatible OpenAI)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"

    # LLM Vision (extraction directe depuis l'image - fournisseur separe de
    # Groq, car Groq ne supporte pas fiablement les images + tool-calling
    # sur les modeles actuellement disponibles). Ex: Gemini ou OpenAI.
    llm_vision_api_key: str = ""
    llm_vision_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_vision_model: str = "gemini-3.6-flash"

    # ERP
    encryption_key: str = ""   # ← ajouté

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()