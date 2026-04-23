import asyncio
from dataclasses import dataclass
import httpx
from fastapi import HTTPException

GENDERIZE_URL = "https://api.genderize.io"
AGIFY_URL = "https://api.agify.io"
NATIONALIZE_URL = "https://api.nationalize.io"

COUNTRY_NAME_MAP = {
    "NG": "Nigeria", "GH": "Ghana", "KE": "Kenya",
    "ZA": "South Africa", "EG": "Egypt", "ET": "Ethiopia",
    "TZ": "Tanzania", "UG": "Uganda", "SN": "Senegal",
    "CM": "Cameroon", "CI": "Côte d'Ivoire", "AO": "Angola",
    "MZ": "Mozambique", "MG": "Madagascar", "BJ": "Benin",
    "BF": "Burkina Faso", "ML": "Mali", "MW": "Malawi",
    "ZM": "Zambia", "ZW": "Zimbabwe", "TG": "Togo",
    "SL": "Sierra Leone", "LR": "Liberia", "GN": "Guinea",
    "RW": "Rwanda", "SO": "Somalia", "TD": "Chad",
    "NE": "Niger", "SD": "Sudan", "SS": "South Sudan",
    "US": "United States", "GB": "United Kingdom",
    "FR": "France", "DE": "Germany", "IN": "India",
    "CN": "China", "BR": "Brazil", "CA": "Canada",
    "AU": "Australia", "PK": "Pakistan", "BD": "Bangladesh",
    "PH": "Philippines", "ID": "Indonesia", "MX": "Mexico",
    "TR": "Turkey", "IR": "Iran", "TH": "Thailand",
    "MM": "Myanmar", "VN": "Vietnam", "CD": "DR Congo",
    "MA": "Morocco", "DZ": "Algeria", "TN": "Tunisia",
    "LY": "Libya", "GR": "Greece", "PL": "Poland",
    "UA": "Ukraine", "RO": "Romania", "NL": "Netherlands",
    "BE": "Belgium", "SE": "Sweden", "NO": "Norway",
    "DK": "Denmark", "FI": "Finland", "PT": "Portugal",
    "CZ": "Czech Republic", "HU": "Hungary", "AT": "Austria",
    "CH": "Switzerland", "ES": "Spain", "IT": "Italy",
    "AR": "Argentina", "CO": "Colombia", "CL": "Chile",
    "PE": "Peru", "VE": "Venezuela", "EC": "Ecuador",
    "BO": "Bolivia", "PY": "Paraguay", "UY": "Uruguay",
    "CR": "Costa Rica", "GT": "Guatemala", "HN": "Honduras",
    "NI": "Nicaragua", "SV": "El Salvador", "PA": "Panama",
    "CU": "Cuba", "DO": "Dominican Republic", "HT": "Haiti",
    "JM": "Jamaica", "TT": "Trinidad and Tobago",
    "RU": "Russia", "JP": "Japan", "KR": "South Korea",
    "SA": "Saudi Arabia", "AE": "United Arab Emirates",
    "IQ": "Iraq", "SY": "Syria", "JO": "Jordan",
    "LB": "Lebanon", "IL": "Israel", "YE": "Yemen",
    "OM": "Oman", "KW": "Kuwait", "QA": "Qatar",
    "BH": "Bahrain", "AF": "Afghanistan", "NP": "Nepal",
    "LK": "Sri Lanka", "KH": "Cambodia", "LA": "Laos",
    "MY": "Malaysia", "SG": "Singapore", "NZ": "New Zealand",
}

@dataclass
class ExternalProfileData:
    gender: str
    gender_probability: float
    sample_size: int
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float

def _classify_age_group(age: int) -> str:
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"

async def _fetch_gender(client: httpx.AsyncClient, name: str) -> dict:
    try:
        response = await client.get(GENDERIZE_URL, params={"name": name})
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail={"status": "error", "message": "Genderize returned an invalid response"})
    if not data.get("gender") or not data.get("count"):
        raise HTTPException(status_code=502, detail={"status": "error", "message": "Genderize returned an invalid response"})
    return data

async def _fetch_age(client: httpx.AsyncClient, name: str) -> dict:
    try:
        response = await client.get(AGIFY_URL, params={"name": name})
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail={"status": "error", "message": "Agify returned an invalid response"})
    if data.get("age") is None:
        raise HTTPException(status_code=502, detail={"status": "error", "message": "Agify returned an invalid response"})
    return data

async def _fetch_nationality(client: httpx.AsyncClient, name: str) -> dict:
    try:
        response = await client.get(NATIONALIZE_URL, params={"name": name})
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail={"status": "error", "message": "Nationalize returned an invalid response"})
    if not data.get("country") or len(data["country"]) == 0:
        raise HTTPException(status_code=502, detail={"status": "error", "message": "Nationalize returned an invalid response"})
    return data

async def fetch_profile_data(name: str) -> ExternalProfileData:
    async with httpx.AsyncClient(timeout=10.0) as client:
        gender_data, age_data, nationality_data = await asyncio.gather(
            _fetch_gender(client, name),
            _fetch_age(client, name),
            _fetch_nationality(client, name)
        )
    top_country = max(nationality_data["country"], key=lambda c: c["probability"])
    country_id = top_country["country_id"]
    age = age_data["age"]
    return ExternalProfileData(
        gender=gender_data["gender"],
        gender_probability=gender_data["probability"],
        sample_size=gender_data["count"],
        age=age,
        age_group=_classify_age_group(age),
        country_id=country_id,
        country_name=COUNTRY_NAME_MAP.get(country_id, country_id),
        country_probability=top_country["probability"]
    )