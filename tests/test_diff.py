from mdf.diff import (
    blast_radius,
    diff_contracts,
    diff_library,
    run_diff,
)


def _mk_contract(cid, version, cols):
    """Build a minimal contract dict for diff testing."""
    return {
        "id": cid,
        "version": version,
        "schema": [
            {"name": cid.split(".")[-1], "properties": [{"name": n, **c} for n, c in cols.items()]}
        ],
    }


BASE_TXN_COLS = {
    "txn_id": {"logicalType": "string", "required": True},
    "card_pan": {"logicalType": "string", "required": True},
    "merchant_name": {"logicalType": "string", "required": False},
}


def test_ac13_column_removed_without_bump_is_breaking():
    """AC-13: removing a column without major bump -> breaking detected."""
    baseline = {"cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "1.0.0", BASE_TXN_COLS)}
    # remove merchant_name, no version bump
    cur_cols = {k: v for k, v in BASE_TXN_COLS.items() if k != "merchant_name"}
    current = {"cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "1.0.0", cur_cols)}

    changes = diff_contracts(current, baseline)
    breaking = [c for c in changes if c.kind == "breaking" and c.category == "column_removed"]
    assert len(breaking) == 1
    assert "merchant_name" in breaking[0].detail


def test_ac13_column_removed_with_major_bump_reports_impact_not_breaking():
    """AC-13: with major bump -> impact reported, not breaking."""
    baseline = {"cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "1.0.0", BASE_TXN_COLS)}
    cur_cols = {k: v for k, v in BASE_TXN_COLS.items() if k != "merchant_name"}
    current = {"cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "2.0.0", cur_cols)}

    changes = diff_contracts(current, baseline)
    assert not any(c.kind == "breaking" for c in changes)
    assert any(c.category == "column_removed_bumped" for c in changes)


def test_type_change_without_bump_is_breaking():
    baseline = {"cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "1.0.0", BASE_TXN_COLS)}
    cur_cols = dict(BASE_TXN_COLS)
    cur_cols["txn_id"] = {"logicalType": "integer", "required": True}
    current = {"cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "1.0.0", cur_cols)}

    changes = diff_contracts(current, baseline)
    assert any(c.kind == "breaking" and "txn_id" in c.detail for c in changes)


def test_dataset_removed_is_breaking():
    baseline = {"cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "1.0.0", BASE_TXN_COLS)}
    current = {}
    changes = diff_contracts(current, baseline)
    assert any(c.kind == "breaking" and c.category == "dataset_removed" for c in changes)


def test_no_changes_no_diff():
    baseline = {"cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "1.0.0", BASE_TXN_COLS)}
    current = {
        "cc.credit_card_txn": _mk_contract("cc.credit_card_txn", "1.0.0", dict(BASE_TXN_COLS))
    }
    changes = diff_contracts(current, baseline)
    assert changes == []


def test_diff_library_rule_disabled_reported_dq6():
    """DQ-6/FR-C.7: disabling a rule is reported in diff."""
    baseline_lib = {"rules": {"luhn": {"sql": "{col} IS NOT NULL", "enabled": True}}}
    current_lib = {"rules": {"luhn": {"sql": "{col} IS NOT NULL", "enabled": False}}}
    changes = diff_library(current_lib, baseline_lib)
    assert any(c.category == "library_rule_disabled" for c in changes)


def test_blast_radius_luhn_ac24():
    """AC-24/DQ-6: blast radius of 'luhn' finds cc.credit_card.card_pan."""
    affected = blast_radius("luhn", base_dir="DataContract")
    pairs = {(a["dataset"], a["column"]) for a in affected}
    assert ("cc.credit_card", "card_pan") in pairs


def test_run_diff_against_baseline_rev():
    """Run full diff against commit 88b982d — no breaking changes expected."""
    result = run_diff("88b982d", base_dir="DataContract")
    # The migration renamed dq/ -> pipeline/ and modified contracts (landing template),
    # but no columns were removed nor types changed — expect no breaking.
    breaking_cats = [c.category for c in result.changes if c.kind == "breaking"]
    # Either empty or only non-column-related; columns are identical across revs
    assert "column_removed" not in breaking_cats
    assert "column_type_changed" not in breaking_cats
