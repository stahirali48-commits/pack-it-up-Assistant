from datetime import datetime
from pathlib import Path
import ast
import csv
import html
import json
import operator
import re
from urllib.request import Request, urlopen

from company_data import COMPANY_CONFIG

LEADS_FILE = Path("data") / "leads.csv"
LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)


# ---------------- COMPANY INFORMATION ----------------

def get_company_information_logic(topic: str = "general") -> str:
    topic = (topic or "general").lower().strip()
    company = COMPANY_CONFIG

    if topic in {"general", "about", "company"}:
        return (
            f"Company Name: {company['company_name']}\n"
            f"About: {company['about']}\n"
            f"Location: {company['location']}\n"
            f"Working Hours: {company['working_hours']}\n"
            f"Email: {company['contact_email']}\n"
            f"Phone: {company['phone']}"
        )

    if topic in {"services", "service"}:
        lines = ["Official services:"]

        for service in company.get("services", {}).values():
            price = service.get("starting_price_pkr")

            price_text = (
                f"Starting from PKR {price:,.0f}"
                if isinstance(price, (int, float))
                else "Starting price not configured"
            )

            lines.append(
                f"- {service['display_name']}: "
                f"{service['description']} ({price_text})"
            )

        return "\n".join(lines)

    if topic in {"location", "address"}:
        return f"Our office is located in {company['location']}."

    if topic in {"hours", "working hours", "timing", "time"}:
        return f"Our working hours are {company['working_hours']}."

    if topic in {"contact", "email", "phone"}:
        return (
            f"Email: {company['contact_email']} | "
            f"Phone: {company['phone']}"
        )

    if topic in company.get("faqs", {}):
        return company["faqs"][topic]

    return (
        "I could not find that exact topic in official company data. "
        "Available topics: general, services, location, working hours, "
        "contact, payment, timeline, support."
    )


# ---------------- SERVICE PRICING ----------------

def normalize_service_name(service: str) -> str:
    service = " ".join(
        (service or "").lower().replace("-", " ").strip().split()
    )

    aliases = {
        "dessert box": "dessert boxes",
        "foil container": "foil containers",
        "aluminium foil container": "foil containers",
        "aluminum foil container": "foil containers",
        "pouch": "pouches",
        "packaging pouch": "pouches",
        "packaging pouches": "pouches",
        "bakery box": "bakery boxes",
        "donut box": "bakery boxes",
        "donut boxes": "bakery boxes",
        "ecommerce box": "ecommerce boxes",
        "e commerce box": "ecommerce boxes",
    }

    return aliases.get(service, service)


def get_service_price_logic(service: str) -> str:
    key = normalize_service_name(service)
    services = COMPANY_CONFIG.get("services", {})
    selected = services.get(key)

    if selected is None:
        return (
            "Service not found. Available services are: "
            + ", ".join(services)
            + "."
        )

    price = selected.get("starting_price_pkr")

    price_text = (
        f"starts from PKR {price:,.0f}"
        if isinstance(price, (int, float))
        else "has no configured starting price"
    )

    return (
        f"{selected['display_name']} {price_text}. "
        f"Description: {selected['description']}. "
        "This is a category starting price, not a confirmed price "
        "for every product variant or pack size."
    )


# ---------------- SAFE CALCULATOR ----------------

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(
        node.value, (int, float)
    ):
        return node.value

    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)

        operation = _ALLOWED_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Operator not allowed")

        return operation(left, right)

    if isinstance(node, ast.UnaryOp):
        operation = _ALLOWED_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Operator not allowed")

        return operation(_safe_eval(node.operand))

    raise ValueError("Only basic arithmetic is allowed")


def calculator_logic(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return str(round(result, 2))

    except Exception as exc:
        return f"Calculation error: {exc}"


# ---------------- SAVE CUSTOMER LEADS ----------------

def save_lead_logic(
    name: str,
    email: str,
    requirement: str
) -> str:

    name = name.strip()
    email = email.strip()
    requirement = requirement.strip()

    if not name or not email or not requirement:
        return (
            "Lead was not saved. Name, email and requirement "
            "are required."
        )

    file_exists = LEADS_FILE.exists()

    try:
        with LEADS_FILE.open(
            "a", newline="", encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "timestamp",
                    "name",
                    "email",
                    "requirement"
                ]
            )

            if not file_exists or LEADS_FILE.stat().st_size == 0:
                writer.writeheader()

            writer.writerow({
                "timestamp": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "name": name,
                "email": email,
                "requirement": requirement,
            })

    except OSError:
        return "Lead could not be saved due to a file/storage error."

    return (
        f"Lead saved successfully for {name} "
        f"with email {email}."
    )


