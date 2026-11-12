-- =====================================================================
-- AutoVenda — Projeto físico do banco de dados
-- SGBD alvo: PostgreSQL 14+ (a aplicação também roda em SQLite para
-- desenvolvimento; o SQLAlchemy gera o esquema equivalente).
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- USUARIO: funcionários que acessam o painel administrativo
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
    id          SERIAL        PRIMARY KEY,
    nome        VARCHAR(100)  NOT NULL,
    email       VARCHAR(120)  NOT NULL,
    senha_hash  VARCHAR(255)  NOT NULL,
    perfil      VARCHAR(10)   NOT NULL DEFAULT 'VENDEDOR',
    ativo       BOOLEAN       NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_usuario_email  UNIQUE (email),
    CONSTRAINT ck_usuario_perfil CHECK (perfil IN ('ADMIN', 'VENDEDOR'))
);

-- ---------------------------------------------------------------------
-- MARCA: fabricantes de veículos
-- ---------------------------------------------------------------------
CREATE TABLE marca (
    id    SERIAL       PRIMARY KEY,
    nome  VARCHAR(50)  NOT NULL,
    CONSTRAINT uq_marca_nome UNIQUE (nome)
);

-- ---------------------------------------------------------------------
-- CLIENTE: interessados/compradores (identificados pelo e-mail)
-- ---------------------------------------------------------------------
CREATE TABLE cliente (
    id         SERIAL        PRIMARY KEY,
    nome       VARCHAR(100)  NOT NULL,
    email      VARCHAR(120)  NOT NULL,
    telefone   VARCHAR(11)   NOT NULL,          -- somente dígitos, com DDD
    cpf        VARCHAR(11),                      -- obrigatório apenas na venda
    criado_em  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cliente_email UNIQUE (email),
    CONSTRAINT uq_cliente_cpf   UNIQUE (cpf),
    -- Os CHECK de formato abaixo repetem no banco o que o Model já valida.
    -- Sem eles, uma carga feita direto por SQL (importação, migração) grava
    -- telefone com máscara ou CPF incompleto, e a aplicação passa a exibir
    -- dado quebrado em tela.
    CONSTRAINT ck_cliente_telefone CHECK (telefone ~ '^[0-9]{10,11}$'),
    CONSTRAINT ck_cliente_cpf      CHECK (cpf IS NULL OR cpf ~ '^[0-9]{11}$')
);

-- ---------------------------------------------------------------------
-- VEICULO: anúncios da loja
-- ---------------------------------------------------------------------
CREATE TABLE veiculo (
    id              SERIAL         PRIMARY KEY,
    marca_id        INTEGER        NOT NULL,
    modelo          VARCHAR(80)    NOT NULL,
    versao          VARCHAR(80),
    ano_fabricacao  SMALLINT       NOT NULL,
    ano_modelo      SMALLINT       NOT NULL,
    cor             VARCHAR(30)    NOT NULL,
    quilometragem   INTEGER        NOT NULL,
    combustivel     VARCHAR(10)    NOT NULL,
    cambio          VARCHAR(10)    NOT NULL,
    preco           NUMERIC(12,2)  NOT NULL,
    placa           VARCHAR(7)     NOT NULL,   -- ABC1234 ou ABC1D23, sem hífen
    descricao       TEXT,
    imagem          VARCHAR(255),              -- nome do arquivo em static/uploads
    status          VARCHAR(10)    NOT NULL DEFAULT 'DISPONIVEL',
    criado_em       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_veiculo_marca         FOREIGN KEY (marca_id) REFERENCES marca (id),
    CONSTRAINT uq_veiculo_placa         UNIQUE (placa),
    CONSTRAINT ck_veiculo_preco         CHECK (preco > 0),
    CONSTRAINT ck_veiculo_quilometragem CHECK (quilometragem >= 0),
    CONSTRAINT ck_veiculo_ano_modelo    CHECK (ano_modelo >= ano_fabricacao AND ano_modelo <= ano_fabricacao + 1),
    CONSTRAINT ck_veiculo_combustivel   CHECK (combustivel IN ('FLEX','GASOLINA','ETANOL','DIESEL','HIBRIDO','ELETRICO')),
    CONSTRAINT ck_veiculo_cambio        CHECK (cambio IN ('MANUAL','AUTOMATICO')),
    CONSTRAINT ck_veiculo_status        CHECK (status IN ('DISPONIVEL','RESERVADO','VENDIDO')),
    -- Placa antiga (ABC1234) ou Mercosul (ABC1D23), sempre com 7 posições e
    -- em maiúsculas. O Model valida com a mesma expressão; replicar aqui
    -- protege o banco de cargas feitas fora da aplicação, que já causaram
    -- falha na listagem do painel ao gravar placa com menos de 7 caracteres.
    CONSTRAINT ck_veiculo_placa         CHECK (placa ~ '^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$')
);
CREATE INDEX ix_veiculo_marca_id ON veiculo (marca_id);
CREATE INDEX ix_veiculo_status   ON veiculo (status);

