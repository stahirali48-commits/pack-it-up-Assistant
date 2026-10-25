
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


# ==================================================
# COMPANY INFORMATION
# ==================================================

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


# ==================================================
# SERVICE PRICING
# ==================================================

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


# ==================================================
# SAFE CALCULATOR
# ==================================================

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


# ==================================================
# SAVE CUSTOMER LEADS
# ==================================================

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
                    "requirement",
                ],
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
        return "Lead could not be saved due to a storage error."

    return f"Lead saved successfully for {name} with email {email}."


# ==================================================
# CATALOG TEXT NORMALIZATION
# ==================================================

def _plain_catalog_text(value) -> str:
    """Convert catalog HTML into readable text."""
    text = html.unescape(
        re.sub(r"<[^>]*>", " ", str(value or ""))
    )
    return re.sub(r"\s+", " ", text).strip()


def _normalize_catalog_text(value) -> str:
    """Normalize micron symbols, dimensions and units."""
    text = _plain_catalog_text(value).lower()

    # Treat Greek mu and micro sign as the word micron.
    text = text.replace("μm", " micron ")
    text = text.replace("µm", " micron ")

    # Normalize spelling variations.
    text = re.sub(r"\bmicrons?\b", "micron", text)
    text = re.sub(
        r"(?<=\d)\s*um\b",
        " micron",
        text
    )

    # Normalize dimensions, e.g. 14×20 and 14 x 20 cm.
    text = text.replace("×", " x ").replace("✕", " x ")
    text = re.sub(r"(\d)\s*x\s*(\d)", r"\1 x \2", text)

    text = re.sub(
        r"(?<=\d)(cm|mm|inches|inch|in)\b",
        r" \1",
        text
    )

    return re.sub(r"\s+", " ", text).strip()


def _catalog_tokens(value) -> list[str]:
    return re.findall(
        r"\d+(?:\.\d+)?|[a-z]+",
        _normalize_catalog_text(value)
    )


def _extract_micron_values(value: str) -> set[str]:
    """Extract explicit micron values from a catalog field."""
    text = _normalize_catalog_text(value)

    # Ignore comparison wording that is not an actual specification.
    text = re.sub(
        r"\b(?:stronger|thicker|heavier|better|more durable)"
        r"\s+than\b[^.;]{0,100}",
        " ",
        text,
    )

    values = set()

    for match in re.finditer(
        r"\b(\d+(?:\.\d+)?)\s*micron\b",
        text
    ):
        number = str(float(match.group(1))).rstrip("0").rstrip(".")
        values.add(number)

    return values


def _requested_micron(query: str):
    """Return an explicitly requested micron value, if supplied."""
    text = _normalize_catalog_text(query)

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*micron\b",
        text
    )

    if not match:
        return None

    return str(float(match.group(1))).rstrip("0").rstrip(".")


# ==================================================
# PRODUCT SEARCH HELPERS
# ==================================================

_QUERY_STOPWORDS = {
    "what", "is", "a", "an", "the", "for", "to", "and", "of",
    "me", "about", "tell", "please", "show", "find", "search",
    "product", "products", "details", "detail", "size", "sizes",
    "which", "my", "i", "need", "want", "you", "can", "do",
    "does", "it", "its", "kya", "kia", "hai", "hain", "he",
    "hota", "hoti", "ka", "ki", "ke", "iska", "is", "batao",
    "chahiye", "mujhe", "mere", "liye", "kaunsa", "konsa",
    "konsi", "kaunsi", "kon", "kaun", "sa", "si", "se", "wale",
    "wali", "wala", "bhi", "abhi", "karna", "batana", "bata",
    "do", "ye", "ya", "aur", "main", "mein", "kis", "kitne",
    "kitni", "material", "materials", "use", "uses", "used",
    "price", "prices", "cost", "costs", "how", "much", "available",
    "availability", "option", "options", "variant", "variants",
    "specification", "specifications", "thickness", "describe",
    "suitable", "recommend", "recommendation", "cm", "mm",
    "inch", "inches", "micron", "microns", "um", "x",
    "tamam", "naam", "bata", "kar", "karke",
}

_SYNONYM_GROUPS = [
    {"kabara", "kabra", "kabari", "garbage", "trash", "waste"},
    {"pouch", "pouches"},
    {"bag", "bags"},
    {"box", "boxes"},
    {"aluminium", "aluminum"},
    {"clear", "transparent"},
    {"golden", "gold"},
]


