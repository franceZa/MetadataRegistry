import pytest
from pathlib import Path
from mdf.validation import validate_foreign_key_references, ValidationReport

def test_valid_fk_references():
    report = ValidationReport()
    contracts = {
        "cc.customer": (
            Path("DataContract/cc/contract/customer.odcs.yaml"),
            {
                "id": "cc.customer",
                "schema": [
                    {
                        "name": "customer",
                        "properties": [
                            {"name": "customer_id", "logicalType": "string"}
                        ],
                    }
                ],
            },
        ),
        "cc.credit_card": (
            Path("DataContract/cc/contract/credit_card.odcs.yaml"),
            {
                "id": "cc.credit_card",
                "schema": [
                    {
                        "name": "credit_card",
                        "properties": [
                            {
                                "name": "customer_id",
                                "logicalType": "string",
                                "customProperties": [
                                    {"property": "foreign_key", "value": "cc.customer.customer_id"}
                                ],
                            }
                        ],
                    }
                ],
            },
        ),
    }
    validate_foreign_key_references(contracts, report)
    assert report.is_valid is True
    assert len(report.errors) == 0

def test_fk_target_dataset_not_found_ac33():
    report = ValidationReport()
    contracts = {
        "cc.credit_card": (
            Path("DataContract/cc/contract/credit_card.odcs.yaml"),
            {
                "id": "cc.credit_card",
                "schema": [
                    {
                        "name": "credit_card",
                        "properties": [
                            {
                                "name": "customer_id",
                                "logicalType": "string",
                                "customProperties": [
                                    {"property": "foreign_key", "value": "cc.unknown_dataset.col"}
                                ],
                            }
                        ],
                    }
                ],
            },
        ),
    }
    validate_foreign_key_references(contracts, report)
    assert report.is_valid is False
    err = next(e for e in report.errors if e.code == "FK_TARGET_NOT_FOUND")
    assert "unknown_dataset" in err.message

def test_fk_target_column_not_found_ac33():
    report = ValidationReport()
    contracts = {
        "cc.customer": (
            Path("DataContract/cc/contract/customer.odcs.yaml"),
            {
                "id": "cc.customer",
                "schema": [
                    {
                        "name": "customer",
                        "properties": [
                            {"name": "customer_id", "logicalType": "string"}
                        ],
                    }
                ],
            },
        ),
        "cc.credit_card": (
            Path("DataContract/cc/contract/credit_card.odcs.yaml"),
            {
                "id": "cc.credit_card",
                "schema": [
                    {
                        "name": "credit_card",
                        "properties": [
                            {
                                "name": "customer_id",
                                "logicalType": "string",
                                "customProperties": [
                                    {"property": "foreign_key", "value": "cc.customer.missing_col"}
                                ],
                            }
                        ],
                    }
                ],
            },
        ),
    }
    validate_foreign_key_references(contracts, report)
    assert report.is_valid is False
    err = next(e for e in report.errors if e.code == "FK_TARGET_NOT_FOUND")
    assert "missing_col" in err.message

def test_fk_type_mismatch_ac33():
    report = ValidationReport()
    contracts = {
        "cc.customer": (
            Path("DataContract/cc/contract/customer.odcs.yaml"),
            {
                "id": "cc.customer",
                "schema": [
                    {
                        "name": "customer",
                        "properties": [
                            {"name": "customer_id", "logicalType": "integer"}
                        ],
                    }
                ],
            },
        ),
        "cc.credit_card": (
            Path("DataContract/cc/contract/credit_card.odcs.yaml"),
            {
                "id": "cc.credit_card",
                "schema": [
                    {
                        "name": "credit_card",
                        "properties": [
                            {
                                "name": "customer_id",
                                "logicalType": "string",
                                "customProperties": [
                                    {"property": "foreign_key", "value": "cc.customer.customer_id"}
                                ],
                            }
                        ],
                    }
                ],
            },
        ),
    }
    validate_foreign_key_references(contracts, report)
    assert report.is_valid is False
    err = next(e for e in report.errors if e.code == "FK_TYPE_MISMATCH")
    assert "logicalType ไม่ตรงกัน" in err.message
