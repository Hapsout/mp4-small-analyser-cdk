#!/bin/bash
set -e

echo "📦 Préparation du layer ffmpeg pour Lambda..."

# Créer les répertoires pour le layer
mkdir -p ffmpeg/bin
mkdir -p ffmpeg/python

# Télécharger ffmpeg statique
echo "🔍 Téléchargement de ffmpeg statique..."
wget -q -O ffmpeg.tar.xz "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
tar -xf ffmpeg.tar.xz
FFMPEG_DIR=$(find . -type d -name "ffmpeg-*-amd64-static")

# Copier ffmpeg et ffprobe dans le layer
echo "📋 Copie des binaires ffmpeg et ffprobe..."
cp "$FFMPEG_DIR/ffmpeg" ffmpeg/bin/
cp "$FFMPEG_DIR/ffprobe" ffmpeg/bin/
chmod +x ffmpeg/bin/ffmpeg
chmod +x ffmpeg/bin/ffprobe

# Installer requests dans le layer
echo "📦 Installation du package requests..."
pip install requests -t ffmpeg/python/

# Nettoyer
echo "🧹 Nettoyage..."
rm -rf "$FFMPEG_DIR" ffmpeg.tar.xz

echo "✅ Layer ffmpeg prêt !"