def _remove_specific_dimensions_and_micron(query: str) -> str:
    """Remove numeric constraints before matching product family words."""
    text = _normalize_catalog_text(query)

    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?"
        r"(?:\s*(?:cm|mm|inches|inch|in))?\b",
        " ",
        text,
    )

    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*micron\b",
        " ",
        text,
    )

    return re.sub(r"\s+", " ", text).strip()


def _query_term_groups(query: str) -> list[set[str]]:
    cleaned = _remove_specific_dimensions_and_micron(query)

    terms = [
        word
        for word in _catalog_tokens(cleaned)
        if word not in _QUERY_STOPWORDS and not word.isdigit()
    ]

    groups = []

    for term in terms:
        group = next(
            (
                synonyms
                for synonyms in _SYNONYM_GROUPS
                if term in synonyms
            ),
            {term},
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


def _product_fields(product: dict) -> dict[str, str]:
    tags = product.get("tags", []) or []

    if isinstance(tags, (list, tuple)):
        tags_text = " ".join(map(str, tags))
    else:
        tags_text = str(tags)

    variants_text = " ".join(
        _variant_search_text(product, variant)
        for variant in (product.get("variants", []) or [])
    )

    return {
        "title": str(product.get("title", "")),
        "description": _plain_catalog_text(
            product.get("body_html", "")
        ),
        "tags": tags_text,
        "product_type": str(product.get("product_type", "")),
        "variants": variants_text,
    }


def _product_search_text(product: dict) -> str:
    return " ".join(_product_fields(product).values())


def _product_micron_status(
    product: dict
) -> tuple[set[str], bool, str]:
    """
    Check product thickness.

    Title and description take priority over tags. If the title and
    description conflict, report the conflict instead of guessing.
    Tags cannot override an explicit product specification.
    """
    fields = _product_fields(product)

    title_values = _extract_micron_values(fields["title"])
    description_values = _extract_micron_values(fields["description"])
    tag_values = _extract_micron_values(fields["tags"])
    type_values = _extract_micron_values(fields["product_type"])
    variant_values = _extract_micron_values(fields["variants"])

    primary_values = title_values | description_values

    if len(primary_values) > 1:
        title_text = (
            ", ".join(sorted(title_values))
            if title_values else "not specified"
        )
        description_text = (
            ", ".join(sorted(description_values))
            if description_values else "not specified"
        )

        note = (
            "The catalog has conflicting micron specifications. "
            f"Title: {title_text}. Description: {description_text}. "
            "Do not present this as a confirmed thickness match."
        )

        return primary_values, True, note

    # Critical: tags cannot override the explicit title/description.
    if primary_values:
        return primary_values, False, ""

    # Only use metadata when no actual specification is available.
    fallback_values = tag_values | type_values

    if not fallback_values:
        fallback_values = variant_values

    return fallback_values, False, ""


def _product_matches_query(product: dict, query: str) -> bool:
    groups = _query_term_groups(query)

    # A query such as "160 micron" is a valid thickness-only search.
    if not groups:
        return True

    catalog_words = set(
        _catalog_tokens(_product_search_text(product))
    )

    return all(
        any(candidate in catalog_words for candidate in group)
        for group in groups
    )


def _requested_dimensions(query: str):
    text = _normalize_catalog_text(query)

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)"
        r"(?:\s*(cm|mm|inches|inch|in))?\b",
        text,
    )

    if not match:
        return set(), None

    return (
        {match.group(1), match.group(2)},
        match.group(3),
    )


def _dimension_is_in_product(product: dict, dimensions: set[str]) -> bool:
    if not dimensions:
        return True

    tokens = set(_catalog_tokens(_product_search_text(product)))
    return dimensions.issubset(tokens)


def _product_dimension_variants(
    product: dict,
    requested_dimensions: set[str],
    requested_unit: str | None,
):
    """Return exact dimension variants only when dimensions occur there."""
    variant_data = []

    for variant in (product.get("variants", []) or []):
        variant_text = _variant_search_text(product, variant)
        variant_tokens = set(_catalog_tokens(variant_text))

        if requested_dimensions:
            if not requested_dimensions.issubset(variant_tokens):
                continue

            if requested_unit and requested_unit not in variant_tokens:
                continue

        variant_data.append((variant, variant_text))

    return variant_data


# ==================================================
# FETCH THE PUBLIC PRODUCT CATALOG
# ==================================================

def _fetch_public_catalog() -> dict:
    """
    Fetch up to 250 products from the public Shopify endpoint.
    For a store with 187 published products, this limit may be sufficient
    if the endpoint returns all published products.
    """
    url = "https://packitup.com.pk/products.json?limit=250"

    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    with urlopen(request, timeout=10) as response:
        return json.load(response)


