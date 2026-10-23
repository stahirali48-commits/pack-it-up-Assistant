from datetime import datetime
from pathlib import Path
import csv
import ast
import operator
import json
from urllib.request import Request, urlopen

from company_data import COMPANY_CONFIG
LEADS_FILE = Path("data") / "leads.csv"
LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_company_information_logic(topic: str = "general") -> str:
    topic = topic.lower().strip()
    company = COMPANY_CONFIG

    if topic in ["general", "about", "company"]:
        return (
            f"Company Name: {company['company_name']}\n"
            f"About: {company['about']}\n"
            f"Location: {company['location']}\n"
            f"Working Hours: {company['working_hours']}\n"
            f"Email: {company['contact_email']}\n"
            f"Phone: {company['phone']}"
        )

    if topic in ["services", "service"]:
        lines = ["Official services:"]
        for key, service in company["services"].items():
            lines.append(
                f"- {service['display_name']}: {service['description']} "
                f"Starting from ${service['starting_price_usd']}"
            )
        return "\n".join(lines)

    if topic in ["location", "address"]:
        return f"Our office is located in {company['location']}."

    if topic in ["hours", "working hours", "timing", "time"]:
        return f"Our working hours are {company['working_hours']}."

    if topic in ["contact", "email", "phone"]:
        return f"Email: {company['contact_email']} | Phone: {company['phone']}"

    if topic in company["faqs"]:
        return company["faqs"][topic]

    return (
        "I could not find that exact topic in official company data. "
        "Available topics: general, services, location, working hours, contact, payment, timeline, support."
    )


def normalize_service_name(service: str) -> str:
    service = service.lower().strip()
    aliases = {
        "web": "website",
        "site": "website",
        "business website": "website",
        "ai bot": "chatbot",
        "bot": "chatbot",
        "ai chatbot": "chatbot",
        "app": "mobile app",
        "application": "mobile app",
        "vision": "computer vision",
        "cv": "computer vision",
        "automation system": "automation",
    }
    return aliases.get(service, service)


def get_service_price_logic(service: str) -> str:
    service_key = normalize_service_name(service)
    services = COMPANY_CONFIG["services"]

    if service_key not in services:
        available = ", ".join(services.keys())
        return f"Service not found. Available services are: {available}."

    selected = services[service_key]
    return (
        f"{selected['display_name']} starts from "
        f"${selected['starting_price_usd']} USD. "
        f"Description: {selected['description']}"
    )

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError("Operator not allowed")
        return _ALLOWED_OPERATORS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        operand = _safe_eval(node.operand)
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError("Operator not allowed")
        return _ALLOWED_OPERATORS[op_type](operand)
    raise ValueError("Only basic arithmetic is allowed")


def calculator_logic(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return str(round(result, 2))
    except Exception as e:
        return f"Calculation error: {e}"


def save_lead_logic(name: str, email: str, requirement: str) -> str:
    name = name.strip()
    email = email.strip()
    requirement = requirement.strip()

    if not name or not email or not requirement:
        return "Lead was not saved. Name, email and requirement are required."

    file_exists = LEADS_FILE.exists()

    with LEADS_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["timestamp", "name", "email", "requirement"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "name": name,
            "email": email,
            "requirement": requirement,
        })

    return f"Lead saved successfully for {name} with email {email}."
def search_products_logic(query: str, limit: int = 5) -> str:
    query = query.strip().lower()

    if not query:
        return "Please enter a product name to search."

    url = "https://packitup.com.pk/products.json?limit=250"
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        with urlopen(request, timeout=10) as response:
            catalog = json.load(response)
    except Exception:
        return (
            "I could not access the product catalog. "
            "Please visit https://packitup.com.pk/"
        )

    matches = []

    for product in catalog.get("products", []):
        title = product.get("title", "")
        description = product.get("body_html", "")
        tags = product.get("tags", [])

        searchable = (
            f"{title} {description} "
            f"{product.get('product_type', '')} {' '.join(tags)}"
        ).lower()

        words = query.split()

        if query not in searchable and not all(
            word in searchable for word in words
        ):
            continue

        prices = []

        for variant in product.get("variants", []):
            try:
               price_value = float(variant.get("price", 0))
            except (TypeError, ValueError):
                continue
            if price_value > 0:
                     prices.append(price_value) 

        price = (
            f"PKR {min(prices):,.0f}"
            if prices
            else "Price not listed"
        )

        handle = product.get("handle", "")
        link = (
            f"https://packitup.com.pk/products/{handle}"
            if handle
            else "https://packitup.com.pk/"
        )

        matches.append(f"- {title} | {price} | {link}")

        if len(matches) >= max(1, min(limit, 10)):
            break

    if not matches:
        return f"No products found for '{query}'."

    return "Matching products:\n" + "\n".join(matches)
