import os
import json
import uuid
import redis
import logging
from flask import Flask, render_template, request, jsonify, session
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from redis.exceptions import RedisError
from flask_session import Session
from botocore.config import Config

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'flask_session:'

# Redis configuration
redis_host = 'chatbotcache-h5c2xw.serverless.use1.cache.amazonaws.com'  # Replace with your actual endpoint
redis_port = 6379  # Default port, change if different

redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    ssl=True,
    ssl_cert_reqs=None,
    decode_responses=False  # Keep as False to handle raw bytes
)

app.config['SESSION_REDIS'] = redis_client
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

Session(app)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Bedrock client with timeout
bedrock_config = Config(
    connect_timeout=5,
    read_timeout=30,
    retries={'max_attempts': 2}
)
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1',
    config=bedrock_config
)

@app.before_request
def before_request():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        logger.info(f"New session created with user_id: {session['user_id']}")
    else:
        logger.debug(f"Existing session found with user_id: {session['user_id']}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_id = session.get('user_id')
    if not user_id:
        logger.error("Chat attempted without user_id in session")
        return jsonify({'error': 'No user session found'}), 400

    user_message = request.json['message']
    
    # Retrieve context from Redis
    context = get_context(user_id)
    logger.debug(f"Retrieved context for user {user_id}: {context}")

    # Add user message to context
    context.append(f"Human: {user_message}")

    # Prepare the request payload for Bedrock
    prompt = "\n".join(context)
    payload = {
        "prompt": prompt + "\n\nAssistant:",
        "max_tokens_to_sample": 300,
        "temperature": 0.7,
        "top_p": 0.9,
    }

    try:
        response = bedrock.invoke_model(
            body=json.dumps(payload),
            modelId="anthropic.claude-v2",
            accept='application/json',
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read())
        bot_response = response_body['completion'].strip()

        # Add bot response to context
        context.append(f"Assistant: {bot_response}")

        # Save updated context
        save_context(user_id, context)
        logger.debug(f"Saved updated context for user {user_id}: {context}")

        return jsonify({'response': bot_response})

    except (BotoCoreError, ClientError) as e:
        logger.error(f"Bedrock API error: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request. Please try again.'}), 500
    except Exception as e:
        logger.exception(f"Unexpected error in chat route: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

@app.route('/clear_context', methods=['POST'])
def clear_context():
    user_id = session.get('user_id')
    if not user_id:
        logger.error("Clear context attempted without user_id in session")
        return jsonify({'error': 'No user session found'}), 400

    try:
        # Clear context
        save_context(user_id, [])
        logger.info(f"Context cleared successfully for user {user_id}")
        return jsonify({'status': 'success', 'message': 'Context cleared'})
    except Exception as e:
        logger.error(f"Error while clearing context for user {user_id}: {str(e)}")
        return jsonify({'error': f'Failed to clear context: {str(e)}'}), 500

@app.route('/list_context', methods=['GET'])
def list_context():
    user_id = session.get('user_id')
    if not user_id:
        logger.error("List context attempted without user_id in session")
        return jsonify({'error': 'No user session found'}), 400
    
    context = get_context(user_id)
    logger.debug(f"Listed context for user {user_id}: {context}")
    return jsonify({'context': context})

def get_context(user_id):
    context_key = f"context:{user_id}"
    try:
        context = redis_client.get(context_key)
        if context:
            try:
                # Try UTF-8 decoding first
                decoded_context = context.decode('utf-8')
            except UnicodeDecodeError:
                # If UTF-8 fails, try Latin-1 (which should never fail)
                decoded_context = context.decode('latin-1')
            
            parsed_context = json.loads(decoded_context)
            logger.debug(f"Retrieved context for user {user_id}: {parsed_context}")
            return parsed_context
        else:
            logger.debug(f"No context found for user {user_id}, initializing new context")
            return []
    except Exception as e:
        logger.error(f"Error while getting context for user {user_id}: {str(e)}")
        return []

def save_context(user_id, context):
    context_key = f"context:{user_id}"
    try:
        encoded_context = json.dumps(context).encode('utf-8')
        redis_client.set(context_key, encoded_context)
        redis_client.expire(context_key, 3600)  # Set expiration to 1 hour
        logger.debug(f"Context saved for user {user_id}: {context}")
    except Exception as e:
        logger.error(f"Error while saving context for user {user_id}: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)