from fastapi import FastAPI, HTTPException
import geoip2.database

app = FastAPI()

# Path to your GeoLite2-City.mmdb file
GEOIP_DB_PATH = "./GeoLite2-City.mmdb"
reader = geoip2.database.Reader(GEOIP_DB_PATH)

def get_ip_info(ip):
    response = reader.city(ip)

    result = {
                "city": response.city.name,
                "country_name": response.country.name,
                # "country_iso_code": response.country.iso_code,
                "subdivision_name": response.subdivisions.most_specific.name,
                # "subdivision_iso_code": response.subdivisions.most_specific.iso_code,
                # "postal_code": response.postal.code,
                "latitude": response.location.latitude,
                "longitude": response.location.longitude,
                # "network": str(response.traits.network),
            }
    return result

# @app.get("/")
# def read_root():
#     return {"message": "Welcome to the GeoIP service"}

@app.post("/")
@app.get("/")
def get_geoip(ip: str):
    try:
        return get_ip_info(ip)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing IP: {e}")


# Cleanup the reader when the app shuts down
@app.on_event("shutdown")
def shutdown_event():
    reader.close()