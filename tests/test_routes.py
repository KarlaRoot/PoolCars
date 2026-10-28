import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "test-only-key")
import main


class RouteTests(unittest.TestCase):
    def setUp(self):
        main.app.config.update(TESTING=True)
        self.client = main.app.test_client()
        self.db_patch = patch("main.Databaze", autospec=True)
        self.factory = self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.db = self.factory.return_value
        self.db.get_employee_choices.return_value = [{"idZamestnance": 7, "jmeno": "Alice", "prijmeni": "Test"}]
        self.db.get_car_info.return_value = [{"idAuta": 3, "spz": "TEST123"}]
        self.db.get_employee_info_by_id.return_value = {
            "idZamestnance": 7, "jmeno": "Alice", "prijmeni": "Test", "divize": "IT", "oddeleni": "BI",
        }
        self.db.get_car_info_by_spz.return_value = {"idAuta": 3, "spz": "TEST123"}
        self.db.insert_rezervace_if_available.return_value = (True, None)
        self.data = dict(idZamestnance="7", spz="TEST123", stavRezervace="nova",
                         prevzetiDne="2026-11-01", odevzdaniDne="2026-11-02")

    def sign_in(self, admin=False):
        with self.client.session_transaction() as session:
            session.update(user="alice", employee_id=7, admin=admin, _csrf_token="test-token")

    def post(self, path, data=None):
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-token"
        return self.client.post(path, data={**(data or {}), "csrf_token": "test-token"})

    def test_public_pages(self):
        for path in ("/", "/login"):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_reservation_requires_login(self):
        self.assertEqual(self.client.get("/rezervace").status_code, 302)
        self.assertEqual(self.post("/insertRezervace", self.data).status_code, 302)
        self.db.insert_rezervace_if_available.assert_not_called()

    def test_admin_pages_deny_regular_user(self):
        self.sign_in()
        for path in ("/auta", "/zamestnanci"):
            self.assertEqual(self.client.get(path).status_code, 302)
        self.assertEqual(self.post("/submit", {}).status_code, 302)
        self.assertEqual(self.post("/zamestnanci", {}).status_code, 302)

    def test_admin_pages_allow_admin(self):
        self.sign_in(admin=True)
        for path in ("/auta", "/zamestnanci"):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_csrf_missing_mismatched_and_unicode(self):
        self.sign_in()
        for token in (None, "wrong", "žluťoučký"):
            data = dict(self.data)
            if token is not None:
                data["csrf_token"] = token
            self.assertEqual(self.client.post("/insertRezervace", data=data).status_code, 400)
        self.db.insert_rezervace_if_available.assert_not_called()

    def test_successful_login_clears_old_session_and_string_zero_is_not_admin(self):
        self.db.login.return_value = {"login": "alice", "idZamestnance": 7, "admin": "0"}
        with self.client.session_transaction() as session:
            session["old"] = "discard"
        self.assertEqual(self.post("/login", {"username": "alice", "password": "password"}).status_code, 302)
        with self.client.session_transaction() as session:
            self.assertEqual(session["employee_id"], 7)
            self.assertFalse(session["admin"])
            self.assertNotIn("old", session)
            self.assertNotIn("_csrf_token", session)

    def test_failed_login_does_not_create_authenticated_session(self):
        self.db.login.return_value = None
        self.post("/login", {"username": "alice", "password": "wrong"})
        with self.client.session_transaction() as session:
            self.assertNotIn("user", session)

    def test_empty_login(self):
        self.assertEqual(self.post("/login").status_code, 400)
        self.db.login.assert_not_called()

    def test_logout_requires_post_and_csrf(self):
        self.sign_in()
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertEqual(self.client.post("/logout").status_code, 400)
        self.assertEqual(self.post("/logout").status_code, 302)
        with self.client.session_transaction() as session:
            self.assertNotIn("user", session)

    def test_employee_detail_permissions(self):
        self.sign_in()
        self.assertEqual(self.client.get("/getEmployeeInfo?employee_id=8").status_code, 403)
        self.db.get_employee_info_by_id.assert_not_called()
        self.assertEqual(self.client.get("/getEmployeeInfo?employee_id=7").status_code, 200)

    def test_employee_choices_and_car_id_render(self):
        self.sign_in()
        response = self.client.get("/rezervace")
        self.assertEqual(response.status_code, 200)
        self.db.get_employee_choices.assert_called_with(employee_id=7)
        self.assertIn(b'data-id="3"', response.data)

    def test_reservation_for_another_employee_is_rejected(self):
        self.sign_in()
        self.assertEqual(self.post("/insertRezervace", {**self.data, "idZamestnance": "8"}).status_code, 302)
        self.db.insert_rezervace_if_available.assert_not_called()

    def test_admin_can_reserve_for_another_employee(self):
        self.sign_in(admin=True)
        self.assertEqual(self.post("/insertRezervace", self.data).status_code, 302)
        self.db.insert_rezervace_if_available.assert_called_once()

    def test_invalid_dates_and_missing_fields(self):
        self.sign_in()
        for changes in ({"spz": ""}, {"prevzetiDne": "invalid"}, {"odevzdaniDne": "2026-10-01"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.post("/insertRezervace", {**self.data, **changes}).status_code, 400)
        self.db.insert_rezervace_if_available.assert_not_called()

    def test_invalid_mileage(self):
        self.sign_in()
        for changes in ({"kmPredJizdou": "-1"}, {"kmPoJizde": "abc"},
                        {"kmPredJizdou": "100", "kmPoJizde": "99"},
                        {"kmPredJizdou": "100", "kmPoJizde": "110", "najetoKm": "20"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.post("/insertRezervace", {**self.data, **changes}).status_code, 400)
        self.db.insert_rezervace_if_available.assert_not_called()

    def test_unknown_employee_or_car(self):
        self.sign_in()
        for method in (self.db.get_employee_info_by_id, self.db.get_car_info_by_spz):
            original = method.return_value
            method.return_value = {}
            self.assertEqual(self.post("/insertRezervace", self.data).status_code, 400)
            method.return_value = original
        self.db.insert_rezervace_if_available.assert_not_called()

    def test_success_redirects_and_uses_server_identity_and_null_mileage(self):
        self.sign_in()
        response = self.post("/insertRezervace", {**self.data, "jmeno": "FORGED", "divize": "FORGED", "idAuta": "99"})
        self.assertEqual(response.status_code, 302)
        args = self.db.insert_rezervace_if_available.call_args.args
        self.assertEqual(args[:7], (7, "Alice", "Test", "IT", "BI", 3, "TEST123"))
        self.assertEqual(args[10:13], (None, None, None))
        self.assertIn(b"Reservation saved.", self.client.get(response.location).data)

    def test_distance_is_calculated(self):
        self.sign_in()
        self.post("/insertRezervace", {**self.data, "kmPredJizdou": "100", "kmPoJizde": "110"})
        self.assertEqual(self.db.insert_rezervace_if_available.call_args.args[10:13], (100, 110, 10))

    def test_conflict_and_database_error_are_not_reported_as_success(self):
        self.sign_in()
        for result, status in (((False, "conflict"), 409), ((False, "error"), 500)):
            self.db.insert_rezervace_if_available.return_value = result
            self.assertEqual(self.post("/insertRezervace", self.data).status_code, status)

    def test_result_validates_year_and_month(self):
        for year, month in (("10000", "1"), ("2026", "13")):
            self.assertEqual(self.post("/result", {"rok": year, "mesic": month}).status_code, 302)
        self.assertEqual(self.post("/result", {"rok": "2026", "mesic": "11"}).status_code, 200)
