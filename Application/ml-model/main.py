from flask import Flask, request
import json
import os
import datetime

app = Flask(__name__)

LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "dns_logs.txt")


def create_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)


def write_to_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


@app.route('/logs', methods=['POST'])
def handle_logs():
    try:
        data = request.get_json(force=True)
        write_to_log(f"Parsed Data: {json.dumps(data, indent=2)}")

    except Exception as e:
        write_to_log(f"Error processing log: {str(e)}")

    return '', 200


if __name__ == '__main__':
    # Make sure the log directory exists
    create_log_dir()

    # Write startup message
    write_to_log("ML container started")

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)