-- Tabela de Usuários (Simples para o mercado)
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    usuario TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    admin INTEGER DEFAULT 0
);

-- Tabela de Produtos do Mercado
CREATE TABLE IF NOT EXISTS produtos (
    id SERIAL PRIMARY KEY,
    ean VARCHAR(20) UNIQUE NOT NULL,
    descricao TEXT NOT NULL,
    preco DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    validade DATE,
    quantidade INTEGER NOT NULL DEFAULT 0,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Movimentações (Entradas e Saídas)
CREATE TABLE IF NOT EXISTS movimentacoes (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER REFERENCES produtos(id),
    tipo VARCHAR(10) NOT NULL, -- 'ENTRADA' ou 'SAIDA'
    quantidade INTEGER NOT NULL,
    data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_id INTEGER REFERENCES usuarios(id),
    observacao TEXT
);

-- Inserir usuário padrão (admin / admin123)
INSERT INTO usuarios (nome, usuario, senha, admin) 
VALUES ('Administrador', 'admin', 'admin123', 1)
ON CONFLICT (usuario) DO NOTHING;
