"""JSON schema definitions for structured agent outputs."""

from __future__ import annotations

from typing import Any

FINANCIAL_REPORT_SCHEMA = {
    "name": "financial_reports",
    "schema": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "additionalProperties": False,
        "required": ["income_statement", "cash_flow", "expense_breakdown"],
        "properties": {
            "income_statement": {
                "type": "object",
                "additionalProperties": False,
                "required": ["periods"],
                "properties": {
                    "periods": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "label",
                                "revenue",
                                "cogs",
                                "gross_profit",
                                "operating_expenses",
                                "operating_income",
                                "other_net",
                                "taxes",
                                "net_income",
                                "margins",
                            ],
                            "properties": {
                                "label": {"type": "string"},
                                "revenue": {"type": "number"},
                                "cogs": {"type": "number"},
                                "gross_profit": {"type": "number"},
                                "operating_expenses": {"type": "number"},
                                "operating_income": {"type": "number"},
                                "other_net": {"type": "number"},
                                "taxes": {"type": "number"},
                                "net_income": {"type": "number"},
                                "margins": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["gross", "operating", "net"],
                                    "properties": {
                                        "gross": {"type": "number"},
                                        "operating": {"type": "number"},
                                        "net": {"type": "number"},
                                    },
                                },
                            },
                        },
                    }
                },
            },
            "cash_flow": {
                "type": "object",
                "additionalProperties": False,
                "required": ["operating", "investing", "financing", "net_change"],
                "properties": {
                    "operating": {"type": "number"},
                    "investing": {"type": "number"},
                    "financing": {"type": "number"},
                    "net_change": {"type": "number"},
                },
            },
            "expense_breakdown": {
                "type": "object",
                "additionalProperties": False,
                "required": ["by_category", "by_vendor", "by_month"],
                "properties": {
                    "by_category": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["label", "total"],
                            "properties": {
                                "label": {"type": "string"},
                                "total": {"type": "number"},
                            },
                        },
                    },
                    "by_vendor": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["label", "total"],
                            "properties": {
                                "label": {"type": "string"},
                                "total": {"type": "number"},
                            },
                        },
                    },
                    "by_month": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["label", "total"],
                            "properties": {
                                "label": {"type": "string"},
                                "total": {"type": "number"},
                            },
                        },
                    },
                },
            },
        },
    },
    "strict": True,
}

SCHEMA_PROFILES: dict[str, dict[str, Any]] = {
    "income_cashflow_expense": {
        "type": "json_schema",
        "json_schema": FINANCIAL_REPORT_SCHEMA,
        "strict": True,
    }
}


def get_response_format(profile: str) -> dict[str, Any] | None:
    """Return response_format payload for the given schema profile."""
    return SCHEMA_PROFILES.get(profile)
