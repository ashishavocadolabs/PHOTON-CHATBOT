from services.shipping_service import get_tracking

def tracking_tool(tracking_number):
    return get_tracking(tracking_number)