import logging
import os

import mysql.connector as dblib
from werkzeug.security import check_password_hash, generate_password_hash


logger = logging.getLogger(__name__)
PASSWORD_HASH_METHOD = os.environ.get("PASSWORD_HASH_METHOD", "pbkdf2:sha256")


class Databaze:
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.config = {
            "host": os.environ.get("DB_HOST", "localhost"),
            "user": os.environ.get("DB_USER", "root"),
            "password": os.environ.get("DB_PASSWORD"),
            "database": os.environ.get("DB_NAME", "poolcars"),
        }

        db_timeout = os.environ.get("DB_CONNECTION_TIMEOUT", "3")
        try:
            self.config["connection_timeout"] = int(db_timeout)
        except ValueError:
            logger.warning("Ignoring invalid DB_CONNECTION_TIMEOUT value: %s", db_timeout)

        db_port = os.environ.get("DB_PORT")
        if db_port:
            try:
                self.config["port"] = int(db_port)
            except ValueError:
                logger.warning("Ignoring invalid DB_PORT value: %s", db_port)

    def _get_connection(self):
        return dblib.connect(**self.config)

    def _close(self, cursor=None, db=None):
        if cursor is not None:
            cursor.close()
        if db is not None:
            db.close()

    def _execute_write(self, sql, values, success_message, error_message):
        db = None
        cursor = None
        try:
            db = self._get_connection()
            cursor = db.cursor()
            cursor.execute(sql, values)
            db.commit()
            logger.info(success_message)
            return True
        except dblib.Error:
            if db is not None:
                db.rollback()
            logger.exception(error_message)
            return False
        finally:
            self._close(cursor, db)

    def login(self):
        """Validate user credentials and return the employee row when valid."""
        if not self.username or self.password is None:
            logger.warning("Login attempt without username or password.")
            return None

        db = None
        cursor = None
        sql = (
            "SELECT idZamestnance, login, admin, heslo "
            "FROM zamestnanci "
            "WHERE login = %s "
            "LIMIT 1"
        )

        try:
            db = self._get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(sql, (self.username,))
            user = cursor.fetchone()

            if not user or not self._password_matches(user.get("heslo")):
                return None

            if user.get("heslo") == self.password:
                self._update_password_hash(cursor, db, user["idZamestnance"], self.password)

            user.pop("heslo", None)
            return user
        except dblib.Error:
            logger.exception("Failed to validate login credentials.")
            return None
        finally:
            self._close(cursor, db)

    def _password_matches(self, stored_password):
        if not stored_password:
            return False

        try:
            if check_password_hash(stored_password, self.password):
                return True
        except ValueError:
            logger.warning("Stored password for %s is not a supported hash.", self.username)

        # Temporary compatibility path for old rows that still contain plaintext.
        return stored_password == self.password

    def _update_password_hash(self, cursor, db, employee_id, password):
        password_hash = generate_password_hash(password, method=PASSWORD_HASH_METHOD)
        cursor.execute(
            "UPDATE zamestnanci SET heslo = %s WHERE idZamestnance = %s",
            (password_hash, employee_id),
        )
        db.commit()
        logger.info("Upgraded plaintext password to a hash for employee %s.", employee_id)

    def insert_car(self, vin, spz, znacka, model, rok_vyroby, najeto_km):
        sql = (
            "INSERT INTO auta (vin, spz, znacka, model, rokVyroby, najetoKm) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        values = (vin, spz, znacka, model, rok_vyroby, najeto_km)
        return self._execute_write(
            sql,
            values,
            "Car was inserted into the database.",
            "Failed to insert car into the database.",
        )

    def get_car_info(self):
        db = None
        cursor = None
        try:
            db = self._get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id AS idAuta, spz FROM auta ORDER BY spz")
            return cursor.fetchall()
        except dblib.Error:
            logger.exception("Failed to load car information.")
            return []
        finally:
            self._close(cursor, db)

    def get_car_info_by_spz(self, spz):
        db = None
        cursor = None
        try:
            db = self._get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id AS idAuta, spz FROM auta WHERE spz = %s LIMIT 1", (spz,))
            return cursor.fetchone() or {}
        except dblib.Error:
            logger.exception("Failed to load car information for SPZ %s.", spz)
            return {}
        finally:
            self._close(cursor, db)

    def insert_employee(
        self,
        id_zamestnance,
        jmeno,
        prijmeni,
        login,
        password,
        email,
        division,
        department,
    ):
        sql = (
            "INSERT INTO zamestnanci "
            "(idZamestnance, jmeno, prijmeni, login, heslo, email, divize, oddeleni) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        )
        password_hash = generate_password_hash(password, method=PASSWORD_HASH_METHOD)
        values = (
            id_zamestnance,
            jmeno,
            prijmeni,
            login,
            password_hash,
            email,
            division,
            department,
        )
        return self._execute_write(
            sql,
            values,
            "Employee was inserted into the database.",
            "Failed to insert employee into the database.",
        )

    def _reservation_sql_and_values(
        self,
        id_zamestnance,
        jmeno,
        prijmeni,
        divize,
        oddeleni,
        id_auta,
        spz,
        stav_rezervace,
        prevzeti_dne,
        odevzdani_dne,
        km_pred_jizdou,
        km_po_jizde,
        najeto_km,
        poskozeni,
    ):
        sql = (
            "INSERT INTO rezervace "
            "(idZamestnance, jmeno, prijmeni, divize, oddeleni, idAuta, spz, "
            "stavRezervace, prevzetiDne, odevzdaniDne, kmPredJizdou, "
            "kmPoJizde, najetoKm, poskozeni) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        values = (
            id_zamestnance,
            jmeno,
            prijmeni,
            divize,
            oddeleni,
            id_auta,
            spz,
            stav_rezervace,
            prevzeti_dne,
            odevzdani_dne,
            km_pred_jizdou,
            km_po_jizde,
            najeto_km,
            poskozeni,
        )
        return sql, values

    def insert_rezervace_if_available(
        self,
        id_zamestnance,
        jmeno,
        prijmeni,
        divize,
        oddeleni,
        id_auta,
        spz,
        stav_rezervace,
        prevzeti_dne,
        odevzdani_dne,
        km_pred_jizdou,
        km_po_jizde,
        najeto_km,
        poskozeni,
    ):
        db = None
        cursor = None
        locked = False
        conflict_sql = (
            "SELECT 1 FROM rezervace "
            "WHERE spz = %s "
            "AND prevzetiDne <= %s "
            "AND odevzdaniDne >= %s "
            "LIMIT 1"
        )
        insert_sql, values = self._reservation_sql_and_values(
            id_zamestnance,
            jmeno,
            prijmeni,
            divize,
            oddeleni,
            id_auta,
            spz,
            stav_rezervace,
            prevzeti_dne,
            odevzdani_dne,
            km_pred_jizdou,
            km_po_jizde,
            najeto_km,
            poskozeni,
        )

        try:
            db = self._get_connection()
            cursor = db.cursor()
            cursor.execute("LOCK TABLES rezervace WRITE")
            locked = True
            cursor.execute(conflict_sql, (spz, odevzdani_dne, prevzeti_dne))

            if cursor.fetchone() is not None:
                return False, "conflict"

            cursor.execute(insert_sql, values)
            db.commit()
            logger.info("Reservation was inserted into the database.")
            return True, None
        except dblib.Error:
            if db is not None:
                db.rollback()
            logger.exception("Failed to insert reservation into the database.")
            return False, "error"
        finally:
            if locked and cursor is not None:
                try:
                    cursor.execute("UNLOCK TABLES")
                except dblib.Error:
                    logger.exception("Failed to unlock rezervace table.")
            self._close(cursor, db)

    def insert_rezervace(self, *args, **kwargs):
        saved, _reason = self.insert_rezervace_if_available(*args, **kwargs)
        return saved

    def inzert_rezervace(self, *args, **kwargs):
        return self.insert_rezervace(*args, **kwargs)

    def get_employee_choices(self, employee_id=None):
        db = None
        cursor = None
        sql = (
            "SELECT idZamestnance, jmeno, prijmeni, divize, oddeleni "
            "FROM zamestnanci"
        )
        values = ()

        if employee_id is not None:
            sql += " WHERE idZamestnance = %s"
            values = (employee_id,)

        sql += " ORDER BY prijmeni, jmeno"

        try:
            db = self._get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(sql, values)
            return cursor.fetchall()
        except dblib.Error:
            logger.exception("Failed to load employee choices.")
            return []
        finally:
            self._close(cursor, db)

    def get_employee_surnames(self):
        db = None
        cursor = None
        try:
            db = self._get_connection()
            cursor = db.cursor()
            cursor.execute("SELECT prijmeni FROM zamestnanci ORDER BY prijmeni")
            return [surname[0] for surname in cursor.fetchall()]
        except dblib.Error:
            logger.exception("Failed to load employee surnames.")
            return []
        finally:
            self._close(cursor, db)

    def get_employee_info_by_id(self, employee_id):
        db = None
        cursor = None
        sql = (
            "SELECT idZamestnance, jmeno, prijmeni, divize, oddeleni "
            "FROM zamestnanci "
            "WHERE idZamestnance = %s "
            "LIMIT 1"
        )

        try:
            db = self._get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(sql, (employee_id,))
            return cursor.fetchone() or {}
        except dblib.Error:
            logger.exception("Failed to load employee information.")
            return {}
        finally:
            self._close(cursor, db)

    def get_employee_info_by_surname(self, surname):
        db = None
        cursor = None
        sql = (
            "SELECT idZamestnance, jmeno, prijmeni, divize, oddeleni "
            "FROM zamestnanci "
            "WHERE prijmeni = %s "
            "ORDER BY prijmeni, jmeno"
        )

        try:
            db = self._get_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(sql, (surname,))
            return cursor.fetchall()
        except dblib.Error:
            logger.exception("Failed to load employee information.")
            return []
        finally:
            self._close(cursor, db)

    def check_existing_reservation(self, spz, prevzeti_dne, odevzdani_dne):
        db = None
        cursor = None
        sql = (
            "SELECT 1 FROM rezervace "
            "WHERE spz = %s "
            "AND prevzetiDne <= %s "
            "AND odevzdaniDne >= %s "
            "LIMIT 1"
        )

        try:
            db = self._get_connection()
            cursor = db.cursor()
            cursor.execute(sql, (spz, odevzdani_dne, prevzeti_dne))
            return cursor.fetchone() is not None
        except dblib.Error:
            logger.exception("Failed to check existing reservations.")
            return False
        finally:
            self._close(cursor, db)
