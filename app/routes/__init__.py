from fastapi import Header, HTTPException
import os
from dotenv import load_dotenv

load_dotenv()
secret_header = os.getenv("secret_api")

def verify_key(x_api_key: str = Header(...)):
  if x_api_key != secret_header:
    raise HTTPException(status_code= 403, detail= "Forbidden")
