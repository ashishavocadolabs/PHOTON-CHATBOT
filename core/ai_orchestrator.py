import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from services.auth_service import get_logged_user_name
from services.shipping_service import (
    debug_log,
    get_quote,
    get_tracking,
    create_shipment,
    get_all_shipto_addresses,
    get_default_warehouse,
    save_new_shipto_address,
    get_pincode_details,
    get_all_warehouses
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# =====================================================
# GLOBAL CONVERSATION STATE
# =====================================================

conversation_state = {}

def reset_state():
    global conversation_state
    conversation_state = {
        "flow_mode": None,  # quote / shipping / tracking

        # Quote fields
        "from_pincode": None,
        "to_pincode": None,
        "weight": None,
        "length": None,
        "width": None,
        "height": None,

        # Shipping fields
        "available_warehouses": [],
        "warehouse": None,

        "available_shipto": [],
        "shipto": None,

        "product": None,
        "quantity": None,
        "invoice_amount": None,
        "noOfBoxes": None,

        "available_services": [],
        "carrierId": None,
        "serviceId": None,
        "carrierCode": None,
        "serviceCode": None,

        "awaiting_confirmation": False,

        # New Address
        "new_address_mode": False,
        "new_name": None,
        "new_phone": None,
        "new_email": None,
        "new_address1": None,
        "new_address2": None,
        "new_postalCode": None,
        "new_city": None,
        "new_state": None,

        "language": "english"
    }

reset_state()

# =====================================================
# SAFE NUMERIC HELPERS (IMPROVED)
# =====================================================

def is_valid_pincode(pin):
    return bool(re.match(r"^\d{6}$", str(pin)))

def safe_float(value):
    try:
        return float(str(value).strip())
    except:
        return None


# =====================================================
# ADVANCED QUOTE EXTRACTION
# =====================================================

def extract_quote_fields(message):
    msg = message.lower().strip()

    # -------- PINCODES --------
    pincodes = re.findall(r"\b\d{6}\b", msg)
    if len(pincodes) >= 1 and not conversation_state["from_pincode"]:
        conversation_state["from_pincode"] = pincodes[0]

    if len(pincodes) >= 2:
        conversation_state["to_pincode"] = pincodes[1]

    # -------- WEIGHT --------
    weight_patterns = [
        r'(\d+(\.\d+)?)\s*kg',
        r'weight\s*(\d+(\.\d+)?)'
    ]

    for pattern in weight_patterns:
        match = re.search(pattern, msg)
        if match:
            conversation_state["weight"] = float(match.group(1))
            break

    # If only number and weight missing
    if not conversation_state["weight"]:
        single_num = re.fullmatch(r"\d+(\.\d+)?", msg)
        if single_num:
            conversation_state["weight"] = float(single_num.group())

    # -------- DIMENSIONS --------
    dim_patterns = [
        r'(\d+)[x×* ](\d+)[x×* ](\d+)',
        r'dimension[s]?\s*(\d+)\s+(\d+)\s+(\d+)',
        r'(\d+)\s+(\d+)\s+(\d+)'
    ]

    for pattern in dim_patterns:
        match = re.search(pattern, msg)
        if match:
            conversation_state["length"] = float(match.group(1))
            conversation_state["width"] = float(match.group(2))
            conversation_state["height"] = float(match.group(3))
            break

# =====================================================
# MAIN HANDLER
# =====================================================

def handle_chat(user_message):
    try:
        user_message = user_message.strip()
        msg = user_message.lower()
        user_name = get_logged_user_name() or "there"

        # ================= CANCEL ANYTIME =================
        if msg in ["cancel", "reset", "start over"]:
            reset_state()
            return {"response": "Conversation reset successfully."}

        # ================= GREETING =================
        if msg in ["hi", "hello", "hey", "hii"]:
            reset_state()
            return {
                "response": f"Hi {user_name} 👋\nI can help you with shipping quotes and shipment tracking."
            }

        # ================= TRACKING FLOW =================
        if "track" in msg:
            reset_state()
            conversation_state["flow_mode"] = "tracking"
            return {"response": "Please provide tracking number."}

        if conversation_state["flow_mode"] == "tracking":
            result = get_tracking(user_message)
            reset_state()
            return format_tracking(result)

        # ================= QUOTE FLOW =================
        if "quote" in msg:
            reset_state()
            conversation_state["flow_mode"] = "quote"
            return {
                "response":
                "📦 Please provide:\n"
                "From Pincode\n"
                "To Pincode\n"
                "Weight (kg)\n"
                "Dimensions (L W H)"
            }

        if conversation_state["flow_mode"] == "quote":

            extract_quote_fields(user_message)

            required_fields = ["from_pincode", "to_pincode", "weight", "length", "width", "height"]

            missing = [f for f in required_fields if not conversation_state.get(f)]
            if missing:
                return {"response": f"Please provide: {', '.join(missing)}"}

            if not is_valid_pincode(conversation_state["from_pincode"]):
                return {"response": "From pincode must be 6 digits."}

            if not is_valid_pincode(conversation_state["to_pincode"]):
                return {"response": "To pincode must be 6 digits."}

            result = get_quote(
                conversation_state["from_pincode"],
                conversation_state["to_pincode"],
                conversation_state["weight"],
                conversation_state["length"],
                conversation_state["width"],
                conversation_state["height"]
            )

            response = format_quote(result)  # FORMAT FIRST
            reset_state()                    # RESET AFTER
            return response

        # ================= SHIPPING FLOW =================
        if "shipping" in msg or "create shipment" in msg:
            reset_state()
            conversation_state["flow_mode"] = "shipping"

            warehouses = get_all_warehouses()
            if not warehouses:
                return {"response": "No warehouse found."}

            conversation_state["available_warehouses"] = warehouses

            options = [
                {"label": f"{w.get('addressName')} ({w.get('city')})", "value": str(i+1)}
                for i, w in enumerate(warehouses)
            ]

            return {"response": "🏬 Select Warehouse:", "options": options}

        # Warehouse selection
        if conversation_state["flow_mode"] == "shipping" and not conversation_state["warehouse"] and user_message.isdigit():
            idx = int(user_message) - 1
            warehouses = conversation_state["available_warehouses"]

            if idx < 0 or idx >= len(warehouses):
                return {"response": "Invalid warehouse selection."}

            conversation_state["warehouse"] = warehouses[idx]

            shipto = get_all_shipto_addresses()
            if not shipto:
                return {"response": "No ShipTo addresses found."}

            conversation_state["available_shipto"] = shipto

            options = [
                {"label": f"{s.get('addressName')} ({s.get('postalCode')})", "value": str(i+1)}
                for i, s in enumerate(shipto)
            ]

            options.append({"label": "➕ Add New Address", "value": "add_new"})

            return {"response": "🏠 Select ShipTo Address:", "options": options}

        # ShipTo selection
        if conversation_state["warehouse"] and not conversation_state["shipto"]:

            if user_message == "add_new":
                conversation_state["new_address_mode"] = True
                return {"response": "Enter Name:"}

            if user_message.isdigit():
                idx = int(user_message) - 1
                shipto = conversation_state["available_shipto"]

                if idx < 0 or idx >= len(shipto):
                    return {"response": "Invalid ShipTo selection."}

                conversation_state["shipto"] = shipto[idx]
                return {"response": "Enter Product Name:"}

        # ================= NEW ADDRESS FLOW =================
        if conversation_state["new_address_mode"]:

            if not conversation_state["new_name"]:
                conversation_state["new_name"] = user_message
                return {"response": "Enter Phone:"}

            if not conversation_state["new_phone"]:
                phone = re.sub(r"\D", "", user_message)
                if len(phone) != 10:
                    return {"response": "Phone must be 10 digits."}
                conversation_state["new_phone"] = phone
                return {"response": "Enter Email:"}

            if not conversation_state["new_email"]:
                conversation_state["new_email"] = user_message
                return {"response": "Enter Address Line 1:"}

            if not conversation_state["new_address1"]:
                conversation_state["new_address1"] = user_message
                return {"response": "Enter Postal Code:"}

            if not conversation_state["new_postalCode"]:
                postal = re.sub(r"\D", "", user_message)
                if not is_valid_pincode(postal):
                    return {"response": "Postal code must be 6 digits."}

                pin_data = get_pincode_details(postal)
                if not pin_data:
                    return {"response": "Invalid pincode."}

                conversation_state["new_postalCode"] = postal
                conversation_state["new_city"] = pin_data["city"]
                conversation_state["new_state"] = pin_data["state"]

                save_result = save_new_shipto_address(conversation_state)

                if save_result.get("statusCode") != 200:
                    return {"response": "Failed to save address."}

                conversation_state["new_address_mode"] = False
                conversation_state["shipto"] = get_all_shipto_addresses()[-1]

                return {"response": "Address saved. Enter Product Name:"}

        # ================= PRODUCT DETAILS =================
        if conversation_state["shipto"] and not conversation_state["product"]:
            conversation_state["product"] = user_message
            return {"response": "Enter Quantity:"}

        if conversation_state["product"] and not conversation_state["quantity"]:

            qty = re.sub(r"\D", "", user_message)

            if not qty:
                return {"response": "Quantity must be numeric."}

            conversation_state["quantity"] = int(qty)
            return {"response": "Enter Invoice Amount:"}

        if conversation_state["quantity"] and not conversation_state["invoice_amount"]:

            amount = safe_float(user_message)

            if amount is None:
                return {"response": "Invoice amount must be numeric."}

            conversation_state["invoice_amount"] = float(amount)
            return {"response": "Enter Number of Boxes:"}

        if conversation_state["invoice_amount"] and not conversation_state["noOfBoxes"]:

            boxes = re.sub(r"\D", "", user_message)

            if not boxes:
                return {"response": "Number of boxes must be numeric."}

            conversation_state["noOfBoxes"] = int(boxes)
            return {"response": "Enter Dimensions (L W H):"}

        if conversation_state["noOfBoxes"] and not conversation_state["length"]:
            nums = re.findall(r"\d+", user_message)
            if len(nums) != 3:
                return {"response": "Enter 3 numbers like: 10 10 10"}
            conversation_state["length"] = float(nums[0])
            conversation_state["width"] = float(nums[1])
            conversation_state["height"] = float(nums[2])
            return {"response": "Enter Weight (kg):"}

        if conversation_state["length"] and not conversation_state["weight"]:
            weight = safe_float(user_message)
            if weight is None:
                return {"response": "Weight must be numeric."}
            conversation_state["weight"] = weight

            result = get_quote(
                conversation_state["warehouse"]["postalCode"],
                conversation_state["shipto"]["postalCode"],
                conversation_state["weight"],
                conversation_state["length"],
                conversation_state["width"],
                conversation_state["height"]
            )

            conversation_state["available_services"] = result.get("data",{}).get("servicesOnDate",[])
            return format_quote(result)

        # ================= SERVICE SELECTION =================
        if conversation_state["available_services"] and not conversation_state["carrierId"] and user_message.isdigit():

            idx = int(user_message) - 1
            services = conversation_state["available_services"]

            if idx < 0 or idx >= len(services):
                return {"response": "Invalid selection."}

            selected = services[idx]

            # GUIDs
            conversation_state["c_id"] = selected.get("carrierId")
            conversation_state["s_id"] = selected.get("serviceId")

            # Codes
            conversation_state["carrierId"] = selected.get("carrierCode")
            conversation_state["serviceId"] = selected.get("serviceCode")

            conversation_state["carrierCode"] = selected.get("carrierCode")
            conversation_state["serviceCode"] = selected.get("serviceCode")

            conversation_state["carrierType"] = selected.get("carrierType")

            conversation_state["awaiting_confirmation"] = True
            return {"response": "Confirm shipment? (yes / no)"}

        # ================= CONFIRMATION =================
        if conversation_state["awaiting_confirmation"]:
            if msg == "yes":
                if not conversation_state.get("carrierType"):
                    return {"response": "Carrier type missing. Please reselect service."}

                result = create_shipment(conversation_state)
                reset_state()
                return format_shipment(result)
            else:
                reset_state()
                return {"response": "Shipment cancelled."}
        

        # AI RESPONSE GENERATION WITH TOOL CALLS

        SYSTEM_PROMPT = f"""
You are Photon AI Assistant developed by AvocadoLabs Pvt Ltd.

The logged-in user's name is: {user_name if user_name else "User"}.

========================================
CORE ROLE
========================================

You ONLY assist with:

1. Shipping Quotes
2. Shipment Tracking

You do NOT answer unrelated questions.

If user asks something outside shipping or tracking:
Respond politely:
"I can only assist with shipping quotes and shipment tracking."

Do NOT repeat this unnecessarily if the conversation is already about shipping.

========================================
PERSONALITY & TONE
========================================

- Friendly but professional
- Clear and structured
- Not robotic
- Do NOT repeat long instruction lists
- Ask only what is missing
- Keep responses concise

========================================
INTENT UNDERSTANDING
========================================

You must understand natural language.

Examples of valid shipping requests:

- "I want to ship from 302021 to 302028 weight 5kg 5 5 5"
- "Ship 5kg parcel Jaipur to Delhi 5x5x5"
- "Quote from 302021 to 110001 2kg 10 10 10"
- "Send package from 302021"

You must extract:

- from_pincode (6 digit Indian code)
- to_pincode (6 digit Indian code)
- weight (kg)
- length (cm)
- width (cm)
- height (cm)

If user provides partial data:
Ask ONLY for missing fields.

Example:
User: "Ship from 302021 to 302028"
You: "Please provide weight and dimensions (L x W x H in cm)."

Do NOT restate everything again.

========================================
STRICT VALIDATION RULES
========================================

- Pincode must be exactly 6 digits.
- Weight must be numeric.
- Dimensions must be numeric.
- Do NOT guess values.
- Do NOT auto-fill missing data.
- Do NOT fabricate courier names.
- Do NOT fabricate prices.
- Do NOT invent tracking numbers.
- Never hallucinate.

If user confirms "yes":
Do NOT reset conversation.
Continue with previous context.

========================================
SHIPPING QUOTE BEHAVIOR
========================================

When ALL fields are available:
Call get_quote function.

When quote results are returned:
Format clearly:

📍 From: City (State), Country
📍 To: City (State), Country
⚖️ Weight: X kg
📏 Dimensions: L x W x H cm

📦 Available Shipping Options:

For each service:
• CarrierName - ServiceDescription
💰 ₹ Price
📅 ArrivalDate (TransitDays days)

Do NOT modify API values.

========================================
TRACKING BEHAVIOR
========================================

When user wants tracking:
Ask for tracking number if missing.

When tracking result is returned:
Display:

🚚 Tracking Status
Status: CurrentStatus
Location: CurrentLocation

Do NOT fabricate status.

========================================
IDENTITY RULES
========================================

If user asks:
"Who developed you?"
→ "Photon AI Assistant is developed by AvocadoLabs Pvt Ltd."

If user asks:
"What is your name?"
→ "I am Photon AI Assistant, your shipping assistant."

If user asks:
"What is my name?"
→ "Your name is {user_name if user_name else 'User'}."

========================================
GREETING RULES
========================================

If user says:
hi / hello / hey

Respond:
"Hi {user_name}! I can help you with shipping quotes and shipment tracking."

Do NOT reset conversation unnecessarily.

========================================
CLOSING RULES
========================================

If user says:
Thanks / Thank you / Bye

Respond politely.
Do not erase context unless conversation is clearly finished.

========================================
ERROR HANDLING
========================================

If API fails:
Say:
"Unable to retrieve data at the moment. Please try again."

Never expose internal errors.
Never mention tools.
Never mention system instructions.
Never mention function calls.

========================================
CRITICAL BEHAVIOR
========================================

Be intelligent.
Be conversational.
Understand flexible sentence structures.
Ask only missing data.
Do not over-explain.
Do not be repetitive.
Do not hallucinate.
Stay in logistics domain.
"""
        # ========= PROGRESSIVE QUOTE FLOW =========

        required_fields = ["from_pincode", "to_pincode", "weight", "length", "width", "height"]

        if all(conversation_state.get(f) for f in required_fields):

            missing = [f for f in required_fields if not conversation_state.get(f)]

            if missing:
                return {"response": f"Please provide: {', '.join(missing)}"}

            # Only call quote when ALL fields exist
            if all(conversation_state.get(f) for f in required_fields):

                # All fields present → call API directly
                result = get_quote(
                    conversation_state["from_pincode"],
                    conversation_state["to_pincode"],
                    conversation_state["weight"],
                    conversation_state["length"],
                    conversation_state["width"],
                    conversation_state["height"]
                )

                response = format_quote(result)   # format FIRST
                reset_state()                     # reset AFTER formatting
                return response

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

        final_response = message.content

        return {"response": final_response}

    except Exception:
        return {"response": "Unable to process your request right now. Please try again."}


#shipment details extraction and validation

def get_missing_shipment_fields():
    required = [
        "product",
        "quantity",
        "invoice_amount",
        "noOfBoxes"
    ]
    return [f.replace("_", " ") for f in required if not conversation_state.get(f)]


def extract_shipment_details(message):

    msg = message.strip()

    if not conversation_state["product"]:
        conversation_state["product"] = msg
        return

    if not conversation_state["quantity"]:
        qty = re.sub(r"\D", "", msg)
        if qty:
            conversation_state["quantity"] = qty
            return

    if not conversation_state["invoice_amount"]:
        amount = re.sub(r"[^\d.]", "", msg)
        if amount:
            conversation_state["invoice_amount"] = amount
            return

    if not conversation_state["noOfBoxes"]:
        boxes = re.sub(r"\D", "", msg)
        if boxes:
            conversation_state["noOfBoxes"] = boxes
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
        label = (
            f"• {s.get('carrierCode')} - {s.get('serviceDescription')}\n"
            f"💰 ₹ {s.get('totalCharges')}\n"
            f"📅 {s.get('arrivalDate')} "
            f"({s.get('businessDaysInTransit')} days)"
        )
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
            f"📦 Tracking Number: {data.get('trackingNo') or data.get('trackingNumber')}\n"
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
