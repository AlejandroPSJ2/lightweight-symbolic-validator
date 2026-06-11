"""Core operations over sequences, sets, multisets, and relations."""

from __future__ import annotations

import unicodedata
from collections import Counter
from typing import Any

from discrete_structure_tool.models import NormalizeConfig, UnsupportedOperationError


def _normalize_scalar(value: Any, config: NormalizeConfig) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value
        if config.trim:
            text = text.strip()
        if config.nfkc:
            text = unicodedata.normalize("NFKC", text)
        if config.casefold:
            text = text.casefold()
        return text
    if isinstance(value, dict):
        return {k: _normalize_scalar(v, config) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_scalar(item, config) for item in value]
    return value


def normalize_items(items: list[Any], config: NormalizeConfig) -> list[Any]:
    """Normalize a list of items (scalars or dict rows) according to config."""
    return [_normalize_scalar(item, config) for item in items]


def _json_key(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value)
    return repr(value)


def _compare_key(value: Any, config: NormalizeConfig) -> str:
    """Comparison key used for matching; may differ from displayed value."""
    return _json_key(_normalize_scalar(value, config))


def _positions(items: list[Any], target: Any, config: NormalizeConfig) -> list[int]:
    target_key = _compare_key(target, config)
    return [index for index, item in enumerate(items) if _compare_key(item, config) == target_key]


def _frequency_map(items: list[Any], config: NormalizeConfig) -> dict[str, int]:
    counts: dict[str, int] = {}
    labels: dict[str, str] = {}
    for item in items:
        key = _compare_key(item, config)
        counts[key] = counts.get(key, 0) + 1
        labels.setdefault(key, str(item))
    return {labels[key]: counts[key] for key in counts}


def _row_key(row: dict[str, Any], keys: list[str], config: NormalizeConfig) -> tuple[str, ...]:
    return tuple(_compare_key(row.get(key), config) for key in keys)


def _ensure_target(target: Any | None, operation: str) -> Any:
    if target is None:
        raise ValueError(f"Operation '{operation}' requires 'target'")
    return target


def _ensure_b(b: list[Any] | None, operation: str) -> list[Any]:
    if b is None:
        raise ValueError(f"Operation '{operation}' requires 'b'")
    return b


def _ensure_keys(keys: list[str] | None, operation: str) -> list[str]:
    if not keys:
        raise ValueError(f"Operation '{operation}' requires non-empty 'keys'")
    return keys


def _set_from_list(items: list[Any], config: NormalizeConfig) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        key = _compare_key(item, config)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _set_membership_list(items: list[Any], config: NormalizeConfig) -> set[str]:
    return {_compare_key(item, config) for item in items}


def _ordered_set_diff(a: list[Any], b_keys: set[str], config: NormalizeConfig) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for item in a:
        key = _compare_key(item, config)
        if key not in b_keys and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _multiset_counter(items: list[Any], config: NormalizeConfig) -> Counter[str]:
    return Counter(_compare_key(item, config) for item in items)


def _counter_to_rep_list(
    counter: Counter[str], template: list[Any], config: NormalizeConfig
) -> list[Any]:
    rep: dict[str, Any] = {}
    for item in template:
        rep.setdefault(_compare_key(item, config), item)
    result: list[Any] = []
    for key, count in sorted(counter.items()):
        result.extend([rep[key]] * count)
    return result


def _display_counts(counter: Counter[str], template: list[Any], config: NormalizeConfig) -> dict[str, int]:
    rep: dict[str, str] = {}
    for item in template:
        key = _compare_key(item, config)
        rep.setdefault(key, str(item))
    return {rep[key]: counter[key] for key in counter}


# --- Sequence operations ---


