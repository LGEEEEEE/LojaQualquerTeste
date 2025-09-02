# app/config.py
import os

class Config:
    # Define o caminho do banco de dados para a pasta 'instance' na raiz do projeto
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///../instance/loja.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Chave secreta para segurança, importante para sessões e outras funcionalidades
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-bem-forte'