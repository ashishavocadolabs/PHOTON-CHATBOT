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
    "quantity": None,
    "noOfBoxes": None,
}


#reset conversation state except quote details

def reset_state():
    for key in conversation_state:
        conversation_state[key] = None

    conversation_state["available_services"] = []
    conversation_state["available_warehouses"] = []
    conversation_state["warehouse_selection_mode"] = False


#main handler for chat messages

def handle_chat(user_message):
    try:
        user_message = user_message.strip()

        #warehouse selection flow
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

        #courier selection flow
        if (
            conversation_state["available_services"]
            and not conversation_state.get("carrierId")
            and user_message.isdigit()
        ):


            index = int(user_message)
            services = conversation_state["available_services"]

            if index < 1 or index > len(services):
                return {"response": "Invalid selection."}

            selected = services[index - 1]
            conversation_state["carrierId"] = selected.get("carrierId")
            conversation_state["serviceId"] = selected.get("serviceId")

            return {
                "response":
                "📦 Please provide shipment details step-by-step:\n\n"
                "1️⃣ Ship To Address\n"
                "2️⃣ Product Name\n"
                "3️⃣ Quantity\n"
                "4️⃣ Invoice Amount\n"
                "5️⃣ Number of Boxes"
            }

       #shipment detail collection flow
        if conversation_state.get("carrierId") and not conversation_state["warehouse_selection_mode"]:

            extract_shipment_details(user_message)

            missing = get_missing_shipment_fields()

            if missing:
                return {"response": f"Please provide: {', '.join(missing)}"}

            from services.shipping_service import get_all_warehouses

            warehouse = get_all_warehouses()

            if not warehouse:
                return {"response": "No warehouse found."}

            conversation_state["available_warehouses"] = (
                [warehouse] if isinstance(warehouse, dict) else warehouse
            )
            conversation_state["warehouse_selection_mode"] = True


            if not warehouse:
                return {"response": "No warehouse found."}

            conversation_state["available_warehouses"] = (
                [warehouse] if isinstance(warehouse, dict) else warehouse
            )

            conversation_state["warehouse_selection_mode"] = True

            options = []

            for i, w in enumerate(conversation_state["available_warehouses"], 1):
                label = f"{'Warehouse: ' + w.get('addressName')} - {w.get('city')} ({w.get('state')}, {w.get('postalCode')}), {w.get('country')} \n {'Address: ' + w.get('address1')} - {w.get('address2')} \n {'Phone: ' + w.get('phone') if w.get('phone') else ''} \n{'Email: ' + w.get('emailId') if w.get('emailId') else ''}"

                options.append({
                    "label": label,
                    "value": str(i)
                })

            return {
                "response": "🏬 Select Ship From Warehouse:",
                "options": options
            }

        #prompt engineering with strict rules for quote and tracking

        SYSTEM_PROMPT = """
First you start Gretting!.......
you are Photon AI Assistant and when ask who developed then give answer developed by AvocadoLabs Pvt Ltd.

STRICT RULES:
- Only help with shipping quotes and tracking.
- Never guess or fabricate values.
- Never generate default weight or dimensions.
- Never invent pincodes.
- Do NOT call any function unless ALL required fields are provided.

========================
FOR SHIPPING QUOTE
========================
Collect:

1. from_pincode (6 digit Indian pincode as STRING)
2. to_pincode (6 digit Indian pincode as STRING)
3. weight (number in KG)
4. length (number in CM)
5. width (number in CM)
6. height (number in CM)

# From: Must be highlighted that pincodes should be 6 digit and sent as STRING.
# To: Must be highlighted that pincodes should be 6 digit and sent as STRING.
# Weight and Dimensions: Must be highlighted that these should not be guessed or auto-filled.
# Available options text line should be highlighted with emojis and formatting for better UX.


# Strict:
# Carrier Name Should be also highlighted with bullet points and better UX.
# INR symbol should be highlighted for price.
# Arrival date and transit days should also be highlighted.

# Warehouse Details should be highlighted with the address name and complete address with phone and email if available.

Rules:
- Pincodes must be exactly 6 digits.
- Always send pincodes as STRING.
- If ANY field is missing → ask for that field.
- Do NOT send null.
- Do NOT auto-fill values.

========================
FOR TRACKING
========================
Require:
- tracking_number (string)

If missing → ask for tracking number.
Do not guess tracking numbers.

If user says:
"help" or "quotation"
→ Ask:
"Please provide from pincode, to pincode, weight (kg) and dimensions (L x W x H in cm)."
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_quote",
                        "description": "Get shipping quote when all required fields are available.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "from_pincode": {"type": "string"},
                                "to_pincode": {"type": "string"},
                                "weight": {"type": "number"},
                                "length": {"type": "number"},
                                "width": {"type": "number"},
                                "height": {"type": "number"}
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_tracking",
                        "description": "Track shipment using tracking number.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "tracking_number": {"type": "string"}
                            }
                        }
                    }
                }
            ],
            tool_choice="auto"
        )

        message = response.choices[0].message

        #tool calls handling

        if message.tool_calls:

            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if function_name == "get_quote":

                required_fields = ["from_pincode", "to_pincode", "weight", "length", "width", "height"]

                for field in required_fields:
                    if field not in args or args[field] in [None, "", 0]:
                        return {"response": f"Please provide {field.replace('_',' ')}."}

                # strict pincode validation
                if not re.match(r"^\d{6}$", str(args["from_pincode"])):
                    return {"response": "Invalid from pincode. It must be 6 digits."}

                if not re.match(r"^\d{6}$", str(args["to_pincode"])):
                    return {"response": "Invalid to pincode. It must be 6 digits."}

                conversation_state.update(args)

                result = get_quote(
                    str(args["from_pincode"]),
                    str(args["to_pincode"]),
                    float(args["weight"]),
                    float(args["length"]),
                    float(args["width"]),
                    float(args["height"])
                )

                return format_quote(result)

            elif function_name == "get_tracking":

                tracking_number = args.get("tracking_number")

                if not tracking_number:
                    return {"response": "Please provide tracking number."}

                result = get_tracking(tracking_number)
                return format_tracking(result)

        return {"response": message.content}

    except Exception as e:
        return {"response": f"System error: {str(e)}"}


#shipment details extraction and validation

def get_missing_shipment_fields():
    required = [
        "address_line1",
        "product",
        "quantity",
        "invoice_amount",
        "noOfBoxes"
    ]
    return [f.replace("_", " ") for f in required if not conversation_state.get(f)]


def extract_shipment_details(message):

    if not conversation_state["address_line1"]:
        conversation_state["address_line1"] = message.strip()
        return

    if not conversation_state["product"]:
        conversation_state["product"] = message.strip()
        return

    if not conversation_state["quantity"]:
        conversation_state["quantity"] = re.sub(r"\D", "", message)
        return

    if not conversation_state["invoice_amount"]:
        conversation_state["invoice_amount"] = re.sub(r"[^\d.]", "", message)
        return

    if not conversation_state["noOfBoxes"]:
        conversation_state["noOfBoxes"] = re.sub(r"\D", "", message)
        return


#formatter functions for quote, shipment and tracking results

def format_quote(result):

    if result.get("statusCode") != 200:
        return {"response": f"Quote Error: {result.get('error')}"}

    services = result.get("data", {}).get("servicesOnDate", [])

    if not services:
        return {"response": "No courier services available."}

    conversation_state["available_services"] = services

    msg = (
        f"📍 From: {result['from_details']['city']} ({result['from_details']['state']}), {result['from_details']['country']}\n"
        f"📍 To: {result['to_details']['city']} ({result['to_details']['state']}), {result['to_details']['country']}\n\n"
        f"⚖️ Weight: {conversation_state['weight']} kg\n"
        f"📏 Dimensions: {conversation_state['length']} x "
        f"{conversation_state['width']} x {conversation_state['height']} cm\n\n"
        "📦 Available Shipping Options:\n\n"
    )

    options = []

    for i, s in enumerate(services, 1):
        label = f"{s.get('carrierCode')} - {s.get('serviceDescription')} \nINR {s.get('totalCharges')} \n{s.get('arrivalDate')} ({s.get('businessDaysInTransit')} days)"
        options.append({
            "label": label,
            "value": str(i)
        })

    return {
        "response": msg,
        "options": options
    }


def format_shipment(result):

    if result.get("statusCode") != 200:
        return {
            "response": result.get("message") or result.get("error") or "Shipment failed."
        }


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