# ---------------- PRODUCT CATALOG HELPERS ----------------

def _plain_catalog_text(value) -> str:
    """Convert catalog HTML to readable text."""

    text = html.unescape(
        re.sub(r"<[^>]*>", " ", str(value or ""))
    )

    return re.sub(r"\s+", " ", text).strip()


def _normalize_catalog_text(value) -> str:
    """Normalize different spellings of product dimensions."""

    text = _plain_catalog_text(value).lower()

    text = text.replace("×", " x ").replace("✕", " x ")

    text = re.sub(
        r"(\d)\s*x\s*(\d)",
        r"\1 x \2",
        text
    )

    text = re.sub(
        r"(?<=\d)(cm|mm|inches|inch|microns|micron)\b",
        r" \1",
        text
    )

    return text


def _catalog_tokens(value) -> list[str]:
    return re.findall(
        r"\d+(?:\.\d+)?|[a-z]+",
        _normalize_catalog_text(value)
    )


_QUERY_STOPWORDS = {
    "what", "is", "a", "an", "the", "for", "to", "and", "of",
    "me", "about", "tell", "please", "show", "find", "search",
    "product", "products", "details", "detail", "which", "my",
    "i", "need", "want", "you", "can", "do", "does", "it", "its",
    "kya", "kia", "hai", "hota", "hoti", "ka", "ki", "ke",
    "iska", "batao", "chahiye", "mujhe", "mere", "liye",
    "kaunsa", "konsa", "x", "mean", "means", "size", "sizes",
    "material", "materials", "use", "uses", "used", "price",
    "prices", "cost", "costs", "how", "much", "available",
    "availability", "option", "options", "variant", "variants",
    "specification", "specifications", "thickness", "describe",
    "suitable", "recommend", "recommendation", "cm", "mm",
    "inch", "inches", "aur", "bhi", "kaun", "kis", "karna",
    "batana", "bata",
}

_SYNONYM_GROUPS = [
    {"kabara", "kabra", "kabari", "garbage", "trash", "waste"},
    {"pouch", "pouches"},
    {"bag", "bags"},
    {"box", "boxes"},
    {"aluminium", "aluminum"},
]


def _query_term_groups(query: str) -> list[set[str]]:
    terms = [
        word
        for word in _catalog_tokens(query)
        if word not in _QUERY_STOPWORDS
    ]

    groups = []

    for term in terms:
        group = next(
            (
                synonyms
                for synonyms in _SYNONYM_GROUPS
                if term in synonyms
            ),
            {term}
        )

        if group not in groups:
            groups.append(group)

    return groups


def _variant_search_text(product: dict, variant: dict) -> str:
    parts = [variant.get("title", "")]

    for index, option in enumerate(
        product.get("options", []) or [],
        start=1
    ):
        value = variant.get(f"option{index}")

        if value and str(value).strip().lower() != "default title":
            option_name = (
                option.get("name", "")
                if isinstance(option, dict)
                else ""
            )

            parts.extend([option_name, value])

    return " ".join(str(part) for part in parts if part)


def _product_search_text(product: dict) -> str:
    tags = product.get("tags", []) or []

    if isinstance(tags, (list, tuple)):
        tags_text = " ".join(map(str, tags))
    else:
        tags_text = str(tags)

    variants_text = " ".join(
        _variant_search_text(product, variant)
        for variant in (product.get("variants", []) or [])
    )

    return " ".join([
        str(product.get("title", "")),
        _plain_catalog_text(product.get("body_html", "")),
        str(product.get("product_type", "")),
        tags_text,
        variants_text,
    ])


def _product_matches_query(product: dict, query: str) -> bool:
    groups = _query_term_groups(query)

    if not groups:
        return False

    catalog_words = set(
        _catalog_tokens(_product_search_text(product))
    )

    return all(
        any(candidate in catalog_words for candidate in group)
        for group in groups
    )


