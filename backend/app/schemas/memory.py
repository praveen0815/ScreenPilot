from pydantic import BaseModel, ConfigDict, Field

from app.memory.schemas import TaskMemoryBundle


class TaskMemoryResponse(TaskMemoryBundle):
    pass


class ClearTaskMemoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    removed_entries: int
    task_id: str


class UserPreferencesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferences: dict[str, str] = Field(default_factory=dict)


class UserPreferencesUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferences: dict[str, str] = Field(default_factory=dict, max_length=20)