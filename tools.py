
from decimal import Decimal, InvalidOperation

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


# --------------------------------------------------
# Shared helper: search the existing product catalog
# --------------------------------------------------

def _lookup_products(query: str) -> str:
    """Retrieve existing catalog data without inventing product facts."""
    if not isinstance(query, str) or not query.strip():
        return "Please provide a product name, size, material, or search term."

    try:
        result = search_products_logic(query.strip())
    except Exception:
        return (
            "Product catalog lookup failed. Product details, prices, "
            "and availability could not be verified."
        )

    if result is None or not str(result).strip():
        return f"No product information was returned for: {query}"

    return str(result)


# --------------------------------------------------
# EXISTING TOOLS: preserved
# --------------------------------------------------

@tool
def get_company_information(topic: str = "general") -> str:
    """Get official company information, contact details, policies,
    location, working hours, payment, and support information."""
    return get_company_information_logic(topic)


@tool
def get_service_price(service: str) -> str:
    """Get the official starting price for a company service.
    Use for service prices, quotations, costs, and budgets."""
    return get_service_price_logic(service)


@tool
def calculator(expression: str) -> str:
    """Calculate arithmetic expressions, percentages, discounts,
    and totals. Example: 2000 - (2000 * 0.15)."""
    return calculator_logic(expression)


@tool
def save_lead(name: str, email: str, requirement: str) -> str:
    """Save a customer lead only when name, email, and requirement
    are available. Confirm success only if saving succeeds."""
    return save_lead_logic(name, email, requirement)


@tool
def search_products(query: str) -> str:
    """Search the existing Pack It Up catalog by product name,
    size, material, or relevant search terms."""
    return _lookup_products(query)


@tool
def check_product_availability(query: str) -> str:
    """Check product availability using the existing stock system.
    Never infer stock status from a product search result."""
    return check_stock_logic(query)


@tool
def get_delivery_information(city: str) -> str:
    """Retrieve official delivery information for a specified city."""
    return get_delivery_info_logic(city)


# --------------------------------------------------
# NEW TOOL 1: PRODUCT DETAILS
# --------------------------------------------------

@tool
def get_product_details(query: str) -> str:
    """Find catalog details for a specific packaging product.
    Use for sizes, materials, thickness, dimensions, features,
    product variants, and listed prices. Return only retrieved data."""
    return _lookup_products(query)


# --------------------------------------------------
# NEW TOOL 2: COMPARE PRODUCTS
# --------------------------------------------------

@tool
def compare_products(product_a: str, product_b: str) -> str:
    """Look up two products separately so their returned catalog
    details can be compared. Do not assume missing specifications
    are equal or invent missing prices."""
    details_a = _lookup_products(product_a)
    details_b = _lookup_products(product_b)

    return (
        f"PRODUCT A: {product_a}\n"
        f"CATALOG RESULTS:\n{details_a}\n\n"
        f"PRODUCT B: {product_b}\n"
        f"CATALOG RESULTS:\n{details_b}\n\n"
        "Compare only specifications explicitly present in these results. "
        "State when a comparison detail is unavailable."
    )


# --------------------------------------------------
# NEW TOOL 3: BULK PRICE CALCULATOR
# --------------------------------------------------

@tool
def calculate_bulk_price(
    verified_unit_price: float,
    quantity: int,
) -> str:
    """Calculate a bulk subtotal using a verified unit price.
    Call ONLY when the price has been explicitly returned by an
    authoritative catalog/tool result or provided by the customer.
    Quantity must use the same unit basis as the price, for example
    pouches when the price is per pouch. This is not a quotation."""
    try:
        price = Decimal(str(verified_unit_price))
    except (InvalidOperation, ValueError):
        return "Invalid unit price. Please provide a valid numeric price."

    if not price.is_finite() or price < 0:
        return "Unit price must be a valid, non-negative number."

    if isinstance(quantity, bool) or quantity <= 0:
        return "Quantity must be a positive whole number."

    total = price * quantity

    return (
        f"Calculated subtotal: {total:,.2f}\n"
        f"Calculation: {price:,.2f} × {quantity:,}\n"
        "Currency is the same as the verified unit price. "
        "This subtotal excludes unverified discounts, taxes, "
        "shipping, printing fees, and other charges. "
        "It is not an official quotation."
    )


