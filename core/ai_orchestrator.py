import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from services.shipping_service import (
    get_quote,
    get_tracking,
    create_shipment,
    get_default_warehouse
)

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

#global conversation state
conversation_state = {
    # Quote
    "from_pincode": None,
    "to_pincode": None,
    "weight": None,
    "length": None,
    "width": None,
    "height": None,

    # Courier selection
    "available_services": [],
    "carrierId": None,
    "serviceId": None,

    # Warehouse
    "available_warehouses": [],
    "warehouse": None,
    "warehouse_selection_mode": False,

    # Customer Details
    "customer_name": None,
    "customer_phone": None,
    "customer_email": None,
    "address_line1": None,

    # Product Details
    "product": None,
    "invoice_amount": None,
    "quantity": None
}


#reset state after shipment creation or when needed
def reset_state():
    for key in conversation_state:
        conversation_state[key] = None

    conversation_state["available_services"] = []
    conversation_state["available_warehouses"] = []
    conversation_state["warehouse_selection_mode"] = False


#main chat handler
def handle_chat(user_message):
    try:
        user_message = user_message.strip()

        # warehouse selection flow
        if conversation_state["warehouse_selection_mode"] and user_message.isdigit():

            index = int(user_message)
            warehouses = conversation_state["available_warehouses"]

            if index < 1 or index > len(warehouses):
                return {"response": "Invalid warehouse selection."}

            conversation_state["warehouse"] = warehouses[index - 1]
            conversation_state["warehouse_selection_mode"] = False

            result = create_shipment(conversation_state)
            response = format_shipment(result)

            if result.get("statusCode") == 200:
                reset_state()

            return response


        #courier service selection flow
        if conversation_state["available_services"] and user_message.isdigit():

            index = int(user_message)
            services = conversation_state["available_services"]

            if index < 1 or index > len(services):
                return {"response": "Invalid selection."}

            selected = services[index - 1]
            conversation_state["carrierId"] = selected.get("carrierId")
            conversation_state["serviceId"] = selected.get("serviceId")

            return {"response":
                    "Please provide:\n"
                    "customer name,\n"
                    "customer phone,\n"
                    "address line1,\n"
                    "product,\n"
                    "invoice amount,\n"
                    "quantity"
                    }


        #collect shipment details → show warehouses
        if conversation_state.get("carrierId") and not conversation_state["warehouse_selection_mode"]:

            extract_shipment_details(user_message)

            missing = get_missing_shipment_fields()

            if missing:
                return {"response": f"Please provide: {', '.join(missing)}"}

            # All shipment details collected → Show warehouses
            warehouse = get_default_warehouse()

            if not warehouse:
                return {"response": "No warehouse found."}

            # If API returns single warehouse
            if isinstance(warehouse, dict):
                conversation_state["available_warehouses"] = [warehouse]
            else:
                conversation_state["available_warehouses"] = warehouse

            conversation_state["warehouse_selection_mode"] = True

            msg = "🏬 Select Ship From Warehouse:\n\n"

            for i, w in enumerate(conversation_state["available_warehouses"], 1):
                msg += (
                    f"{i}. {w.get('addressName')} - "
                    f"{w.get('city')} ({w.get('state')})\n"
                )

            msg += "\nType warehouse number to confirm."

            return {"response": msg}


       # AI Orchestration with Groq
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": """
You are Photon AI Shipping Assistant.

Help only with shipping quotes and tracking.

If user asks for quote:
Collect:
- from_pincode (string)
- to_pincode (string)
- weight (number)
- length (number)
- width (number)
- height (number)

