from pydantic import EmailStr, BaseSettings
# import boto3


class Settings(BaseSettings):
    DATABASE_URL: str
    MONGO_INITDB_DATABASE: str

    JWT_PUBLIC_KEY: str
    JWT_PRIVATE_KEY: str
    REFRESH_TOKEN_EXPIRES_IN: int
    ACCESS_TOKEN_EXPIRES_IN: int
    JWT_ALGORITHM: str

    CLIENT_ORIGIN: str
    DOMAIN_NAME: str

    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: EmailStr

    STRIPE_API_KEY: str
    STRIPE_SECRET_KEY: str

    class Config:
        env_file = "./.env"


settings = Settings()

# s3 = boto3.client(
#     "s3",
#     aws_access_key_id="AKIAUMLQOJ7A2A62DXNZ",
#     aws_secret_access_key="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",
#
# )
#
# bucket_name = "airesumebuilder"