def sequence_operation(
    operation: str,
    a: list[Any],
    b: list[Any] | None,
    target: Any | None,
    keys: list[str] | None,
    config: NormalizeConfig,
) -> tuple[Any, dict[str, Any] | None]:
    del b, keys

    if operation == "frequency":
        if target is not None:
            positions = _positions(a, target, config)
            return len(positions), {
                "positions": positions,
                "counts": {str(target): len(positions)},
            }
        counts = _frequency_map(a, config)
        return counts, {"counts": counts}

    if operation == "count":
        target = _ensure_target(target, operation)
        positions = _positions(a, target, config)
        return len(positions), {"positions": positions}

    if operation == "positions":
        target = _ensure_target(target, operation)
        positions = _positions(a, target, config)
        return positions, {"positions": positions, "counts": {str(target): len(positions)}}

    if operation == "membership":
        target = _ensure_target(target, operation)
        positions = _positions(a, target, config)
        return len(positions) > 0, {"positions": positions}

    if operation == "deduplicate":
        seen: set[str] = set()
        result: list[Any] = []
        duplicate_items: list[Any] = []
        for item in a:
            key = _compare_key(item, config)
            if key in seen:
                if item not in duplicate_items:
                    duplicate_items.append(item)
                continue
            seen.add(key)
            result.append(item)
        witness: dict[str, Any] = {"duplicate_items": duplicate_items}
        return result, witness if duplicate_items else None

    if operation == "duplicates":
        counts = _multiset_counter(a, config)
        duplicate_items: list[Any] = []
        duplicate_positions: dict[str, list[int]] = {}
        seen_values: dict[str, Any] = {}
        for index, item in enumerate(a):
            key = _compare_key(item, config)
            seen_values.setdefault(key, item)
            if counts[key] > 1:
                duplicate_positions.setdefault(key, []).append(index)
        for key, positions in duplicate_positions.items():
            if len(positions) > 1:
                duplicate_items.append(seen_values[key])
        return duplicate_items, {
            "duplicate_items": duplicate_items,
            "positions": duplicate_positions,
            "counts": {k: len(v) for k, v in duplicate_positions.items()},
        }

    raise UnsupportedOperationError("sequence", operation)


# --- Set operations ---


def set_operation(
    operation: str,
    a: list[Any],
    b: list[Any] | None,
    target: Any | None,
    keys: list[str] | None,
    config: NormalizeConfig,
) -> tuple[Any, dict[str, Any] | None]:
    del keys
    set_a = _set_from_list(a, config)
    keys_a = _set_membership_list(set_a, config)

    if operation == "membership":
        target = _ensure_target(target, operation)
        return _compare_key(target, config) in keys_a, None

    if operation == "union":
        b_items = _ensure_b(b, operation)
        result = _set_from_list(set_a + _set_from_list(b_items, config), config)
        return result, None

    if operation == "intersection":
        b_items = _ensure_b(b, operation)
        keys_b = _set_membership_list(b_items, config)
        result = [item for item in set_a if _compare_key(item, config) in keys_b]
        return result, None

    if operation == "difference":
        b_items = _ensure_b(b, operation)
        keys_b = _set_membership_list(b_items, config)
        result = _ordered_set_diff(set_a, keys_b, config)
        return result, {"missing_items": result}

    if operation == "symmetric_difference":
        b_items = _ensure_b(b, operation)
        set_b = _set_from_list(b_items, config)
        keys_b = _set_membership_list(set_b, config)
        only_a = _ordered_set_diff(set_a, keys_b, config)
        only_b = _ordered_set_diff(set_b, keys_a, config)
        result = only_a + only_b
        return result, {"missing_items": only_a + only_b}

    if operation == "subset":
        b_items = _ensure_b(b, operation)
        keys_b = _set_membership_list(b_items, config)
        missing = [item for item in set_a if _compare_key(item, config) not in keys_b]
        is_subset = len(missing) == 0
        witness = {"missing_items": missing} if missing else None
        return is_subset, witness

    if operation == "superset":
        b_items = _ensure_b(b, operation)
        set_b = _set_from_list(b_items, config)
        missing = [item for item in set_b if _compare_key(item, config) not in keys_a]
        is_superset = len(missing) == 0
        witness = {"missing_items": missing} if missing else None
        return is_superset, witness

    if operation == "coverage":
        b_items = _ensure_b(b, operation)
        missing = _ordered_set_diff(_set_from_list(b_items, config), keys_a, config)
        is_covered = len(missing) == 0
        witness = {"missing_items": missing} if missing else None
        return is_covered, witness

    if operation == "duplicates":
        counts = _multiset_counter(a, config)
        duplicate_items = [
            item for item in set_a if counts[_compare_key(item, config)] > 1
        ]
        display_counts = _display_counts(counts, a, config)
        return duplicate_items, {
            "duplicate_items": duplicate_items,
            "counts": {k: v for k, v in display_counts.items() if v > 1},
        }

    raise UnsupportedOperationError("set", operation)


