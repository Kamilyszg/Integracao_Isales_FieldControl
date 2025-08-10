import requests
import json
import time
from datetime import datetime
import mysql.connector

api_key_field = ''

log_path = 'log_post_impedido.txt'
logs_succeded_path = 'log_post_bem_sucedido.txt'

headers_field = {
    "Content-Type": "application/json;charset=UTF-8",
    "X-Api-Key": api_key_field
}

params_field = {
    'q': 'created_at>=:"2025-01-01T00:00:00Z"',
    'sort':'created_at'
}

def buscar_endereco_por_id(cliente_id):
    cursor.execute("SELECT * FROM endereco WHERE cliente_id = %s", (cliente_id,))
    return cursor.fetchall()

def registrar_log(mensagem):

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {mensagem}"

    print(log_line)

    with open(log_path, 'a', encoding='utf-8') as log_file:
        log_file.write(mensagem + '\n')

def buscar_os_pgto_local(endereco_id):
    cursor.execute(
        """SELECT os.id, os.tipo_servico, os.coluna_id, os.vendedor, os.modulos, os.data_fechamento, os.inversor1, os.inversor2, os.inversor3, os.valor, 
        os.observacoes AS observacoes_projeto, os.acesso, os.isales_id, os.field_id, pgto.forma_pgto, pgto.responsavel_financiamento, 
        pgto.valor_seguro, pgto.observacoes AS observacoes_pgto
        FROM os INNER JOIN pagamento pgto
            ON os.id = pgto.os_id
        WHERE endereco_id = %s""", (endereco_id,))
    return cursor.fetchall()

def montar_descricao_os(os):
    descricao = ""

    if os.get('vendedor'):
        descricao += f"VENDEDOR: {os.get('vendedor')}\n\n"

    if os.get('data_fechamento'):
        descricao += f"DATA DE FECHAMENTO: {os.get('data_fechamento')}\n\n"

    if os.get('modulos'):
        descricao += f"KIT ADQUIRIDO:\n- {os.get('modulos')}\n"

    if os.get('inversor1'):
        descricao += f"- {os.get('inversor1')}\n"

    if os.get('inversor2'):
        descricao += f"- {os.get('inversor2')}\n"
    
    if os.get('inversor3'):
        descricao += f"- {os.get('inversor3')}\n"

    if os.get('acesso'):
        descricao += f"ACESSO AO LOCAL: {os.get('acesso')}\n"

    if os.get('observacoes_projeto'):
        descricao += f"OBSERVAÇÕES DO PROJETO: {os.get('observacoes_projeto')}\n"

    if os.get('valor'):
        descricao += f"VALOR DO CONTRATO: {os.get('valor')}\n"

    if os.get('forma_pgto'):
        descricao += f"FORMA DE PAGAMENTO: {os.get('forma_pgto')}\n"

    if os.get('responsavel_financiamento'):
        descricao += f"RESPONSÁVEL FINANCIAMENTO: {os.get('responsavel_financiamento')}\n"

    if os.get('valor_seguro'):
        descricao += f"VALOR DO SEGURO: {os.get('valor_seguro')}\n"

    if os.get('observacoes_pgto'):
        descricao += f"OBSERVAÇÕES DO PAGAMENTO: {os.get('observacoes_pgto')}\n"

    return descricao.strip()

definir_assunto_map = {
    'MTgyMTc2OjYyNDg5': 'Aumento de Sistema',
    'MTcyMTExOjYyNDg5': 'Instalação',
    'MzE2MTA0OjYyNDg5': 'Cancelamento'
}

def definir_assunto(tipo_servico, nome_cliente):
    titulo = definir_assunto_map.get(tipo_servico, 'Solicitação') #verificar necessidade de mudança
    return f"{titulo}: {nome_cliente}"

