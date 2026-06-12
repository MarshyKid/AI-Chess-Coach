import unittest

import ai_chess_coach


class PackageImportTest(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertIsNotNone(ai_chess_coach)
