
"""
Experimental Pure Python compatibility layer
for the ormsgpack API used by LangGraph.

Uses msgpack.fallback instead of the native
ormsgpack DLL blocked by Windows security.
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
    """Compatible encoding exception."""
    pass


# ==========================================
# 4. ENUM PREPROCESSING
# ==========================================

def _prepare_enums(obj, default=None):

    if isinstance(obj, Enum):

        if default is not None:
            return default(obj)

        return obj.value

    if isinstance(obj, dict):

        return {
            _prepare_enums(key, default):
            _prepare_enums(value, default)
            for key, value in obj.items()
        }

    if isinstance(obj, list):

        return [
            _prepare_enums(item, default)
            for item in obj
        ]

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

    # FIX:
    # Pure Python msgpack requires ext_hook
    # to be callable when explicitly provided.

    if ext_hook is not None:

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
        "native_extension": False,
        "pure_python": True,
        "ext_type_supported": True,
        "non_string_keys_supported": True,
        "ext_hook_none_supported": True
    }
