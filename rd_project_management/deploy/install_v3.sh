#!/bin/bash
# =============================================================================
# INSTALADOR - Orion P&D v3.0
# Novidades: Tradução completa (EN/ES/pt_BR) + Esqueci Minha Senha (SMTP tenant)
# =============================================================================
# Uso:
#   1. Copie o pacote orion_pd_v3_deploy.tar.gz para o servidor
#   2. tar -xzf orion_pd_v3_deploy.tar.gz
#   3. cd orion_pd_v3_deploy
#   4. sudo bash install_v3.sh [/caminho/da/instalacao]
#
# Se o caminho não for informado, usa /var/www/rd_project_management
# =============================================================================

set -e

BASE_DIR="${1:-/var/www/rd_project_management}"
BACKUP_DIR="/var/www/backups/orion_v3_$(date +%Y%m%d_%H%M%S)"
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=================================================================="
echo "  INSTALADOR - Orion P&D v3.0"
echo "  Traducao completa EN/ES + Reset de Senha via SMTP do tenant"
echo "=================================================================="
echo ""
echo "  Diretorio de instalacao : $BASE_DIR"
echo "  Diretorio do pacote     : $PKG_DIR"
echo "  Backup sera criado em   : $BACKUP_DIR"
echo ""

if [ ! -d "$BASE_DIR" ]; then
    echo "[ERRO] Diretorio $BASE_DIR nao existe."
    echo "       Informe o caminho correto: sudo bash install_v3.sh /caminho/da/app"
    exit 1
fi

read -p "Continuar com a instalacao? (s/N) " CONFIRM
if [[ ! "$CONFIRM" =~ ^[sS]$ ]]; then
    echo "Instalacao cancelada."
    exit 0
fi

# -----------------------------------------------------------------------------
# 1. BACKUP
# -----------------------------------------------------------------------------
echo ""
echo "[1/7] Criando backup..."
mkdir -p "$BACKUP_DIR"
for item in app.py models.py extensions.py babel.cfg requirements.txt routes services templates translations static; do
    if [ -e "$BASE_DIR/$item" ]; then
        cp -r "$BASE_DIR/$item" "$BACKUP_DIR/" 2>/dev/null || true
    fi
done
# Backup do banco (sqlite)
find "$BASE_DIR" -maxdepth 2 -name "*.db" -exec cp {} "$BACKUP_DIR/" \; 2>/dev/null || true
echo "      Backup criado em: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# 2. PARAR APLICACAO
# -----------------------------------------------------------------------------
echo ""
echo "[2/7] Parando aplicacao..."
STOPPED=""
if systemctl is-active --quiet orion-pd 2>/dev/null; then
    systemctl stop orion-pd && STOPPED="systemd"
elif command -v supervisorctl >/dev/null 2>&1 && supervisorctl status orion-pd 2>/dev/null | grep -q RUNNING; then
    supervisorctl stop orion-pd && STOPPED="supervisor"
elif command -v pm2 >/dev/null 2>&1 && pm2 list 2>/dev/null | grep -q orion-pd; then
    pm2 stop orion-pd && STOPPED="pm2"
elif pgrep -f "gunicorn.*app:create_app" >/dev/null 2>&1; then
    pkill -f "gunicorn.*app:create_app" && STOPPED="gunicorn"
fi
if [ -n "$STOPPED" ]; then
    echo "      Aplicacao parada via $STOPPED."
else
    echo "      [AVISO] Nenhum processo detectado automaticamente."
    echo "              Se a app estiver rodando, pare-a manualmente agora."
    read -p "      Pressione ENTER para continuar..."
fi

# -----------------------------------------------------------------------------
# 3. COPIAR ARQUIVOS
# -----------------------------------------------------------------------------
echo ""
echo "[3/7] Copiando arquivos..."

# Arquivos core
for f in app.py models.py extensions.py babel.cfg requirements.txt; do
    if [ -f "$PKG_DIR/$f" ]; then
        cp "$PKG_DIR/$f" "$BASE_DIR/$f"
        echo "      core: $f"
    fi
done

# Rotas
mkdir -p "$BASE_DIR/routes"
cp "$PKG_DIR/routes/"*.py "$BASE_DIR/routes/" 2>/dev/null && echo "      routes/ atualizado"

# Servicos
mkdir -p "$BASE_DIR/services"
cp "$PKG_DIR/services/"*.py "$BASE_DIR/services/" 2>/dev/null && echo "      services/ atualizado (inclui email_service.py NOVO)"

# Templates (todos - contem os marcadores de traducao)
cp -r "$PKG_DIR/templates/." "$BASE_DIR/templates/" && echo "      templates/ atualizado (75+ arquivos com i18n)"

# Traducoes compiladas
mkdir -p "$BASE_DIR/translations"
cp -r "$PKG_DIR/translations/." "$BASE_DIR/translations/" && echo "      translations/ atualizado (pt_BR, en, es + .mo compilados)"

# Scripts de migracao
mkdir -p "$BASE_DIR/deploy"
cp "$PKG_DIR/migrate_password_reset.py" "$BASE_DIR/deploy/" 2>/dev/null || true
echo "      deploy/migrate_password_reset.py copiado"

