# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import unittest

import rcav2.database


class TestDatabase(unittest.TestCase):
    def test_database(self) -> None:
        engine = rcav2.database.create(":memory:")
        # Check that a non-existent report returns None
        report = rcav2.database.get(engine, "react", "test")
        self.assertEqual(report, None)
        # After the get, a placeholder has been created, now set the events
        rcav2.database.set(engine, "react", "test", "events")
        report = rcav2.database.get(engine, "react", "test")
        self.assertEqual(report, "events")

    def test_database_composite_key(self) -> None:
        engine = rcav2.database.create(":memory:")
        # Create two reports with same build, different workflow
        report = rcav2.database.get(engine, "react", "test")
        self.assertEqual(report, None)
        report = rcav2.database.get(engine, "other", "test")
        self.assertEqual(report, None)

        # Set events for the first report
        rcav2.database.set(engine, "react", "test", "react-events")
        # Set events for the second report
        rcav2.database.set(engine, "other", "test", "other-events")

        # Check that the events are correct for each report
        report = rcav2.database.get(engine, "react", "test")
        self.assertEqual(report, "react-events")
        report = rcav2.database.get(engine, "other", "test")
        self.assertEqual(report, "other-events")
