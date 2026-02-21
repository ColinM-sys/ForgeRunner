from pydantic import BaseModel


class BucketResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    is_system: bool
    color: str
    example_count: int = 0

    model_config = {"from_attributes": True}


class BucketCreate(BaseModel):
    name: str
    display_name: str
    description: str = ""
    color: str = "#6B7280"
    detection_rules: dict = {}
