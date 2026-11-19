
"""
Experimental Pure Python compatibility layer
for the ormsgpack API used by LangGraph.

Backend: msgpack.fallback
Purpose: Avoid blocked native ormsgpack DLL.
"""

import sys
from enum import Enum

from msgpack import fallback


# ==========================================
# 1. COMPATIBILITY OPTIONS
# ==========================================

OPT_NON_STR_KEYS = 1 << 0
OPT_PASSTHROUGH_DATACLASS = 1 << 1
OPT_PASSTHROUGH_DATETIME = 1 << 2
OPT_PASSTHROUGH_ENUM = 1 << 3
OPT_PASSTHROUGH_UUID = 1 << 4
OPT_REPLACE_SURROGATES = 1 << 5


# ==========================================
# 2. EXTENSION TYPE
# ==========================================

Ext = fallback.ExtType


# ==========================================
# 3. ENCODING EXCEPTION
# ==========================================

class MsgpackEncodeError(TypeError):
    """Compatible serialization exception."""
    pass


# ==========================================
# 4. PREPARE PYTHON OBJECTS
# ==========================================

def _prepare_enums(obj, default=None):

    # IMPORTANT:
    # ExtType and Timestamp must be preserved.
    # ExtType is a tuple subclass.

    if isinstance(
        obj,
        (fallback.ExtType, fallback.Timestamp)
    ):
        return obj

    # Handle Enum before primitive/container types.

    if isinstance(obj, Enum):

        if default is not None:
            return default(obj)

        return obj.value

    # Dictionary

    if isinstance(obj, dict):

        return {
            _prepare_enums(key, default):
            _prepare_enums(value, default)
            for key, value in obj.items()
        }

    # List

    if isinstance(obj, list):

        return [
            _prepare_enums(item, default)
            for item in obj
        ]

    # Tuple

    if isinstance(obj, tuple):

        return tuple(
            _prepare_enums(item, default)
            for item in obj
        )

    return obj


# ==========================================
# 5. PACKB
# ==========================================

def packb(
    obj,
    *,
    default=None,
    option=0
):

    try:

        prepared = _prepare_enums(
            obj,
            default
        )

        packer = fallback.Packer(
            default=default,
            use_bin_type=True,
            unicode_errors="replace"
        )

        return packer.pack(prepared)

    except MsgpackEncodeError:
        raise

    except Exception as exc:

        raise MsgpackEncodeError(
            str(exc)
        ) from exc


# ==========================================
# 6. UNPACKB
# ==========================================

def unpackb(
    packed,
    *,
    ext_hook=None,
    option=0,
    **kwargs
):

    kwargs.setdefault(
        "raw",
        False
    )

    kwargs.setdefault(
        "strict_map_key",
        not bool(option & OPT_NON_STR_KEYS)
    )

    # Pass ext_hook only when callable.

    if ext_hook is not None:

        if not callable(ext_hook):
            raise TypeError(
                "ext_hook must be callable or None"
            )

        kwargs["ext_hook"] = ext_hook

    return fallback.unpackb(
        packed,
        **kwargs
    )


# ==========================================
# 7. INSTALL COMPATIBILITY MODULE
# ==========================================

def install():

    module = sys.modules[__name__]

    existing = sys.modules.get("ormsgpack")

    if existing is not None and existing is not module:

        raise RuntimeError(
            "Another ormsgpack module is already loaded."
        )

    sys.modules["ormsgpack"] = module

    return True


# ==========================================
# 8. MODULE INFORMATION
# ==========================================

def get_info():

    return {
        "implementation": "msgpack.fallback",
        "pure_python": True,
        "native_extension": False,
        "extension_type": True,
        "non_string_keys": True,
        "ext_hook": True
    }
