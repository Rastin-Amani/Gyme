PY ?= python3
PYBABEL ?= pybabel

i18n-extract:
	$(PYBABEL) extract -F babel.cfg -k _ -k ngettext:1,2 -o app/locales/messages.pot app

i18n-add: i18n-extract ## new locale: make i18n-add LOCALE=de
	$(PYBABEL) init -i app/locales/messages.pot -d app/locales -l $(LOCALE)

i18n-update: i18n-extract
	$(PYBABEL) update -i app/locales/messages.pot -d app/locales

i18n-compile:
	$(PYBABEL) compile -d app/locales --use-fuzzy

test:
	pytest -q
