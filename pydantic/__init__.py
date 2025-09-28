"""Minimal subset of pydantic required for offline tests."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple, Union, get_args, get_origin


class ValidationError(Exception):
    """Simplified ValidationError carrying message and optional field name."""

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class FieldInfo:
    def __init__(self, default=..., description: str | None = None):
        self.default = default
        self.description = description


def Field(*, default=..., description: str | None = None):
    """Return a FieldInfo instance mimicking pydantic.Field."""

    return FieldInfo(default=default, description=description)


class ConfigDict(dict):
    """Shallow dict subclass used to mirror pydantic.ConfigDict."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class BaseModelMeta(type):
    """Metaclass collecting annotations for BaseModel subclasses."""

    def __new__(mcls, name, bases, namespace):
        annotations = namespace.get("__annotations__", {})
        namespace.setdefault("model_config", ConfigDict())
        namespace["__fields__"] = dict(annotations)
        return super().__new__(mcls, name, bases, namespace)


class BaseModel(metaclass=BaseModelMeta):
    """Very small subset of pydantic.BaseModel features used in tests."""

    def __init__(self, **data):
        fields = getattr(self, "__fields__", {})
        processed: Dict[str, Any] = {}
        for field_name, field_type in fields.items():
            default_value = getattr(type(self), field_name, ...)
            if isinstance(default_value, FieldInfo):
                default_value = default_value.default
            if field_name in data:
                value = data[field_name]
            elif default_value is ...:
                raise ValidationError(f"Missing required field '{field_name}'", field_name)
            else:
                value = default_value
            if not self._check_type(field_type, value):
                raise ValidationError(
                    f"Invalid type for field '{field_name}': expected {field_type}, got {type(value).__name__}",
                    field_name,
                )
            processed[field_name] = value
            setattr(self, field_name, value)

        extra_fields = set(data.keys()) - set(fields.keys())
        if extra_fields:
            raise ValidationError("Unexpected fields: " + ", ".join(sorted(extra_fields)))
        self._data = processed

    def model_dump(self) -> Dict[str, Any]:
        return dict(self._data)

    @staticmethod
    def _check_type(expected_type: Any, value: Any) -> bool:
        if expected_type is Any:
            return True
        origin = get_origin(expected_type)
        if origin is None:
            if isinstance(expected_type, type):
                return isinstance(value, expected_type)
            return True
        if origin in (list, List):
            (inner_type,) = get_args(expected_type) or (Any,)
            return isinstance(value, list) and all(
                BaseModel._check_type(inner_type, item) for item in value
            )
        if origin in (dict, Dict):
            args = get_args(expected_type) or (Any, Any)
            key_type, val_type = args if len(args) == 2 else (Any, Any)
            return isinstance(value, dict) and all(
                BaseModel._check_type(key_type, k)
                and BaseModel._check_type(val_type, v)
                for k, v in value.items()
            )
        if origin in (tuple, Tuple):
            args = get_args(expected_type)
            if len(args) == 2 and args[1] is Ellipsis:
                return isinstance(value, tuple) and all(
                    BaseModel._check_type(args[0], item) for item in value
                )
            return isinstance(value, tuple) and len(value) == len(args) and all(
                BaseModel._check_type(arg, item) for arg, item in zip(args, value)
            )
        if origin in (set, Set):
            (inner_type,) = get_args(expected_type) or (Any,)
            return isinstance(value, set) and all(
                BaseModel._check_type(inner_type, item) for item in value
            )
        if origin is Union:
            return any(BaseModel._check_type(arg, value) for arg in get_args(expected_type))
        return True


def validator(*_args, **_kwargs):
    """Dummy validator decorator for compatibility."""

    def decorator(func):
        return func

    return decorator