-- O campo atualizado_em é mantido pela aplicação (onupdate do SQLAlchemy).
-- Um UPDATE executado direto no banco não passa por ela, então a trigger
-- abaixo garante que a coluna reflita de fato a última alteração da linha.
CREATE OR REPLACE FUNCTION fn_veiculo_atualizado_em() RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_veiculo_atualizado_em
    BEFORE UPDATE ON veiculo
    FOR EACH ROW
    EXECUTE FUNCTION fn_veiculo_atualizado_em();

-- ---------------------------------------------------------------------
-- PROPOSTA: ofertas enviadas pela vitrine
-- ---------------------------------------------------------------------
CREATE TABLE proposta (
    id              SERIAL         PRIMARY KEY,
    veiculo_id      INTEGER        NOT NULL,
    cliente_id      INTEGER        NOT NULL,
    valor_ofertado  NUMERIC(12,2)  NOT NULL,
    mensagem        VARCHAR(500),
    status          VARCHAR(10)    NOT NULL DEFAULT 'PENDENTE',
    criado_em       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_proposta_veiculo FOREIGN KEY (veiculo_id) REFERENCES veiculo (id) ON DELETE CASCADE,
    CONSTRAINT fk_proposta_cliente FOREIGN KEY (cliente_id) REFERENCES cliente (id),
    CONSTRAINT ck_proposta_valor   CHECK (valor_ofertado > 0),
    CONSTRAINT ck_proposta_status  CHECK (status IN ('PENDENTE','ACEITA','RECUSADA'))
);
CREATE INDEX ix_proposta_veiculo_id ON proposta (veiculo_id);
CREATE INDEX ix_proposta_cliente_id ON proposta (cliente_id);
CREATE INDEX ix_proposta_status     ON proposta (status);

-- ---------------------------------------------------------------------
-- VENDA: fechamento do negócio (1 venda por veículo)
-- ---------------------------------------------------------------------
CREATE TABLE venda (
    id               SERIAL         PRIMARY KEY,
    veiculo_id       INTEGER        NOT NULL,
    cliente_id       INTEGER        NOT NULL,
    vendedor_id      INTEGER        NOT NULL,
    proposta_id      INTEGER,
    valor_final      NUMERIC(12,2)  NOT NULL,
    forma_pagamento  VARCHAR(15)    NOT NULL,
    data_venda       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_venda_veiculo      FOREIGN KEY (veiculo_id)  REFERENCES veiculo (id),
    CONSTRAINT fk_venda_cliente      FOREIGN KEY (cliente_id)  REFERENCES cliente (id),
    CONSTRAINT fk_venda_vendedor     FOREIGN KEY (vendedor_id) REFERENCES usuario (id),
    CONSTRAINT fk_venda_proposta     FOREIGN KEY (proposta_id) REFERENCES proposta (id),
    CONSTRAINT uq_venda_veiculo      UNIQUE (veiculo_id),
    CONSTRAINT uq_venda_proposta     UNIQUE (proposta_id),
    CONSTRAINT ck_venda_valor        CHECK (valor_final > 0),
    CONSTRAINT ck_venda_forma_pgto   CHECK (forma_pagamento IN ('A_VISTA','FINANCIAMENTO','CONSORCIO'))
);
CREATE INDEX ix_venda_cliente_id  ON venda (cliente_id);
CREATE INDEX ix_venda_vendedor_id ON venda (vendedor_id);

-- ---------------------------------------------------------------------
-- Documentação no próprio catálogo do SGBD
-- ---------------------------------------------------------------------
COMMENT ON TABLE usuario  IS 'Funcionários com acesso ao painel (ADMIN ou VENDEDOR)';
COMMENT ON TABLE marca    IS 'Fabricantes de veículos';
COMMENT ON TABLE cliente  IS 'Interessados e compradores, identificados pelo e-mail';
COMMENT ON TABLE veiculo  IS 'Veículos anunciados; status controla a exibição no catálogo';
COMMENT ON TABLE proposta IS 'Ofertas de compra enviadas pela vitrine pública';
COMMENT ON TABLE venda    IS 'Vendas concluídas; cada veículo pode ser vendido uma única vez';

COMMIT;
