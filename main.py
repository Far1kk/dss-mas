from dotenv import load_dotenv
import os
load_dotenv()

def main():
    print(f"Hello World!!! and secret token from env: {os.getenv('secret_token', 'Error of secret token(')}")

if __name__ == "__main__":
    main()