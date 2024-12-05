import mysql.connector as dblib
from flask import session
from flask import jsonify, request
import logging

class Databaze:
        def __init__(self, username, password):
                self.username = username
                self.password = password


        def login(self):
                db = dblib.connect(
                host = "localhost",
                user = "root",
                password = "",
                database = "poolcars"
                 )

                cursor = db.cursor(dictionary=True)

                sql = f"Select * from zamestnanci where login ='{self.username}' and heslo = '{self.password}'" 
                cursor.execute(sql)
        
                result = cursor.fetchone()

                db.close()

                resultlogin = False

                if result:
                        if len(result) > 0:
                                print("Přihlášení úspěšné! Poolcar")
                                if result["admin"] == 1:
                                        session["admin"] = True
                                        print(session)
                                resultlogin = True
                        else:
                                print("Přihlášení neúspěšné. Zkontrolujte uživatelské jméno a heslo.Poolcar")
                                resultlogin = False

                return resultlogin
       
        
        def insert_car(self, vin, spz, znacka, model, rok_vyroby, najeto_km):
                db = dblib.connect(
                host="localhost",
                user="root",
                password="",
                database="poolcars"
                )

                cursor = db.cursor()

                # Použijte placeholdery pro zabránění SQL injection
                sql = "INSERT INTO auta (vin, spz, znacka, model, rokVyroby, najetoKm) VALUES (%s, %s, %s, %s, %s, %s)"
                values = (vin, spz, znacka, model, rok_vyroby, najeto_km)

                try:
                        cursor.execute(sql, values)
                        db.commit()
                        print("Data byla úspěšně vložena do databáze.")
                except Exception as e:
                        db.rollback()
                        print(f"Chyba při vkládání dat do databáze: {e}")
                finally:
                        db.close()    

        def get_car_info(self):
                db = dblib.connect(
                        host="localhost",
                        user="root",
                        password="",
                        database="poolcars"
                )

                cursor = db.cursor(dictionary=True)

                sql = "SELECT * FROM auta"
                cursor.execute(sql)

                result = cursor.fetchall()
                db.close()

                car_info = [{"spz": car["spz"]} for car in result]


                return car_info   
        
        def insert_employee(self, idZamestnance, jmeno, prijmeni, login, password, email, division, department):
                db = dblib.connect(
                host="localhost",
                user="root",
                password="",
                database="poolcars"
                )

                cursor = db.cursor()

                sql = "INSERT INTO zamestnanci (idZamestnance, jmeno, prijmeni, login, heslo, email, divize, oddeleni) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                values = (idZamestnance, jmeno, prijmeni, login, password, email, division, department)

                try:
                        cursor.execute(sql, values)
                        db.commit()
                        print("Zaměstnanec byl úspěšně vložen do databáze.")
                except Exception as e:
                        db.rollback()
                        print(f"Chyba při vkládání zaměstnance do databáze: {e}")
                finally:
                        db.close()
         

        def inzert_rezervace(self, idZamestnance, jmeno, prijmeni, divize, oddeleni, idAuta, spz, stavRezervace, prevzetiDne, odevzdaniDne, kmPredJizdou, kmPoJizde, najetoKm, poskozeni):
                db = dblib.connect(
                host="localhost",
                user="root",
                password="",
                database="poolcars"
                )

                cursor = db.cursor()

                sql = "INSERT INTO rezervace (idZamestnance, jmeno, prijmeni, divize, oddeleni, idAuta, spz, stavRezervace, prevzetiDne, odevzdaniDne, kmPredJizdou, kmPoJizde, najetoKm, poskozeni) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                values = (idZamestnance, jmeno, prijmeni, divize, oddeleni, idAuta, spz, stavRezervace, prevzetiDne, odevzdaniDne, kmPredJizdou, kmPoJizde, najetoKm, poskozeni)

                try:
                        cursor.execute(sql, values)
                        db.commit()
                        print("Data byla úspěšně vložena do databáze.")
                except Exception as e:
                        db.rollback()
                        print(f"Chyba při vkládání dat do databáze: {e}")
                finally:
                        db.close()
         
        def get_employee_surnames(self):
                db = dblib.connect(
                        host="localhost",
                        user="root",
                        password="",
                        database="poolcars"
                )

                cursor = db.cursor()

                sql = "SELECT prijmeni FROM zamestnanci"
                cursor.execute(sql)

                # Fetch všechny řádky
                result = cursor.fetchall()
                db.close()

                # Použijte index 0 pro získání hodnoty z tuplu
                surnames = [surname[0] for surname in result]

                return surnames

        

        
        
        def get_employee_info_by_surname(self, surname):
                db = dblib.connect(
                        host="localhost",
                        user="root",
                        password="",
                        database="poolcars"
                )

                
                cursor = db.cursor()

                sql = "SELECT * FROM zamestnanci WHERE prijmeni = %s"
                values = (surname,)

                try:
                        cursor.execute(sql, values)
                        result = cursor.fetchone()  # Použijeme fetchone místo fetchall

                        print(f"Výsledek dotazu: {result}")

                        if result:
                                employee_info = {
                                'idZamestnance': result[0],
                                'jmeno': result[1],
                                
                                # ... další pole
                        }
                                return employee_info
                        else:
                                return {}
                except Exception as e:
                        print(f"Chyba při získávání informací o zaměstnanci: {e}")
                        return {}
                finally:
                        db.close()
                        
        def check_existing_reservation(self, spz, prevzetiDne, odevzdaniDne):
                db = dblib.connect(
                        host="localhost",
                        user="root",
                        password="",
                        database="poolcars"
                )
                try:
                        cursor = db.cursor()

                        sql = "SELECT * FROM rezervace WHERE spz = %s AND ((prevzetiDne <= %s AND odevzdaniDne >= %s) OR (prevzetiDne <= %s AND odevzdaniDne >= %s))"
                        values = (spz, odevzdaniDne, odevzdaniDne, prevzetiDne, prevzetiDne)

                        logging.debug(f"Executing SQL query: {sql} with values: {values}")

                        cursor.execute(sql, values)
                        result = cursor.fetchall()
                        db.close()

                        logging.debug(f"SQL query result: {result}")

                        return bool(result)
                except Exception as e:
                        logging.error(f"Error in check_existing_reservation: {e}")
                        return False
       