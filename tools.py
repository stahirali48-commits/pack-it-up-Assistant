from langchain.tools import tool
from business_logic import (
    get_company_information_logic,
    get_service_price_logic,
    calculator_logic,
    save_lead_logic,
    search_products_logic,
    check_stock_logic,
    get_delivery_info_logic,
)

@tool
def get_company_information(topic: str = "general") -> str:
    """
    Get official company information.
    Use this for questions about company intro, services, location,
    working hours, contact details, payment, timeline or support.
    """
    return get_company_information_logic(topic)

@tool
def get_service_price(service: str) -> str:
    """
    Get the official starting price of a company service.
    Use this when the user asks about cost, price, budget or quotation.
    """
    return get_service_price_logic(service)

@tool
def calculator(expression: str) -> str:
    """
    Calculate basic arithmetic expressions.
    Use this for discounts, totals, percentages and simple project cost calculations.
    Example input: '2000 - (2000 * 0.15)'
    """
    return calculator_logic(expression)

@tool
def save_lead(name: str, email: str, requirement: str) -> str:
    """
    Save an interested customer's lead.
    Use this only when the user has provided name, email and requirement.
    """
    return save_lead_logic(name, email, requirement)
@tool
def search_products(query: str) -> str:
    """
    Search Pack It Up products by name.
    Use this when a customer wants to find packaging products.
    """
    return search_products_logic(query)
@tool
def check_product_availability(query: str) -> str:
    """
    Check whether a Pack It Up product is available for purchase.
    Use this when a customer asks about product availability.
    """
    return check_stock_logic(query)
@tool
def get_delivery_information(city: str) -> str:
    """
    Get Pack It Up delivery information for a city.
    Use this when a customer asks about delivery time or shipping.
    """
    return get_delivery_info_logic(city)
tools = [get_company_information, get_service_price, calculator, save_lead, search_products, check_product_availability, get_delivery_information]