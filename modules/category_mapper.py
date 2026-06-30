"""Map a free-text item description to a store category (Phase 10)."""

from __future__ import annotations

# Ordered: the first category whose keyword is found wins.
CATEGORY_KEYWORDS = [
    ("Charges", [
        "packing and handling", "freight", "handling charge", "transport charge",
    ]),
    ("Electrical Store", [
        "tape", "cable", "battery", "volt", "electrical", "insulation",
        "flashlight", "led", "wire", "fuse", "lamp", "bulb", "socket",
    ]),
    ("Galley Store", [
        "spoon", "plate", "mug", "bowl", "cooking", "galley", "hot plate",
        "fork", "knife", "tumbler", "cup", "saucer", "pot ", "pan", "grater",
        "oven", "kitchen", "ladle", "cutlery", "tray", "jug", "whisk", "scoop",
    ]),
    ("Safety Store", [
        "gloves", "eyewear", "immersion", "safety", "face shield", "helmet",
        "goggle", "lifejacket", "life jacket", "fire", "respirator", "ear muff",
    ]),
    ("Deck Store", [
        "rope", "shackle", "ladder", "grinder", "wrench", "hammer", "chisel",
        "welding", "paint", "brush", "scraper", "pliers", "screwdriver",
        "spanner", "drill",
    ]),
    ("Cleaning / Cabin Store", [
        "soap", "detergent", "garbage", "bag", "towel", "sheet", "pillow",
        "blanket", "cleanser", "bleach", "wax", "napkin", "tissue", "curtain",
        "duvet", "mattress", "cloth", "mop", "broom", "sponge",
    ]),
    ("Engine Store", [
        "pump", "motor", "valve", "bearing", "o-ring", "gasket", "filter",
        "seal", "piston", "injector", "compressor",
    ]),
]

DEFAULT_CATEGORY = "Others"


def map_category(description) -> str:
    """Return the best-guess store category for a description, or 'Others'."""
    if not description:
        return DEFAULT_CATEGORY
    d = str(description).lower()
    for category, keywords in CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in d:
                return category
    return DEFAULT_CATEGORY
