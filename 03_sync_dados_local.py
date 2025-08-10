import mysql.connector
import json
from datetime import datetime

# tratar atualização de clientes - 
# tratar consulta de apenas novos clientes
# aguardar para mudar para a API do maps
# tentar fazer o post individual de um cliente e uma os (considerando a atividade criada)
# escalar para os demais clientes
# em caso de dados obrigatorios pendentes, armazenar clientes separadamente para tratamento manual
# implementação de notificação via email (cadastrados e com erro)

with open('clientes_processados.json', 'r', encoding='utf-8') as file:
    clientes_completos = json.load(file)

# conexão com o banco de dados relacional
conexao = mysql.connector.connect(
    host= 'localhost',
    user= 'root',
    password= '',
    database= 'sync_isales_field'
)

# criação do cursor que realizará as ações no banco de dados
cursor = conexao.cursor()

log_path = 'log_erros_insercao.txt'

# verificação se o cliente existe no banco 
def cliente_existe(doc_pessoal):
    cursor.execute("SELECT id FROM cliente WHERE doc_pessoal = %s", (doc_pessoal,))
    resultado = cursor.fetchone() # faz a busca
    if resultado: # se encontrar
        return True, resultado[0]  # retorna True e o id do cliente
    else: # se não encontrar
        return False, None # retorna False e none
    
def buscar_endereco_por_isales_id(isales_id):
    cursor.execute("""
        SELECT e.id, e.cep, e.logradouro, e.numero, e.complemento, e.bairro, e.cidade, e.estado, 
               e.link_localizacao, e.latitude, e.longitude, os.isales_id
        FROM endereco e
        INNER JOIN os ON e.id = os.endereco_id
        WHERE os.isales_id = %s
    """, (isales_id,))

    resultado = cursor.fetchone()
    if resultado:
        return True, {
            'id': resultado[0],
            'cep': resultado[1],
            'logradouro': resultado[2],
            'numero': resultado[3],
            'complemento': resultado[4],
            'bairro': resultado[5],
            'cidade': resultado[6],
            'estado': resultado[7],
            'link_localizacao': resultado[8],
            'latitude': resultado[9],
            'longitude': resultado[10],
            'isales_id': resultado[11]
        }
    else:
        return False, None


def os_existe(cliente_id, endereco_id, isales_id):
    cursor.execute("""
        SELECT id, tipo_servico, coluna_id, modulos, inversor1, inversor2, inversor3, valor, observacoes, acesso
        FROM os
        WHERE cliente_id = %s AND endereco_id = %s AND isales_id = %s
    """, (cliente_id, endereco_id, isales_id))

    resultado = cursor.fetchone()
    if resultado:
        return True, {
            'id': resultado[0],
            'tipo_servico': resultado[1],
            'coluna_id': resultado[2],
            'modulos': resultado[3],
            'inversor1': resultado[4],
            'inversor2': resultado[5],
            'inversor3': resultado[6],
            'valor': resultado[7],
            'observacoes': resultado[8],
            'acesso': resultado[9],
        }
    else:
        return False, None
    
def pgto_existe(os_id):
    cursor.execute("""
        SELECT id, forma_pgto, responsavel_financiamento, valor_seguro, observacoes
        FROM pagamento
        WHERE os_id = %s""", (os_id,))
    
    resultado = cursor.fetchone()
    if resultado:
        return True, {
            'id': resultado[0],
            'forma_pgto': resultado[1],
            'responsavel_financiamento': resultado[2],
            'valor_seguro': resultado[3],
            'observacoes': resultado[4]
        }
    else:
        return False, None
    
def tratar_lista(valor):
    if isinstance(valor, list):
        return ', '.join(str(v) for v in valor) if valor else ''
    elif valor is None:
        return ''
    return str(valor)

