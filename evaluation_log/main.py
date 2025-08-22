import argparse

import uvicorn

from evaluation_log import app

parser = argparse.ArgumentParser(description="Evaluation Log")
parser.add_argument("--port", type=int, default=8002, help="Port to run the server on")

if __name__ == "__main__":
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port) 