def criar_location(endereco, cliente_id_field, cliente_local, modo_teste=False):

    if modo_teste:
        print(f"[MODO TESTE] Location não enviada para {cliente['nome']}")
        return f'teste_location_id{cliente['id']}'

    location_payload = {
        'name': f"{endereco.get('logradouro', '')} - {endereco.get('numero', '')}",
        'customer': {
            'id': cliente_id_field
        },
        'address': {
            'postalCode': endereco.get('cep', ''),
            'street': endereco.get('logradouro', ''),
            'number': endereco.get('numero', ''),
            'neighborhood': endereco.get('bairro', ''),
            'city': endereco.get('cidade', ''),
            'state': endereco.get('estado', ''),
            'complement': endereco.get('complemento', ''),
            'coords': {
                'latitude': endereco.get('latitude'),
                'longitude': endereco.get('longitude')
            }
        }
    }
    
    try:
        print(f"Criando o endereço de ID {endereco.get('id')} do cliente {cliente_local.get('id')} - {cliente_local.get('nome')}")

        response = requests.post(
            f"https://carchost.fieldcontrol.com.br/customers/{cliente_id_field}/locations",
            headers=headers_field,
            json=location_payload
        )
        response.raise_for_status()

        retorno = response.json()
        location_field_id = retorno['id']

        cursor.execute(
            "UPDATE endereco SET location_field_id = %s WHERE id = %s",
            (location_field_id, endereco.get('id'))
        )
        conexao.commit()

        with open(logs_succeded_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"Localização criada com sucesso: {cliente_local.get('nome')} - {endereco.get('logradouro')} - {location_field_id}\n")

        return location_field_id

    except requests.exceptions.RequestException:
        registrar_log(f"ID: {cliente_local.get('id')} - NOME: {cliente_local.get('nome')} - Erro ao cadastrar endereço {endereco.get('id')}")
        return None

def criar_solicitacao_os(os, cliente_local, cliente_id_field, location_field_id, modo_teste=False):
    

    ticket_payload = {
        'name': cliente_local.get('nome'),
        'external': {
            'id': os.get('isales_id')
        },
        'subject': definir_assunto(os.get('tipo_servico'), cliente_local.get('nome')),
        'message': montar_descricao_os(os),
        'customer': {
            'id': cliente_id_field
        },
        'service': {
            'id': os.get('tipo_servico')
        },
        'location': {
            'id': location_field_id
        }
    }
    
    if modo_teste:
        print(f"\n[MODO TESTE] OS NÃO ENVIADA: {os.get('id')} - {cliente_local.get('nome')}")
        print("[MODO TESTE] Payload que seria enviado:")
        print(json.dumps(ticket_payload, indent=4, ensure_ascii=False))
        return
    
    try:
        print(f"Criando a OS de ID {os.get('id')} para cliente {cliente_local.get('id')} - {cliente_local.get('nome')}")

        response = requests.post(
            'https://carchost.fieldcontrol.com.br/tickets/',
            headers=headers_field,
            json=ticket_payload
        )
        response.raise_for_status()

        retorno = response.json()
        ticket_id = retorno['id']

        cursor.execute(
            "UPDATE os SET field_id = %s, criado_pelo_script = %s WHERE id = %s",
            (ticket_id, True, os.get('id'))
        )
        conexao.commit()

        # Marca o status como enviado
        status = buscar_status_nao_enviado(os['id'])
        if status:
            cursor.execute("""
                UPDATE os_status_historico
                SET enviado_field = TRUE
                WHERE id = %s
            """, (status['id'],))
            conexao.commit()

        with open(logs_succeded_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"OS criada com sucesso: {cliente_local.get('nome')} - OS ID: {ticket_id}\n")

    except requests.exceptions.RequestException:
        registrar_log(f"ID: {cliente_local.get('id')} - NOME: {cliente_local.get('nome')} - Erro ao criar OS {os.get('id')}")

def criar_cliente(cliente, endereco_primario, modo_teste=False):

    if modo_teste:
        print(f"[MODO TESTE] Cliente não enviado: {cliente['nome']}")
        return f'teste_id_cliente{cliente['id']}', f'teste_location_id{cliente['id']}'

    payload = {
        'name': cliente.get('nome'),
        'documentNumber': cliente.get('doc_pessoal'),
        'address': {
            'zipCode': endereco_primario.get('cep', ''),
            'street': endereco_primario.get('logradouro', ''),
            'number': endereco_primario.get('numero', ''),
            'neighborhood': endereco_primario.get('bairro', ''),
            'complement': endereco_primario.get('complemento', ''),
            'city': endereco_primario.get('cidade', ''),
            'state': endereco_primario.get('estado', ''),
            'coords': {
                'latitude': endereco_primario.get('latitude'),
                'longitude': endereco_primario.get('longitude')
            }
        }
    }

    try:
        print(f"Criando cliente: ID {cliente.get('id')} - NOME {cliente.get('nome')}")

        response = requests.post(
            f"https://carchost.fieldcontrol.com.br/customers",
            headers=headers_field,
            json=payload
        )
        response.raise_for_status()

        retorno = response.json()
        cliente_id_field = retorno['id']
        location_id = retorno['primaryLocation']['id']

        with open(logs_succeded_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"Cliente criado com sucesso: {cliente.get('nome')} - ID: {cliente_id_field}\n")

        return cliente_id_field, location_id

    except requests.exceptions.RequestException as e:
        registrar_log(f"ID: {cliente.get('id')} - NOME: {cliente.get('nome')} - Erro ao criar cliente: {e}")
        return None, None
    