# inserção de dados
try:
    conexao.start_transaction()
    for cliente in clientes_completos:
        existe_cliente, cliente_id = cliente_existe(cliente['doc'])

        if not existe_cliente:
            cursor.execute(
                """ INSERT INTO cliente (
                    nome,
                    doc_pessoal,
                    email,
                    telefone,
                    telefone_secundario
                ) VALUES( %s, %s, %s, %s, %s)""",
                (
                    cliente['nome'],
                    cliente['doc'],
                    cliente['email'],
                    cliente['telefone'],
                    cliente['telefone_secundario'],
                )
            )
            cliente_id = cursor.lastrowid
        else:
            print(f"Cliente {cliente['nome']} já existe, ignorando inserção.")

        # verificação do endereço
        existe_endereco, endereco_dados = buscar_endereco_por_isales_id(cliente['id']) #param isales_id

        if not existe_endereco:
            cursor.execute(
                """ INSERT INTO endereco (
                    cep,
                    logradouro,
                    numero,
                    complemento,
                    bairro,
                    cidade,
                    estado,
                    link_localizacao,
                    latitude,
                    longitude,
                    location_field_id,
                    cliente_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    cliente['endereço']['cep'],
                    cliente['endereço']['logradouro'],
                    cliente['endereço']['numero'],
                    cliente['endereço']['complemento'],
                    cliente['endereço']['bairro'],
                    cliente['endereço']['cidade'],
                    cliente['endereço']['estado'],
                    cliente['endereço']['link_localizacao'],
                    cliente['endereço'].get('latitude', None),
                    cliente['endereço'].get('longitude', None),
                    None, # location id só após o post
                    cliente_id #insere o id do último cliente criado no bd
                ) 
            )    
            endereco_id = cursor.lastrowid
        else:
            # se existe, verificar se houve alteração
            endereco_existente = endereco_dados  # O dicionário que veio da consulta
            endereco_id = endereco_existente['id']  

            # Comparar os campos que podem ter sido atualizados
            if (
                cliente['endereço']['cep'] != endereco_existente['cep'] or
                cliente['endereço']['logradouro'] != endereco_existente['logradouro'] or 
                cliente['endereço']['numero'] != endereco_existente['numero'] or
                cliente['endereço']['complemento'] != endereco_existente['complemento'] or
                cliente['endereço']['bairro'] != endereco_existente['bairro'] or
                cliente['endereço']['cidade'] != endereco_existente['cidade'] or
                cliente['endereço']['estado'] != endereco_existente['estado'] or
                cliente['endereço']['link_localizacao'] != endereco_existente['link_localizacao'] or
                cliente['endereço'].get('latitude') != endereco_existente['latitude'] or
                cliente['endereço'].get('longitude') != endereco_existente['longitude']
            ):
                # Se houver diferença, atualiza o endereço no banco
                cursor.execute(
                    """UPDATE endereco
                    SET cep = %s, logradouro = %s, numero = %s, complemento = %s, bairro = %s, 
                    cidade = %s, estado = %s, link_localizacao = %s, latitude = %s, longitude = %s
                    WHERE id = %s""",
                    (
                        cliente['endereço']['cep'],
                        cliente['endereço']['logradouro'],
                        cliente['endereço']['numero'],
                        cliente['endereço']['complemento'],
                        cliente['endereço']['bairro'],
                        cliente['endereço']['cidade'],
                        cliente['endereço']['estado'],
                        cliente['endereço']['link_localizacao'],
                        cliente['endereço'].get('latitude'),
                        cliente['endereço'].get('longitude'),
                        endereco_id
                    )
                )
                print(f"Endereço atualizado para cliente id {cliente_id}.")
            else:
                print(f"Endereço já atualizado para cliente id {cliente_id}.")

        # verificação os
        existe_os, os_dados = os_existe(cliente_id, endereco_id, cliente['id']) # ID do cliente no iSales, não é o ID local do banco

        if not existe_os:
            cursor.execute(
                """ INSERT INTO os (
                    tipo_servico,
                    coluna_id,
                    vendedor,
                    data_fechamento,
                    modulos,
                    inversor1,
                    inversor2,
                    inversor3,
                    valor,
                    observacoes,
                    acesso,
                    isales_id,
                    field_id,
                    cliente_id,
                    endereco_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    cliente['servico_field'],
                    cliente['coluna_id'],
                    cliente['vendedor'],
                    cliente['data_fechamento'],
                    cliente['placas'],
                    cliente['inversor_1'],
                    cliente['inversor_2'],
                    cliente['inversor_3'],
                    cliente['valor_projeto'],
                    cliente['observacoes_projeto'],
                    tratar_lista(cliente['acesso_local']),
                    cliente['id'], #id isales
                    None, # field id só será adicionado após o post
                    cliente_id,
                    endereco_id
                )   
            )
            os_id = cursor.lastrowid

            # inserir de imediato o status do projeto no histórico
            status_inicial = 'cancelado' if cliente['coluna_id'] == 20363 else 'ativo'
            observacao = f"Status inicial com base na coluna_id {cliente['coluna_id']} no momento da criação da OS"

            # Insere no histórico
            cursor.execute("""
                INSERT INTO os_status_historico (os_id, status, observacao, enviado_field)
                VALUES (%s, %s, %s, %s)
            """, (os_id, status_inicial, observacao, False))

        else:
            os_existente = os_dados
            os_id = os_existente['id']

            if (
                cliente['servico_field'] != os_existente['tipo_servico'] or cliente['coluna_id'] != os_existente['coluna_id'] or 
                cliente['placas'] != os_existente['modulos'] or cliente['inversor_1'] != os_existente['inversor1'] or 
                cliente['inversor_2'] != os_existente['inversor2'] or  cliente['inversor_3'] != os_existente['inversor3'] or 
                cliente['valor_projeto'] != os_existente['valor'] or cliente['observacoes_projeto'] != os_existente['observacoes'] or
                cliente['acesso_local'] != os_existente['acesso']):
                    
                    # se a mudança foi na coluna_id, registrar o histórico de status
                    if cliente['coluna_id'] != os_existente['coluna_id']:
                        status_anterior = 'cancelado' if os_existente['coluna_id'] == 20363 else 'ativo'
                        status_novo = 'cancelado' if cliente['coluna_id'] == 20363 else 'ativo'
                        observacao = f"Status alterado de {status_anterior} para {status_novo}."

                        cursor.execute("""
                            INSERT INTO os_status_historico (os_id, status, observacao, enviado_field)
                            VALUES (%s, %s, %s, %s)
                        """, (os_id, status_novo, observacao, False))

                    cursor.execute(
                        """UPDATE os
                        SET tipo_servico = %s, coluna_id = %s, modulos = %s, inversor1 = %s, inversor2 = %s, inversor3 = %s, valor = %s, observacoes = %s, acesso = %s
                        WHERE id = %s""", 
                        ( 
                            cliente['servico_field'],
                            cliente['coluna_id'],
                            cliente['placas'],
                            cliente['inversor_1'],
                            cliente['inversor_2'],
                            cliente['inversor_3'],
                            cliente['valor_projeto'],
                            cliente['observacoes_projeto'],
                            tratar_lista(cliente['acesso_local']),
                            os_id
                        )
                    )
        
            else:
                print(f"OS já atualizada para cliente id {cliente_id}")
            
        # verificação pagamento
        existe_pgto, pgto_dados = pgto_existe(os_id)

        if not existe_pgto:
            cursor.execute(
                """ INSERT INTO pagamento (
                    forma_pgto,
                    responsavel_financiamento,
                    valor_seguro,
                    observacoes,
                    os_id
                ) VALUES (%s, %s, %s, %s, %s)""",
                (
                    tratar_lista(cliente['forma_pagamento']),
                    cliente['financiamento_nome'],
                    cliente['valor_seguro'],
                    cliente['observacoes_pagamento'],
                    os_id
                )
            )
        else:
            pgto_existente = pgto_dados
            pgto_id = pgto_dados['id']

            if (
                cliente['forma_pagamento'] != pgto_existente['forma_pgto'] or
                cliente['financiamento_nome'] != pgto_existente['responsavel_financiamento'] or
                cliente['valor_seguro'] != pgto_existente['valor_seguro'] or
                cliente['observacoes_pagamento'] != pgto_existente['observacoes']
            ):
                cursor.execute(
                    """UPDATE pagamento
                    SET forma_pgto = %s, responsavel_financiamento = %s, valor_seguro = %s, observacoes = %s
                    WHERE id = %s""",
                    (
                        tratar_lista(cliente['forma_pagamento']),
                        cliente['financiamento_nome'],
                        cliente['valor_seguro'],
                        cliente['observacoes_pagamento'],
                        pgto_id
                    )
                )
                print(f"Pagamento atualizado para OS id {os_id}.")
            else:
                print(f"Pagamento já atualizado para OS id {os_id}.")

        conexao.commit()
    print("Dados inseridos com sucesso!")

except mysql.connector.Error as erro:
    nome_cliente = cliente['nome'] if 'cliente' in locals() else 'Desconhecido'
    mensagem = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro na transação do cliente {nome_cliente}: {erro}"
    print(mensagem)
    conexao.rollback()

    with open(log_path, 'a', encoding='utf-8') as log_file:
        log_file.write(mensagem + '\n')
        log_file.write(f"Dados do cliente: {json.dumps(cliente, ensure_ascii=False)}\n\n")

finally:
    cursor.close()
    conexao.close()