def _fetch_public_catalog() -> dict:
    """
    Fetch the public Shopify catalog.
    This endpoint returns up to 250 products per request.
    """

    url = "https://packitup.com.pk/products.json?limit=250"

    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(request, timeout=10) as response:
        return json.load(response)


def _requested_dimensions(query: str):
    normalized = _normalize_catalog_text(query)

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)"
        r"(?:\s*(cm|mm|inches|inch|in))?\b",
        normalized
    )

    if not match:
        return set(), None

    return (
        {match.group(1), match.group(2)},
        match.group(3)
    )


def _variant_price_text(variant: dict) -> str:
    try:
        price = float(variant.get("price"))

        if price >= 0:
            return f"PKR {price:,.2f} (catalog-listed price)"

    except (TypeError, ValueError):
        pass

    return "Price not listed in catalog response"


def _variant_availability_text(variant: dict) -> str:
    available = variant.get("available")

    if available is True:
        return "Website purchase flag: available"

    if available is False:
        return "Website purchase flag: unavailable"

    return "Availability status not provided"


# ---------------- PRODUCT SEARCH ----------------

def search_products_logic(
    query: str,
    limit: int = 5
) -> str:
    """
    Search the live catalog by product name, description,
    tags, sizes, variants and listed prices.
    """

    if not isinstance(query, str) or not query.strip():
        return (
            "Please enter a product name, size, material, "
            "or search term."
        )

    try:
        catalog = _fetch_public_catalog()

    except Exception:
        return (
            "I could not access the live product catalog, so "
            "product details and prices cannot be verified right now. "
            "Please visit https://packitup.com.pk/"
        )

    requested_sizes, requested_unit = _requested_dimensions(query)
    matched_products = []

    for product in catalog.get("products", []):

        if not _product_matches_query(product, query):
            continue

        title = _plain_catalog_text(
            product.get("title", "Untitled product")
        )

        description = _plain_catalog_text(
            product.get("body_html", "")
        )

        variants = product.get("variants", []) or []
        variant_lines = []

        for variant in variants:
            variant_text = _variant_search_text(product, variant)
            tokens = set(_catalog_tokens(variant_text))

            if (
                requested_sizes
                and not requested_sizes.issubset(tokens)
            ):
                continue

            if requested_unit and requested_unit not in tokens:
                continue

            variant_title = _plain_catalog_text(
                variant.get("title", "")
            )

            if (
                not variant_title
                or variant_title.lower() == "default title"
            ):
                variant_title = variant_text or "Unnamed variant"

            variant_lines.append(
                f"  - {variant_title} | "
                f"{_variant_price_text(variant)} | "
                f"{_variant_availability_text(variant)}"
            )

        if requested_sizes and not variant_lines:
            variant_block = (
                "Exact matching size variant was not confirmed "
                "in the catalog response. Do not assume this product "
                "is available in the requested dimensions."
            )

        elif variant_lines:
            variant_block = (
                "Listed variants:\n"
                + "\n".join(variant_lines[:10])
            )

        else:
            variant_block = (
                "Variant details are not provided "
                "in the catalog response."
            )

        if len(description) > 700:
            description = description[:697].rstrip() + "..."

        product_link = (
            f"https://packitup.com.pk/products/{product.get('handle')}"
            if product.get("handle")
            else "https://packitup.com.pk/"
        )

        details = (
            description
            or "Description not provided in the catalog response."
        )

        output = (
            f"- {title}\n"
            f"Description: {details}\n"
            f"{variant_block}\n"
            f"Product page: {product_link}"
        )

        groups = _query_term_groups(query)

        title_words = set(_catalog_tokens(title))

        variant_words = set(
            _catalog_tokens(
                " ".join(
                    _variant_search_text(product, variant)
                    for variant in variants
                )
            )
        )

        score = sum(
            3 if group.intersection(title_words)
            else 2 if group.intersection(variant_words)
            else 1
            for group in groups
        )

        matched_products.append((score, output))

    if not matched_products:
        return (
            f"No matching catalog products were found for '{query}'. "
            "The catalog may use a different product name or size format."
        )

    matched_products.sort(
        key=lambda item: item[0],
        reverse=True
    )

    try:
        result_limit = max(1, min(int(limit), 10))

    except (TypeError, ValueError):
        result_limit = 5

    return (
        "Matching products from the live catalog:\n\n"
        + "\n\n".join(
            text for _, text in matched_products[:result_limit]
        )
    )