def _variant_price_text(variant: dict) -> str:
    try:
        price = float(variant.get("price"))

        if price >= 0:
            return f"PKR {price:,.2f}"

    except (TypeError, ValueError):
        pass

    return "Price not listed in catalog response"


def _variant_availability_text(variant: dict) -> str:
    available = variant.get("available")

    if available is True:
        return "Available for purchase"

    if available is False:
        return "Unavailable for purchase"

    return "Availability not provided by the catalog"


# ==================================================
# PRODUCT SEARCH
# ==================================================

def search_products_logic(query: str, limit: int = 10) -> str:
    """
    Search products by name, dimensions and micron.
    Do not mix conflicting thicknesses or invent prices.
    """
    if not isinstance(query, str) or not query.strip():
        return "Please enter a product name, size, material, or micron."

    try:
        catalog = _fetch_public_catalog()

    except Exception:
        return (
            "The live product catalog could not be accessed, so product "
            "details and prices cannot be verified right now. "
            "Please visit https://packitup.com.pk/"
        )

    requested_micron = _requested_micron(query)
    dimensions, requested_unit = _requested_dimensions(query)

    matched_products = []
    conflicts = []

    for product in catalog.get("products", []):
        if not _product_matches_query(product, query):
            continue

        title = _plain_catalog_text(
            product.get("title", "Untitled product")
        )

        description = _plain_catalog_text(
            product.get("body_html", "")
        )

        micron_values, has_conflict, conflict_note = (
            _product_micron_status(product)
        )

        if requested_micron:
            if has_conflict:
                conflicts.append(f"- {title}: {conflict_note}")
                continue

            if requested_micron not in micron_values:
                continue

        if dimensions and not _dimension_is_in_product(product, dimensions):
            continue

        variants = product.get("variants", []) or []

        # If size is encoded in variant options, filter to that exact size.
        # If the product description lists a size but variant data doesn't
        # map prices to size, do not pretend the price is size-specific.
        size_variants = _product_dimension_variants(
            product,
            dimensions,
            requested_unit,
        )

        if dimensions and size_variants:
            selected_variants = size_variants
            size_price_note = ""
        elif dimensions:
            selected_variants = []
            size_price_note = (
                "The requested size appears in the product text, but the "
                "catalog does not map a price or stock flag to that exact "
                "size variant. Confirm the exact variant before quoting."
            )
        else:
            selected_variants = [
                (variant, _variant_search_text(product, variant))
                for variant in variants
            ]
            size_price_note = ""

        variant_lines = []

        for variant, variant_text in selected_variants[:10]:
            variant_title = _plain_catalog_text(
                variant.get("title", "")
            )

            if (
                not variant_title
                or variant_title.lower() == "default title"
            ):
                variant_title = (
                    _plain_catalog_text(variant_text)
                    or "Unnamed variant"
                )

            variant_lines.append(
                f"  - {variant_title} | "
                f"{_variant_price_text(variant)} | "
                f"{_variant_availability_text(variant)}"
            )

        if variant_lines:
            variant_block = (
                "Catalog variant results:\n"
                + "\n".join(variant_lines)
            )
        else:
            variant_block = (
                "No exact size-specific price or stock record "
                "was confirmed by the catalog."
            )

        if size_price_note:
            variant_block += "\n" + size_price_note

        thickness_line = (
            "Catalog thickness: "
            + ", ".join(sorted(micron_values))
            + " micron"
            if micron_values
            else "Thickness is not explicitly confirmed in the catalog."
        )

        if len(description) > 900:
            description = description[:897].rstrip() + "..."

        handle = product.get("handle", "")
        link = (
            f"https://packitup.com.pk/products/{handle}"
            if handle else "https://packitup.com.pk/"
        )

        fields = _product_fields(product)
        title_words = set(_catalog_tokens(title))
        variant_words = set(_catalog_tokens(fields["variants"]))
        groups = _query_term_groups(query)

        score = sum(
            3 if group.intersection(title_words)
            else 2 if group.intersection(variant_words)
            else 1
            for group in groups
        )

        matched_products.append((
            score,
            (
                f"Product: {title}\n"
                f"Description: "
                f"{description or 'Not provided in catalog'}\n"
                f"{thickness_line}\n"
                f"{variant_block}\n"
                f"Product page: {link}"
            ),
        ))

    if not matched_products and not conflicts:
        return (
            f"No exact catalog match was found for '{query}'. "
            "The requested micron, size, or product specification may "
            "not be explicitly recorded in the public catalog. Do not guess."
        )

    matched_products.sort(key=lambda item: item[0], reverse=True)

    try:
        result_limit = max(1, min(int(limit), 20))
    except (TypeError, ValueError):
        result_limit = 10

    output = []

    if conflicts:
        output.append(
            "CATALOG SPECIFICATION CONFLICTS — NOT CONFIRMED MATCHES:\n"
            + "\n".join(dict.fromkeys(conflicts))
        )

    if matched_products:
        output.append(
            "CATALOG PRODUCT MATCHES:\n\n"
            + "\n\n".join(
                text for _, text in matched_products[:result_limit]
            )
        )

    return "\n\n".join(output)


