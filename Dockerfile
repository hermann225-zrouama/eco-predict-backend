# Utiliser une image python légère
FROM python:3.10-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier seulement le fichier requirements.txt d'abord pour bénéficier du cache Docker
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache

# Copier le reste des fichiers de l'application
COPY . /app

# Exposer le port 8000 pour l'application
EXPOSE 8000

# Commande de lancement de l'application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
