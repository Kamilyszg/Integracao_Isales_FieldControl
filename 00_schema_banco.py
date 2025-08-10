import mysql.connector

# conexão com o banco de dados relacional
conexao = mysql.connector.connect(
    host= 'localhost',
    user= 'root',
    password= '',
    database= 'sync_isales_field'
)

# criação do cursor que realizará as ações no banco de dados
cursor = conexao.cursor()

# cliente
cursor.execute(
    """CREATE TABLE IF NOT EXISTS cliente (
        id INT PRIMARY KEY AUTO_INCREMENT UNIQUE,
        nome VARCHAR(50),
        doc_pessoal VARCHAR(20) UNIQUE,
        email VARCHAR(255),
        telefone VARCHAR(20),
        telefone_secundario VARCHAR(20),
        field_id VARCHAR(255) NULL UNIQUE,
        criado_pelo_script BOOLEAN NULL DEFAULT FALSE
    )"""
)

# endereço
# relacionamento 1-n entre os e endereco 
# uma os pode ter um endereco
# um edereco pode ter varias os

cursor.execute(
    """CREATE TABLE IF NOT EXISTS endereco (
        id INT PRIMARY KEY AUTO_INCREMENT UNIQUE,
        cep VARCHAR(10),
        logradouro VARCHAR(255),
        numero VARCHAR(20),
        complemento VARCHAR(255) NULL,
        bairro VARCHAR(255),
        cidade VARCHAR(255),
        estado VARCHAR(255),
        link_localizacao VARCHAR(500),
        latitude VARCHAR(50),
        longitude VARCHAR(50),
        location_field_id VARCHAR(255),
        cliente_id INT,
        FOREIGN KEY (cliente_id) REFERENCES cliente(id)
    )"""
)

# OS (projetos)
cursor.execute(
    """CREATE TABLE IF NOT EXISTS os (
        id INT PRIMARY KEY AUTO_INCREMENT UNIQUE,
        tipo_servico VARCHAR(255),
        coluna_id INT,
        vendedor VARCHAR(255),
        data_fechamento DATETIME,
        modulos VARCHAR(255),
        inversor1 VARCHAR(500),
        inversor2 VARCHAR(500),
        inversor3 VARCHAR(500),
        valor VARCHAR(50),
        observacoes TEXT,
        acesso VARCHAR(255),
        isales_id VARCHAR(50) UNIQUE,
        field_id VARCHAR(255) NULL UNIQUE,
        criado_pelo_script BOOLEAN NULL DEFAULT FALSE,
        cliente_id INT,
        endereco_id INT,
        FOREIGN KEY (cliente_id) REFERENCES cliente(id),
        FOREIGN KEY (endereco_id) REFERENCES endereco(id)
    )"""
)

# histórico da OS - para casos de cancelamento ou alterações de status
cursor.execute(
    """CREATE TABLE IF NOT EXISTS os_status_historico (
        id INT PRIMARY KEY AUTO_INCREMENT,
        os_id INT,
        status VARCHAR(50),
        data_status DATETIME DEFAULT CURRENT_TIMESTAMP,
        observacao TEXT,
        enviado_field BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (os_id) REFERENCES os(id)
    )"""
)

# pagamento
cursor.execute(
    """CREATE TABLE IF NOT EXISTS pagamento (
        id INT PRIMARY KEY AUTO_INCREMENT UNIQUE,
        forma_pgto VARCHAR(255),
        responsavel_financiamento VARCHAR(255) NULL,
        valor_seguro VARCHAR(50),
        observacoes TEXT,
        os_id INT,
        FOREIGN KEY (os_id) REFERENCES os(id)
    )"""
)
    
print("Tabelas criadas com sucesso!")

cursor.close()
conexao.close()