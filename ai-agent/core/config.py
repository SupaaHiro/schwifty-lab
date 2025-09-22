from pathlib import Path
from pydantic import BaseModel, Field


class Config(BaseModel):
    model: str = Field(..., min_length=1,
                       description="Model name, must be a non-empty string")
    embedding_name: str = Field(..., min_length=1,
                                description="Embedding name, must be a non-empty string")
    docs_path: Path = Field(...,
                            description="Path to the documentation directory")
    docs_glob: str = Field(default="**/*.md", min_length=1,
                           description="Glob pattern for documentation files")
    db_path: Path = Field(..., description="Path to the database file")
    collection_name: str = Field(..., min_length=1,
                                 description="Collection name, must be a non-empty string")

    @staticmethod
    def load_from_file(file_path: str) -> "Config":
        import json
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Config(**data)
