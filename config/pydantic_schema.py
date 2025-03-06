from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class ContainerNameEnum(str, Enum):
    dc = "DC" # Dry Container
    nc = "HC" # "High Cubes"
    ot = "OT" # "Open Top"
    pw = "PW" # "Pallet Wide"
    dd = "DD" # "Double Doors"
    gp = "GP" # " General Purpose"
    tk = "TK"
    tc = "TC"
    dv = "DV"
    rf = "RF"
    fh = "RH"
    vgp = "VGP"
    ft = "FT"
    h = "H"
    bulk = "Bulk"

    # @classmethod
    # def from_full_name(cls, name: str) -> "ContainerNameEnum | None":
    #     mapping = {
    #         "Dry Container": cls.dc,
    #         "High Cubes": cls.nc,
    #         "Open Top": cls.ot,
    #         "Pallet Wide": cls.pw,
    #         "Double Doors": cls.dd,
    #         "General Purpose": cls.gp,
    #     }
    #     return mapping.get(name, None) or cls.__members__.get(name.lower())


class ContainersSchema(BaseModel):
    container: str = Field(description="Container number in format 'XXXU1234567' (ISO 6346). Return necessarily in format '[A-Z]{3}U\d{7}'")
    container_goods: str | None = Field(description="name (description) of goods")
    seals: list[str] = Field(description="Seal numbers. Can be located separately or as part of '<container>/<type>/<SEALS>'")
    size: int = Field(description="Container size (' or ft)")
    type: ContainerNameEnum = Field(description="Container type abbreviation")
    gross_weight: float | None = Field(description="Gross weight / GW / WT (kg)")
    tara_weight: float | None = Field(description="Tare weight (kg))")
    total_weight: float | None = Field(description="Total weight (kg)")
    measurement: float | None = Field(description="Measurement (CBM)")


class PydanticSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Запрещает дополнительные поля

    bill_of_lading: str = Field(description="Bill of lading number")
    shipper: str | None = Field(description="Shipper company name with address")
    consignee: str | None = Field(description="Consignee Company name with address")
    notify: str | None = Field(description="Notify party name with address")
    vessel: str | None = Field(description="Ocean vessel and Voyage number (Voy. No)")
    port_of_loading: str | None = Field(description="Port of loading")
    port_of_discharge: str | None = Field(description="Port of discharge")
    containers: list[ContainersSchema]