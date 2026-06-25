#!/bin/bash
# Script de atualização do sistema de traduções (i18n)
# Uso: bash scripts/update_translations.sh [opção]
#   Sem opção : extrai, atualiza e compila (fluxo completo)
#   --extract : só extrai strings novas para messages.pot
#   --update  : só atualiza os .po a partir do .pot
#   --compile : só compila os .po para .mo
#   --check   : verifica strings sem tradução nos .po
#   --backup  : cria backup dos arquivos de tradução

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TRANSLATIONS_DIR="$PROJECT_DIR/translations"
LOCALES=("pt_BR" "en" "es")
POT_FILE="$TRANSLATIONS_DIR/messages.pot"
BACKUP_DIR="$PROJECT_DIR/translations_backup/$(date +%Y%m%d_%H%M%S)"
BABEL_CFG="$PROJECT_DIR/babel.cfg"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()   { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error()  { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

# --- Garantir que está no diretório correto ---
cd "$PROJECT_DIR"

# --- Verificar dependências ---
check_deps() {
    if ! command -v pybabel &>/dev/null; then
        warn "pybabel não encontrado. Tentando instalar Flask-Babel..."
        pip install flask-babel --quiet || error "Falha ao instalar Flask-Babel"
    fi
}

# --- Backup dos arquivos de tradução ---
do_backup() {
    header "Backup"
    mkdir -p "$BACKUP_DIR"
    for locale in "${LOCALES[@]}"; do
        po_file="$TRANSLATIONS_DIR/$locale/LC_MESSAGES/messages.po"
        mo_file="$TRANSLATIONS_DIR/$locale/LC_MESSAGES/messages.mo"
        dest_dir="$BACKUP_DIR/$locale/LC_MESSAGES"
        mkdir -p "$dest_dir"
        [ -f "$po_file" ] && cp "$po_file" "$dest_dir/" && log "Backup: $locale/messages.po"
        [ -f "$mo_file" ] && cp "$mo_file" "$dest_dir/" && log "Backup: $locale/messages.mo"
    done
    [ -f "$POT_FILE" ] && cp "$POT_FILE" "$BACKUP_DIR/"
    log "Backup salvo em: $BACKUP_DIR"
}

# --- Extrair strings dos templates e rotas ---
do_extract() {
    header "Extração de strings"
    pybabel extract \
        -F "$BABEL_CFG" \
        -k "_" \
        -k "lazy_gettext" \
        -k "gettext" \
        --project="Orion P&D" \
        --copyright-holder="Orion PMO" \
        -o "$POT_FILE" \
        . \
        2>&1 | grep -v "^$" || true

    total=$(grep -c "^msgid" "$POT_FILE" 2>/dev/null || echo 0)
    log "Extraídas $total strings para messages.pot"
}

# --- Atualizar arquivos .po com novas strings ---
do_update() {
    header "Atualização dos arquivos .po"
    for locale in "${LOCALES[@]}"; do
        po_file="$TRANSLATIONS_DIR/$locale/LC_MESSAGES/messages.po"
        po_dir="$TRANSLATIONS_DIR/$locale/LC_MESSAGES"

        if [ -f "$po_file" ]; then
            pybabel update \
                -i "$POT_FILE" \
                -d "$TRANSLATIONS_DIR" \
                -l "$locale" \
                --no-fuzzy-matching \
                2>&1 | grep -v "^$" || true
            log "Atualizado: $locale/messages.po"
        else
            mkdir -p "$po_dir"
            pybabel init \
                -i "$POT_FILE" \
                -d "$TRANSLATIONS_DIR" \
                -l "$locale" \
                2>&1 | grep -v "^$" || true
            log "Criado novo: $locale/messages.po"
        fi
    done
}

# --- Compilar .po para .mo ---
do_compile() {
    header "Compilação dos arquivos .mo"
    pybabel compile \
        -d "$TRANSLATIONS_DIR" \
        --statistics \
        2>&1 | grep -v "^$" || true
    log "Todos os arquivos .mo compilados"
}

# --- Verificar strings sem tradução ---
do_check() {
    header "Verificação de strings sem tradução"
    all_ok=true
    for locale in "${LOCALES[@]}"; do
        po_file="$TRANSLATIONS_DIR/$locale/LC_MESSAGES/messages.po"
        if [ ! -f "$po_file" ]; then
            warn "$locale: arquivo .po não encontrado"
            continue
        fi

        # Conta msgstr vazios (excluindo o header vazio)
        empty=$(awk '
            /^msgid ""/{skip=1; next}
            /^msgid /{skip=0}
            /^msgstr ""$/ && !skip {count++}
            END {print count+0}
        ' "$po_file")

        total=$(grep -c "^msgid" "$po_file" || echo 0)
        translated=$(( total - empty - 1 ))  # -1 pelo header

        if [ "$empty" -gt 0 ]; then
            warn "$locale: $empty strings SEM tradução (de $translated traduzidas)"
            all_ok=false
            # Lista as 10 primeiras sem tradução
            echo "  Exemplos:"
            awk '
                /^msgid ""/{skip=1; next}
                /^msgid /{skip=0; last_id=$0}
                /^msgstr ""$/ && !skip {print "    " last_id; count++}
                count>=10{exit}
            ' "$po_file" | sed 's/^msgid //'
        else
            log "$locale: $translated strings traduzidas — COMPLETO"
        fi
    done
    $all_ok && log "Todas as traduções estão completas!"
}

# --- Mostrar estatísticas ---
do_stats() {
    header "Estatísticas"
    echo ""
    printf "  %-10s %10s %10s %10s\n" "Idioma" "Total" "Traduzidas" "Faltando"
    printf "  %-10s %10s %10s %10s\n" "------" "-----" "----------" "-------"
    for locale in "${LOCALES[@]}"; do
        po_file="$TRANSLATIONS_DIR/$locale/LC_MESSAGES/messages.po"
        if [ -f "$po_file" ]; then
            total=$(grep -c "^msgid" "$po_file" || echo 1)
            total=$(( total - 1 ))  # header
            empty=$(awk '
                /^msgid ""/{skip=1; next}
                /^msgid /{skip=0}
                /^msgstr ""$/ && !skip {count++}
                END {print count+0}
            ' "$po_file")
            translated=$(( total - empty ))
            printf "  %-10s %10d %10d %10d\n" "$locale" "$total" "$translated" "$empty"
        fi
    done
    echo ""
}

# --- FLUXO COMPLETO ---
do_all() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   Orion P&D — Atualização de Traduções   ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""

    check_deps
    do_backup
    do_extract
    do_update
    do_compile
    do_check
    do_stats

    echo -e "${GREEN}✓ Atualização completa!${NC}"
    echo "  Para adicionar novas traduções, edite os arquivos:"
    for locale in "${LOCALES[@]}"; do
        echo "    translations/$locale/LC_MESSAGES/messages.po"
    done
    echo "  Depois execute: bash scripts/update_translations.sh --compile"
    echo ""
}

# --- Parse de argumentos ---
case "${1:-}" in
    --extract) check_deps; do_extract ;;
    --update)  check_deps; do_extract; do_update ;;
    --compile) check_deps; do_compile ;;
    --check)   do_check; do_stats ;;
    --backup)  do_backup ;;
    --stats)   do_stats ;;
    --help|-h)
        echo "Uso: bash scripts/update_translations.sh [opção]"
        echo ""
        echo "Opções:"
        echo "  (sem opção)  Fluxo completo: backup + extração + atualização + compilação"
        echo "  --extract    Só extrai strings novas dos arquivos fonte → messages.pot"
        echo "  --update     Extrai e atualiza os .po com novas strings (não sobrescreve existentes)"
        echo "  --compile    Só compila os .po para .mo (necessário após editar traduções)"
        echo "  --check      Verifica quais strings ainda não foram traduzidas"
        echo "  --stats      Mostra estatísticas de cobertura por idioma"
        echo "  --backup     Cria backup dos arquivos de tradução atuais"
        echo ""
        ;;
    "") do_all ;;
    *)  error "Opção desconhecida: $1. Use --help para ver as opções." ;;
esac
