#!/bin/bash

set -e

echo "[+] Actualizando repositorios..."
sudo apt update

echo "[+] Instalando dependencias del sistema..."
sudo apt install -y \
    python3 \
    python3-venv \
    python3-tk \
    python3-opencv \
    python3-numpy \
    python3-pil \
    ffmpeg \
    mediainfo \
    libimage-exiftool-perl \
    hashdeep

echo "[+] Creando directorio del proyecto..."

mkdir -p ~/VideoForensics/{input,output,reports,frames,logs}

echo "[+] Creando entorno virtual..."

cd ~/VideoForensics

python3 -m venv venv

source venv/bin/activate

pip install --upgrade pip

pip install \
    numpy \
    opencv-python \
    scikit-image \
    pandas \
    matplotlib \
    pillow

echo "[+] Instalación terminada."
echo ""
echo "Para activar el entorno:"
echo "source ~/VideoForensics/venv/bin/activate"