# -----------------------------------------------------------------------------
# 4. DEPENDENCIAS
# -----------------------------------------------------------------------------
echo ""
echo "[4/7] Instalando dependencias novas (Flask-Babel, Flask-Mail, Babel)..."
PIP="pip3"
if [ -f "$BASE_DIR/venv/bin/pip" ]; then
    PIP="$BASE_DIR/venv/bin/pip"
    echo "      Usando virtualenv: $BASE_DIR/venv"
fi
$PIP install -q Flask-Babel==4.0.0 Flask-Mail==0.9.1 Babel==2.14.0 || {
    echo "      [AVISO] Falha ao instalar via pip. Instale manualmente:"
    echo "              $PIP install Flask-Babel Flask-Mail Babel"
}
echo "      Dependencias OK."

# -----------------------------------------------------------------------------
# 5. MIGRACAO DO BANCO
# -----------------------------------------------------------------------------
echo ""
echo "[5/7] Aplicando migracao do banco (colunas de reset de senha)..."
PYTHON="python3"
if [ -f "$BASE_DIR/venv/bin/python" ]; then
    PYTHON="$BASE_DIR/venv/bin/python"
fi
cd "$BASE_DIR"
$PYTHON - <<'PYEOF'
import sqlite3, glob, os

# Localiza o banco sqlite
candidates = glob.glob('*.db') + glob.glob('instance/*.db')
if not candidates:
    print("      [INFO] Nenhum banco SQLite encontrado.")
    print("             As colunas serao criadas automaticamente no primeiro start da app.")
else:
    for db_path in candidates:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for col, sql in [
            ("password_reset_token", "ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(100)"),
            ("password_reset_expires", "ALTER TABLE users ADD COLUMN password_reset_expires DATETIME"),
        ]:
            try:
                cur.execute(sql)
                conn.commit()
                print(f"      [{db_path}] Coluna adicionada: {col}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"      [{db_path}] Coluna ja existe: {col}")
                elif "no such table" in str(e).lower():
                    print(f"      [{db_path}] Tabela users nao existe (banco sera criado no start)")
                    break
                else:
                    print(f"      [{db_path}] ERRO em {col}: {e}")
        conn.close()
PYEOF
echo "      Migracao concluida."

# -----------------------------------------------------------------------------
# 6. VALIDACAO
# -----------------------------------------------------------------------------
echo ""
echo "[6/7] Validando instalacao..."
ERRORS=0
for f in "$BASE_DIR/services/email_service.py" \
         "$BASE_DIR/templates/auth/forgot_password.html" \
         "$BASE_DIR/templates/auth/reset_password.html" \
         "$BASE_DIR/translations/en/LC_MESSAGES/messages.mo" \
         "$BASE_DIR/translations/es/LC_MESSAGES/messages.mo" \
         "$BASE_DIR/translations/pt_BR/LC_MESSAGES/messages.mo"; do
    if [ -f "$f" ]; then
        echo "      OK: ${f#$BASE_DIR/}"
    else
        echo "      FALTANDO: ${f#$BASE_DIR/}"
        ERRORS=$((ERRORS+1))
    fi
done

# Teste de import
$PYTHON -c "
import sys; sys.path.insert(0, '$BASE_DIR')
from services.email_service import send_password_reset_email
print('      OK: email_service importa corretamente')
" 2>/dev/null || echo "      [AVISO] Nao foi possivel validar import (dependencias?)"

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "      [ERRO] $ERRORS arquivo(s) faltando. Verifique o pacote."
    exit 1
fi

# -----------------------------------------------------------------------------
# 7. REINICIAR APLICACAO
# -----------------------------------------------------------------------------
echo ""
echo "[7/7] Reiniciando aplicacao..."
case "$STOPPED" in
    systemd)    systemctl start orion-pd && echo "      Reiniciada via systemd." ;;
    supervisor) supervisorctl start orion-pd && echo "      Reiniciada via supervisor." ;;
    pm2)        pm2 start orion-pd && echo "      Reiniciada via pm2." ;;
    *)          echo "      [MANUAL] Inicie a aplicacao:"
                echo "               gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'" ;;
esac

echo ""
echo "=================================================================="
echo "  INSTALACAO CONCLUIDA!"
echo "=================================================================="
echo ""
echo "  Novidades desta versao:"
echo "   - Traducao completa de TODAS as telas (PT/EN/ES)"
echo "   - Seletor de idioma no menu e no perfil/cadastro de usuario"
echo "   - 'Esqueci minha senha' na tela de login"
echo "     (email enviado via SMTP configurado na empresa/tenant)"
echo ""
echo "  Verifique:"
echo "   1. Acesse /login e clique em 'Esqueci minha senha'"
echo "   2. Troque o idioma no menu e navegue pelas telas"
echo "   3. Confirme que o SMTP do tenant esta configurado em"
echo "      Empresas > Editar > Configuracao de Email"
echo ""
echo "  Rollback em caso de problemas:"
echo "   cp -r $BACKUP_DIR/* $BASE_DIR/ && systemctl restart orion-pd"
echo ""
