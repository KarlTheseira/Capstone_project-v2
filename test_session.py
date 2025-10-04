#!/usr/bin/env python3
"""
Quick session test for FlashStudio
"""
from flask import Flask, session, request, jsonify
from datetime import timedelta
import os

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Configure session
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'test-secret-key')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

@app.route('/set_session')
def set_session():
    session.clear()
    session.permanent = True
    session['admin'] = True
    session['admin_logged_in'] = True
    session['user_type'] = 'admin'
    session.modified = True
    return jsonify({
        'status': 'session_set',
        'session': dict(session),
        'permanent': session.permanent
    })

@app.route('/check_session')
def check_session():
    return jsonify({
        'status': 'session_checked',
        'session': dict(session),
        'permanent': session.permanent,
        'admin': session.get('admin'),
        'admin_logged_in': session.get('admin_logged_in'),
        'user_type': session.get('user_type')
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=True)