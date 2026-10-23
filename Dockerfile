FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs as uid 1000
RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

# CPU-only torch keeps the image small
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# bake the Demucs model into the image so the first job doesn't download it
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs_6s')"

COPY --chown=user . .

# bake the Transkun V2 Aug model (checksum-verified) into the image
RUN python server/models.py
ENV HOST=0.0.0.0 PORT=7860
EXPOSE 7860
CMD ["python", "server/app.py"]
