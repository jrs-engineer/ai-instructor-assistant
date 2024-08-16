db-up:
	docker compose up postgres -d

run-app: db-up
	streamlit run main.py
	
.PHONY: db-up run-app