# --- Multiset operations ---


def multiset_operation(
    operation: str,
    a: list[Any],
    b: list[Any] | None,
    target: Any | None,
    keys: list[str] | None,
    config: NormalizeConfig,
) -> tuple[Any, dict[str, Any] | None]:
    del keys
    counter_a = _multiset_counter(a, config)

    if operation == "frequency":
        if target is not None:
            key = _compare_key(target, config)
            count = counter_a.get(key, 0)
            positions = _positions(a, target, config)
            return count, {"positions": positions, "counts": {str(target): count}}
        counts = _display_counts(counter_a, a, config)
        return counts, {"counts": counts}

    if operation == "membership":
        target = _ensure_target(target, operation)
        count = counter_a.get(_compare_key(target, config), 0)
        return count > 0, {"counts": {str(target): count}}

    if operation == "union":
        b_items = _ensure_b(b, operation)
        counter_b = _multiset_counter(b_items, config)
        merged = counter_a + counter_b
        result = _counter_to_rep_list(merged, a + b_items, config)
        return result, {"counts": _display_counts(merged, a + b_items, config)}

    if operation == "intersection":
        b_items = _ensure_b(b, operation)
        counter_b = _multiset_counter(b_items, config)
        merged = counter_a & counter_b
        result = _counter_to_rep_list(merged, a + b_items, config)
        return result, {"counts": _display_counts(merged, a + b_items, config)}

    if operation == "difference":
        b_items = _ensure_b(b, operation)
        counter_b = _multiset_counter(b_items, config)
        merged = counter_a - counter_b
        result = _counter_to_rep_list(merged, a, config)
        rep = {_compare_key(item, config): item for item in a}
        missing_items = [
            rep[key] for key in sorted(merged) for _ in range(merged[key])
        ]
        return result, {
            "missing_items": missing_items,
            "counts": _display_counts(merged, a, config),
        }

    if operation == "subset":
        b_items = _ensure_b(b, operation)
        counter_b = _multiset_counter(b_items, config)
        missing_counter = counter_a - counter_b
        is_subset = len(missing_counter) == 0
        rep = {_compare_key(item, config): item for item in a}
        missing_items = [
            rep[key] for key in sorted(missing_counter) for _ in range(missing_counter[key])
        ]
        witness = {
            "missing_items": missing_items,
            "counts": dict(missing_counter),
        } if missing_items else None
        return is_subset, witness

    if operation == "superset":
        b_items = _ensure_b(b, operation)
        counter_b = _multiset_counter(b_items, config)
        missing_counter = counter_b - counter_a
        is_superset = len(missing_counter) == 0
        rep = {_compare_key(item, config): item for item in b_items}
        missing_items = [
            rep[key] for key in sorted(missing_counter) for _ in range(missing_counter[key])
        ]
        witness = {
            "missing_items": missing_items,
            "counts": dict(missing_counter),
        } if missing_items else None
        return is_superset, witness

    if operation == "duplicates":
        duplicate_items = [item for item in a if counter_a[_compare_key(item, config)] > 1]
        seen: set[str] = set()
        unique_duplicates: list[Any] = []
        for item in duplicate_items:
            key = _compare_key(item, config)
            if key not in seen:
                seen.add(key)
                unique_duplicates.append(item)
        counts = _display_counts(counter_a, a, config)
        return unique_duplicates, {
            "duplicate_items": unique_duplicates,
            "counts": {k: v for k, v in counts.items() if v > 1},
        }

    raise UnsupportedOperationError("multiset", operation)


# --- Relation operations ---


