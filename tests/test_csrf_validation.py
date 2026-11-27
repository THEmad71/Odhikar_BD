"""
Odhikar BD - Isolated CSRF validation tests.

Uses the actual CSRF function definitions extracted from
source code without importing application modules.

No database connections, HTTP calls, or Gemini requests.
"""

import ast
import copy
import hashlib
import hmac
import secrets
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]


def load_function(path, function_name, namespace):
    """Load one function definition without importing its module."""

    tree = ast.parse(
        (ROOT / path).read_text(encoding="utf-8")
    )

    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]

    assert len(matches) == 1, (
        f"Expected one definition of {function_name}"
    )

    node = copy.deepcopy(matches[0])

    # Remove dependency-injection defaults and type annotations.
    # Tests call dependencies explicitly.
    node.decorator_list = []
    node.args.defaults = [
        ast.Constant(value=None)
        for _ in node.args.defaults
    ]

    for arg in (
        node.args.posonlyargs
        + node.args.args
        + node.args.kwonlyargs
    ):
        arg.annotation = None

    node.returns = None

    module = ast.fix_missing_locations(
        ast.Module(body=[node], type_ignores=[])
    )

    exec(compile(module, str(path), "exec"), namespace)

    return namespace[function_name]


@pytest.fixture
def member_functions():
    namespace = {
        "hashlib": hashlib,
        "hmac": hmac,
        "secrets": secrets,
    }

    path = "src/odhikar/api.py"

    generate = load_function(
        path, "generate_csrf_token", namespace
    )

    validate = load_function(
        path, "validate_csrf_token", namespace
    )

    return generate, validate


def test_member_valid_token(member_functions):
    generate, validate = member_functions

    token = generate("session-A")

    assert validate("session-A", token) is True


@pytest.mark.parametrize(
    "invalid",
    [
        "",
        "invalid",
        ".",
        "nonce.",
        ".signature",
        None,
        123,
        "x" * 513,
    ],
)
def test_member_invalid_token(member_functions, invalid):
    _, validate = member_functions

    assert validate("session-A", invalid) is False


def test_member_modified_signature(member_functions):
    generate, validate = member_functions

    token = generate("session-A")
    nonce, signature = token.split(".", 1)

    changed = (
        "0" if signature[0] != "0" else "1"
    ) + signature[1:]

    assert validate(
        "session-A", f"{nonce}.{changed}"
    ) is False


def test_member_other_session_rejected(member_functions):
    generate, validate = member_functions

    token = generate("session-A")

    assert validate("session-B", token) is False


@pytest.fixture
def member_csrf_guard(member_functions):
    generate, validate = member_functions

    namespace = {
        "hmac": hmac,
        "HTTPException": HTTPException,
        "CSRF_COOKIE": "test_member_csrf",
        "validate_request_origin": lambda request: None,
        "validate_csrf_token": validate,
    }

    guard = load_function(
        "src/odhikar/api.py",
        "require_csrf",
        namespace,
    )

    return generate, guard


@pytest.mark.parametrize(
    "case",
    ["missing_header", "missing_cookie", "mismatch"],
)
def test_member_csrf_guard_rejects_invalid(
    member_csrf_guard, case
):
    generate, guard = member_csrf_guard
    token = generate("session-A")

    cookies = {"test_member_csrf": token}
    headers = {"X-CSRF-Token": token}

    if case == "missing_header":
        headers.clear()
    elif case == "missing_cookie":
        cookies.clear()
    else:
        headers["X-CSRF-Token"] = "invalid"

    request = SimpleNamespace(
        cookies=cookies,
        headers=headers,
    )

    with pytest.raises(HTTPException) as error:
        guard(request, {"session_token": "session-A"})

    assert error.value.status_code == 403


def test_member_csrf_guard_accepts_valid(
    member_csrf_guard,
):
    generate, guard = member_csrf_guard
    token = generate("session-A")

    request = SimpleNamespace(
        cookies={"test_member_csrf": token},
        headers={"X-CSRF-Token": token},
    )

    context = {"session_token": "session-A"}

    assert guard(request, context) == context


@pytest.fixture
def guest_csrf_guard(member_functions):
    generate, validate = member_functions

    namespace = {
        "hmac": hmac,
        "HTTPException": HTTPException,
        "GUEST_CSRF_COOKIE": "odhikar_guest_csrf",
        "validate_csrf": validate,
    }

    guard = load_function(
        "src/odhikar/guest_routes.py",
        "guest_csrf",
        namespace,
    )

    return generate, guard


@pytest.mark.parametrize(
    "case",
    [
        "missing_header",
        "missing_cookie",
        "mismatch",
        "invalid_signature",
    ],
)
def test_guest_csrf_guard_rejects_invalid(
    guest_csrf_guard, case
):
    generate, guard = guest_csrf_guard

    token = generate("guest-session-A")

    cookies = {"odhikar_guest_csrf": token}
    headers = {"X-CSRF-Token": token}

    if case == "missing_header":
        headers.clear()
    elif case == "missing_cookie":
        cookies.clear()
    elif case == "mismatch":
        headers["X-CSRF-Token"] = "wrong"
    else:
        invalid = "nonce.invalid-signature"
        cookies["odhikar_guest_csrf"] = invalid
        headers["X-CSRF-Token"] = invalid

    request = SimpleNamespace(
        cookies=cookies,
        headers=headers,
    )

    with pytest.raises(HTTPException) as error:
        guard(
            request,
            {"token": "guest-session-A"},
        )

    assert error.value.status_code == 403


def test_guest_csrf_guard_accepts_valid(
    guest_csrf_guard,
):
    generate, guard = guest_csrf_guard

    token = generate("guest-session-A")

    request = SimpleNamespace(
        cookies={"odhikar_guest_csrf": token},
        headers={"X-CSRF-Token": token},
    )

    context = {"token": "guest-session-A"}

    assert guard(request, context) == context
