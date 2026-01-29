pricing_list = [
    {"start": 1, "end": 20, "price": 5_000, "m2": None, "currency": "TRY", "symbol": "₺"},
    {"start": 20, "end": 50, "price": 10_000, "m2": None, "currency": "TRY", "symbol": "₺"},
    {"start": 50, "end": 100, "price": 20_000, "m2": None, "currency": "TRY", "symbol": "₺"},
    {"start": 100, "end": 300, "price": None, "m2": 35, "currency": "TRY", "symbol": "₺"},
    {"start": 300, "end": float("inf"), "price": None, "m2": 30, "currency": "TRY", "symbol": "₺"},
]

pricing_materials = [
    "vert_220cm", "vert_120cm", "l_part", "triangle"
]

one_time_pricing_list = {
    "tie": {"price": 120, "currency": "TRY", "symbol": "₺"}
}

MATERIAL_M2 = 5

def _total_pricing_materials(material_list: dict) -> int:
    total = 0
    for material_name in material_list.keys():
        if not material_name in pricing_materials:
            continue

        count = material_list[material_name]
        total += count

    return total

def _total_one_time_pricing(material_list: dict) -> int:
    total = 0
    for material_name in one_time_pricing_list.keys():
        if not material_name in one_time_pricing_list.keys():
            continue

        count = material_list[material_name]
        total += count * one_time_pricing_list[material_name]["price"]

    return total

def calculate_price(material_list: dict):
    total_count = _total_pricing_materials(material_list)

    pricing_method = {}
    for pricing in pricing_list:
        if pricing["end"] > total_count:
            pricing_method = pricing
            break

    if not pricing_method:
        return -1, "-1", "-1"

    if pricing_method["price"]:
        return pricing_method["price"], pricing_method["currency"], pricing_method["symbol"]

    m2_price = pricing_method["m2"]
    total_price = 0
    for material_name in material_list.keys():
        if not material_name in pricing_materials:
            continue

        count = material_list[material_name]
        total_m2 = count * MATERIAL_M2
        price = total_m2 * m2_price

        total_price += price

    return total_price, pricing_method["currency"], pricing_method["symbol"]