# ==================================================
# PRODUCT AVAILABILITY
# ==================================================

def check_stock_logic(query: str) -> str:
    """Check catalog purchase flags for relevant products and variants."""
    if not isinstance(query, str) or not query.strip():
        return "Please enter a product name, size, or micron."

    try:
        catalog = _fetch_public_catalog()

    except Exception:
        return (
            "Product availability could not be retrieved. "
            "Please check https://packitup.com.pk/"
        )

    requested_micron = _requested_micron(query)
    dimensions, requested_unit = _requested_dimensions(query)

    matches = []
    conflicts = []

    for product in catalog.get("products", []):
        if not _product_matches_query(product, query):
            continue

        title = _plain_catalog_text(
            product.get("title", "Untitled product")
        )

        micron_values, has_conflict, conflict_note = (
            _product_micron_status(product)
        )

        if requested_micron:
            if has_conflict:
                conflicts.append(f"- {title}: {conflict_note}")
                continue

            if requested_micron not in micron_values:
                continue

        if dimensions and not _dimension_is_in_product(product, dimensions):
            continue

        variants = product.get("variants", []) or []

        size_variants = _product_dimension_variants(
            product,
            dimensions,
            requested_unit,
        )

        if dimensions and size_variants:
            selected_variants = size_variants
            size_note = ""
        elif dimensions:
            selected_variants = []
            size_note = (
                "The size appears in the product text, but the catalog "
                "does not associate a stock flag with that exact size."
            )
        else:
            selected_variants = [
                (variant, _variant_search_text(product, variant))
                for variant in variants
            ]
            size_note = ""

        flags = [
            variant.get("available")
            for variant, _ in selected_variants
            if isinstance(variant.get("available"), bool)
        ]

        if not selected_variants and dimensions:
            status = "Exact size availability is not confirmed"
        elif not flags:
            status = "Availability status not provided by catalog"
        elif any(flags):
            status = "At least one matching variant is available"
        else:
            status = "All matching variants are marked unavailable"

        variant_lines = []

        for variant, variant_text in selected_variants[:10]:
            label = _plain_catalog_text(variant.get("title", ""))

            if not label or label.lower() == "default title":
                label = (
                    _plain_catalog_text(variant_text)
                    or "Unnamed variant"
                )

            variant_lines.append(
                f"  - {label}: {_variant_availability_text(variant)}"
            )

        handle = product.get("handle", "")
        link = (
            f"https://packitup.com.pk/products/{handle}"
            if handle else "https://packitup.com.pk/"
        )

        lines = [f"- {title}: {status}"]

        if variant_lines:
            lines.extend(variant_lines)

        if size_note:
            lines.append(size_note)

        lines.append(f"  Product page: {link}")
        matches.append("\n".join(lines))

        if len(matches) >= 20:
            break

    output = []

    if conflicts:
        output.append(
            "CATALOG SPECIFICATION CONFLICTS — AVAILABILITY NOT CONFIRMED:\n"
            + "\n".join(dict.fromkeys(conflicts))
        )

    if matches:
        output.append(
            "Product availability from matching catalog records:\n"
            + "\n\n".join(matches)
        )

    if not output:
        return (
            f"No exact catalog match was found for '{query}'. "
            "Availability cannot be verified from the available catalog data."
        )

    return "\n\n".join(output)


# ==================================================
# DELIVERY INFORMATION
# ==================================================

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


# ==================================================
# BULK ORDER ESTIMATE
# ==================================================

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

    product_key = aliases.get(product, product)
    selected = services.get(product_key)

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
        f"Configured category starting price: PKR {price:,.2f}\n"
        f"Illustrative subtotal: PKR {total:,.2f}\n"
        "This is only an arithmetic estimate using the category "
        "starting price, not an official quotation. Confirm the exact "
        "product, pack size, actual unit price, bulk discounts, and "
        "shipping charges before ordering."
    )
