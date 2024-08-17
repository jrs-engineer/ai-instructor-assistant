db-up:
	docker compose up postgres -d

db-down:
	docker compose down

db-init: db-up
	sleep 1
	python3 db_script.py

run-app: db-up
	streamlit run main.py
	
.PHONY: db-up db-down db-init run-app
