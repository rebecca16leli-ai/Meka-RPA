-- Schema mínimo (Módulo: Banco local). Last-write simples; sem migrações por ora.

CREATE TABLE IF NOT EXISTS condominios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_pasta  TEXT NOT NULL,
    nome_almah  TEXT NOT NULL,          -- nome EXATO no Almah (base da validação)
    ativo       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS lancamentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    condominio      TEXT NOT NULL,
    competencia     TEXT NOT NULL,      -- MM/AAAA
    fornecedor      TEXT NOT NULL,
    descricao       TEXT,
    valor_liquido   REAL,
    vencimento      TEXT,               -- ISO yyyy-mm-dd
    status          TEXT NOT NULL DEFAULT 'pendente',
    arquivos        TEXT,               -- JSON list de caminhos
    observacao      TEXT,
    chave_dup       TEXT,               -- chave de duplicidade (R6)
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lanc_chave_dup ON lancamentos(chave_dup);

-- Fila de jobs (desacopla a UI Streamlit do worker Playwright — R4)
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lancamento_id INTEGER,
    estado        TEXT NOT NULL DEFAULT 'na_fila',  -- na_fila|executando|concluido|erro
    criado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT,
    FOREIGN KEY (lancamento_id) REFERENCES lancamentos(id)
);

CREATE TABLE IF NOT EXISTS evidencias (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lancamento_id INTEGER,
    etapa         TEXT NOT NULL,
    caminho       TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nivel         TEXT NOT NULL,
    etapa         TEXT,
    mensagem      TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);
