from __future__ import annotations

import unittest

from services.evermem_config import EverMemConfig


class EverMemConfigTests(unittest.TestCase):
    def test_update_from_headers_accepts_lowercase_names_and_explicit_scope(self) -> None:
        config = EverMemConfig()

        config.update_from_headers(
            {
                "x-evermem-enabled": "true",
                "x-evermem-url": "https://memory.example.com",
                "x-evermem-key": "memory-key",
                "x-evermem-scope": "workspace-main",
            }
        )

        self.assertTrue(config.enabled)
        self.assertEqual(config.url, "https://memory.example.com")
        self.assertEqual(config.key, "memory-key")
        self.assertEqual(config.memory_scope, "workspace-main")
        self.assertIsNotNone(config.get_service())

    def test_update_from_headers_falls_back_to_client_hash_without_scope(self) -> None:
        config = EverMemConfig()

        config.update_from_headers(
            {
                "x-evermem-enabled": "true",
                "x-evermem-key": "memory-key",
                "x-client-id": "client-123",
            }
        )

        self.assertTrue(config.memory_scope.startswith("client_"))
        self.assertEqual(len(config.memory_scope), len("client_") + 24)


if __name__ == "__main__":
    unittest.main()
