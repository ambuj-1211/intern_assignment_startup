import time
import uuid
from random import choice

from flask import Flask, abort, jsonify, request
from redis import Redis

app = Flask(__name__)
redis = Redis(host='0.0.0.0', port=6379, db=0)

KEY_LIFETIME = 300  # 5 minutes in seconds
BLOCK_DURATION = 60  # 1 minute in seconds

def generate_key():
    return str(uuid.uuid4())

# Endpoint to create new keys
@app.route('/keys', methods=['POST'])
def create_key():
    key_id = generate_key()
    current_time = int(time.time())
    redis.hmset(key_id, {'createdAt': current_time, 'isBlocked': 'false'})
    redis.expire(key_id, KEY_LIFETIME)
    return jsonify({"keyId": key_id}), 201

@app.route('/keys', methods=['GET'])
def retrieve_key():
    # Get all available (unblocked) keys
    available_keys = [key.decode('utf-8') for key in redis.keys('*') if redis.hget(key, 'isBlocked') == b'false']
    
    if not available_keys:
        return jsonify({}), 404

    # Randomly select a key from available keys
    key_id = choice(available_keys)
    current_time = int(time.time())
    
    print(f"The KEY ID BY CHOICE COMMAND {key_id}")
    # return jsonify({"keyId": key_id}), 200
    # Block the selected key
    redis.hset(key_id, 'isBlocked', 'true')
    redis.hset(key_id, 'blockedAt', current_time)
    redis.expire(key_id, BLOCK_DURATION)  # Set expiration to automatically unblock after BLOCK_DURATION seconds
    
    return jsonify({"keyId": key_id}), 200

# Endpoint to get information about a specific key
@app.route('/keys/<key_id>', methods=['GET'])
def get_key_info(key_id):
    if not redis.exists(key_id):
        return jsonify({}), 404
    key_info = redis.hgetall(key_id)
    return jsonify({
        "isBlocked": key_info[b'isBlocked'].decode('utf-8'),
        "blockedAt": int(key_info.get(b'blockedAt', 0)),
        "createdAt": int(key_info[b'createdAt'])
    }), 200

# # Endpoint to delete a specific key
@app.route('/keys/<key_id>', methods=['DELETE'])
def delete_key(key_id):
    if not redis.exists(key_id):
        return jsonify({}), 404
    redis.delete(key_id)
    return jsonify({"status": "Key deleted"}), 200

# Endpoint to unblock a key
@app.route('/keys/<key_id>', methods=['PUT'])
def unblock_key(key_id):
    if not redis.exists(key_id):
        return jsonify({}), 404
    redis.hset(key_id, 'isBlocked', 'false')
    redis.persist(key_id)
    return jsonify({"status": "Key unblocked"}), 200

# # Endpoint to keep key alive
@app.route('/keepalive/<key_id>', methods=['PUT'])
def keep_alive_key(key_id):
    if not redis.exists(key_id):
        return jsonify({}), 404
    redis.expire(key_id, KEY_LIFETIME)  # Reset key lifetime
    return jsonify({"status": "Keep-alive refreshed"}), 200

if __name__ == '__main__':
    app.run(debug=True)
