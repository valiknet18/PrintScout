from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tg_user_id: int
    tg_username: str | None
    first_name: str | None


class PrinterIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: str = Field(pattern="^(fdm|resin)$")
    build_x_mm: float = Field(gt=0, le=2000)
    build_y_mm: float = Field(gt=0, le=2000)
    build_z_mm: float = Field(gt=0, le=2000)
    nozzle_mm: float | None = Field(default=None, gt=0, le=2)
    materials: list[str] = Field(default_factory=list)


class PrinterOut(PrinterIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