# --------------------------------------------------
# NEW TOOL 4: SMART PACKAGING RECOMMENDATION
# --------------------------------------------------

@tool
def recommend_packaging(
    product_to_pack: str,
    intended_use: str,
    requirements: str = "",
) -> str:
    """Find catalog options relevant to a customer's packaging need.
    Consider the product being packed, intended use, and stated
    requirements. This tool searches catalog data; it does not
    guarantee suitability, food safety, stock, or certification."""
    query = (
        f"{product_to_pack} {intended_use} {requirements}"
    ).strip()

    results = _lookup_products(query)

    return (
        f"Customer's product: {product_to_pack}\n"
        f"Intended use: {intended_use}\n"
        f"Requirements: {requirements or 'Not specified'}\n\n"
        f"RETRIEVED CATALOG RESULTS:\n{results}\n\n"
        "Recommend only options supported by the retrieved data. "
        "Ask follow-up questions when size, material, or application "
        "requirements are insufficient."
    )


# --------------------------------------------------
# NEW TOOL 5: PACKAGING MATERIAL GUIDE
# --------------------------------------------------

@tool
def get_packaging_material_guide(material_or_need: str) -> str:
    """Explain common packaging materials in general terms and
    search the catalog for relevant products. General information
    does not confirm that a material or product is sold by the company."""
    topic = material_or_need.lower()

    general_guidance = {
        "ldpe": (
            "LDPE is a flexible polyethylene plastic commonly used "
            "for bags and flexible packaging. Exact properties depend "
            "on the product specification."
        ),
        "bopp": (
            "BOPP is oriented polypropylene film often used for "
            "clear or printed packaging. The complete packaging "
            "structure determines its actual performance."
        ),
        "kraft": (
            "Kraft refers to a type of paper commonly used in bags "
            "and paper packaging. Strength and suitability depend "
            "on paper grade, construction, and any coating."
        ),
        "foil": (
            "Foil-based packaging may use a multi-layer laminate "
            "for barrier performance. The exact laminate structure "
            "must be checked for the intended application."
        ),
        "gsm": (
            "GSM means grams per square metre. It measures material "
            "mass per area and is commonly used for paper. GSM is "
            "not directly interchangeable with plastic thickness in microns."
        ),
        "micron": (
            "A micron is one-millionth of a metre. For film, 1 micron "
            "equals 0.001 mm. Check the supplier's specification to "
            "understand which layer or total structure the value describes."
        ),
    }

    explanations = [
        explanation
        for keyword, explanation in general_guidance.items()
        if keyword in topic
    ]

    general_text = (
        "\n".join(explanations)
        if explanations
        else (
            "Material suitability depends on the product being packed, "
            "required barrier properties, thickness, sealing, and use case. "
            "More specific requirements may be needed."
        )
    )

    catalog_results = _lookup_products(material_or_need)

    return (
        "GENERAL MATERIAL GUIDE (not a product specification):\n"
        f"{general_text}\n\n"
        f"CATALOG SEARCH RESULTS:\n{catalog_results}\n\n"
        "Do not infer food-grade status, certifications, exact thickness, "
        "or availability unless supported by verified product information."
    )


# --------------------------------------------------
# NEW TOOL 6: DIMENSION CONVERTER
# --------------------------------------------------

