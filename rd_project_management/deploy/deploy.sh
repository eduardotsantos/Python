#!/bin/bash
# =============================================================================
# DEPLOY PACKAGE - Orion P&D v2.0
# Central de Conformidade + Orion Autônomos PMO
# =============================================================================
# Gerado em: $(date)
# =============================================================================

echo "=================================================="
echo "  DEPLOY - Orion P&D v2.0"
echo "  Novos Módulos: Conformidade + PMO IA"
echo "=================================================="

# Diretório base (ajuste conforme seu servidor)
BASE_DIR="/var/www/rd_project_management"
BACKUP_DIR="/var/www/backups/$(date +%Y%m%d_%H%M%S)"

# 1. Criar backup
echo ""
echo "[1/5] Criando backup..."
mkdir -p $BACKUP_DIR
cp -r $BASE_DIR/app.py $BACKUP_DIR/
cp -r $BASE_DIR/models.py $BACKUP_DIR/
cp -r $BASE_DIR/templates $BACKUP_DIR/
cp -r $BASE_DIR/routes $BACKUP_DIR/
cp -r $BASE_DIR/static $BACKUP_DIR/
echo "      Backup criado em: $BACKUP_DIR"

# 2. Copiar novos arquivos
echo ""
echo "[2/5] Copiando novos arquivos..."

# Criar diretórios necessários
mkdir -p $BASE_DIR/agents
mkdir -p $BASE_DIR/templates/compliance/{risks,pending,nc,bugs,actions}
mkdir -p $BASE_DIR/templates/pmo_agents
mkdir -p $BASE_DIR/routes

echo "      Diretórios criados."

# 3. Parar aplicação (ajuste conforme seu setup)
echo ""
echo "[3/5] Parando aplicação..."
# Descomente a linha apropriada:
# systemctl stop orion-pd
# supervisorctl stop orion-pd
# pm2 stop orion-pd
echo "      (MANUAL: pare a aplicação antes de continuar)"

# 4. Aplicar migration
echo ""
echo "[4/5] Aplicando migration do banco de dados..."
cd $BASE_DIR
# Se usar Flask-Migrate:
# flask db upgrade
# Se não usar, execute o script de migração manual:
python3 migrate_compliance_pmo.py
echo "      Migration concluída."

# 5. Reiniciar aplicação
echo ""
echo "[5/5] Reiniciando aplicação..."
# Descomente a linha apropriada:
# systemctl start orion-pd
# supervisorctl start orion-pd
# pm2 start orion-pd
echo "      (MANUAL: inicie a aplicação)"

echo ""
echo "=================================================="
echo "  DEPLOY CONCLUÍDO!"
echo "=================================================="
echo ""
echo "Novos recursos disponíveis:"
echo "  - /compliance - Central de Pendências e Conformidade"
echo "  - /pmo - Orion Autônomos PMO (11 Agentes IA)"
echo ""
echo "Em caso de problemas, restaure o backup:"
echo "  cp -r $BACKUP_DIR/* $BASE_DIR/"
echo ""
