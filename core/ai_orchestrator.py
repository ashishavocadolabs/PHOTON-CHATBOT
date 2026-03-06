from collections import Counter
from datetime import datetime, timedelta
import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from services.auth_service import get_logged_user_name
from services.shipping_service import (
    get_quote,
    get_tracking,
    create_shipment,
    get_all_shipto_addresses,
    get_default_warehouse,
    save_new_shipto_address,
    get_pincode_details,
    get_all_warehouses,
    get_recent_shipments  
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

LOCATION_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle;margin-right:5px">
<path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z"/>
<circle cx="12" cy="10" r="2.5"/>
</svg>
"""

WEIGHT_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle;margin-right:5px">
<path d="M6 9h12l-1 10H7L6 9z"/>
<path d="M9 9a3 3 0 0 1 6 0"/>
</svg>
"""

DIM_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle;margin-right:5px">
<path d="M3 7h18M3 17h18"/>
<path d="M6 7v10M18 7v10"/>
</svg>
"""

BOX_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle;margin-right:5px">
<path d="M3 7l9-4 9 4-9 4-9-4z"/>
<path d="M3 7v10l9 4 9-4V7"/>
</svg>
"""

MONEY_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle;margin-right:5px">
<circle cx="12" cy="12" r="9"/>
<path d="M9 12h6"/>
<path d="M12 9v6"/>
</svg>
"""

CALENDAR_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle;margin-right:5px">
<rect x="3" y="5" width="18" height="16" rx="2"/>
<path d="M16 3v4M8 3v4M3 11h18"/>
</svg>
"""
TRUCK_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16"
style="vertical-align:middle;margin-right:5px">
<rect x="1" y="3" width="15" height="13"/>
<polygon points="16,8 20,8 23,11 23,16 16,16"/>
<circle cx="5.5" cy="18.5" r="2.5"/>
<circle cx="18.5" cy="18.5" r="2.5"/>
</svg>
"""
WAREHOUSE_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16"
style="vertical-align:middle;margin-right:6px">
<path d="M3 9l9-6 9 6"/>
<path d="M4 10v10h16V10"/>
<path d="M9 21V12h6v9"/>
</svg>
"""

HOME_ICON = """
<svg viewBox="0 0 24 24" width="20" height="20"
style="vertical-align:middle;margin-right:6px">
<path d="M3 10l9-7 9 7"/>
<path d="M5 10v10h14V10"/>
</svg>
"""

PLUS_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16"
style="vertical-align:middle;margin-right:6px">
<path d="M12 5v14M5 12h14"/>
</svg>
"""

CHART_ICON = """
<svg viewBox="0 0 24 24" width="16" height="16"
style="vertical-align:middle;margin-right:5px">
<path d="M4 19V5"/>
<path d="M10 19V9"/>
<path d="M16 19V13"/>
<path d="M22 19H2"/>
</svg>
"""
# recent shipments analysis for better response generation (not used currently, can be integrated in future)
def analyze_recent_shipments(data):

    shipments = data.get("data", [])

    if not shipments:
        return None

    from_cities = []
    to_cities = []
    weights = []
    lengths = []
    widths = []
    heights = []
    boxes = []

    for s in shipments:

        from_cities.append(s.get("cityFrom"))
        to_cities.append(s.get("shipToCityName"))

        # SAFE WEIGHT
        try:
            weights.append(float(str(s.get("weight", "0")).split(",")[0]))
        except:
            continue

        # SAFE LENGTH
        try:
            lengths.append(float(str(s.get("length", "0")).split(",")[0]))
        except:
            continue

        # SAFE WIDTH
        try:
            widths.append(float(str(s.get("width", "0")).split(",")[0]))
        except:
            continue

        # SAFE HEIGHT
        try:
            heights.append(float(str(s.get("height", "0")).split(",")[0]))
        except:
            continue

        try:
            boxes.append(int(s.get("noOfPackages",1)))
        except:
            pass

    if not weights:
        return None

    return {
        "from_city": Counter(from_cities).most_common(1)[0][0],
        "to_city": Counter(to_cities).most_common(1)[0][0],

        "weight": Counter(weights).most_common(3),
        "length": Counter(lengths).most_common(3),
        "width": Counter(widths).most_common(3),
        "height": Counter(heights).most_common(3),
        "boxes": Counter(boxes).most_common(3)
    }


def get_smart_address_suggestion():

    today = datetime.now()
    all_shipments = []

    for i in range(30):
        check_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        recent = get_recent_shipments(check_date)

        if recent.get("statusCode") == 200 and recent.get("data"):
            all_shipments.extend(recent.get("data"))

    if not all_shipments:
        return None

    from_cities = []
    to_cities = []

    for s in all_shipments:
        if s.get("cityFrom"):
            from_cities.append(s.get("cityFrom"))

        if s.get("shipToCityName"):
            to_cities.append(s.get("shipToCityName"))

    if not from_cities or not to_cities:
        return None

    return {
        "from_city": Counter(from_cities).most_common(1)[0][0],
        "to_city": Counter(to_cities).most_common(1)[0][0]
    }
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

        "language": "english",

        "recent_shipments": [],
        "selected_past_shipment": None,
        "modify_mode": False,

        "smart_flow": False
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

    for pin in pincodes:
        if not conversation_state["from_pincode"]:
            conversation_state["from_pincode"] = pin
        elif not conversation_state["to_pincode"]:
            conversation_state["to_pincode"] = pin

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

    # SMART single number for weight (only if weight missing)
    if (
        conversation_state["flow_mode"] == "quote"
        and not conversation_state["weight"]
    ):
        single_number = re.fullmatch(r"\d+(\.\d+)?", msg)
        if single_number:
            value = float(single_number.group())

            # 🚫 DO NOT treat 6-digit numbers as weight (likely pincode)
            if not re.fullmatch(r"\d{6}", msg) and value <= 1000:
                conversation_state["weight"] = value
                return

    # -------- DIMENSIONS --------
    dim_patterns = [
        r'(\d+)[x×*](\d+)[x×*](\d+)',
        r'(\d+)\s+(\d+)\s+(\d+)'
    ]

    for pattern in dim_patterns:
        match = re.search(pattern, msg)
        if match:
            conversation_state["length"] = float(match.group(1))
            conversation_state["width"] = float(match.group(2))
            conversation_state["height"] = float(match.group(3))
            break

def detect_intent(message):
    msg = message.lower().strip()

    if "track" in msg:
        return "tracking"

    if "quote" in msg or "rate" in msg or "price" in msg:
        return "quote"

    if "ship" in msg or "create shipment" in msg or "shipment" in msg:
        return "shipping"

    if "help" in msg:
        return "help"

    return None

# =====================================================
# MAIN HANDLER
# =====================================================

def handle_chat(user_message):
    try:
        user_message = user_message.strip()
        msg = user_message.lower()
        intent = detect_intent(msg)
        user_name = get_logged_user_name() or "there"

        # ================= CANCEL ANYTIME =================
        if msg in ["cancel", "reset", "start over"]:
            reset_state()
            return {"response": "Conversation reset successfully."}

        # ================= GREETING =================
        if msg in ["hi", "hello", "hey", "hii"]:
            reset_state()
            return {
                "response": f"Hi {user_name}\nWhat would you like to do today?",
                "options": [
                {"label": "Create Shipment", "value": "create shipment"},
                {"label": "Get Quote", "value": "quote"},
                {"label": "Track Shipment", "value": "tracking"}
            ]
        }

        # ================= TRACKING FLOW =================
        if intent == "tracking":
            reset_state()
            conversation_state["flow_mode"] = "tracking"
            return {"response": "<b>Sure! Please provide your tracking number.</b>"}

        if conversation_state["flow_mode"] == "tracking":
            result = get_tracking(user_message)
            reset_state()
            return format_tracking(result)

        # ================= HELP INTENT =================
        if intent == "help":
            return {
                "response":
                f"Absolutely {user_name}!\n\n"
                "I can help you with:\n"
                "• Shipping Quotes (rates & pricing)\n"
                "• Creating Shipments\n"
                "• Shipment Tracking\n\n"
                "Which one do you need help with?"
            }
        # ================= QUOTE FLOW =================
        if intent == "quote":
            reset_state()
            conversation_state["flow_mode"] = "quote"
            return {
                "response":
                "Sure! I can help you with shipping rates.<br><br>"
                "<b>Please provide:</b><br>"
                "<b>From</b> Pincode<br>"
                "<b>To</b> Pincode<br>"
                "<b>Weight</b> (kg)<br>"
                "<b>Dimensions</b> (L W H)"
            }

        if conversation_state["flow_mode"] == "quote" and not conversation_state["available_services"]:

            extract_quote_fields(user_message)

            required_fields = [
                "from_pincode",
                "to_pincode",
                "weight",
                "length",
                "width",
                "height"
            ]

            missing = [f for f in required_fields if not conversation_state.get(f)]

            if missing:

                readable = {
                    "from_pincode": "From Pincode",
                    "to_pincode": "To Pincode",
                    "weight": "Weight (kg)",
                    "length": "Length (cm)",
                    "width": "Width (cm)",
                    "height": "Height (cm)"
                }

                missing_readable = [readable[m] for m in missing]

                return {
                    "response": "<b>Please provide:</b>\n" + "\n".join(missing_readable)
                }

                #  All fields available → call API
            result = get_quote(
                conversation_state["from_pincode"],
                conversation_state["to_pincode"],
                conversation_state["weight"],
                conversation_state["length"],
                conversation_state["width"],
                conversation_state["height"]
            )

            response = format_quote(result)

            # stop quote loop
            conversation_state["flow_mode"] = None

            # add confirmation buttons
            response["options"].append({
            "label": "Yes, Create Shipment",
            "value": "start_shipping"
            })

            response["options"].append({
            "label": "No",
            "value": "cancel_shipping"
            })

            return response
        
        # ================= START SHIPPING FROM QUOTE =================
        if user_message == "start_shipping":

            # start shipment flow
            conversation_state["flow_mode"] = None

            # trigger shipping intent
            return handle_chat("create shipment")


        if user_message == "cancel_shipping":
            reset_state()
            return {"response": "Shipment creation cancelled."}

        # ================= SHIPPING FLOW =================
        if intent == "shipping" and conversation_state["flow_mode"] is None:
            reset_state()
            conversation_state["flow_mode"] = "shipping"

            today = datetime.now()
            all_shipments = []

            for i in range(7):  # last 7 days
                check_date = (today -   timedelta(days=i)).strftime("%Y-%m-%d")
                recent = get_recent_shipments(check_date)

                if recent.get("statusCode") == 200 and recent.get("data"):
                    all_shipments.extend(recent.get("data"))

            if all_shipments:
                # 🔥 AI ANALYSIS LAYER  
                analysis = analyze_recent_shipments({"data": all_shipments})

                if analysis:

                    conversation_state["weight_suggestions"] = [x[0] for x in analysis["weight"]]

                    conversation_state["dimension_suggestions"] = {
                        "length": [x[0] for x in analysis["length"]],
                        "width": [x[0] for x in analysis["width"]],
                        "height": [x[0] for x in analysis["height"]],
                    }
                    conversation_state["box_suggestions"] = [x[0] for x in analysis["boxes"]]
                    conversation_state["ai_suggestion"] = analysis

                    return {
                        "response":
                            f"{CHART_ICON} Shipment Insights (Last 30 Days)\n\n"
                            f"• Most used route: {analysis['from_city']} → {analysis['to_city']}\n"
                            f"• Most common weight: {analysis['weight'][0][0]} kg\n"
                            f"• Most common dimensions: "
                            f"{analysis['length'][0][0]}x{analysis['width'][0][0]}x{analysis['height'][0][0]}\n\n"
                            "What would you like to do?",
                        "options": [
                            {
                                "label": f"""
                                <div style="display:flex;flex-direction:column;align-items:center;text-align:center;position:relative">

                                <div style="
                                position:absolute;
                                top:-6px;
                                right:-6px;
                                background:#2ecc71;
                                color:white;
                                font-size:10px;
                                padding:2px 6px;
                                border-radius:10px;
                                font-weight:600;">
                                Suggested
                                </div>

                                <div style="margin-bottom:6px">
                                {TRUCK_ICON}
                                </div>

                                <div style="font-weight:600;font-size:13px">
                                Ship Using Most Frequent Details
                                </div>

                                </div>
                                """,
                                "value": "smart_ship"
                            },

                            {
                                "label": f"""
                                <div style="display:flex;flex-direction:column;align-items:center;text-align:center">

                                <div style="margin-bottom:6px">
                                {WAREHOUSE_ICON}
                                </div>

                                <div style="font-weight:600;font-size:13px">
                                Select Warehouse Manually
                                </div>

                                </div>
                                """,
                                "value": "fresh"
                            }
                        ]
                    }

                shipments = all_shipments[:5]  # show last 5
                conversation_state["recent_shipments"] = shipments

                options = []

                for i, s in enumerate(shipments, 1):
                    label = (
                        f"User Name: {s.get('userId') or 'Unknown User'} \n"
                        f"{s.get('carrierId') or 'Unknown Carrier'} - {s.get('carrierType') or 'Unknown Service'}\n"
                        f"Ship From: {s.get('cityFrom') or 'Unknown'} → "
                        f"Ship To: {s.get('shipToCityName') or 'Unknown'} \n "
                        f"Weight: {s.get('weight')}kg | \n"
                        f"Dimensions: {s.get('length')}x{s.get('width')}x{s.get('height')}\n"
                        f"Date Created: {s.get('shipDateBegin')}"
                    )
                    options.append({"label": label, "value": f"past_{i}"})

                options.append({"label": "🆕 Start Fresh Shipment", "value": "fresh"})

                return {
                    "response": "I found your recent shipments. Select one to continue:",
                    "options": options
                }

            warehouses = get_all_warehouses()
            if not warehouses:
                return {"response": "No warehouse found."}

            conversation_state["available_warehouses"] = warehouses

            options = [
            {
            "label": f"""
            <div style="display:flex;flex-direction:column;align-items:center;text-align:center">

            <div style="margin-bottom:6px">
            {WAREHOUSE_ICON}
            </div>

            <div style="
            font-weight:600;
            font-size:13px;
            max-width:140px;
            word-break:break-word;
            line-height:1.3;
            ">
            {w.get('addressName')}
            </div>

            <div style="font-size:12px;color:#333">
            {w.get('city')}
            </div>

            </div>
            """,
            "value": str(i+1)
            }
            for i, w in enumerate(warehouses)
            ]

            return {"response": f"<b>{WAREHOUSE_ICON} Please select a warehouse:</b>", "options": options}
        
        # ================= PAST SHIPMENT SELECTION =================
        if conversation_state["flow_mode"] == "shipping" and user_message.startswith("past_"):

            index = int(user_message.split("_")[1]) - 1
            shipments = conversation_state["recent_shipments"]

            if index < 0 or index >= len(shipments):
                return {"response": "Invalid selection."}

            selected = shipments[index]
            conversation_state["selected_past_shipment"] = selected

            return {
                "response": "What would you like to do?",
                "options": [
                    {"label": "🚚 Ship Same Details", "value": "ship_same"},
                    {"label": "✏ Modify Details & Create New Shipment", "value": "modify_past"},
                    {"label": "❌ Cancel", "value": "cancel"}
                ]
            }

        # ================= START FRESH SHIPMENT =================
        if user_message == "fresh":

            warehouses = get_all_warehouses()

            if not warehouses:
                return {"response": "No warehouse found."}

            conversation_state["available_warehouses"] = warehouses

            options = [
                {
                    "label": f"""
                    <div style="display:flex;flex-direction:column;align-items:center;text-align:center">

                    <div style="margin-bottom:6px">
                    {WAREHOUSE_ICON}
                    </div>

                    <div style="
                    font-weight:600;
                    font-size:13px;
                    max-width:140px;
                    word-break:break-word;
                    line-height:1.3;
                    ">
                    {w.get('addressName')}
                    </div>

                    <div style="font-size:12px;color:#333">
                    {w.get('city')}
                    </div>

                    </div>
                    """,
                    "value": str(i+1)
                }
                for i, w in enumerate(warehouses)
            ]

            return {
                "response": f"<b>{WAREHOUSE_ICON} Please select a warehouse:</b>",
                "options": options
            }
        
        # ================= SMART SHIP =================
        if user_message == "smart_ship":

            conversation_state["smart_flow"] = True

            analysis = conversation_state.get("ai_suggestion")

            if not analysis:
                return {"response": "No AI suggestion available."}
            
             # CLEAN SHIPPING STATE
            conversation_state.update({
                "product": None,
                "quantity": None,
                "invoice_amount": None,
                "noOfBoxes": None,
                "carrierId": None,
                "serviceId": None,
                "carrierCode": None,
                "serviceCode": None,
                "awaiting_confirmation": False
            })

            # Prefill state
            conversation_state["weight"] = float(analysis["weight"][0][0])
            conversation_state["length"] = float(analysis["length"][0][0])
            conversation_state["width"] = float(analysis["width"][0][0])
            conversation_state["height"] = float(analysis["height"][0][0])

            # Auto match warehouse
            warehouses = get_all_warehouses()
            conversation_state["available_warehouses"] = warehouses

            conversation_state["warehouse"] = None
            for w in warehouses:
                if str(w.get("city","")).lower() == str(analysis["from_city"]).lower():
                    conversation_state["warehouse"] = w
                    break

            shipto_list = get_all_shipto_addresses()
            conversation_state["available_shipto"] = shipto_list

            conversation_state["shipto"] = None
            for s in shipto_list:
                if str(s.get("city","")).lower() == str(analysis["to_city"]).lower():
                    conversation_state["shipto"] = s
                    break

            if not conversation_state["warehouse"] or not conversation_state["shipto"]:
                return {"response": "Unable to auto-match addresses. Please select manually."}

            return {
                "response": f"""
                <b>Suggested shipment details loaded.</b><br><br>

                {LOCATION_ICON} From: {analysis['from_city']}<br>
                {LOCATION_ICON} To: {analysis['to_city']}<br>
                {WEIGHT_ICON} Weight: {conversation_state['weight']} kg<br>
                {DIM_ICON} Dimensions: {conversation_state['length']} x {conversation_state['width']} x {conversation_state['height']} cm<br><br>

                <b>Enter Product Name:</b>
                """
            }
        
        if user_message == "show_recent":

            shipments = conversation_state.get("recent_shipments", [])

            if not shipments:
                return {"response": "No recent shipments found."}

            options = []

            for i, s in enumerate(shipments, 1):
                label = (
                    f"{s.get('carrierId')} - {s.get('carrierType')}\n"
                    f"{s.get('cityFrom')} → {s.get('shipToCityName')} | "
                    f"{s.get('weight')}kg | "
                    f"{s.get('length')}x{s.get('width')}x{s.get('height')}"
                )
                options.append({"label": label, "value": f"past_{i}"})

            options.append({"label": "🆕 Start Fresh Shipment", "value": "fresh"})

            return {
                "response": "Select one recent shipment:",
                "options": options
            }

        # ================= SHIP SAME DETAILS =================
        if user_message == "ship_same":

            past = conversation_state["selected_past_shipment"]

            # Prefill shipment details
            conversation_state["weight"] = float(past.get("weight"))
            conversation_state["length"] = float(past.get("length"))
            conversation_state["width"] = float(past.get("width"))
            conversation_state["height"] = float(past.get("height"))

            # Static fallback product (can modify later)
            conversation_state["product"] = "General Goods"
            conversation_state["quantity"] = 1
            conversation_state["invoice_amount"] = 1000
            conversation_state["noOfBoxes"] = past.get("noOfPackages", 1)

            # Get warehouse & shipto
            warehouses = get_all_warehouses()
            conversation_state["available_warehouses"] = warehouses

            # Try auto-match warehouse
            for w in warehouses:
                if w.get("city") == past.get("cityFrom"):
                    conversation_state["warehouse"] = w
                    break

            shipto_list = get_all_shipto_addresses()
            conversation_state["available_shipto"] = shipto_list

            for s in shipto_list:
                if s.get("city") == past.get("shipToCityName"):
                    conversation_state["shipto"] = s
                    break

            # If auto-match failed → fallback manual
            if not conversation_state["warehouse"] or not conversation_state["shipto"]:
                return {
                    "response": "Please select warehouse to continue:",
                    "options": [
                        {"label": f"{w.get('addressName')} ({w.get('city')})", "value": str(i+1)}
                        for i, w in enumerate(warehouses)
                    ]
                }

            # Directly go to quote
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
        
        #modify past shipment flow
        if msg.strip() == "modify_past":

            past = conversation_state.get("selected_past_shipment")

            if not past:
                return {"response": "No shipment selected. Please choose a shipment first."}

            conversation_state["modify_mode"] = True

            # -----------------------------
            # Prefill numeric fields
            # -----------------------------
            conversation_state["weight"] = float(past.get("weight") or 0)
            conversation_state["length"] = float(past.get("length") or 0)
            conversation_state["width"] = float(past.get("width") or 0)
            conversation_state["height"] = float(past.get("height") or 0)
            conversation_state["noOfBoxes"] = int(past.get("noOfPackages") or 1)

            conversation_state["product"] = "General Goods"
            conversation_state["quantity"] = 1
            conversation_state["invoice_amount"] = 0

            # -----------------------------
            # 🔥 CRITICAL FIX: AUTO MATCH
            # -----------------------------
            warehouses = get_all_warehouses()
            conversation_state["available_warehouses"] = warehouses
            conversation_state["warehouse"] = None

            for w in warehouses:
                if str(w.get("city", "")).strip().lower() == str(past.get("cityFrom", "")).strip().lower():
                    conversation_state["warehouse"] = w
                    break

            shipto_list = get_all_shipto_addresses()
            conversation_state["available_shipto"] = shipto_list
            conversation_state["shipto"] = None

            for s in shipto_list:
                if str(s.get("city", "")).strip().lower() == str(past.get("shipToCityName", "")).strip().lower():
                    conversation_state["shipto"] = s
                    break

            if not conversation_state["warehouse"] or not conversation_state["shipto"]:
                return {"response": "Unable to auto-match warehouse or ShipTo. Please select manually."}

            # -----------------------------
            # RETURN EDIT FORM
            # -----------------------------
            return {
                "type": "edit_form",
                "title": "Modify Shipment Details",
                "submit_action": "submit_modify_form",
                "fields": [
                    {"name": "product", "label": "Product", "type": "text", "value": conversation_state["product"]},
                    {"name": "quantity", "label": "Quantity", "type": "number", "value": conversation_state["quantity"]},
                    {"name": "invoice_amount", "label": "Invoice Amount", "type": "number", "value": conversation_state["invoice_amount"]},
                    {"name": "noOfBoxes", "label": "No of Boxes", "type": "number", "value": conversation_state["noOfBoxes"]},
                    {"name": "weight", "label": "Weight (kg)", "type": "number", "value": conversation_state["weight"]},
                    {"name": "length", "label": "Length (cm)", "type": "number", "value": conversation_state["length"]},
                    {"name": "width", "label": "Width (cm)", "type": "number", "value": conversation_state["width"]},
                    {"name": "height", "label": "Height (cm)", "type": "number", "value": conversation_state["height"]}
                ]
            }
        # ================= MODIFY FORM SUBMIT =================
        if user_message.startswith("submit_modify_form:"):

            json_data = user_message.replace("submit_modify_form:", "")
            updated = json.loads(json_data)

            for key, value in updated.items():
                conversation_state[key] = value

            result = get_quote(
                conversation_state["warehouse"]["postalCode"],
                conversation_state["shipto"]["postalCode"],
                conversation_state["weight"],
                conversation_state["length"],
                conversation_state["width"],
                conversation_state["height"]
            )

            services = result.get("data", {}).get("servicesOnDate", [])

            conversation_state["available_services"] = services

            # AI COURIER SELECTION
            best_service = select_best_courier(services)

            if best_service:

                conversation_state["carrierId"] = best_service.get("carrierCode")
                conversation_state["serviceId"] = best_service.get("serviceCode")

                conversation_state["carrierCode"] = best_service.get("carrierCode")
                conversation_state["serviceCode"] = best_service.get("serviceCode")

                conversation_state["carrierType"] = best_service.get("carrierType")

                conversation_state["awaiting_confirmation"] = True

                return {
                    "response":
                    f"AI selected best courier automatically:\n\n"
                    f"Carrier: {best_service.get('carrierCode')} - {best_service.get('serviceDescription')}\n"
                    f"Price: ₹ {best_service.get('totalCharges')}\n"
                    f"Arrival: {best_service.get('arrivalDate')}\n\n"
                    "Confirm shipment?",
                    "options": [
                        {
                            "label": """
                            <span style="display:flex;align-items:center;gap:6px">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                            <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2"/>
                            </svg>
                            Yes, Create Shipment
                            </span>
                            """,
                            "value": "yes"
                        },
                        {
                            "label": """
                            <span style="display:flex;align-items:center;gap:6px">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                            <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2"/>
                            </svg>
                            Choose Manually
                            </span>
                            """,
                            "value": "manual_service"
                        }
                    ]
                }

            return format_quote(result)
        
        # ================= SMART ADDRESS =================
        if user_message == "smart_address":

            suggestion = conversation_state.get("address_ai")

            if not suggestion:
                return {"response": "No smart address suggestion available."}

            warehouses = get_all_warehouses()
            shipto = get_all_shipto_addresses()

            for w in warehouses:
                if str(w.get("city","")).lower() == str(suggestion["from_city"]).lower():
                    conversation_state["warehouse"] = w
                    break

            for s in shipto:
                if str(s.get("city","")).lower() == str(suggestion["to_city"]).lower():
                    conversation_state["shipto"] = s
                    break

            if conversation_state["warehouse"] and conversation_state["shipto"]:
                return {
                    "response": f"""
                    <span style="display:flex;align-items:center;gap:6px">
                    <svg width="16" height="16" viewBox="0 0 24 24">
                    <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2"/>
                    </svg>
                    Suggested addresses selected successfully.
                    </span><br>
                    <b>Enter Product Name:</b>
                    """
                }

            return {"response": "Unable to auto match addresses. Please select manually."}
        
        # ================= MANUAL ADDRESS =================
        if user_message == "manual_address":

            warehouses = get_all_warehouses()

            if not warehouses:
                return {"response": "No warehouse found."}

            conversation_state["available_warehouses"] = warehouses

            options = [
                {"label": f"{w.get('addressName')} ({w.get('city')})", "value": str(i+1)}
                for i, w in enumerate(warehouses)
            ]

            return {"response": f"<b>{WAREHOUSE_ICON} Please select a warehouse:</b>", "options": options}
            
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
            {
            "label": f"""
            <div style="display:flex;flex-direction:column;align-items:center;text-align:center">

            <div style="margin-bottom:6px">
            {HOME_ICON}
            </div>

            <div style="font-weight:600">
            {s.get('addressName')}
            </div>

            <div>
            {s.get('city')} ({s.get('postalCode')}, {s.get('state')})
            </div>

            <div>
            Phone: {s.get('phone')}
            </div>

            </div>
            """,
            "value": str(i+1)
            }
            for i, s in enumerate(shipto)
            ]

            options.append({
            "label": f"""
            <span style="display:flex;align-items:center;gap:6px">
            {PLUS_ICON}
            Add New Address
            </span>
            """,
            "value": "add_new"
            })

            return {"response": f"<b>{HOME_ICON} Select ShipTo Address:</b>", "options": options}

        # ================= NEW ADDRESS FLOW =================
        if conversation_state["new_address_mode"]:

            if not conversation_state["new_name"]:
                conversation_state["new_name"] = user_message
                return {"response": "<b>Enter Phone:</b>"}

            if not conversation_state["new_phone"]:
                phone = re.sub(r"\D", "", user_message)
                if len(phone) != 10:
                    return {"response": "Phone must be 10 digits."}
                conversation_state["new_phone"] = phone
                return {"response": "<b>Enter Email:</b>"}

            if not conversation_state["new_email"]:
                conversation_state["new_email"] = user_message
                return {"response": "<b>Enter Address Line 1:</b>"}

            if not conversation_state["new_address1"]:
                conversation_state["new_address1"] = user_message
                return {"response": "<b>Enter Postal Code:</b>"}

            if not conversation_state["new_postalCode"]:
                postal = re.sub(r"\D", "", user_message)
                if not is_valid_pincode(postal):
                    return {"response": "<b>Postal code must be 6 digits.</b>"}

                pin_data = get_pincode_details(postal)
                if not pin_data:
                    return {"response": "<b>Invalid pincode.</b>"}

                conversation_state["new_postalCode"] = postal
                conversation_state["new_city"] = pin_data["city"]
                conversation_state["new_state"] = pin_data["state"]

                save_result = save_new_shipto_address(conversation_state)

                if save_result.get("statusCode") != 200:
                    return {"response": "<b>Failed to save address.</b>"}

                conversation_state["new_address_mode"] = False
                conversation_state["shipto"] = get_all_shipto_addresses()[-1]

                return {"response": "<b>Address saved. Enter Product Name:</b>"}

         # ShipTo selection
        if conversation_state["warehouse"] and not conversation_state["shipto"]:

            if user_message == "add_new":
                conversation_state["new_address_mode"] = True
                return {"response": "<b>Enter Name:</b>"}

            if user_message.isdigit():
                idx = int(user_message) - 1
                shipto = conversation_state["available_shipto"]

                if idx < 0 or idx >= len(shipto):
                    return {"response": "Invalid ShipTo selection."}

                conversation_state["shipto"] = shipto[idx]
                return {"response": "<b>Enter Product Name:</b>"}
            
        # ================= PRODUCT DETAILS =================
        if conversation_state["shipto"] and not conversation_state["product"]:
            conversation_state["product"] = user_message
            return {"response": "<b>Enter Quantity:</b>"}

        if conversation_state["product"] and not conversation_state["quantity"]:

            qty = re.sub(r"\D", "", user_message)

            if not qty:
                return {"response": "<b>Quantity must be numeric.</b>"}

            conversation_state["quantity"] = int(qty)
            return {"response": "<b>Enter Invoice Amount:</b>"}

        if conversation_state["quantity"] and not conversation_state["invoice_amount"]:

            amount = safe_float(user_message)

            if amount is None:
                return {"response": "<b>Invoice amount must be numeric.</b>"}

            conversation_state["invoice_amount"] = float(amount)
            boxes = conversation_state.get("box_suggestions", [])

            options = []

            for b in boxes:
                options.append({
                    "label": f"{b} Boxes",
                    "value": str(b)
                })

            return {
                "response": "<b>Enter Number of Boxes:</b>",
                "options": options
            }

        if conversation_state["invoice_amount"] and not conversation_state["noOfBoxes"]:

            # SMART SHIP → skip dimension + weight
            if conversation_state.get("smart_flow"):

                boxes = re.sub(r"\D", "", user_message)

                if not boxes:
                    return {"response": "<b>Number of boxes must be numeric.</b>"}

                conversation_state["noOfBoxes"] = int(boxes)

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
            boxes = re.sub(r"\D", "", user_message)

            if not boxes:
                return {"response": "<b>Number of boxes must be numeric.</b>"}

            conversation_state["noOfBoxes"] = int(boxes)
            dims = conversation_state.get("dimension_suggestions", {})

            options = []

            for l in dims.get("length", []):
                for w in dims.get("width", []):
                    for h in dims.get("height", []):
                        options.append({
                            "label": f"{l} x {w} x {h}",
                            "value": f"{l} {w} {h}"
                        })

            return {
                "response": "<b>Enter Dimensions (L W H):</b>",
                "options": options[:4]
            }

        if conversation_state["noOfBoxes"] and not conversation_state["length"]:
            nums = re.findall(r"\d+", user_message)
            if len(nums) != 3:
                return {"response": "Enter 3 numbers like: 10 10 10"}
            conversation_state["length"] = float(nums[0])
            conversation_state["width"] = float(nums[1])
            conversation_state["height"] = float(nums[2])
            weights = conversation_state.get("weight_suggestions", [])

            options = []

            for w in weights:
                options.append({
                    "label": f"{w} kg",
                    "value": str(w)
                })

            return {
                "response": "<b>Enter Weight (kg):</b>",
                "options": options
            }

        if conversation_state["length"] and not conversation_state["weight"]:
            weight = safe_float(user_message)
            if weight is None:
                return {"response": "<b>Weight must be numeric.</b>"}
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
        
        # ================= MANUAL SERVICE =================
        if user_message == "manual_service":

            services = conversation_state["available_services"]

            options = []

            for i, s in enumerate(services, 1):

                label = (
                    f"{s.get('carrierCode')} - {s.get('serviceDescription')}\n"
                    f"₹ {s.get('totalCharges')} | "
                    f"{s.get('businessDaysInTransit')} days"
                )

                options.append({
                    "label": label,
                    "value": str(i)
                })

            return {
                "response": "Choose courier service:",
                "options": options
            }

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

            return {
                "response": "<b>Confirm shipment?</b>",
                "options": [
                    {
                        "label": """
                        <span style="display:flex;align-items:center;gap:6px">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2"/>
                        </svg>
                        Yes, Create Shipment
                        </span>
                        """,
                        "value": "yes"
                    },
                    {
                        "label": """
                        <span style="display:flex;align-items:center;gap:6px">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2"/>
                        </svg>
                        Cancel Shipment
                        </span>
                        """,
                        "value": "no"
                    }
                ]
            }

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
                return {"response": "<b>Shipment cancelled.</b>"}
        

        # AI RESPONSE GENERATION WITH TOOL CALLS

        SYSTEM_PROMPT = f"""
You are Photon AI Assistant developed by AvocadoLabs Pvt Ltd.

The logged-in user's name is: {user_name if user_name else "User"}.

========================================
CORE ROLE
========================================

You ONLY assist with:

1. Shipping Quotes
2. creating shipments
3. Shipment Tracking

You do NOT answer unrelated questions.

If user asks something outside shipping or tracking:
Respond politely:
"I can only assist with <b>shipping quotes, creating shipments, and shipment tracking.</b>"

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
"Hi {user_name}! I can help you with shipping quotes, creating shipments, and shipment tracking."

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
            tool_choice="auto",
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

def select_best_courier(services):

    if not services:
        return None

    def safe_price(service):
        try:
            return float(service.get("totalCharges", 999999))
        except:
            return 999999

    def safe_days(service):
        try:
            return int(service.get("businessDaysInTransit", 999))
        except:
            return 999

    sorted_services = sorted(
        services,
        key=lambda s: (safe_price(s), safe_days(s))
    )

    return sorted_services[0]
#formatter functions for quote, shipment and tracking results

def format_quote(result):

    if result.get("statusCode") != 200:
        return {"response": f"Quote Error: {result.get('error')}"}

    services = result.get("data", {}).get("servicesOnDate", [])

    if not services:
        return {"response": "No courier services available."}

    conversation_state.update({
        "available_services": services
    })

    msg = (
        f"<b>{LOCATION_ICON} From:</b> {result['from_details']['city']} "
        f"({result['from_details']['state']}), {result['from_details']['country']}<br>"

        f"<b>{LOCATION_ICON} To:</b> {result['to_details']['city']} "
        f"({result['to_details']['state']}), {result['to_details']['country']}<br><br>"

        f"<b>{WEIGHT_ICON} Weight:</b> {conversation_state['weight']} kg<br>"

        f"<b>{DIM_ICON} Dimensions:</b> {conversation_state['length']} x "
        f"{conversation_state['width']} x {conversation_state['height']} cm<br><br>"

        f"<b>{BOX_ICON} Available Shipping Options:</b><br><br>"
    )

    options = []

    for i, s in enumerate(services, 1):
        label = f"""
        <div class="service-card">

        <div class="service-title">
        {s.get('carrierCode')} - {s.get('serviceDescription')}
        </div>

        <div class="service-row">
        <span>{MONEY_ICON} ₹ {s.get('totalCharges')}</span>
        <span>{CALENDAR_ICON} {s.get('businessDaysInTransit')} days</span>
        </div>

        </div>
        """
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

    carrier = (
        data.get("carrierName")
        or data.get("carrierCode")
        or "Not Available"
    )

    tracking = (
        data.get("trackingNo")
        or data.get("trackingNumber")
        or "Not Available"
    )

    return {
        "response":
            """
<b>Shipment Created Successfully!</b><br><br>

<span style="display:flex;align-items:center;gap:6px;">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
<rect x="1" y="3" width="15" height="13" stroke="currentColor" stroke-width="2"/>
<polygon points="16,8 20,8 23,11 23,16 16,16" stroke="currentColor" stroke-width="2"/>
<circle cx="5.5" cy="18.5" r="2.5" stroke="currentColor" stroke-width="2"/>
<circle cx="18.5" cy="18.5" r="2.5" stroke="currentColor" stroke-width="2"/>
</svg>
Courier: """ + carrier + """
</span>

<span style="display:flex;align-items:center;gap:6px;margin-top:4px;">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
<path d="M3 7l9-4 9 4-9 4-9-4z" stroke="currentColor" stroke-width="2"/>
<path d="M3 7v10l9 4 9-4V7" stroke="currentColor" stroke-width="2"/>
</svg>
Tracking Number: """ + tracking + """
</span>
"""
    }


def format_tracking(result):

    if result.get("statusCode") != 200:
        return {"response": result.get("error", "Tracking failed.")}

    data = result.get("data", {})

    response = (
        f"{TRUCK_ICON} <b>Tracking Status</b><br><br>"
        f"Status: {data.get('currentStatus')}<br>"
        f"Location: {data.get('currentLocation')}"
    )
    return {"response": response}
