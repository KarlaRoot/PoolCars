import os
import unittest
from unittest.mock import MagicMock, patch

from werkzeug.security import generate_password_hash, check_password_hash
from PoolCar import Databaze
import mysql.connector


class LoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hashed = generate_password_hash("correct horse", method="pbkdf2:sha256:1000")

    def setUp(self):
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.fetchone.return_value = {
            "idZamestnance": 7, "login": "alice", "admin": 0, "heslo": self.hashed,
        }
        self.cursor.rowcount = 1
        self.db = Databaze(username="alice", password="correct horse")
        self.connection_patch = patch.object(self.db, "_get_connection", return_value=self.connection)
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)

    def test_correct_hash_login_removes_password(self):
        user = self.db.login()
        self.assertEqual(user["idZamestnance"], 7)
        self.assertNotIn("heslo", user)
        self.connection.commit.assert_not_called()
        self.connection.close.assert_called_once()

    def test_wrong_password(self):
        self.db.password = "wrong"
        self.assertIsNone(self.db.login())

    def test_stored_hash_itself_is_not_a_password_even_in_legacy_mode(self):
        self.db.password = self.hashed
        with patch.dict(os.environ, {"ALLOW_LEGACY_PASSWORDS": "1"}):
            self.assertIsNone(self.db.login())

    def test_unsupported_hash_does_not_fall_back(self):
        self.cursor.fetchone.return_value["heslo"] = "unknown$salt$value"
        self.db.password = "unknown$salt$value"
        with patch.dict(os.environ, {"ALLOW_LEGACY_PASSWORDS": "1"}):
            self.assertIsNone(self.db.login())

    def test_unknown_user(self):
        self.cursor.fetchone.return_value = None
        self.assertIsNone(self.db.login())

    def test_sql_injection_is_bound_as_a_value(self):
        self.db.username = "' OR 1=1 --"
        self.cursor.fetchone.return_value = None
        self.assertIsNone(self.db.login())
        sql, values = self.cursor.execute.call_args.args
        self.assertNotIn(self.db.username, sql)
        self.assertEqual(values, (self.db.username,))

    def test_plaintext_disabled_by_default(self):
        self.cursor.fetchone.return_value["heslo"] = "correct horse"
        with patch.dict(os.environ, {"ALLOW_LEGACY_PASSWORDS": "0"}):
            self.assertIsNone(self.db.login())

    def test_legacy_password_is_upgraded(self):
        self.cursor.fetchone.return_value["heslo"] = "correct horse"
        with patch.dict(os.environ, {"ALLOW_LEGACY_PASSWORDS": "1"}):
            self.assertIsNotNone(self.db.login())
        sql, values = self.cursor.execute.call_args.args
        self.assertIn("AND heslo = %s", sql)
        self.assertTrue(check_password_hash(values[0], "correct horse"))
        self.assertEqual(values[1:], (7, "correct horse"))
        self.connection.commit.assert_called_once()

    def test_concurrent_password_change_rejects_legacy_login(self):
        self.cursor.fetchone.return_value["heslo"] = "correct horse"
        self.cursor.rowcount = 0
        with patch.dict(os.environ, {"ALLOW_LEGACY_PASSWORDS": "1"}):
            self.assertIsNone(self.db.login())
        self.connection.commit.assert_not_called()

    def test_connection_failure_fails_closed(self):
        with patch.object(self.db, "_get_connection", side_effect=mysql.connector.Error("offline")):
            self.assertIsNone(self.db.login())