_UNIT_TO_MM = {
    "mm": Decimal("1"),
    "millimeter": Decimal("1"),
    "millimeters": Decimal("1"),
    "cm": Decimal("10"),
    "centimeter": Decimal("10"),
    "centimeters": Decimal("10"),
    "m": Decimal("1000"),
    "meter": Decimal("1000"),
    "meters": Decimal("1000"),
    "in": Decimal("25.4"),
    "inch": Decimal("25.4"),
    "inches": Decimal("25.4"),
}


@tool
def convert_packaging_dimensions(
    width: float,
    height: float,
    from_unit: str,
    to_unit: str,
) -> str:
    """Convert known width and height values between mm, cm, metres,
    and inches. Use only when the source unit is known. This tool
    converts measurements and does not verify product dimensions."""
    source = from_unit.strip().lower()
    target = to_unit.strip().lower()

    if source not in _UNIT_TO_MM:
        return "Unsupported source unit. Use mm, cm, m, or inches."

    if target not in _UNIT_TO_MM:
        return "Unsupported target unit. Use mm, cm, m, or inches."

    try:
        w = Decimal(str(width))
        h = Decimal(str(height))
    except (InvalidOperation, ValueError):
        return "Width and height must be valid numeric measurements."

    if (
        not w.is_finite()
        or not h.is_finite()
        or w <= 0
        or h <= 0
    ):
        return "Width and height must be positive, finite numbers."

    width_mm = w * _UNIT_TO_MM[source]
    height_mm = h * _UNIT_TO_MM[source]

    converted_width = width_mm / _UNIT_TO_MM[target]
    converted_height = height_mm / _UNIT_TO_MM[target]

    return (
        f"Original dimensions: {w} × {h} {source}\n"
        f"Converted dimensions: "
        f"{converted_width:.2f} × {converted_height:.2f} {target}\n"
        "This is a mathematical unit conversion, not confirmation "
        "of a catalog product's dimensions."
    )


# --------------------------------------------------
# NEW TOOL 7: PACKAGING TERMINOLOGY
# --------------------------------------------------

@tool
def explain_packaging_term(term: str) -> str:
    """Explain common packaging terms such as micron, GSM, gusset,
    zipper pouch, stand-up pouch, flat pouch, and laminate.
    This is general educational guidance, not a product specification."""
    topic = term.strip().lower()

    definitions = {
        "micron": (
            "A micron is a unit of length equal to 0.001 mm. "
            "It is commonly used to express plastic film thickness."
        ),
        "gsm": (
            "GSM means grams per square metre. It describes material "
            "mass per area and is commonly used for paper."
        ),
        "gusset": (
            "A gusset is an added fold or panel that can provide "
            "extra depth or capacity to a bag or pouch."
        ),
        "zipper": (
            "A zipper pouch has a reclosable closure. Actual sealing "
            "and barrier performance depend on its design and material."
        ),
        "stand-up pouch": (
            "A stand-up pouch is designed with a base or gusset that "
            "allows it to stand when filled, depending on construction."
        ),
        "flat pouch": (
            "A flat pouch is generally a flat-format bag without "
            "a stand-up base. Exact construction depends on the product."
        ),
        "laminate": (
            "A laminate combines layers of material to achieve "
            "specific properties. Its performance depends on the layers "
            "and their construction."
        ),
    }

    for keyword, definition in definitions.items():
        if keyword in topic:
            return (
                f"{keyword.title()}: {definition}\n"
                "For exact Pack It Up product specifications, "
                "check the relevant catalog listing."
            )

    return (
        f"No specific explanation is configured for '{term}'. "
        "Please check the relevant product specification or provide "
        "more context."
    )


# --------------------------------------------------
# REGISTER ALL TOOLS
# --------------------------------------------------

tools = [
    # Existing tools
    get_company_information,
    get_service_price,
    calculator,
    save_lead,
    search_products,
    check_product_availability,
    get_delivery_information,

    # New tools
    get_product_details,
    compare_products,
    calculate_bulk_price,
    recommend_packaging,
    get_packaging_material_guide,
    convert_packaging_dimensions,
    explain_packaging_term,
]
