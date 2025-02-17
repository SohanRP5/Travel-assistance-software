from flask import Flask, render_template, request, redirect, url_for, session, flash
import wikipedia
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

db_config = {
    'host': 'localhost',
    'user': 'root',  
    'password': '12345',  
    'database': 'travel_guide',
    'port': 3307 
}

def save_contact_to_db(name, email, message):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO contact_info (name, email, message) VALUES (%s, %s, %s)",
            (name, email, message)
        )
        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

# Function to get Wikipedia info
def get_wikipedia_info(place_name, lang='en'):
    wikipedia.set_lang(lang)
    try:
        summary = wikipedia.summary(place_name, sentences=3)
        full_page = wikipedia.page(place_name)
        images = full_page.images[:3]
        return {'summary': summary, 'images': images, 'url': full_page.url}
    except wikipedia.exceptions.DisambiguationError as e:
        return {'error': f"Multiple results found for {place_name}. Please refine your search."}
    except wikipedia.exceptions.PageError:
        return {'error': f"No results found for {place_name}."}
    except Exception as e:
        return {'error': str(e)}


@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))  
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    lang = request.args.get('lang', 'en')
    place_details = get_wikipedia_info(query, lang)

    booking_info = get_booking_info(query)

    return render_template('result.html', place_details=place_details, place_name=query, booking_info=booking_info)

def get_booking_info(destination_name):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("SELECT resort_name, available_rooms, price_per_night FROM resorts WHERE destination = %s", (destination_name,))
        resorts = cursor.fetchall()
        cursor.close()
        connection.close()
        
        # Return booking info as a dictionary
        return {'resorts': resorts}
    except mysql.connector.Error as err:
        print(f"Error fetching booking info: {err}")
        return {'error': 'Could not fetch booking information'}

@app.route('/destination/<name>')
def destination_detail(name):
    return render_template('detail.html', name=name)

@app.route('/book/<destination>', methods=['GET', 'POST'])
def book(destination):
    if request.method == 'POST':
        resort_name = request.form['resort-name']
        check_in = request.form['check-in']
        check_out = request.form['check-out']
        rooms = request.form['rooms']
        accessories = ', '.join(request.form.getlist('accessories'))
        special_request = request.form['special-request']

        # Save booking info to database
        save_booking_to_db(destination, resort_name, check_in, check_out, rooms, accessories, special_request)
        return redirect(url_for('thank_you'))

    supported_destinations = ['tokyo', 'paris', 'newyork', 'london', 'sydney']
    if destination.lower() in supported_destinations:
        return render_template('book.html', destination=destination)
    return redirect(url_for('home'))

def save_booking_to_db(destination, resort_name, check_in, check_out, rooms, accessories, special_request):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO bookings (destination, resort_name, check_in, check_out, rooms, accessories, special_request) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (destination, resort_name, check_in, check_out, rooms, accessories, special_request)
        )
        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        save_contact_to_db(name, email, message)
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('thank_you'))
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute("SELECT id, username, password FROM users_info WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            connection.close()

            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid credentials. Please try again.', 'danger')
                return render_template('login.html')
        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')

        password_hash = generate_password_hash(password)

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO users_info (username, email, password) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            connection.commit()
            cursor.close()
            connection.close()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')
            return render_template('signup.html')

    return render_template('signup.html')

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('services'))

@app.route('/services', methods=['GET', 'POST'])
def services():
    if request.method == 'POST':
        place_name = request.form['place_name']
        description = request.form['description']
        rating = request.form['rating']

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            cursor.execute(
                "INSERT INTO places (name, description, rating) VALUES (%s, %s, %s)",
                (place_name, description, rating)
            )
            connection.commit()
            cursor.close()
            connection.close()
            flash('Place added successfully!', 'success')
            return redirect(url_for('services'))

        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')
            return render_template('error.html', error="Could not insert data into the database.")

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM places")
        places_data = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('services.html', places=places_data)

    except mysql.connector.Error as err:
        flash(f"Error: {err}", 'danger')
        return render_template('error.html', error="Could not fetch data from the database.")

if __name__ == '__main__':
    app.run(debug=True)
