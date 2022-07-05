.DEFAULT_GOAL := help

.PHONY: coverage help tox syntax-check syntax-format pip-compile pip-install \
	sdist-project-quotes collectstatic-project-quotes \
	compose-project-quotes-build compose-project-quotes-up

coverage:  ## Run tests with coverage.
	coverage erase
	coverage run --source=django_comments_ink \
		--omit=*migrations*,*tests* -m pytest -ra
	coverage report -m
	@sh ./ccsvg.sh ||:

syntax-check:  ## Check syntax code (isort and black).
	black --check django_comments_ink

syntax-format:  ## Format syntax code (isort and black).
	black django_comments_ink

tox:  ## Run tox.
	python -m tox

pip-compile:  ## Generate requirements.txt and requirements-dev.txt files.
	python -c "import piptools" > /dev/null 2>&1 || pip install pip-tools
	pip-compile --generate-hashes --allow-unsafe \
		--output-file requirements.txt requirements.in
	pip-compile --allow-unsafe \
		--output-file requirements-tests.txt requirements-tests.in
	pip-compile --generate-hashes --allow-unsafe \
		--output-file requirements-dev.txt requirements-dev.in

pip-install:  ## Install dependencies listed in requirements-dev.txt.
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

sdist-project-quotes:  # Create source tarballs for django-comments-ink and demos projects.
	. venv/bin/activate && python setup.py sdist && deactivate
	cd demos/project-quotes/ && . pqenv/bin/activate && python setup.py sdist && deactivate

collectstatic-project-quotes:  # django's collectstatic for demos project.
	cd demos/project-quotes/ && . pqenv/bin/activate && python project_quotes/manage.py collectstatic --noinput && deactivate

compose-project-quotes-build: sdist-project-quotes
	source .env && docker-compose -f demos/project-quotes/docker-compose.yml build web

compose-project-quotes-up: sdist-project-quotes collectstatic-project-quotes
	source .env && docker-compose -f demos/project-quotes/docker-compose.yml up -d

help: ## Show help message
	@IFS=$$'\n' ; \
	help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/:/'`); \
	printf "%s\n\n" "Usage: make [task]"; \
	printf "%-20s %s\n" "task" "help" ; \
	printf "%-20s %s\n" "------" "----" ; \
	for help_line in $${help_lines[@]}; do \
		IFS=$$':' ; \
		help_split=($$help_line) ; \
		help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		printf '\033[36m'; \
		printf "%-20s %s" $$help_command ; \
		printf '\033[0m'; \
		printf "%s\n" $$help_info; \
	done
