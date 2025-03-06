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


class ContainersSchema(BaseModel):
    container: str = Field(description=(
        "Unique container number following ISO 6346 format. "
        "It consists of 4 letters (owner code + 'U') followed by 7 digits (e.g., 'MSKU1234567'). "
        "Ensure it is strictly in the format '[A-Z]{3}U\\s?\\d{7}'. "
        "Container numbers often appear in sections labeled 'Container No.', 'CNTR NO.', 'Container Number', or within 'Marks & Nos.'."
    ))
    container_goods: str | None = Field(description=(
        "Description of the goods inside the container. "
        "This information is often found in sections labeled 'Description of Goods', 'Cargo Description', or 'Goods'. "
        "It may include product names, material types, or HS codes (Harmonized System). "
        "If multiple products are listed, return all of them."
    ))
    seals: list[str] = Field(description=(
        "Seal numbers (SEALS) used to secure the container. "
        "They are typically alphanumeric (e.g., 'ML-CN8621330', 'ALPHA123456') or numeric (e.g., '987654321'). "
        "Commonly found in columns labeled 'Seal No.', 'Seal #', 'Security Seal', or 'Seals'. "
        "Seal numbers are always linked to a specific container and often listed next to the container number. "
        "Seals may also be embedded in a structured format such as 'CONTAINER/SIZE/SEAL' (e.g., 'VSTU9002514/40HC/NSPL0808'). "
        "In such cases, extract only the seal number(s) and exclude container number, size, and other values like weights or product references. "
        "If multiple seals exist, return all of them in the order they appear."
    ))
    size: int = Field(description="Container size in feet, typically 20, 40, or 45.")
    type: ContainerNameEnum = Field(description=(
        "Standardized container type code (e.g., 'DC' for Dry Container, 'HC' for High Cube)."
    ))
    gross_weight: float | None = Field(description=(
        "Total weight of the container including goods, in kilograms (kg). "
        "Often labeled as 'Gross Weight', 'GW', 'Weight', or 'WT'. "
        "Ensure the unit is in kilograms and convert if necessary."
    ))
    tare_weight: float | None = Field(description=(
        "Tare weight of the container (weight of the empty container) in kilograms (kg). "
        "Labeled as 'Tare Weight' or 'Tare'. Found near gross weight in the document."
    ))
    measurement: float | None = Field(description=(
        "Total cargo volume inside the container, measured in cubic meters (CBM). "
        "Often labeled as 'Measurement', 'CBM', or 'Volume'. Ensure unit is in cubic meters."
    ))


class PydanticSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Запрещает дополнительные поля

    bill_of_lading: str = Field(description="Unique Bill of Lading (B/L) number assigned to the shipment.")
    shipper: str | None = Field(description="Shipper company name with address")
    consignee: str | None = Field(description="Consignee Company name with address")
    notify: str | None = Field(description="Notify party name with address")
    vessel: str | None = Field(description=(
        "Name of the ocean vessel carrying the shipment. "
        "Commonly labeled as 'Vessel', 'Vessel Name', or 'Carrier Vessel'."
    ))
    voyage: str | None = Field(description=(
        "Voyage number assigned to the vessel for this shipment. "
        "Common labels include 'Voyage No.', 'Voy. No.', or 'Voyage'."
    ))
    port_of_loading: str | None = Field(description="Port where the cargo is loaded onto the vessel")
    port_of_discharge: str | None = Field(description="Port where the cargo is discharged from the vessel.")
    containers: list[ContainersSchema]