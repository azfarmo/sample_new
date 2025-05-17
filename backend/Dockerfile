FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the policy directory exists if you want to mount it or bake it in
RUN mkdir -p backend/policy

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Command to run when the container starts
# The --host 0.0.0.0 makes it accessible from outside the container
CMD ["uvicorn", "backend.rl_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]