# ---------------- PRODUCT AVAILABILITY ----------------

def check_stock_logic(query: str) -> str:
    """
    Check public catalog availability flags.
    This does not return physical stock counts.
    """

    if not isinstance(query, str) or not query.strip():
        return "Please enter a product name or size."

    try:
        catalog = _fetch_public_catalog()

    except Exception:
        return (
            "Could not retrieve product availability. "
            "Please check https://packitup.com.pk/"
        )

    requested_sizes, requested_unit = _requested_dimensions(query)
    matches = []

    for product in catalog.get("products", []):

        if not _product_matches_query(product, query):
            continue

        relevant_variants = []

        for variant in product.get("variants", []) or []:
            tokens = set(
                _catalog_tokens(
                    _variant_search_text(product, variant)
                )
            )

            if (
                requested_sizes
                and not requested_sizes.issubset(tokens)
            ):
                continue

            if requested_unit and requested_unit not in tokens:
                continue

            relevant_variants.append(variant)

        title = _plain_catalog_text(
            product.get("title", "Untitled product")
        )

        link = (
            f"https://packitup.com.pk/products/{product.get('handle')}"
            if product.get("handle")
            else "https://packitup.com.pk/"
        )

        if requested_sizes and not relevant_variants:
            status = (
                "Exact requested size variant not confirmed; "
                "availability for this size cannot be verified"
            )

        else:
            flags = [
                variant.get("available")
                for variant in relevant_variants
                if isinstance(variant.get("available"), bool)
            ]

            if not flags:
                status = "Availability status not provided"

            elif any(flags):
                status = (
                    "Available for purchase (catalog variant flag)"
                )

            else:
                status = (
                    "Currently unavailable (catalog variant flag)"
                )

        matches.append(f"- {title} | {status} | {link}")

        if len(matches) >= 5:
            break

    if not matches:
        return f"No matching products were found for '{query}'."

    return (
        "Product availability from the catalog:\n"
        + "\n".join(matches)
    )


# ---------------- DELIVERY INFORMATION ----------------

def get_delivery_info_logic(city: str) -> str:
    city = (city or "").strip()

    if not city:
        return "Please provide your delivery city."

    if city.lower() == "karachi":
        delivery = (
            "Standard delivery: 2–3 working days. "
            "Same-day express delivery may be available at an extra "
            "charge, subject to confirmation."
        )

    else:
        delivery = "Standard delivery: 3–5 working days."

    return (
        f"Delivery information for {city.title()}:\n"
        f"{delivery}\n"
        "Orders are usually processed within 24 hours after confirmation. "
        "Weekend and public-holiday orders are processed on the next "
        "working day.\n"
        "Shipping charges are calculated at checkout.\n"
        "Official policy: "
        "https://packitup.com.pk/policies/shipping-policy"
    )


# ---------------- BULK ORDER ESTIMATE ----------------

def calculate_bulk_order_logic(
    product: str,
    quantity: int
) -> str:

    product = (product or "").strip().lower()

    if not product:
        return "Please provide a product name."

    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity <= 0
    ):
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

    key = aliases.get(product, product)
    selected = services.get(key)

    if selected is None:
        for item in services.values():
            if product == item.get("display_name", "").lower():
                selected = item
                break

    if selected is None:
        return (
            "Product/category not found. Available categories: "
            + ", ".join(services.keys())
        )

    try:
        price = float(selected.get("starting_price_pkr"))

    except (TypeError, ValueError):
        return (
            "A valid starting price is not configured for this category."
        )

    if price <= 0:
        return (
            "A valid starting price is not configured for this category."
        )

    total = price * quantity

    return (
        f"Category: {selected['display_name']}\n"
        f"Quantity: {quantity}\n"
        f"Configured starting price: PKR {price:,.2f}\n"
        f"Illustrative subtotal: PKR {total:,.2f}\n"
        "This is only an arithmetic estimate using the category "
        "starting price, not an official quotation. Confirm the "
        "product, pack size, actual unit price, bulk discounts, "
        "and shipping before ordering."
    )
