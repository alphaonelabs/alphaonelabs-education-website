FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install pre-commit black isort flake8 djlint

CMD ["pre-commit", "run", "--all-files"]