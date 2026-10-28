import unittest
from unittest.mock import MagicMock, patch
import mysql.connector
from PoolCar import Databaze


def reservation_args(start="2026-11-01", end="2026-11-02", car_id=3, spz="TEST123"):
    return (7, "Alice", "Test", "IT", "BI", car_id, spz, "nova", start, end,
            None, None, None, "")


class ReservationTransactionTests(unittest.TestCase):
    def setUp(self):
        self.db = Databaze()
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.patcher = patch.object(self.db, "_get_connection", return_value=self.connection)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_success_locks_car_before_checking_overlap_and_writing(self):
        self.cursor.fetchone.side_effect = [(3, "TEST123"), None]
        self.assertEqual(self.db.insert_rezervace_if_available(*reservation_args()), (True, None))
        self.connection.start_transaction.assert_called_once()
        queries = self.cursor.execute.call_args_list
        self.assertIn("FROM auta", queries[0].args[0])
        self.assertIn("FOR UPDATE", queries[0].args[0])
        self.assertIn("FOR UPDATE", queries[1].args[0])
        self.assertEqual(queries[1].args[1], (3, "2026-11-02", "2026-11-01"))
        self.assertIn("INSERT INTO rezervace", queries[2].args[0])
        self.assertEqual(queries[2].args[1][10:13], (None, None, None))
        self.connection.commit.assert_called_once()
        self.connection.close.assert_called_once()

    def test_conflict_rolls_back_without_inserting(self):
        self.cursor.fetchone.side_effect = [(3, "TEST123"), (1,)]
        self.assertEqual(self.db.insert_rezervace_if_available(*reservation_args()), (False, "conflict"))
        self.connection.commit.assert_not_called()
        self.connection.rollback.assert_called_once()
        self.assertEqual(self.cursor.execute.call_count, 2)

    def test_missing_or_changed_car_fails_closed(self):
        for car in (None, (3, "CHANGED")):
            self.cursor.fetchone.return_value = car
            self.assertEqual(self.db.insert_rezervace_if_available(*reservation_args()), (False, "error"))
        self.connection.commit.assert_not_called()

    def test_insert_failure_rolls_back(self):
        self.cursor.fetchone.side_effect = [(3, "TEST123"), None]
        self.cursor.execute.side_effect = [None, None, mysql.connector.Error("write failed")]
        self.assertEqual(self.db.insert_rezervace_if_available(*reservation_args()), (False, "error"))
        self.connection.rollback.assert_called_once()
        self.connection.close.assert_called_once()

    def test_car_primary_key_is_aliased(self):
        self.cursor.fetchall.return_value = [{"idAuta": 3, "spz": "TEST123"}]
        self.assertEqual(self.db.get_car_info()[0]["idAuta"], 3)
        self.assertIn("id AS idAuta", self.cursor.execute.call_args.args[0])
