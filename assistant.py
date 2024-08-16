import re
import json
import logging

import transformers
import torch

import psycopg2

db_uri = "postgresql://postgres:password@localhost/db"
conn = psycopg2.connect(db_uri)
cur = conn.cursor()

model_id = "meta-llama/Meta-Llama-3.1-8B-Instruct"

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)

prompt = """
You are a PostgreSQL expert. Given an input question, create a syntactically correct \
PostgreSQL query based on the table creation query and samples. \
You can order the results to return the most informative data in the database. \
Never query for all columns from a table. You must query only the columns that are \
needed to answer the question. Wrap each column name in double quotes (") to denote \
them as delimited identifiers. Pay attention to use only the column names you can see \
in the tables below. Be careful to not query for columns that do not exist. \
Also, pay attention to which column is in which table.
You should check if there are any missing fields in case of the insert statement. \
If there are any missing fields, you should request these fields to the user. \
This request should be clear and simple with one sentence. \
The sql query should be simple and should not contain any comments or unnecessary information. \
The output should include the type of the query (SELECT, INSERT, UPDATE, DELETE, ERROR) \
The output should not include any explanation.

table creation query:
```
CREATE TABLE IF NOT EXISTS student (
    student_id INTEGER PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS score (
    score_id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES student(student_id) ON DELETE CASCADE,
    subject VARCHAR(100) NOT NULL,
    score INTEGER CHECK (score >= 0 AND score <= 100)
);
```

sample questions and queries:
```
{"Question": "Retrieve the average score for each student.", "Query": "
    SELECT s.student_id, s.first_name, s.last_name, AVG(sc.score) AS average_score
    FROM student s
    JOIN score sc ON s.student_id = sc.student_id
    GROUP BY s.student_id, s.first_name, s.last_name;
", "Type": "SELECT"}

{"Question": "Find the highest score in each subject.", "Query": "
    SELECT subject, MAX(score) AS highest_score
    FROM score
    GROUP BY subject;
", "Type": "SELECT"}

{"Question": "List all students who have scored above 90 in any subject.", "Query": "
    SELECT s.student_id, s.first_name, s.last_name, sc.subject, sc.score
    FROM student s
    JOIN score sc ON s.student_id = sc.student_id
    WHERE sc.score > 90;
", "Type": "SELECT"}

{"Question": "Count the number of students who have taken each subject.", "Query": "
    SELECT subject, COUNT(DISTINCT student_id) AS student_count
    FROM score
    GROUP BY subject;
", "Type": "SELECT"}

{"Question": "Retrieve students who have not taken any exams.", "Query": "
    SELECT s.student_id, s.first_name, s.last_name
    FROM student s
    LEFT JOIN score sc ON s.student_id = sc.student_id
    WHERE sc.student_id IS NULL;
", "Type": "SELECT"}

{"Question": "Add a new student named John Smith with ID 1234.", "Query": "
    INSERT INTO student (student_id, first_name, last_name)
    VALUES (1234, 'John', 'Smith');
", "Type": "INSERT"}

{"Question": "Add a score of 90 for Jane Doe in Math.", "Query": "
    INSERT INTO score (student_id, subject, score)
    VALUES ((SELECT student_id FROM student WHERE first_name = 'Jane' AND last_name = 'Doe'), 'Math', 90);
", "Type": "INSERT"}

{"Question": "Summarize all student scores in Physics.", "Query": "
    SELECT s.first_name, s.last_name, score
    FROM score sc
    JOIN student s ON sc.student_id = s.student_id
    WHERE subject = 'Physics';
", "Type": "SELECT"}
    
{"Question": "What is the score of John Smith?", "Query": "
    Which subject do you want to know the score of John Smith?
"}

{"Question": "Insert a score of 85 for John Smith.", "Query": "
    Which subject did John Smith take?
", "Type": "ERROR"}

{"Question": "Retrieve the highest score of each student.", "Query": "
    SELECT s.student_id, s.first_name, s.last_name, MAX(sc.score) AS highest_score
    FROM student s
    JOIN score sc ON s.student_id = sc.student_id
    GROUP BY s.student_id, s.first_name, s.last_name;
", "Type": "SELECT"}

{"Question": "List the highest 10 students based on their average score.", "Query": "
    SELECT s.student_id, s.first_name, s.last_name, AVG(sc.score) AS average_score
    FROM student s
    JOIN score sc ON s.student_id = sc.student_id
    GROUP BY s.student_id, s.first_name, s.last_name
    ORDER BY average_score DESC
    LIMIT 10;
", "Type": "SELECT"}

{"Question": "John has scored 80 in Math. Add this score to the database.", "Query": "
    What is John's last name?
", "Type": "ERROR"}

{"Question": "John Doe has scored 80 in Math. Add this score to the database.", "Query": "
    INSERT INTO score (student_id, subject, score)
    VALUES ((SELECT student_id FROM student WHERE first_name = 'John' AND last_name = 'Doe'), 'Math', 80);
"}

{"Question": "Add a student named Anna Jammy.", "Query": "
    What is Anna Jammy's student ID?
", "Type": "ERROR"}
     
{"Question": "Update John Smith's score in Math to 85.", "Query": "
    UPDATE score
    SET score = 85
    WHERE student_id = (SELECT student_id FROM student WHERE first_name = 'John' AND last_name = 'Smith') AND subject = 'Math';
", "Type": "UPDATE"}

{"Question": "Delete all scores of Jack Poll.", "Query": "
    DELETE FROM score
    WHERE student_id = (SELECT student_id FROM student WHERE first_name = 'Jack' AND last_name = 'Poll');
", "Type": "DELETE"}

{"Question": "Remove the student named James Chris.", "Query": "
    DELETE FROM student
    WHERE first_name = 'James' AND last_name = 'Chris' CASCADE;
", "Type": "DELETE"}

{"Question": "Modify the Physics score of White Poll!", "Query": "
    What is the new score for White Poll in Physics?
", "Type": "ERROR"}
``` 

The output should be in the following format:
```
{"Question": "--Question--", "Query": "--Query--", "Type": "--Type--"}
```"""

def get_query(question):
    print("question: " + question)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "question", "content": question}
    ]

    outputs = pipeline(messages, max_new_tokens=300)

    try:
        return get_regular_query(outputs)
    except Exception as e:
        return "", e

def get_regular_query(outputs):
    output_string = outputs[0]["generated_text"][-1]['content']
    print("output_string: " + output_string)
    output = re.search(r'\{(?:.|\n)+\}', output_string).group()
    output = re.sub(r'`', '"', output)
    output_json = json.loads(output, strict=False)
    query = output_json["Query"]
    query = re.sub(r'"', "'", query)
    print(query)
    return query, output_json["Type"]

def get_result(question):
    query, query_type = get_query(question)

    if len(query) == 0:
        return None, "JSON ERROR: " + str(query_type)
    
    if query_type == "ERROR":
        return "ERROR", query
    
    try:
        res = cur.execute(query)
        if query_type == "SELECT":
            columns = cur.description
            if isinstance(columns[0], tuple):
                columns = columns[0]
            return (cur.fetchall(), columns), query
        else:
            conn.commit()
            return f"{cur.rowcount} rows {query_type}", query
    except Exception as e:
        conn.rollback()
        return None, "SQL ERROR: " + str(e)

    