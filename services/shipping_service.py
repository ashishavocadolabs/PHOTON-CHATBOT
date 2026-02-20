import requests
import json
from services.auth_service import get_headers, login

BASE_URL = "https://api.shipphoton.com"

DEBUG = True  # urn OFF in production


#debug logging utility
def debug_log(title, data=None):
    if DEBUG:
        print(f"\n========== {title} ==========")
        if data is not None:
            try:
                print(json.dumps(data, indent=2))
            except:
                print(data)
        print("================================\n")


#automatically handle token expiration and network errors
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
        return {
            "error": f"Network error: {str(e)}"
        }


#pincode details lookup
def get_pincode_details(pincode):

    url = f"{BASE_URL}/api/Common/GetPincodeDetails"

    params = {
        "pincode": str(pincode),
        "country": "IN"
    }

    response = safe_request("GET", url, params=params, headers=get_headers())

    if isinstance(response, dict):
        return None

    if response.status_code != 200:
        return None

    try:
        json_data = response.json()
        data = json_data.get("data", {})

# HANDLE STRING RESPONSE
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


# get shipping quote
def get_quote(from_pincode, to_pincode, weight, length, width, height):

    try:
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
            return {
                "statusCode": 500,
                "error": response["error"]
            }

        if response.status_code != 200:
            return {
                "statusCode": response.status_code,
                "error": response.text
            }

        quote_data = response.json()
        quote_data["from_details"] = from_details
        quote_data["to_details"] = to_details

        return quote_data

    except Exception as e:
        debug_log("QUOTE ERROR", str(e))
        return {
            "statusCode": 500,
            "error": f"Quote processing error: {str(e)}"
        }

def get_all_warehouses():
    try:
        url = f"{BASE_URL}/api/Common/AddressList"

        params = {
            "AddressType": "ShipFrom"
        }

        response = safe_request("GET", url, params=params, headers=get_headers())

        if isinstance(response, dict):
            return []

        if response.status_code != 200:
            return []

        data = response.json().get("data", [])

        # Only active warehouses
        active = [w for w in data if w.get("isActive")]

        debug_log("ALL ACTIVE WAREHOUSES", active)

        return active

    except Exception as e:
        debug_log("WAREHOUSE ERROR", str(e))
        return []


# get default warehouse (ship from address)
def get_default_warehouse():
    try:
        url = f"{BASE_URL}/api/Common/AddressList"

        params = {
            "AddressType": "ShipFrom"  #  REQUIRED
        }

        response = safe_request("GET", url, params=params, headers=get_headers())

        if isinstance(response, dict):
            return None

        if response.status_code != 200:
            return None

        data = response.json().get("data", [])

        debug_log("WAREHOUSE LIST", data)

        if not data:
            debug_log("NO WAREHOUSE FOUND")

        for address in data:
            if address.get("priority") or address.get("isDefault"):
                debug_log("SELECTED WAREHOUSE", address)
                return address

        selected = data[0] if data else None

        debug_log("FALLBACK WAREHOUSE", selected)

        return selected

    except Exception as e:
        debug_log("WAREHOUSE ERROR", str(e))
        return None


# create shipment
def create_shipment(state):

    warehouse = state.get("warehouse")
    if state.get("to_pincode") == warehouse.get("postalCode"):
        return {
            "statusCode": 400,
            "error": "Ship From and Ship To pincode cannot be same."
        }


    if not warehouse:
        return {"statusCode": 400, "error": "Warehouse not selected."}

    to_details = get_pincode_details(state.get("to_pincode"))
    if not to_details:
        return {"statusCode": 400, "error": "Invalid destination pincode."}

    url = f"{BASE_URL}/api/Shipping/QuickShip"

    try:
        noOfBoxes = int(state.get("noOfBoxes"))
        quantity = int(state.get("quantity"))
        invoice_amount = float(state.get("invoice_amount"))
        weight = float(state.get("weight"))
        length = float(state.get("length"))
        width = float(state.get("width"))
        height = float(state.get("height"))
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
        "shipToAddress": state.get("address_line1"),
        "shipToPincode": state.get("to_pincode"),
        "shipToCity": to_details.get("city"),
        "shipToState": to_details.get("state"),
        "shipToCountry": "IN",
        "noOfBoxes": noOfBoxes,
        "weight": weight,
        "length": length,
        "width": width,
        "height": height,
        "weightUom": "KG",
        "lengthUom": "CM"
    }

    final_payload = {"obj": payload}   #  IMPORTANT FIX

    debug_log("QUICKSHIP PAYLOAD", final_payload)

    response = safe_request("POST", url, json=final_payload, headers=get_headers())

    if response.status_code != 200:
        return {"statusCode": response.status_code, "error": response.text}

    return response.json()


# track shipment
def get_tracking(tracking_number):

    try:
        url = f"{BASE_URL}/api/Shipping/GetTracking"
        params = {"trackingNumber": tracking_number}

        response = safe_request("GET", url, params=params, headers=get_headers())

        if isinstance(response, dict):
            return {
                "statusCode": 500,
                "error": response["error"]
            }

        if response.status_code != 200:
            return {
                "statusCode": response.status_code,
                "error": response.text
            }

        return response.json()

    except Exception as e:
        debug_log("TRACKING ERROR", str(e))
        return {
            "statusCode": 500,
            "error": f"Tracking error: {str(e)}"
        }
