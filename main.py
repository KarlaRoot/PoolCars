from flask import Flask, render_template, request, flash, session, make_response, redirect, url_for
from PoolCar import Databaze


app = Flask(__name__)
app.secret_key = "ultratajneheslo123"

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db_instance = Databaze(username, password)
        resultlogin = db_instance.login()
        if resultlogin == True:
            session["user"] = username
            return redirect(url_for('home'))
        else:
            print("Přihlášení neúspěšné. Zkus to znovu. Main")
        return render_template('login.html')
    return render_template('login.html')


@app.route('/auta')
def auta():
    try:
        session["admin"]
        return render_template('auta.html')
    except:
        return redirect(url_for('home'))
   
@app.route('/zamestnanci', methods=['GET', 'POST'])
def zamestnanci():
    
        try:
                admin = session.get("admin", False)
                if request.method == 'POST':
                    idZamestnance = request.form.get('idZamestnance')
                    firstName = request.form.get('firstName')
                    lastName = request.form.get('lastName')
                    login = request.form.get('login')
                    password = request.form.get('password')
                    email = request.form.get('email')
                    division = request.form.get('division')
                    department = request.form.get('department')

                    db = Databaze(username='your_username', password='your_password')
                    
                    db.insert_employee(idZamestnance, firstName, lastName, login, password, email, division, department)

            
                    return render_template('zamestnanci.html', data={'idZamestnance': idZamestnance, 'firstName': firstName, 'lastName': lastName, 'login': login, 'password': password, 'email': email, 'division': division, 'department': department})
        except:
                return redirect(url_for('home'))
        
        return render_template('zamestnanci.html')
  
   

@app.route("/result", methods = ["POST"])
def result():
    selected_year = int(request.form['rok'])
    selected_month = int(request.form['mesic'])
    



@app.route('/rezervace', methods=['GET', 'POST'])
def rezervace():
    if request.method == 'POST':
        idZamestnance = request.form.get('idZamestnance')
        employee_info = {'idZamestnance': '', 'jmeno': ''}

        # Získání příjmení zaměstnanců
        db = Databaze(username='your_username', password='your_password')
        surnames = db.get_employee_surnames()

        # Výpis příjmení do konzole
        print("Surnames in /rezervace:", surnames)
        # Přesměrování na jinou cestu pro zpracování formuláře
        return redirect(url_for('insert_rezervace'))
    else:
      
        # Set default values for employee_info
        employee_info = {'idZamestnance': '', 'jmeno': ''}

        # Získání příjmení zaměstnanců
        db = Databaze(username='your_username', password='your_password')
        surnames = db.get_employee_surnames()

        # Výpis příjmení do konzole
        print("Surnames in /rezervace:", surnames)

    return render_template('rezervace.html', employee_info=employee_info, surnames=surnames)

@app.route('/insertRezervace', methods=['POST'])
def insert_rezervace():
    if request.method == 'POST':
        # Zpracování odeslaného formuláře
        idZamestnance = request.form.get('idZamestnance')
        jmeno = request.form.get('jmeno')
        idAuta = request.form.get('idAuta')
        spz = request.form.get('spz')
        stavRezervace = request.form.get('stavRezervace')
        kmPredJizdou = request.form.get('kmPredJizdou')
        kmPoJizde = request.form.get('kmPoJizde')
        najetoKm = request.form.get('najetoKm')
        poskozeni = request.form.get('poskozeni')
        prevzetiDne = request.form.get('prevzetiDne')
        odevzdaniDne = request.form.get('odevzdaniDne')
        divize = request.form.get('divize')
        oddeleni = request.form.get('oddeleni')

       
        db = Databaze(username='your_username', password='your_password')
        car_info = db.get_car_info()
        
        

        existing_reservation = db.check_existing_reservation(spz, prevzetiDne, odevzdaniDne)

        surnames = []  
        employee_info = None  

         # rezervace již existuje
        if existing_reservation:
            return render_template('rezervace.html', car_info=car_info, surnames=surnames,
                                employee_info=employee_info, error="Reservation already exists for the specified period.")

        # Získání příjmení zaměstnanců z formuláře
        prijmeni = request.form.get('prijmeni')
        prijmeni_list = [prijmeni] if prijmeni else []
        print("spz:", spz)

        # Iterace přes každé příjmení a provedení rezervace
        for prijmeni in prijmeni_list:
            db.inzert_rezervace(
                idZamestnance, jmeno, prijmeni, divize, oddeleni,
                idAuta, spz, stavRezervace, prevzetiDne, odevzdaniDne,
                kmPredJizdou, kmPoJizde, najetoKm, poskozeni
            )
        spz = request.form.get('spz')

        
        if prijmeni_list:
            surname = prijmeni_list[0]
            # Získání aktuálních hodnot pro 'spz' a příjmení zaměstnanců
            surnames = [surname for surname in db.get_employee_surnames()]

            # Získání informací o zaměstnanci podle vybraného příjmení
            employee_info = db.get_employee_info_by_surname(surname)
            print("Surnames:", surnames)

            return render_template('rezervace.html', car_info=car_info, surnames=surnames,
                                   employee_info=employee_info if 'employee_info' in locals() else None)
        else:
          
            return render_template('rezervace.html', car_info=car_info, surnames=[], employee_info=None)

    # GET
    return render_template('rezervace.html')


@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        vin = request.form.get('vin')
        spz = request.form.get('spz')
        znacka = request.form.get('znacka')
        model = request.form.get('model')
        rok_vyroby = request.form.get('rokVyroby')
        najeto_km = request.form.get('najetoKm')

        print(f"Odeslaná data: {vin}, {spz}, {znacka}, {model}, {rok_vyroby}, {najeto_km}")

        db = Databaze(username='your_username', password='your_password')
        db.insert_car(vin, spz, znacka, model, rok_vyroby, najeto_km)

        print(f"Data byla úspěšně vložena do databáze: {vin}, {spz}, {znacka}, {model}, {rok_vyroby}, {najeto_km}")

        return render_template('auta.html')





@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)


"""
@app.route("/zamestnanci")
if session admin == true
prokliky na dalsi formulare
session [user]
session [admin]
"""
