.PHONY: dev migrate superuser install build watch

install:
	pip install -r requirements.txt
	npm install

dev:
	python manage.py runserver & npm run watch

migrate:
	python manage.py makemigrations
	python manage.py migrate

superuser:
	python manage.py createsuperuser

build:
	npm run build

watch:
	npm run watch

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

shell:
	python manage.py shell