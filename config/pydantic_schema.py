from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ContainerNameEnum(str, Enum):
    """Типы контейнеров"""
    dc = "DC"  # Dry Container
    nc = "HC"  # "High Cubes"
    ot = "OT"  # "Open Top"
    pw = "PW"  # "Pallet Wide"
    dd = "DD"  # "Double Doors"
    gp = "GP"  # " General Purpose"
    tk = "TK"
    tc = "TC"
    dv = "DV"
    rf = "RF"
    fh = "RH"
    vgp = "VGP"
    ft = "FT"
    hq = "HQ"
    h = "H"
    bulk = "Bulk"


class ContainersSchema(BaseModel):
    """Извлечение информации о контейнерах."""
    container: str = Field(description=(
        "Unique container number following ISO 6346 format. "
        "It consists of 4 letters (owner code + 'U') followed by 7 digits (e.g., 'MSKU1234567'). "
        "Ensure it is strictly in the format '[A-Z]{3}U\\s?\\d{7}'. "
        "Container numbers often appear in sections labeled 'Container No.', 'CNTR NO.', 'Container Number', or within 'Marks & Nos.'. "
        "In cases where the container number appears in a structured format such as 'SIZE/CONTAINER/SEAL/OTHER_DATA', extract only the container number."
    ))
    container_goods: str = Field(description=(
        "Detailed description of the goods inside the container. "
        "This information is commonly found under sections labeled 'Description of Goods', 'Cargo Description', or 'Goods'. "
        "**Include only relevant details such as product names, material types, and packaging information.** "
        "**Exclude any unrelated information**, such as container type, container size, contact details (e.g., email, phone number), tax identification numbers (e.g., INN), or addresses. "
        "If multiple products are listed, return all relevant items."
    ))
    seals: list[str] = Field(description=(
        "Seal numbers (SEALS) used to secure the container. "
        "They are typically alphanumeric (e.g., 'ML-CN8621330', 'ALPHA123456') or numeric (e.g., '987654321'). "
        "Commonly found in columns labeled 'Seal No.', 'Seal #', 'Security Seal', or 'Seals'. "
        "Seal numbers are always linked to a specific container and often listed next to the container number. "
        "Seals may also be embedded in a structured format such as 'SIZE_TYPE/CONTAINER/SEAL/OTHER_DATA' (e.g., '40HC/VSTU9002514/NSPL0808'). "
        "In such cases, extract only the seal number(s) and exclude container number, size, and other values like weights or product references. "
        "If multiple seals exist, return all of them in the order they appear."
    ))
    size: int | None = Field(description=(
        "Container size in feet, typically 20, 40, or 45. "
        "If found in a structured format like 'SIZE_TYPE/CONTAINER/SEAL/OTHER_DATA', extract only the numerical size value."
    ))
    type: ContainerNameEnum = Field(description=(
        "Standardized container type code (e.g., 'DC' for Dry Container, 'HC' for High Cube). "
        "If found in a structured format such as 'SIZE_TYPE/CONTAINER/SEAL/OTHER_DATA', extract only the container type. "
        "If not found, return an empty string ('')"
    ))
    gross_weight: float | None = Field(description=(
        "Total weight of the container including goods, in kilograms (kg). "
        "Often labeled as 'Gross Weight', 'GW', 'Weight', or 'WT'. "
        "Ensure the unit is in kilograms and convert if necessary. "
        "If only a single Gross Weight value is provided and there are multiple containers listed in the document, divide the Gross Weight equally among the number of containers."
    ))
    tare_weight: float | None = Field(description=(
        "Tare weight of the container (weight of the empty container) in kilograms (kg). "
        "Labeled as 'Tare Weight' or 'Tare'. Found near gross weight in the document."
    ))
    measurement: float | None = Field(description=(
        "Total cargo volume inside the container, measured in cubic meters (CBM). "
        "Often labeled as 'Measurement', 'CBM', or 'Volume'. Ensure unit is in cubic meters."
    ))


class BaseCompanySchema(BaseModel):
    """
    Базовая схема для извлечения информации о компаниях.
    Используется для 'Shipper', 'Consignee', 'Notify Party'.
    Содержит название компании и страну регистрации.
    """
    company_name: str = Field(description=(
        "Full legal name of the company. "
        # "Typically found under sections labeled 'Shipper', 'Exporter', 'Consignee', 'Receiver', or 'Notify Party'. "
        "Extract the complete and accurate name."
    ))
    country: str = Field(description=(
        "Country where the company is registered. "
        "Extract only the country name, ignoring full addresses."
    ))


class CompanyWithNumbersSchema(BaseCompanySchema):
    """
    Расширенная схема для получения дополнительной инфоримации о компаниях (ИНН, КПП).
    Используется для 'Consignee' и 'Notify Party'.
    """
    inn: int | None = Field(description=(
        "Taxpayer Identification Number (ИНН) of the company, if available. "
        "Extract strictly as a 10- or 12-digit numeric value. "
        "Make sure the number is associated with the company name in the context."
    ))
    kpp: int | None = Field(description=(
        "Tax Registration Reason Code (КПП) of the company, if available. "
        "Extract strictly as a 9-digit numeric value. "
        "Make sure the number is associated with the company name in the context."
    ))
    # TODO: доработать промпт, inn consignee попадает в inn notify


class PydanticSchema(BaseModel):
    """
    Основная схема для извлечения необходимой информации из Bill of Lading.
    """
    model_config = ConfigDict(extra="forbid")  # Запрещает дополнительные поля

    bill_of_lading: str = Field(description=(
        "Unique Bill of Lading (B/L) number assigned to the shipment. "
        "Typically found under 'Bill of Lading No.', 'B/L No.', or similar labels."
    ))
    shipper: BaseCompanySchema = Field(description=(
        "Information about the shipper (exporter), responsible for sending the cargo. "
        "Commonly found under 'Shipper', 'Exporter', or 'Consignor'."
    ))
    consignee: CompanyWithNumbersSchema = Field(description=(
        "Information about the consignee (importer or receiver of goods). "
        "Commonly found under 'Consignee' or 'Receiver'. "
        "Includes company name, country, and tax identification numbers (ИНН/КПП)."
    ))
    notify: CompanyWithNumbersSchema = Field(description=(
        "Information about the Notify Party (the entity that should be informed upon cargo arrival). "
        "Commonly found under 'Notify Party'. "
        "Includes company name, country, and tax identification numbers (ИНН/КПП)."
    ))
    vessel: str = Field(description=(
        "Name of the ocean vessel carrying the shipment. "
        "Commonly found under 'Vessel', 'Vessel Name', or 'Carrier Vessel'."
    ))
    voyage: str = Field(description=(
        "Voyage number assigned to the vessel for this shipment. "
        "Common labels include 'Voyage No.', 'Voy. No.', 'V#', or 'Voyage'."
    ))
    port_of_loading: str = Field(description="Port where the cargo is loaded onto the vessel")
    port_of_discharge: str = Field(description="Port where the cargo is discharged from the vessel.")
    containers: list[ContainersSchema]
