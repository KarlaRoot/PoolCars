"""Opt-in integration tests. Use ONLY an isolated database ending in _test.

Creates schema.sql tables and removes them on completion; refuses a nonempty DB.
"""
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest

from PoolCar import Databaze
from tests.test_database import reservation_args


@unittest.skipUnless(os.environ.get("RUN_MYSQL_TESTS") == "1", "isolated MySQL not requested")
class MySQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("DB_NAME", "").endswith("_test"):
            raise RuntimeError("DB_NAME must end in _test")
        cls.db = Databaze()
        cls.connection = cls.db._get_connection()
        cls.cursor = cls.connection.cursor()
        cls.cursor.execute("SHOW TABLES")
        if cls.cursor.fetchall():
            cls.cursor.close()
            cls.connection.close()
            raise RuntimeError("Integration database must be empty")
        cls.addClassCleanup(cls.cleanup_database)
        schema = Path(__file__).resolve().parents[1] / "schema.sql"
        for statement in schema.read_text().split(";"):
            if statement.strip():
                cls.cursor.execute(statement)
        cls.connection.commit()
        if not cls.db.insert_employee(7, "Alice", "Test", "alice", "correct horse", "alice@example.test", "IT", "BI"):
            raise RuntimeError("Could not seed employee")
        for vin, spz in (("TESTVIN0000000001", "TEST123"), ("TESTVIN0000000002", "OTHER123")):
            if not cls.db.insert_car(vin, spz, "Test", "Model", 2020, 100):
                raise RuntimeError("Could not seed car")

    @classmethod
    def cleanup_database(cls):
        for table in ("rezervace", "auta", "zamestnanci"):
            cls.cursor.execute("DROP TABLE IF EXISTS " + table)
        cls.cursor.close()
        cls.connection.close()

    def setUp(self):
        self.cursor.execute("DELETE FROM rezervace")
        self.connection.commit()

    def reserve(self, start="2026-11-01", end="2026-11-02", car_id=1, spz="TEST123"):
        return Databaze().insert_rezervace_if_available(*reservation_args(start, end, car_id, spz))

    def test_real_password_login_and_injection(self):
        self.assertIsNotNone(Databaze("alice", "correct horse").login())
        self.assertIsNone(Databaze("alice", "wrong").login())
        self.assertIsNone(Databaze("' OR 1=1 --", "wrong").login())
        self.cursor.execute("SELECT heslo FROM zamestnanci WHERE idZamestnance=7")
        hashed = self.cursor.fetchone()[0]
        self.connection.rollback()
        self.assertIsNone(Databaze("alice", hashed).login())

    def test_overlap_boundaries_and_other_car(self):
        self.assertEqual(self.reserve(), (True, None))
        for start, end in (("2026-10-31", "2026-11-01"), ("2026-11-02", "2026-11-03"),
                           ("2026-11-01", "2026-11-02"), ("2026-10-01", "2026-12-01"),
                           ("2026-11-01", "2026-11-01")):
            with self.subTest(start=start, end=end):
                self.assertEqual(self.reserve(start, end), (False, "conflict"))
        self.assertEqual(self.reserve("2026-11-03", "2026-11-04"), (True, None))
        self.assertEqual(self.reserve(car_id=2, spz="OTHER123"), (True, None))

    def test_concurrent_same_car_only_one_booking(self):
        barrier = Barrier(2)
        def competing_booking(_):
            barrier.wait(timeout=10)
            return self.reserve()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(competing_booking, range(2)))
        self.assertCountEqual(results, [(True, None), (False, "conflict")])
        self.cursor.execute("SELECT COUNT(*) FROM rezervace")
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.connection.rollback()
