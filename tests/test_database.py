# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import unittest

import rcav2.database


class TestDatabase(unittest.TestCase):
    def test_database(self) -> None:
        engine = rcav2.database.create(":memory:")
        report = rcav2.database.get(engine, "react", "test")
        self.assertEqual(report, None)
        rcav2.database.set(engine, "test", "events")
        report = rcav2.database.get(engine, "react", "test")
        self.assertEqual(report, "events")
