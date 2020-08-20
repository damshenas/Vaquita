import os
import logging
import sys
import json

script_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "{}/assets".format(script_path))

import pymysql as mysql

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    conn = mysql.connect(os.environ['HOSTNAME'], user=os.environ['USERNAME'], passwd=os.environ['PASSWORD'], db=os.environ['DB_NAME'], connect_timeout=5)
except mysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def handler(event, context):
    item_count = 0

    with conn.cursor() as cur:
        cur.execute("create table Employee ( EmpID  int NOT NULL, Name varchar(255) NOT NULL, PRIMARY KEY (EmpID))")
        cur.execute('insert into Employee (EmpID, Name) values(1, "Joe")')
        cur.execute('insert into Employee (EmpID, Name) values(2, "Bob")')
        cur.execute('insert into Employee (EmpID, Name) values(3, "Mary")')
        conn.commit()
        cur.execute("select * from Employee")
        for row in cur:
            item_count += 1
            logger.info(row)
            #print(row)
    conn.commit()

    return "Added %d items from RDS MySQL table" %(item_count)