def criar_telefone(cliente_id_field, telefone, modo_teste=False):

    if modo_teste:
        print(f"[MODO TESTE] Telefone não enviado: {telefone}")
        return

    payload = {
        "number": telefone,
        "type": "mobile"
    }

    try:
        response = requests.post(
            f"https://carchost.fieldcontrol.com.br/customers/{cliente_id_field}/phones",
            headers=headers_field,
            json=payload
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        registrar_log(f"Erro ao criar telefone {telefone} para cliente {cliente_id_field}: {e}")
        return False

def criar_email(cliente_id_field, email, modo_teste=False):
    
    if modo_teste:
        print(f"[MODO TESTE] E-mail não enviado: {email}")
        return
    
    payload = {
        "address": email,
        "type": "personal"
    }
    
    try:
        response = requests.post(
            f"https://carchost.fieldcontrol.com.br/customers/{cliente_id_field}/emails",
            headers=headers_field,
            json=payload
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        registrar_log(f"Erro ao criar e-mail {email} para cliente {cliente_id_field}: {e}")
        return False

def buscar_status_nao_enviado(os_id):
    cursor.execute("""
        SELECT id, status
        FROM os_status_historico
        WHERE os_id = %s AND enviado_field = FALSE
        ORDER BY data_status DESC
        LIMIT 1
    """, (os_id,))
    return cursor.fetchone()  # retorna {'id': ..., 'status': ...} ou None

# get de clientes cadastrados
clientes_field_url = 'https://carchost.fieldcontrol.com.br/customers'
clientes_field = []

# parâmetros de paginação
limit = 100
offset = 0
total_count = None

try:
    while True:
        params_field['limit'] = limit
        params_field['offset'] = offset

        response = requests.get(clientes_field_url, params=params_field, headers=headers_field)
        data_clientes_field = response.json()

        clientes_field.extend(data_clientes_field['items'])

        if total_count is None: #pag 1
            total_count = data_clientes_field['totalCount'] #recebe a quantidade de resultados total
        
        offset += limit # offset recebe o indice do cliente da próxima pag

        if offset >= total_count: #pag final
            break

        time.sleep(1)
except requests.exceptions.RequestException as e:
    print("Erro ao acessar a API:", e)

with open('field_customers.json', 'w', encoding='utf-8') as file:
    json.dump(clientes_field, file, ensure_ascii=False, indent=4)
        
# comparação com o banco local
clientes_cadastrados = {
    'criados_pelo_script': [],
    'criados_manualmente': []
}

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="sync_isales_field"
)
cursor = conexao.cursor(dictionary=True, buffered=True)

cursor.execute("SELECT * FROM cliente")
clientes_locais = cursor.fetchall()

modo_teste = True

clientes_locais = [cliente for cliente in clientes_locais if cliente['id'] in [847, 961, 880]]

clientes_a_cadastrar = []

for cliente_local in clientes_locais:
    encontrado_na_field = next((cliente for cliente in clientes_field if cliente_local['doc_pessoal'] == cliente['documentNumber']), None)

    if not encontrado_na_field:
        clientes_a_cadastrar.append(cliente_local) 

    else: 
        cliente_id_local = cliente_local['id']
        cliente_id_field = encontrado_na_field['id']

        if cliente_local['criado_pelo_script'] == 0:
            clientes_cadastrados['criados_manualmente'].append({
                'cliente_local': cliente_local,
                'cliente_field': encontrado_na_field
            })

            if not cliente_local['field_id']:
                cursor.execute("UPDATE cliente SET field_id = %s WHERE id = %s", (cliente_id_field, cliente_id_local))
                conexao.commit()

        elif cliente_local['criado_pelo_script'] == 1:
            clientes_cadastrados['criados_pelo_script'].append({
                'cliente_local': cliente_local,
                'cliente_field': encontrado_na_field
            })

            #verificação do endereço - se possui location_id, já foi cadastrado
            enderecos_locais = buscar_endereco_por_id(cliente_id_local)

            for endereco in enderecos_locais:
                if not endereco['location_field_id']:
                    # post location
                    location_field_id = criar_location(endereco, cliente_id_field, cliente_local, modo_teste=modo_teste)

                    if location_field_id:
                        os_locais = buscar_os_pgto_local(endereco['id'])

                        for os in os_locais:
                            if not os['field_id']:
                                # post ticket
                                criar_solicitacao_os(os, cliente_local, cliente_id_field, location_field_id, modo_teste=modo_teste)

                else:
                    location_field_id = endereco['location_field_id']

                    os_locais = buscar_os_pgto_local(endereco['id'])

                    for os in os_locais:
                        if not os['field_id']:
                            criar_solicitacao_os(os, cliente_local, cliente_id_field, location_field_id, modo_teste=modo_teste)

                        #aqui vejo se há alguma alteração na coluna do isales
                        else:
                            status_pendente = buscar_status_nao_enviado(os['id'])

                            if not status_pendente:
                                continue

                            criar_solicitacao_os(os, cliente_local, cliente_id_field, location_field_id, modo_teste=modo_teste)

        else:
            mensagem = f"ID: {cliente_id_local} - NOME: {cliente_local['nome']} - Campo 'criado_pelo_script' está nulo ou inválido"
            registrar_log(mensagem)

for cliente in clientes_a_cadastrar: 

    print(f"cliente a ser criado de ID {cliente['id']}")

    cliente_id_local = cliente['id']
    enderecos_locais = buscar_endereco_por_id(cliente_id_local)

    cursor.execute("SELECT coluna_id FROM os WHERE cliente_id = %s", (cliente_id_local,))
    coluna_id = cursor.fetchone()

    if coluna_id == 20363:  # OS cancelada, ignora
        continue

    if not enderecos_locais:
        mensagem = f"ID: {cliente_id_local} - NOME: {cliente['nome']} - Não é possível criar o cliente: sem endereços"
        registrar_log(mensagem)
        continue

    endereco_primario = enderecos_locais[0]
    outros_enderecos = enderecos_locais[1:]

    cliente_id_field, primary_location_id = criar_cliente(cliente, endereco_primario, modo_teste=modo_teste)

    if not cliente_id_field:
        mensagem = f"ID: {cliente_id_local} - NOME: {cliente['nome']} - Erro ao criar cliente na Field"
        registrar_log(mensagem)
        continue
    
    # Atualiza cliente no banco
    cursor.execute(
        "UPDATE cliente SET field_id = %s, criado_pelo_script = %s WHERE id = %s",
        (cliente_id_field, True, cliente_id_local)
    )
    conexao.commit()

    # Atualiza endereço primário
    cursor.execute(
        "UPDATE endereco SET location_field_id = %s WHERE id = %s",
        (primary_location_id, endereco_primario['id'])
    )
    conexao.commit()

    # cadastro de contatos
    if cliente.get('telefone'):
        criar_telefone(cliente_id_field, cliente['telefone'], modo_teste=modo_teste)
    
    if cliente.get('telefone_secundario'):
        criar_telefone(cliente_id_field, cliente['telefone_secundario'], modo_teste=modo_teste)

    if cliente.get('email'):
        criar_email(cliente_id_field, cliente['email'], modo_teste=modo_teste)

     # Criação de OS para o endereço primário
    os_primaria = buscar_os_pgto_local(endereco_primario['id'])

    for os in os_primaria:
        if os['coluna_id'] == 20363:  # OS cancelada, ignora
            registrar_log(f"OS cancelada ignorada para cliente {cliente['id']} - {cliente['nome']}")
            continue

        if not os['field_id']:
            criar_solicitacao_os(os, cliente, cliente_id_field, primary_location_id, modo_teste=modo_teste)

    # cadastro de demais endereços          
    for endereco in outros_enderecos:
        location_field_id = criar_location(endereco, cliente_id_field, cliente, modo_teste=modo_teste)

        if location_field_id:
            cursor.execute("UPDATE endereco SET location_field_id = %s WHERE id = %s", (location_field_id, endereco['id']))
            conexao.commit()

            # cadastro ticket
            os_locais = buscar_os_pgto_local(endereco['id'])

            for os in os_locais:
                if os['coluna_id'] == 20363:  # OS cancelada, ignora
                    registrar_log(f"OS cancelada ignorada para cliente {cliente['id']} - {cliente['nome']}")
                    continue

                if not os['field_id']:
                    criar_solicitacao_os(os, cliente, cliente_id_field, location_field_id, modo_teste=modo_teste)

cursor.close()
conexao.close()