FROM python:3.11-slim

# Create a non-root user specifically for Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app
COPY --chown=user . $HOME/app

# Install all requirements
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

# Run uvicorn via python module invocation to bypass any PATH resolution bugs
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
