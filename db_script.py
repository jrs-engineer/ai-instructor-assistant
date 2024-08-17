import psycopg2

db_uri = "postgresql://postgres:password@localhost/db"
conn = psycopg2.connect(db_uri)
cur = conn.cursor()

create_student_table = """
CREATE TABLE IF NOT EXISTS student (
    student_id INTEGER PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL
);
"""

create_score_table = """
CREATE TABLE IF NOT EXISTS score (
    score_id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES student(student_id) ON DELETE CASCADE,
    subject VARCHAR(100) NOT NULL,
    score INTEGER CHECK (score >= 0 AND score <= 100)
);
"""

cur.execute(create_student_table)
cur.execute(create_score_table)

cur.executemany(
    "INSERT INTO student (first_name, last_name, student_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
    [
        ('John', 'Doe', 1),
        ('Jane', 'Smith', 2),
        ('Emily', 'Johnson', 3)
    ]
)

cur.executemany(
    "INSERT INTO score (student_id, subject, score) VALUES (%s, %s, %s)",
    [
        (1, 'Science', 95),
        (1, 'Physics', 88),
        (2, 'Mathematics', 78),
        (2, 'Physics', 85),
        (3, 'Mathematics', 92),
        (3, 'Science', 90)
    ]
)

conn.commit()

print("DB init done!!!")