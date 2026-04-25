import os
import string
import random
import psycopg2
import redis
from flask import Flask, jsonify, redirect, request
# testing to see if code is updated
app = Flask(__name__)

# Redis connection
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    decode_responses=True
)

# Postgres connection
def get_db():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        database=os.environ.get('DB_NAME', 'urlshortener'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres')
    )

# Create table if not exists
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            short_code VARCHAR(10) UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            clicks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

# Generate short code
def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

@app.route('/health')
def health():
    try:
        redis_client.ping()
        redis_status = 'up'
    except:
        redis_status = 'down'
    
    try:
        conn = get_db()
        conn.close()
        db_status = 'up'
    except:
        db_status = 'down'
    
    return jsonify({
        'status': 'healthy',
        'redis': redis_status,
        'postgres': db_status
    })

@app.route('/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    original_url = data.get('url')
    
    if not original_url:
        return jsonify({'error': 'URL is required'}), 400
    
    short_code = generate_code()
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO urls (short_code, original_url) VALUES (%s, %s)',
        (short_code, original_url)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    redis_client.setex(short_code, 3600, original_url)
    
    return jsonify({
        'short_code': short_code,
        'short_url': f"http://localhost/{short_code}"
    }), 201

@app.route('/<code>')
def redirect_url(code):
    original_url = redis_client.get(code)
    
    if not original_url:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'SELECT original_url FROM urls WHERE short_code = %s',
            (code,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if not result:
            return jsonify({'error': 'URL not found'}), 404
        
        original_url = result[0]
        redis_client.setex(code, 3600, original_url)
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'UPDATE urls SET clicks = clicks + 1 WHERE short_code = %s',
        (code,)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(original_url)

@app.route('/stats/<code>')
def stats(code):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT short_code, original_url, clicks, created_at FROM urls WHERE short_code = %s',
        (code,)
    )
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if not result:
        return jsonify({'error': 'URL not found'}), 404
    
    return jsonify({
        'short_code': result[0],
        'original_url': result[1],
        'clicks': result[2],
        'created_at': str(result[3])
    })

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)