import mysql.connector

# Parameter Input
user, password, db_name, case_database = 'root', 'gh314wns!', 'cbr', 'case_database'

def main():
    conn = mysql.connector.connect(user=user, password=password)
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name};")
    cursor.execute(f"USE {db_name};")
    cursor.execute(f"""CREATE TABLE {case_database} (
    h smallint NOT NULL PRIMARY KEY,
    p JSON NOT NULL,
    alt FLOAT NOT NULL, 
    awt FLOAT NOT NULL);""")

    cursor.execute(f"""
    CREATE TABLE MACHINES(
    M varchar(5) NOT NULL PRIMARY KEY);""")

    cursor.execute(f"""
    CREATE TABLE PROCESSES(
    JOB_TYPE varchar(15) NOT NULL,
    OP varchar(8) NOT NULL,
    PROCESS int NOT NULL,
    MACHINES json NOT NULL,
    PRIMARY KEY (JOB_TYPE, OP));""")

    cursor.execute(f"""
    CREATE TABLE SETUPS(
    PRIOR_JT varchar(15) NOT NULL,
    PRIOR_OP varchar(8) NOT NULL,
    NOW_JT varchar(15) NOT NULL,
    NOW_OP varchar(8) NOT NULL,
    SETUP INT NOT NULL,
    PRIMARY KEY (PRIOR_JT, PRIOR_OP, NOW_JT, NOW_OP),
    FOREIGN KEY (PRIOR_JT, PRIOR_OP) REFERENCES PROCESSES (job_type, op),
    FOREIGN KEY (NOW_JT, NOW_OP) REFERENCES PROCESSES (job_type, op));""")
    cursor.close()

if __name__ == '__main__':
    main()