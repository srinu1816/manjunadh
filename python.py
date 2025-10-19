from flask import Flask, jsonify, render_template, request
import math
import random
import os
import pymysql
from datetime import datetime
import time
import traceback
import socket

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'coupon-db.c7i4sqkq8oou.eu-west-1.rds.amazonaws.com',
    'user': 'admin', 
    'password': '3j86iHyknpE4knYimwfn',
    'database': 'coupon_db',
    'port': 3306,
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10
}

def get_db_connection():
    """Create database connection with detailed error reporting"""
    try:
        print(f"🔗 Connecting to {DB_CONFIG['host']}...")
        connection = pymysql.connect(**DB_CONFIG)
        print("✅ Database connection successful")
        return connection, "Connected successfully"
    except pymysql.MySQLError as e:
        error_code = e.args[0]
        error_message = e.args[1] if len(e.args) > 1 else str(e)
        
        print(f"❌ MySQL Error {error_code}: {error_message}")
        
        # Common error codes and their meanings
        error_messages = {
            1045: "Access denied - check username/password",
            1049: f"Database '{DB_CONFIG['database']}' does not exist",
            2003: "Cannot connect to MySQL server - check security groups and public access",
            1044: "Access denied for database - check user permissions",
            2005: "Unknown MySQL server host - check RDS endpoint",
            1698: "Access denied for user - authentication plugin issue"
        }
        
        user_message = error_messages.get(error_code, error_message)
        return None, user_message
        
    except Exception as e:
        print(f"❌ Unexpected connection error: {e}")
        return None, f"Unexpected error: {str(e)}"

def init_database():
    """Initialize database tables"""
    print("🔄 Attempting database initialization...")
    
    connection, message = get_db_connection()
    if not connection:
        print(f"💥 Cannot initialize database: {message}")
        return False, message
    
    try:
        with connection.cursor() as cursor:
            # Create coupons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coupons (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    coupon_code VARCHAR(50) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used BOOLEAN DEFAULT FALSE,
                    used_at TIMESTAMP NULL
                )
            ''')
            print("✅ Coupons table ready")
            
            # Create usage_logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    coupon_code VARCHAR(50) NOT NULL,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45)
                )
            ''')
            print("✅ Usage_logs table ready")
            
        connection.commit()
        print("🎉 Database initialization completed successfully")
        return True, "Database initialized successfully"
        
    except Exception as e:
        error_msg = f"Database initialization failed: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
    finally:
        connection.close()

def generate_coupon_code():
    """Generate a unique coupon code"""
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))

def simulate_cpu_load():
    """Simulate moderate CPU load"""
    for i in range(1, 10000):
        math.sqrt(i)

@app.route('/')
def home():
    """Main page route"""
    try:
        # Simulate CPU load
        simulate_cpu_load()
        
        # Generate coupon
        coupon = generate_coupon_code()
        print(f"🎫 Generated coupon: {coupon}")
        
        # Try to store in database
        connection, db_message = get_db_connection()
        db_status = "connected" if connection else "disconnected"
        
        if connection:
            try:
                with connection.cursor() as cursor:
                    # Insert coupon
                    cursor.execute(
                        'INSERT IGNORE INTO coupons (coupon_code) VALUES (%s)',
                        (coupon,)
                    )
                    
                    # Log generation
                    ip_address = request.remote_addr or 'unknown'
                    cursor.execute(
                        'INSERT INTO usage_logs (coupon_code, ip_address) VALUES (%s, %s)',
                        (coupon, ip_address)
                    )
                    
                connection.commit()
                print("✅ Coupon stored in database")
                db_message = "Coupon stored successfully"
                
            except Exception as e:
                print(f"⚠️ Failed to store coupon: {e}")
                db_status = "error"
                db_message = f"Storage error: {str(e)}"
            finally:
                connection.close()
        else:
            print(f"⚠️ Running without database storage: {db_message}")
        
        # Render template
        return render_template('index.html', 
                             coupon=coupon, 
                             db_status=db_status,
                             db_message=db_message,
                             status="generated")
        
    except Exception as e:
        print(f"💥 Critical error in home route: {e}")
        print(traceback.format_exc())
        # Fallback response
        coupon = generate_coupon_code()
        return f"""
        <html>
            <head><title>Random Coupon Generator</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>🎁 Random Coupon Generator</h1>
                <div style="background: linear-gradient(45deg, #ff6b6b, #ff8e53); color: white; padding: 20px; border-radius: 10px; margin: 20px;">
                    <h2>Your Random Coupon:</h2>
                    <div style="font-size: 2em; font-weight: bold;">{coupon}</div>
                </div>
                <p>Database Status: <strong>disconnected</strong></p>
                <p>Message: Running in offline mode</p>
                <button onclick="window.location.reload()" style="padding: 10px 20px; background: linear-gradient(45deg, #4776E6, #8E54E9); color: white; border: none; border-radius: 5px; cursor: pointer;">
                    Generate New Coupon
                </button>
            </body>
        </html>
        """

@app.route('/generate')
def generate_coupon():
    """API endpoint to generate a new coupon"""
    try:
        simulate_cpu_load()
        coupon = generate_coupon_code()
        
        connection, db_message = get_db_connection()
        db_status = "connected" if connection else "disconnected"
        
        if connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        'INSERT IGNORE INTO coupons (coupon_code) VALUES (%s)',
                        (coupon,)
                    )
                    
                    ip_address = request.remote_addr or 'unknown'
                    cursor.execute(
                        'INSERT INTO usage_logs (coupon_code, ip_address) VALUES (%s, %s)',
                        (coupon, ip_address)
                    )
                    
                connection.commit()
                db_message = "Coupon generated and stored"
            except Exception as e:
                print(f"❌ Failed to store coupon: {e}")
                db_status = "error"
                db_message = f"Storage error: {str(e)}"
            finally:
                connection.close()
        else:
            db_message = "Running in offline mode - coupon not stored"
        
        return jsonify({
            'coupon': coupon,
            'status': 'generated',
            'database': db_status,
            'message': db_message,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"💥 Error in generate route: {e}")
        return jsonify({
            'error': str(e),
            'coupon': generate_coupon_code(),  # Fallback coupon
            'database': 'error',
            'message': 'Using fallback coupon'
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        connection, message = get_db_connection()
        db_status = "healthy" if connection else "unhealthy"
        
        if connection:
            connection.close()
            
        return jsonify({
            'status': 'ok',
            'database': db_status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'database': 'unhealthy',
            'message': str(e)
        }), 500

# Initialize application
print("🚀 Starting Random Coupon Generator Application...")
print(f"📊 RDS Endpoint: {DB_CONFIG['host']}")
print(f"🔑 Database: {DB_CONFIG['database']}")
print(f"👤 Username: {DB_CONFIG['user']}")

# Initialize database
init_success, init_message = init_database()
if init_success:
    print("✅ Database initialization completed")
else:
    print(f"⚠️ Database initialization: {init_message}")
    print("🔄 Application will run in mixed mode")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Flask application on port {port}")
    print("✅ Application is ready!")
    app.run(host='0.0.0.0', port=port, debug=False)  # Changed debug to False for production
