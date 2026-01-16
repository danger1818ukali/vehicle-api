import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()

# -------- CORS FIX (ALLOW ALL) --------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

META = {
    "API_Developer": "@AyushIsInvalid",
    "Code_Developer": "@AV_AYUSH",
    "Data_Founder": "@GURUOP7572"
}

def extract(vehicle_no: str):
    v = vehicle_no.upper().replace(" ", "").replace("-", "")
    r = requests.get(
        f"https://vahanx.in/rc-search/{v}",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10
    )
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    if "Vehicle Not Found" in soup.text:
        return None

    data = {"registration_no": v, "sections": {}}

    def grab(box, name):
        out = {}
        for c in box.find_all(["div", "li"]):
            k = c.find("span")
            v = c.find("p")
            if k and v:
                out[k.text.strip().strip(":")] = v.text.strip()
        if out:
            data["sections"][name] = out

    for d in soup.find_all("div", class_="hrc-details-card"):
        h = d.find("h3")
        if h:
            grab(d, h.text.strip())

    blur = soup.find("div", class_="rc-blur-content")
    if blur:
        grab(blur, "Other Information")

    return data


def normalize(raw):
    s = raw["sections"]
    g = lambda a, b: s.get(a, {}).get(b)

    return {
        "meta": {
            "registration_no": raw["registration_no"],
            "source": "vahanx.in",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            **META
        },
        "general_details": {
            "model_name": g("General Details", "Modal Name"),
            "owner_name": g("General Details", "Owner Name"),
            "rto_code": g("General Details", "Code"),
            "rto_city": g("General Details", "City Name"),
            "rto_contact": {
                "phone": g("General Details", "Phone"),
                "website": g("General Details", "Website"),
                "address": g("General Details", "Address")
            }
        },
        "ownership_details": {
            "owner_name": g("Ownership Details", "Owner Name"),
            "father_name": g("Ownership Details", "Father's Name"),
            "owner_serial": g("Ownership Details", "Owner Serial No"),
            "registration_number": g("Ownership Details", "Registration Number"),
            "registered_rto": g("Ownership Details", "Registered RTO")
        },
        "vehicle_details": {
            "manufacturer": g("Vehicle Details", "Model Name"),
            "model": g("Vehicle Details", "Maker Model"),
            "vehicle_class": g("Vehicle Details", "Vehicle Class"),
            "fuel": {
                "type": g("Vehicle Details", "Fuel Type"),
                "norms": g("Vehicle Details", "Fuel Norms")
            },
            "identifiers": {
                "chassis_no": g("Vehicle Details", "Chassis Number"),
                "engine_no": g("Vehicle Details", "Engine Number")
            }
        },
        "insurance": {
            "company": g("Insurance Information", "Insurance Company"),
            "policy_no": g("Insurance Information", "Insurance No"),
            "expiry_date": g("Insurance Information", "Insurance Expiry")
        },
        "important_dates": {
            "registration_date": g("Important Dates & Validity", "Registration Date"),
            "vehicle_age": g("Important Dates & Validity", "Vehicle Age"),
            "fitness_upto": g("Important Dates & Validity", "Fitness Upto"),
            "tax_upto": g("Important Dates & Validity", "Tax Upto"),
            "puc": {
                "upto": g("Important Dates & Validity", "PUC Upto"),
                "status": g("Important Dates & Validity", "PUC Expiry In")
            },
            "insurance": {
                "upto": g("Important Dates & Validity", "Insurance Upto"),
                "remaining": g("Important Dates & Validity", "Insurance Expiry In")
            }
        },
        "other_information": {
            "financer_name": g("Other Information", "Financer Name"),
            "cubic_capacity_cc": g("Other Information", "Cubic Capacity"),
            "seating_capacity": g("Other Information", "Seating Capacity"),
            "permit_type": g("Other Information", "Permit Type"),
            "blacklist_status": g("Other Information", "Blacklist Status"),
            "noc_details": g("Other Information", "NOC Details")
        }
    }


@app.get("/vehicle")
def vehicle(vehicle_no: str):
    raw = extract(vehicle_no)
    if not raw:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return normalize(raw)
