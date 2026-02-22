import requests
import json
from services.auth_service import get_headers, login, get_logged_user_id

BASE_URL = "https://api.shipphoton.com"
DEBUG = True  # Turn OFF in production

#debug logger
def debug_log(title, data=None):
    if DEBUG:
        print(f"\n========== {title} ==========")
        if data is not None:
            try:
                print(json.dumps(data, indent=2))
            except:
                print(data)
        print("================================\n")


#safe request with auto token refresh
def safe_request(method, url, **kwargs):
    try:
        debug_log("API REQUEST", {
            "method": method,
            "url": url,
            "payload": kwargs.get("json"),
            "params": kwargs.get("params")
        })

        response = requests.request(method, url, timeout=30, **kwargs)

        if response.status_code == 401:
            debug_log("TOKEN EXPIRED - REFRESHING")
            login()
            response = requests.request(method, url, timeout=30, **kwargs)

        debug_log("API RESPONSE STATUS", response.status_code)

        try:
            debug_log("API RESPONSE BODY", response.json())
        except:
            debug_log("API RESPONSE TEXT", response.text)

        return response

    except requests.exceptions.RequestException as e:
        debug_log("NETWORK ERROR", str(e))
        return {"error": f"Network error: {str(e)}"}


#get pincode details
def get_pincode_details(pincode):
    url = f"{BASE_URL}/api/Common/GetPincodeDetails"
    params = {"pincode": str(pincode), "country": "IN"}

    response = safe_request("GET", url, params=params, headers=get_headers())

    if isinstance(response, dict) or response.status_code != 200:
        return None

    try:
        json_data = response.json()
        data = json_data.get("data", {})

        if isinstance(data, str):
            data = json.loads(data)

        result = {
            "city": data.get("cityName"),
            "state": data.get("stateCode"),
            "country": "IN"
        }

        debug_log("PINCODE DETAILS RESULT", result)
        return result

    except Exception as e:
        debug_log("PINCODE PARSE ERROR", str(e))
        return None


#get quote API
def get_quote(from_pincode, to_pincode, weight, length, width, height):

    from_details = get_pincode_details(from_pincode)
    to_details = get_pincode_details(to_pincode)

    if not from_details or not to_details:
        return {
            "statusCode": 400,
            "error": "Invalid pincode or not serviceable."
        }

    url = f"{BASE_URL}/api/Shipping/GetQuote"

    payload = {
        "shipFromPinCode": str(from_pincode),
        "shipFromCity": from_details["city"],
        "shipFromState": from_details["state"],
        "shipFromCountry": "IN",
        "shipToPincode": str(to_pincode),
        "shipToCity": to_details["city"],
        "shipToState": to_details["state"],
        "shipToCountry": "IN",
        "length": str(length),
        "width": str(width),
        "height": str(height),
        "lengthUom": "CM",
        "weight": str(weight),
        "weightUom": "KG",
    }

    response = safe_request("POST", url, json=payload, headers=get_headers())

    if isinstance(response, dict):
        return {"statusCode": 500, "error": response["error"]}

    if response.status_code != 200:
        return {"statusCode": response.status_code, "error": response.text}

    quote_data = response.json()
    quote_data["from_details"] = from_details
    quote_data["to_details"] = to_details

    return quote_data


#GET ALL ACTIVE SHIPFROM WAREHOUSES
def get_all_warehouses():
    url = f"{BASE_URL}/api/Common/AddressList"
    params = {"AddressType": "ShipFrom"}

    response = safe_request("GET", url, params=params, headers=get_headers())

    if isinstance(response, dict) or response.status_code != 200:
        return []

    data = response.json().get("data", [])

    active = [
        w for w in data
        if w.get("isActive")
        and str(w.get("addressType", "")).lower() == "shipfrom"
    ]

    debug_log("ALL ACTIVE WAREHOUSES", active)
    return active


#GET ALL ACTIVE SHIPTO ADDRESSES FOR LOGGED IN USER
def get_all_shipto_addresses():
    url = f"{BASE_URL}/api/Common/AddressList"
    params = {"AddressType": "ShipTo"}

    response = safe_request("GET", url, params=params, headers=get_headers())

    if isinstance(response, dict) or response.status_code != 200:
        return []

    data = response.json().get("data", [])
    user_id = get_logged_user_id()

    active = [
        a for a in data
        if a.get("isActive")
        and str(a.get("addressType", "")).lower() == "shipto"
        and a.get("createdBy") == user_id
    ]

    debug_log("USER SHIPTO ADDRESSES", active)
    return active


#default warehouse selection logic
def get_default_warehouse():
    warehouses = get_all_warehouses()

    if not warehouses:
        return None

    for w in warehouses:
        if w.get("priority") or w.get("isDefault"):
            return w

    return warehouses[0]


#create shipment
def create_shipment(state):

    warehouse = state.get("warehouse")
    shipto = state.get("shipto")

    if not warehouse:
        return {"statusCode": 400, "error": "Warehouse not selected."}

    if not shipto:
        return {"statusCode": 400, "error": "Ship To address not selected."}

    if warehouse.get("postalCode") == shipto.get("postalCode"):
        return {
            "statusCode": 400,
            "error": "Ship From and Ship To pincode cannot be same."
        }

    url = f"{BASE_URL}/api/Shipping/QuickShip"

    try:
        quantity = int(state.get("quantity"))
        invoice_amount = float(state.get("invoice_amount"))
        weight = float(state.get("weight"))
        length = float(state.get("length"))
        width = float(state.get("width"))
        height = float(state.get("height"))
        noOfBoxes = int(state.get("noOfBoxes") or 1)
    except Exception:
        return {"statusCode": 400, "error": "Invalid numeric values."}

    payload = {
        "product": state.get("product"),
        "carrierId": state.get("carrierId"),
        "serviceId": state.get("serviceId"),
        "quantity": quantity,
        "invoiceAmount": invoice_amount,

        "shipFromAddressName": warehouse.get("addressName"),
        "organization": warehouse.get("name"),
        "shipFromPincode": warehouse.get("postalCode"),

        "shipToName": shipto.get("name"),
        "shipToPhone": shipto.get("phone"),
        "shipToEmail": shipto.get("emailId"),
        "shipToAddress": shipto.get("address1"),
        "shipToPincode": shipto.get("postalCode"),
        "shipToCity": shipto.get("city"),
        "shipToState": shipto.get("state"),
        "shipToCountry": shipto.get("country"),

        "noOfBoxes": noOfBoxes,
        "weight": weight,
        "length": length,
        "width": width,
        "height": height,
        "weightUom": "KG",
        "lengthUom": "CM"
    }

    final_payload = {"obj": payload}

    debug_log("QUICKSHIP PAYLOAD", final_payload)

    response = safe_request("POST", url, json=final_payload, headers=get_headers())

    if isinstance(response, dict):
        return {"statusCode": 500, "error": response["error"]}

    if response.status_code != 200:
        return {"statusCode": response.status_code, "error": response.text}

    return response.json()


#Tracking API
def get_tracking(tracking_number):

    url = f"{BASE_URL}/api/Shipping/GetTracking"
    params = {"trackingNumber": tracking_number}

    response = safe_request("GET", url, params=params, headers=get_headers())

    if isinstance(response, dict):
        return {"statusCode": 500, "error": response["error"]}

    if response.status_code != 200:
        return {"statusCode": response.status_code, "error": response.text}

    return response.json()