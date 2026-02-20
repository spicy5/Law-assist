import psycopg2
db_name='lawassist'
host='localhost'
user='postgres'
password='bojackhorseman07'
port='5432'
def create_connection():
    return psycopg2.connect(
        database=db_name,
        host=host,
        user=user,
        password=password,
        port=port
    )