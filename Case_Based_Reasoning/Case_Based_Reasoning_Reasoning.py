import mysql.connector
from Case_Based_Reasoning_CaseGeneration_Repetition import params
from numpy import random as rd

def main():
    conn = mysql.connector.connect(user='root', password='gh314wns!', database='cbr')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM case_database;")
    N_R = 1000
    H = rd.choice(list(range(1, [i[0] for i in cursor][0] + 1)), size=int(N_R * rd.random()), replace=False).tolist()
    R = []
    sigma = N_R = len(H)

    cursor.execute(f"SELECT * FROM case_database ORDER BY {params["w"]} * alt + ({1 - params["w"]}) * awt ASC;")
    database = [row for row in cursor]
    for c in database:

        h, p, alt, awt = c
        cursor.execute(f"SELECT job_type, job FROM s_o_{h}")
        s_o = [(jt, job) for jt, job in cursor]
        while len(R) < N_R:
            if h in H:
                if c not in R:
                    R.append(c)
                H.remove(h)
            elif sigma >0:
                if c not in R:
                    R.append(c)
                sigma -= 1
            else: break
    for row in R:
        print(row)
    print(len(R))
if __name__=="__main__":
    main()