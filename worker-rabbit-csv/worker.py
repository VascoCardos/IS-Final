import pika
import json
import os
import logging
from io import StringIO
import pandas as pd
import pg8000

# RabbitMQ configurations
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PW = os.getenv("RABBITMQ_PW", "password")
QUEUE_NAME = 'csv_chunks'

# Database configurations
DBHOST = os.getenv('DBHOST', 'localhost')
DBUSERNAME = os.getenv('DBUSERNAME', 'myuser')
DBPASSWORD = os.getenv('DBPASSWORD', 'mypassword')
DBNAME = os.getenv('DBNAME', 'mydatabase')
DBPORT = os.getenv('DBPORT', '5432')

# Configure logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger()

# To store reassembled file chunks
reassembled_data = []


def save_to_database(df):
    """
    Saves a pandas DataFrame to the database.
    """
    try:
        conn = pg8000.connect(
            user=DBUSERNAME,
            password=DBPASSWORD,
            host=DBHOST,
            port=int(DBPORT),
            database=DBNAME
        )
        cursor = conn.cursor()

        # Example: Insert data into a table named 'data_table'
        for index, row in df.iterrows():
            insert_query = """
            INSERT INTO data_table (column1, column2, column3)
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (row['column1'], row['column2'], row['column3']))

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Data successfully saved to the database.")
    except Exception as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)


def process_message(ch, method, properties, body):
    """
    Callback to process each message received from RabbitMQ.
    """
    global reassembled_data

    str_stream = body.decode('utf-8')
    if str_stream == "__EOF__":
        logger.info("EOF marker received. Finalizing...")
        file_content = b"".join(reassembled_data)
        csv_text = file_content.decode('utf-8')

        if len(reassembled_data) > 0:
            csvfile = StringIO(csv_text)
            df = pd.read_csv(csvfile)
            logger.info(f"DataFrame created with {len(df)} rows.")
            save_to_database(df)
        else:
            logger.warning("No data to process.")

        reassembled_data.clear()
    else:
        reassembled_data.append(body)


def main():
    """
    Main function to start the worker.
    """
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PW)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=int(RABBITMQ_PORT),
            credentials=credentials
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)

    logger.info(f"Waiting for messages from queue '{QUEUE_NAME}'...")
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_message, auto_ack=True)
    channel.start_consuming()


if __name__ == "__main__":
    main()