def check_stock_logic(query: str) -> str:
    query = query.strip().lower()

    if not query:
        return "Please enter a product name."

    url = "https://packitup.com.pk/products.json?limit=250"
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        with urlopen(request, timeout=10) as response:
            catalog = json.load(response)
    except Exception:
        return "Could not retrieve product availability. Please check the website."

    matches = []

    for product in catalog.get("products", []):
        title = product.get("title", "")
        description = product.get("body_html", "")
        tags = product.get("tags", [])

        searchable = (
            f"{title} {description} "
            f"{product.get('product_type', '')} {' '.join(tags)}"
        ).lower()

        words = query.split()

        if query not in searchable and not all(
            word in searchable for word in words
        ):
            continue

        variants = product.get("variants", [])
        availability = [
            variant["available"]
            for variant in variants
            if isinstance(variant.get("available"), bool)
        ]

        if not availability:
            status = "Availability status not provided"
        elif any(availability):
            status = "Available for purchase"
        else:
            status = "Currently unavailable"

        handle = product.get("handle", "")
        link = (
            f"https://packitup.com.pk/products/{handle}"
            if handle
            else "https://packitup.com.pk/"
        )

        matches.append(f"- {title} | {status} | {link}")

        if len(matches) >= 5:
            break

    if not matches:
        return f"No matching products found for '{query}'."

    return "Product availability:\n" + "\n".join(matches)
def get_delivery_info_logic(city: str) -> str:
    city = city.strip()

    if not city:
        return "Please provide your delivery city."

    if city.lower() == "karachi":
        delivery = (
            "Standard delivery: 2–3 working days. "
            "Same-day express delivery may be available "
            "at an extra charge, subject to confirmation."
        )
    else:
        delivery = "Standard delivery: 3–5 working days."

    return (
        f"Delivery information for {city.title()}:\n"
        f"{delivery}\n"
        "Orders are usually processed within 24 hours "
        "after confirmation. Weekend and public-holiday "
        "orders are processed on the next working day.\n"
        "Shipping charges are calculated at checkout.\n"
        "Official policy: "
        "https://packitup.com.pk/policies/shipping-policy"
    )
def calculate_bulk_order_logic(product: str, quantity: int) -> str:
    product = product.strip().lower()

    if not product:
        return "Please provide a product name."

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return "Quantity must be a positive whole number."

    services = COMPANY_CONFIG.get("services", {})

    aliases = {
        "dessert box": "dessert boxes",
        "foil container": "foil containers",
        "packaging pouch": "pouches",
        "pouch": "pouches",
        "donut box": "bakery boxes",
        "ecommerce box": "ecommerce boxes",
    }

    product_key = aliases.get(product, product)
    selected = services.get(product_key)

    if selected is None:
        for key, item in services.items():
            if product == item.get("display_name", "").lower():
                selected = item
                break

    if selected is None:
        return "Product not found. Available products: " + ", ".join(services.keys())

    price = selected.get("starting_price_pkr")

    try:
        price = float(price)
    except (TypeError, ValueError):
        return "A valid starting price is not available for this product."

    if price <= 0:
        return "A valid starting price is not available for this product."

    total = price * quantity

    return (
        f"Product: {selected['display_name']}\n"
        f"Quantity: {quantity}\n"
        f"Starting price per listed unit: PKR {price:,.2f}\n"
        f"Estimated subtotal: PKR {total:,.2f}\n"
        "This is an estimate based on the configured starting price. "
        "Confirm pack size, actual product price, bulk discounts, "
        "and shipping charges before placing the order."
    )