
import tempfile
import threading
import unittest

from pathlib import Path

from src.odhikar.usage_limits import (
    UsageStore,
    GUEST_LIMIT,
    MEMBER_LIMIT,
    DAY_SECONDS,
    DHAKA_OFFSET,
)


class UsageLimitTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.store = UsageStore(
            Path(self.temp_dir.name) / "test_usage.sqlite"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_guest_five_messages_then_block(self):
        now = 1_800_000_000

        token = self.store.create_guest(now=now)

        principal = self.store.guest_principal(
            token,
            now=now
        )

        self.assertIsNotNone(principal)

        for index in range(GUEST_LIMIT):
            result = self.store.check_and_consume(
                "guest",
                principal,
                now=now + index
            )

            self.assertTrue(result.allowed)

            self.assertEqual(
                result.remaining,
                GUEST_LIMIT - index - 1
            )

        blocked = self.store.check_and_consume(
            "guest",
            principal,
            now=now + GUEST_LIMIT
        )

        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.remaining, 0)

    def test_member_resets_at_dhaka_midnight(self):
        start = (
            (
                (1_800_000_000 + DHAKA_OFFSET)
                // DAY_SECONDS
            ) * DAY_SECONDS
            - DHAKA_OFFSET
        )

        for _ in range(MEMBER_LIMIT):
            result = self.store.check_and_consume(
                "member",
                "user-123",
                now=start + 60
            )

            self.assertTrue(result.allowed)

        blocked = self.store.check_and_consume(
            "member",
            "user-123",
            now=start + 61
        )

        self.assertFalse(blocked.allowed)

        next_day = self.store.check_and_consume(
            "member",
            "user-123",
            now=start + DAY_SECONDS
        )

        self.assertTrue(next_day.allowed)

    def test_guest_session_expiry(self):
        now = 1_800_000_000

        token = self.store.create_guest(now=now)

        expired = self.store.guest_principal(
            token,
            now=now + DAY_SECONDS
        )

        self.assertIsNone(expired)

    def test_account_isolation(self):
        now = 1_800_000_000

        self.store.check_and_consume(
            "member",
            "alice",
            now=now
        )

        bob = self.store.status(
            "member",
            "bob",
            now=now
        )

        self.assertEqual(bob.used, 0)

    def test_concurrent_requests(self):
        now = 1_800_000_000

        outcomes = []
        lock = threading.Lock()

        def worker():
            result = self.store.check_and_consume(
                "member",
                "shared-user",
                now=now
            )

            with lock:
                outcomes.append(result.allowed)

        threads = [
            threading.Thread(target=worker)
            for _ in range(50)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(
            sum(outcomes),
            MEMBER_LIMIT
        )

        self.assertEqual(len(outcomes), 50)


if __name__ == "__main__":
    unittest.main()
