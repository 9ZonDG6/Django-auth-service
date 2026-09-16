.PHONY: check check-deploy createsuperuser server flush-expired-tokens cleanup-axes

SAFE_MIGRATIONS_EXCLUDE_APPS ?= axes silk token_blacklist
AXES_LOG_RETENTION_DAYS ?= 30

define run_check
	@output_file=$$(mktemp); \
	if $(2) > $$output_file 2>&1; then \
		printf '\n\033[1;34m%s\033[0m   \033[0;32m✔ Passed\033[0m\n' "$(1)"; \
		if [ -s $$output_file ]; then \
			awk 'BEGIN { blank = "" } /^[[:space:]]*$$/ { blank = blank $$0 ORS; next } { printf "%s", blank; blank = ""; print }' $$output_file; \
		fi; \
		rm -f $$output_file; \
	else \
		status=$$?; \
		printf '\n\033[1;34m%s\033[0m   \033[0;31m✘ Failed\033[0m\n' "$(1)"; \
		if [ -s $$output_file ]; then \
			awk 'BEGIN { blank = "" } /^[[:space:]]*$$/ { blank = blank $$0 ORS; next } { printf "%s", blank; blank = ""; print }' $$output_file; \
		fi; \
		rm -f $$output_file; \
		$(if $(3),$(3) || true;) \
		exit $$status; \
	fi
endef

check:
	$(call run_check,Uv lock,uv lock --check)
	$(call run_check,Ruff format,uv run ruff format)
	$(call run_check,Ruff lint,uv run ruff check --fix)
	$(call run_check,Ty,uv run ty check)
	$(call run_check,Pytest,uv run pytest)
	$(call run_check,Django check,uv run python manage.py check)
	$(call run_check,Django makemigrations,uv run python manage.py makemigrations --check --dry-run)
	$(call run_check,Django safe migrations,uv run python manage.py check_migrations --exclude-apps $(SAFE_MIGRATIONS_EXCLUDE_APPS))
	$(call run_check,Dotenv lint,uv run dotenv-linter .env.example)
	$(call run_check,Import linter,uv run lint-imports)
	@printf '\n\033[1;32m✔ All checks passed!\033[0m\n'

check-deploy:
	$(call run_check,Django check --deploy,ENVIRONMENT=production DEBUG=false SECRET_KEY=$$(uv run python -c "import secrets; print(secrets.token_urlsafe(50))") uv run python manage.py check --deploy)

createsuperuser:
	@uv run python manage.py shell -v 0 -c "import sys; from django.conf import settings; sys.exit(0 if settings.ENVIRONMENT == 'local' else 1)" \
		|| (printf "\033[0;31mENVIRONMENT != local — не создаю admin/admin здесь. Используй 'uv run python manage.py createsuperuser' с реальным паролем.\033[0m\n"; exit 1)
	@printf "\033[1;34mCreating Django superuser...\033[0m\n"
	@DJANGO_SUPERUSER_USERNAME="admin" \
	DJANGO_SUPERUSER_PASSWORD="admin" \
	uv run python manage.py createsuperuser --noinput

# Таблицы token_blacklist растут бесконечно без периодической чистки.
# Это нужно повесить на cron/scheduler (например, раз в сутки).
# Или искать более правильное решение
flush-expired-tokens:
	@uv run python manage.py flushexpiredtokens

server:
	@printf "\033[1;34mStarting local server...\033[0m\n"
	@uv run python manage.py runserver

cleanup-axes:
	@uv run python manage.py cleanup_axes --days $(AXES_LOG_RETENTION_DAYS)
