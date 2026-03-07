#!/usr/bin/env python3
"""
解析 International Tables of GI/GL Values 2021 (Supplemental Table 1) v2
基于 pdftotext 的行号关联策略: 找到每个 GI±SEM 行，回溯找食物名。
"""
import re
import json
import csv

INPUT = "GI_Tables_2021_raw.txt"
OUTPUT_JSON = "gi_tables_2021.json"
OUTPUT_CSV = "gi_tables_2021.csv"

CATEGORIES = {
    "BAKERY PRODUCTS": "Bakery Products",
    "BEVERAGES": "Beverages",
    "BREADS": "Breads",
    "BREAKFAST CEREALS": "Breakfast Cereals",
    "CEREAL GRAINS": "Cereal Grains",
    "COOKIES": "Cookies",
    "CRACKERS": "Crackers",
    "DAIRY PRODUCTS": "Dairy Products",
    "FRUIT AND FRUIT": "Fruit",
    "INFANT FORMULA": "Infant Formula",
    "LEGUMES": "Legumes",
    "MEAL REPLACEMENT": "Meal Replacement",
    "NUTRITIONAL SUPPORT": "Nutritional Support",
    "NUTS": "Nuts",
    "PASTA AND NOODLES": "Pasta & Noodles",
    "SNACK FOODS": "Snack Foods",
    "SOUPS": "Soups",
    "SUGARS AND SYRUPS": "Sugars & Syrups",
    "VEGETABLES": "Vegetables",
    "REGIONAL OR TRADITIONAL": "Regional/Traditional Foods",
}

SKIP_LINES = {
    "GI2 ±", "SEM", "(Glu = 100)", "Supplemental Table",
    "Atkinson FS", "Online Supplemental", "Food Number",
    "Explanatory note", "Country of", "Year of", "Subjects",
    "Avail", "Timepoints", "Sample", "Reference", "Test",
    "Average available", "portion", "TABLE OF CONTENTS",
}


def parse():
    with open(INPUT, "r", encoding="utf-8") as f:
        lines = f.readlines()

    foods = []
    current_category = "Unknown"
    category_line_nums = {}

    # First pass: identify category positions
    for i, line in enumerate(lines):
        stripped = line.strip().upper()
        for key, name in CATEGORIES.items():
            if stripped.startswith(key):
                category_line_nums[i] = name

    # Second pass: find every GI±SEM pattern and backtrack to food name
    gi_pattern = re.compile(r'^(\d{1,3})\s*±\s*(\d{1,3})$')

    for i, line in enumerate(lines):
        stripped = line.strip()
        gi_match = gi_pattern.match(stripped)
        if not gi_match:
            continue

        gi_value = int(gi_match.group(1))
        gi_sem = int(gi_match.group(2))

        if gi_value < 5 or gi_value > 130:
            continue

        # Determine category: find the nearest category header above
        cat = "Unknown"
        for line_num in sorted(category_line_nums.keys(), reverse=True):
            if line_num < i:
                cat = category_line_nums[line_num]
                break

        # Look for GL value: next non-empty line after GI
        gl_value = None
        for j in range(i + 1, min(i + 3, len(lines))):
            gl_match = re.match(r'^(\d{1,2})$', lines[j].strip())
            if gl_match:
                gl_val = int(gl_match.group(1))
                if gl_val <= 60:
                    gl_value = gl_val
                    break

        # Backtrack to find food name: look for a line starting with a number (food ID)
        # then the food name follows
        food_name = None
        country = None
        for j in range(i - 1, max(i - 30, 0), -1):
            bline = lines[j].strip()

            # Skip known header/metadata lines
            skip = False
            for s in SKIP_LINES:
                if bline.startswith(s):
                    skip = True
                    break
            if skip or not bline:
                continue

            # Country line (standalone country name)
            if re.match(r'^(Australia|USA|Canada|UK|Sweden|Denmark|France|Germany|Italy|'
                       r'Japan|China|India|Philippines|Brazil|Mexico|South Africa|'
                       r'New Zealand|Belgium|Netherlands|Spain|Singapore|Malaysia|'
                       r'South Korea|Taiwan|Thailand|Indonesia|Sri Lanka|Pakistan|'
                       r'Norway|Finland|Ireland|Poland|Kenya|Nigeria|Turkey|Iran|Israel|'
                       r'Saudi Arabia|United Kingdom|Czech Republic|Hungary|'
                       r'Chile|Colombia|Peru|Lebanon|Jordan|Kuwait|Egypt|'
                       r'United States|Bangladesh|Fiji|Papua New Guinea)$',
                       bline, re.IGNORECASE):
                country = bline
                continue

            # Year line
            if re.match(r'^(19|20)\d{2}\*?$', bline):
                continue

            # Food ID + name pattern
            id_match = re.match(r'^(\d+)\s+(.+)', bline)
            if id_match:
                food_name = id_match.group(2).strip()
                break

            # If line looks like a food name continuation (has letters, not just numbers)
            if re.search(r'[a-zA-Z]{3,}', bline) and not re.match(r'^\d+$', bline):
                # Could be food name or continuation - take the first substantive text
                if len(bline) > 5:
                    food_name = bline
                    break

        if food_name and gi_value:
            # Clean up food name
            food_name = re.sub(r'\s*\([^)]*manufacturer[^)]*\)', '', food_name, flags=re.IGNORECASE)
            food_name = food_name.strip().rstrip(',').strip()

            if gi_value <= 55:
                gi_level = "Low"
            elif gi_value <= 69:
                gi_level = "Medium"
            else:
                gi_level = "High"

            foods.append({
                "food_name": food_name,
                "gi_value": gi_value,
                "gi_sem": gi_sem,
                "gl_value": gl_value,
                "gi_level": gi_level,
                "category": cat,
                "country": country,
            })

    return foods


def deduplicate(foods):
    seen = set()
    unique = []
    for f in foods:
        key = (f["food_name"].lower()[:50], f["gi_value"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def main():
    print(f"[INFO] Parsing {INPUT} (v2 backtrack strategy)...")
    foods = parse()
    foods = deduplicate(foods)
    foods.sort(key=lambda x: (x["category"], x["gi_value"]))

    for i, f in enumerate(foods, 1):
        f["id"] = i

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(foods, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "food_name", "gi_value", "gi_sem", "gl_value",
            "gi_level", "category", "country"
        ])
        writer.writeheader()
        writer.writerows(foods)

    # Stats
    categories = {}
    gi_dist = {"Low": 0, "Medium": 0, "High": 0}
    countries = {}
    for food in foods:
        cat = food["category"]
        categories[cat] = categories.get(cat, 0) + 1
        gi_dist[food["gi_level"]] += 1
        c = food.get("country") or "Unknown"
        countries[c] = countries.get(c, 0) + 1

    print(f"[OK] Extracted {len(foods)} unique foods")
    print(f"     GI: Low={gi_dist['Low']}, Medium={gi_dist['Medium']}, High={gi_dist['High']}")
    print(f"     Categories ({len(categories)}):")
    for cat, n in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"       {cat}: {n}")
    print(f"     Top countries:")
    for c, n in sorted(countries.items(), key=lambda x: -x[1])[:10]:
        print(f"       {c}: {n}")
    print(f"     Saved: {OUTPUT_JSON}, {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