def _ensure_rows(a: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(a):
        if not isinstance(item, dict):
            raise ValueError(
                f"Relation rows must be dicts; item at index {index} is {type(item).__name__}"
            )
        rows.append(item)
    return rows


def _row_matches(row: dict[str, Any], target: dict[str, Any], keys: list[str], config: NormalizeConfig) -> bool:
    return all(
        _compare_key(row.get(key), config) == _compare_key(target.get(key), config)
        for key in keys
    )


def relation_operation(
    operation: str,
    a: list[Any],
    b: list[Any] | None,
    target: Any | None,
    keys: list[str] | None,
    config: NormalizeConfig,
) -> tuple[Any, dict[str, Any] | None]:
    rows_a = _ensure_rows(a)

    if operation == "project":
        key_list = _ensure_keys(keys, operation)
        result = [{key: row.get(key) for key in key_list} for row in rows_a]
        return result, None

    if operation == "group_by":
        key_list = _ensure_keys(keys, operation)
        groups: dict[tuple[str, ...], int] = {}
        representatives: dict[tuple[str, ...], tuple[Any, ...]] = {}
        for row in rows_a:
            group_key = _row_key(row, key_list, config)
            groups[group_key] = groups.get(group_key, 0) + 1
            representatives.setdefault(group_key, tuple(row.get(key) for key in key_list))
        result = [
            {
                **{key_list[i]: representatives[group_key][i] for i in range(len(key_list))},
                "count": count,
            }
            for group_key, count in sorted(groups.items(), key=lambda item: item[0])
        ]
        counts = {str(representatives[k]): v for k, v in groups.items()}
        return result, {"counts": counts}

    if operation == "join":
        key_list = _ensure_keys(keys, operation)
        rows_b = _ensure_rows(_ensure_b(b, operation))
        index: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for row in rows_b:
            index.setdefault(_row_key(row, key_list, config), []).append(row)

        result: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []
        for row in rows_a:
            matches = index.get(_row_key(row, key_list, config), [])
            if not matches:
                unmatched.append(row)
                continue
            for match in matches:
                merged = {**row}
                for key, value in match.items():
                    if key not in key_list:
                        merged[f"{key}_b"] = value
                result.append(merged)
        witness = {"missing_items": unmatched} if unmatched else None
        return result, witness

    if operation == "duplicates":
        key_list = _ensure_keys(keys, operation)
        seen: dict[tuple[str, ...], list[int]] = {}
        for index, row in enumerate(rows_a):
            row_key = _row_key(row, key_list, config)
            seen.setdefault(row_key, []).append(index)
        duplicate_rows = [rows_a[positions[0]] for positions in seen.values() if len(positions) > 1]
        duplicate_positions = {str(k): v for k, v in seen.items() if len(v) > 1}
        return duplicate_rows, {
            "duplicate_items": duplicate_rows,
            "positions": duplicate_positions,
            "counts": {k: len(v) for k, v in duplicate_positions.items()},
        }

    if operation == "coverage":
        key_list = _ensure_keys(keys, operation)
        if len(key_list) == 1:
            column = key_list[0]
            missing_items = [row.get(column) for row in rows_a if row.get(column) is None]
            is_covered = len(missing_items) == 0
            witness = {"missing_items": missing_items} if missing_items else None
            return is_covered, witness

        if len(key_list) == 2:
            source_key, target_key = key_list
            missing_items = [
                row.get(source_key)
                for row in rows_a
                if row.get(source_key) is not None and row.get(target_key) is None
            ]
            is_covered = len(missing_items) == 0
            witness = {"missing_items": missing_items} if missing_items else None
            return is_covered, witness

        raise ValueError("Operation 'coverage' requires one or two keys")

    if operation == "membership":
        target = _ensure_target(target, operation)
        if not isinstance(target, dict):
            raise ValueError("Operation 'membership' on relations requires 'target' as a dict row")
        key_list = _ensure_keys(keys, operation)
        positions = [
            index
            for index, row in enumerate(rows_a)
            if _row_matches(row, target, key_list, config)
        ]
        return len(positions) > 0, {"positions": positions}

    raise UnsupportedOperationError("relation", operation)


def dispatch_operation(
    kind: str,
    operation: str,
    a: list[Any],
    b: list[Any] | None,
    target: Any | None,
    keys: list[str] | None,
    config: NormalizeConfig,
) -> tuple[Any, dict[str, Any] | None]:
    if kind == "sequence":
        return sequence_operation(operation, a, b, target, keys, config)
    if kind == "set":
        return set_operation(operation, a, b, target, keys, config)
    if kind == "multiset":
        return multiset_operation(operation, a, b, target, keys, config)
    if kind == "relation":
        return relation_operation(operation, a, b, target, keys, config)
    raise UnsupportedOperationError(kind, operation)
