# Guia de Instalação - AWS Windows Server

## Pré-requisitos AWS

### 1. Criar Instância EC2

1. Acesse o **Console AWS** > **EC2** > **Launch Instance**
2. Selecione a AMI: **Microsoft Windows Server 2022 Base**
3. Tipo de instância recomendado: **t3.small** (mínimo) ou **t3.medium**
4. Configure o **Security Group** com as regras:

| Tipo | Protocolo | Porta | Origem |
|------|-----------|-------|--------|
| RDP | TCP | 3389 | Seu IP |
| HTTP | TCP | 80 | 0.0.0.0/0 |
| Custom TCP | TCP | 5000 | 0.0.0.0/0 |

5. Crie ou selecione um **Key Pair** para acesso RDP
6. Lance a instância

### 2. Conectar à Instância

1. Aguarde a instância iniciar (Status: running)
2. Clique em **Connect** > **RDP Client**
3. Baixe o arquivo RDP e obtenha a senha com seu Key Pair

---

## Métodos de Instalação

### Método 1: Script User Data (Automático)

Cole o conteúdo de `aws_userdata.ps1` no campo **User Data** durante a criação da instância.

**Vantagem:** Instalação totalmente automática
**Desvantagem:** Precisa configurar URL do repositório

### Método 2: Script PowerShell (Recomendado)

1. Conecte via RDP à instância
2. Copie a pasta do projeto para `C:\GestaoPD\`
3. Abra **PowerShell como Administrador**
4. Execute:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
cd C:\GestaoPD\scripts
.\install_windows.ps1
```

### Método 3: Instalação Manual

1. Conecte via RDP
2. Instale Python 3.11: https://www.python.org/downloads/
3. Abra **CMD como Administrador**:

```batch
cd C:\GestaoPD
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install waitress
```

4. Inicie a aplicação:

```batch
python -m waitress --host=0.0.0.0 --port=5000 app:app
```

---

## Configuração como Serviço Windows

### Usando NSSM (Recomendado)

1. Baixe NSSM: https://nssm.cc/download
2. Extraia e copie `nssm.exe` para `C:\Windows\System32`
3. Execute:

```batch
nssm install GestaoPD "C:\GestaoPD\venv\Scripts\python.exe" "-m waitress --host=0.0.0.0 --port=5000 app:app"
nssm set GestaoPD AppDirectory "C:\GestaoPD"
nssm set GestaoPD Description "Sistema de Gestao de Projetos de P&D"
nssm set GestaoPD Start SERVICE_AUTO_START
nssm start GestaoPD
```

### Usando Agendador de Tarefas

1. Abra **Task Scheduler**
2. Clique em **Create Task**
3. **General**: Nome: GestaoPD, Executar com privilégios mais altos
4. **Triggers**: Na inicialização do sistema
5. **Actions**: Iniciar programa: `C:\GestaoPD\start.bat`
6. **Conditions**: Desmarque "Iniciar somente se conectado à rede AC"

---

## Configuração de Proxy Reverso (Opcional)

### Com IIS

1. Instale IIS: Server Manager > Add Roles and Features
2. Instale módulos:
   - URL Rewrite: https://www.iis.net/downloads/microsoft/url-rewrite
   - ARR: https://www.iis.net/downloads/microsoft/application-request-routing

3. Configure proxy reverso no `web.config`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="ReverseProxy" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://localhost:5000/{R:1}" />
                </rule>
            </rules>
        </rewrite>
    </system.webServer>
</configuration>
```

---

## Variáveis de Ambiente

Crie ou edite o arquivo `.env` em `C:\GestaoPD\`:

```env
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=sqlite:///C:/GestaoPD/rd_projects.db
PORT=5000
FLASK_ENV=production
```

Para produção, gere uma chave secreta forte:

```powershell
[guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
```

---

## Usando Banco de Dados Externo (Opcional)

### PostgreSQL (Amazon RDS)

1. Crie uma instância RDS PostgreSQL
2. Instale o driver: `pip install psycopg2-binary`
3. Configure `.env`:

```env
DATABASE_URL=postgresql://usuario:senha@endpoint-rds:5432/gestao_pd
```

### SQL Server (Amazon RDS)

1. Crie uma instância RDS SQL Server
2. Instale o driver: `pip install pyodbc`
3. Configure `.env`:

```env
DATABASE_URL=mssql+pyodbc://usuario:senha@endpoint-rds:1433/gestao_pd?driver=ODBC+Driver+17+for+SQL+Server
```

---

## Logs e Monitoramento

### Logs da Aplicação

Os logs são salvos em:
- `C:\GestaoPD\logs\stdout.log`
- `C:\GestaoPD\logs\stderr.log`

### Verificar Status do Serviço

```powershell
# Se usando NSSM
nssm status GestaoPD

# Se usando Agendador de Tarefas
Get-ScheduledTask -TaskName "GestaoPD"
```

### Reiniciar Serviço

```powershell
nssm restart GestaoPD
# ou
Restart-ScheduledTask -TaskName "GestaoPD"
```

---

## Troubleshooting

### Aplicação não inicia

1. Verifique os logs em `C:\GestaoPD\logs\`
2. Teste manualmente:
   ```batch
   cd C:\GestaoPD
   venv\Scripts\activate
   python app.py
   ```

### Porta bloqueada

1. Verifique firewall Windows:
   ```powershell
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*5000*"}
   ```
2. Verifique Security Group na AWS

### Acesso negado externamente

1. Confirme que o Security Group permite TCP na porta 5000
2. Verifique se a instância tem IP público
3. Confirme que não há Network ACL bloqueando

### Erro de dependências

```batch
venv\Scripts\pip install --force-reinstall -r requirements.txt
```

---

## Backup

### Backup do Banco de Dados

```powershell
# Copia o arquivo do banco de dados
Copy-Item "C:\GestaoPD\rd_projects.db" "C:\Backups\rd_projects_$(Get-Date -Format 'yyyyMMdd').db"

# Ou use S3
aws s3 cp C:\GestaoPD\rd_projects.db s3://seu-bucket/backups/
```

### Backup Automatizado

Crie uma tarefa agendada que execute diariamente:

```powershell
$backupScript = {
    $date = Get-Date -Format "yyyyMMdd"
    Copy-Item "C:\GestaoPD\rd_projects.db" "C:\Backups\rd_projects_$date.db"
}
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-Command $backupScript"
Register-ScheduledTask -TaskName "GestaoPD-Backup" -Trigger $trigger -Action $action
```

---

## Atualização

Para atualizar a aplicação:

```powershell
# Parar serviço
nssm stop GestaoPD

# Backup
Copy-Item "C:\GestaoPD\rd_projects.db" "C:\Backups\rd_projects_pre_update.db"

# Atualizar arquivos
# (copie os novos arquivos para C:\GestaoPD)

# Atualizar dependências
& C:\GestaoPD\venv\Scripts\pip.exe install -r C:\GestaoPD\requirements.txt

# Reiniciar
nssm start GestaoPD
```

---

## Contato e Suporte

- Login padrão: `admin` / `admin123`
- **IMPORTANTE:** Altere a senha após o primeiro acesso!
