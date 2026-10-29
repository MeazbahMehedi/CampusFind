"""Editable campus vocabulary. Historical report values are retained when options change."""

import json

from .models import CampusSetting, db

DEFAULTS = {
    "categories": [
        "Electronics",
        "Bags",
        "Keys",
        "Cards & IDs",
        "Books",
        "Clothing",
        "Accessories",
        "Other",
    ],
    "locations": [
        "Central Library",
        "Teaching Building",
        "Cafeteria",
        "Sports Center",
        "Student Dormitory",
        "Campus Garden",
        "Other",
    ],
    "collection_points": ["Campus Help Desk", "Central Library Reception"],
    "handover_instructions": "Bring a student ID and your claim reference. Arrange a collection time with the campus help desk before visiting.",
}


def campus_settings():
    values = dict(DEFAULTS)
    for setting in db.session.scalars(db.select(CampusSetting)).all():
        values[setting.key] = json.loads(setting.value)
    return values


def save_settings(values):
    for key, value in values.items():
        row = db.session.get(CampusSetting, key)
        if row is None:
            row = CampusSetting(key=key)
            db.session.add(row)
        row.value = json.dumps(value, ensure_ascii=False)