Always send pincodes as STRING.
Never send null values.
"""
                },
                {"role": "user", "content": user_message}
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_quote",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "from_pincode": {"type": "string"},
                                "to_pincode": {"type": "string"},
                                "weight": {"type": "number"},
                                "length": {"type": "number"},
                                "width": {"type": "number"},
                                "height": {"type": "number"}
                            },
                            "required": [
                                "from_pincode",
                                "to_pincode",
                                "weight",
                                "length",
                                "width",
                                "height"
                            ]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_tracking",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "tracking_number": {"type": "string"}
                            },
                            "required": ["tracking_number"]
                        }
                    }
                }
            ],
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:

            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            # Force pincode string
            if "from_pincode" in args:
                args["from_pincode"] = str(args["from_pincode"])
            if "to_pincode" in args:
                args["to_pincode"] = str(args["to_pincode"])

            if function_name == "get_quote":

                conversation_state.update(args)

                result = get_quote(
                    args["from_pincode"],
                    args["to_pincode"],
                    args["weight"],
                    args["length"],
                    args["width"],
                    args["height"]
                )

                return format_quote(result)

            elif function_name == "get_tracking":

                result = get_tracking(args["tracking_number"])
                return format_tracking(result)

        return {"response": message.content}

    except Exception as e:
        return {"response": f"System error: {str(e)}"}


#shipment details extraction
def get_missing_shipment_fields():
    required = [
        "customer_name",
        "customer_phone",
        "address_line1",
        "product",
        "invoice_amount",
        "quantity"
    ]

    missing = []
    for field in required:
        if not conversation_state.get(field):
            missing.append(field.replace("_", " "))

    return missing


def extract_shipment_details(message):

    if not conversation_state["customer_name"]:
        conversation_state["customer_name"] = message.split("is")[-1].strip()
        return

    if not conversation_state["customer_phone"]:
        conversation_state["customer_phone"] = re.sub(r"\D", "", message)
        return

    if not conversation_state["address_line1"]:
        conversation_state["address_line1"] = message
        return

    if not conversation_state["product"]:
        conversation_state["product"] = message
        return

    if not conversation_state["invoice_amount"]:
        conversation_state["invoice_amount"] = re.sub(r"[^\d.]", "", message)
        return

    if not conversation_state["quantity"]:
        conversation_state["quantity"] = re.sub(r"\D", "", message)
        return


#formatter functions
def format_quote(result):

    if result.get("statusCode") != 200:
        return {"response": f"Quote Error: {result.get('error')}"}

    services = result.get("data", {}).get("servicesOnDate", [])

    if not services:
        return {"response": "No courier services available."}

    conversation_state["available_services"] = services

    msg = (
        f"📍 From: {result['from_details']['city']} "
        f"({result['from_details']['state']})\n"
        f"📍 To: {result['to_details']['city']} "
        f"({result['to_details']['state']})\n\n"
        f"⚖️ Weight: {conversation_state['weight']} kg\n"
        f"📏 Dimensions: {conversation_state['length']} x "
        f"{conversation_state['width']} x "
        f"{conversation_state['height']} cm\n\n"
        "📦 Available Shipping Options:\n\n"
    )

    for i, s in enumerate(services, 1):
        msg += (
            f"{i}. 🚚 {s.get('carrierCode')} - "
            f"{s.get('serviceDescription')}\n"
            f"💰 ₹{s.get('totalCharges')}\n"
            f"📅 {s.get('businessDaysInTransit')} days\n"
            "----------------------------------\n"
        )

    msg += "\nPlease type the option number to book shipment."

    return {"response": msg}


def format_shipment(result):

    if result.get("statusCode") != 200:
        return {"response": result.get("error", "Shipment failed.")}

    data = result.get("data", {})

    return {
        "response":
            "✅ Shipment Created Successfully!\n\n"
            f"🚚 Courier: {data.get('carrierCode')}\n"
            f"📦 Tracking Number: {data.get('trackingNumber')}\n"
            f"🧾 AWB: {data.get('awbNumber')}"
    }


def format_tracking(result):

    if result.get("statusCode") != 200:
        return {"response": result.get("error", "Tracking failed.")}

    data = result.get("data", {})

    return {
        "response":
            "🚚 Tracking Status\n\n"
            f"Status: {data.get('currentStatus')}\n"
            f"Location: {data.get('currentLocation')}"
    }