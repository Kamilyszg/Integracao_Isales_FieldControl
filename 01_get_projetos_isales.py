import requests
import re
import json
import tqdm
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

api_key_isales = ''

params_isales = {
    "api_token": api_key_isales
}

# colunas necessárias isales - serviço correspondente na field
coluna_para_servico = {
    17840: "MTcyMTExOjYyNDg5",  # Instalação
    20024: "MTgyMTc2OjYyNDg5",  # Aumento
    20363: 'MzE2MTA0OjYyNDg5' #cancelado
}

# clientes presentes no funil de engenharia - isales
funil_clientes = []

params_isales['funil_id'] = 2666
params_isales['desde'] = '2025-01-01'
params_isales['ate'] = datetime.now().strftime('%Y-%m-%d')

funil_clientes_path = 'https://app.isales.company/api/funil-clientes'

def retirar_especiais(texto):
    if texto:
        return re.sub(r'\D', '', texto)
    return None

def buscar_valor(campos, campo_antigo, campo_novo):
    """
    Primeiro tenta buscar o campo novo (preferido).
    Se estiver vazio, busca o campo antigo.
    """
    # Se o campo novo existe e está preenchido, retorna ele
    if campo_novo in campos and campos[campo_novo] not in [None, '', []]:
        return campos[campo_novo]
    
    # Se o campo antigo existe e está preenchido, retorna ele
    if campo_antigo in campos and campos[campo_antigo] not in [None, '', []]:
        return campos[campo_antigo]
    
    # Se nenhum estiver preenchido, retorna None
    return None

#vai receber o id
def completar_cliente(cliente_id):

    # pular se não está no interesse
    if cliente_id not in clientes_interesse:
        return None
    
    cli = clientes_interesse[cliente_id]

    try:
        response_cliente = requests.get(f"https://app.isales.company/api/clientes?api_token={api_key_isales}&cliente_id={cliente_id}")
        response_cliente.raise_for_status()
        cliente = response_cliente.json().get('clientes', {})

        cliente_infos = {
            'id': cliente_id,
            'nome': cliente.get('nome'),
            'doc': retirar_especiais(cliente.get('cpf')),
            'email': cliente.get('email'),
            'telefone': retirar_especiais(cliente.get('telefone')),
            'telefone_secundario': retirar_especiais(cliente.get('telefone_secundario')),

            'endereço': {
                'cep': retirar_especiais(cliente.get('cep')),
                'logradouro': cliente.get('logradouro', ''),
                'numero': cliente.get('numero', ''),
                'complemento': cliente.get('complemento'),
                'bairro': cliente.get('bairro', ''),
                'cidade': cliente.get('cidade', ''),
                'estado': cliente.get('estado', ''),
                'link_localizacao': cliente.get('link_localizacao')
            },

            'coluna_id': cli['coluna_id'],
            'servico_field': coluna_para_servico.get(cli['coluna_id']),
            'vendedor': cli.get('cliente', {}).get('vendedor'),
            'data_fechamento': cliente.get('data_fechamento')
        }

        response_proposta = requests.get(f"https://app.isales.company/api/propostas?api_token={api_key_isales}&cliente_id={cliente_id}")
        response_proposta.raise_for_status()
        proposta = response_proposta.json().get('propostas', {})

        cliente_infos['placas'] = proposta.get('mod_descricao')

        cliente_infos['inversor_1'] = proposta.get('inv_descricao')
        cliente_infos['inversor_2'] = proposta.get('inv2_descricao')
        cliente_infos['inversor_3'] = proposta.get('inv3_descricao')

        cliente_infos['valor_projeto'] = proposta.get('valor_final')

        response_campos_customizados = requests.get(f"https://app.isales.company/api/campo-customizado?api_token={api_key_isales}&cliente_id={cliente_id}")
        response_campos_customizados.raise_for_status()
        data_campos_customizados = response_campos_customizados.json()

        campos = data_campos_customizados['clientes']

        cliente_infos['valor_seguro'] = campos.get('VALOR DO SEGURO', None)
        cliente_infos['forma_pagamento'] = buscar_valor(campos, 'Forma de Pagamento', 'FORMA DE PAGAMENTO')
        cliente_infos['financiamento_nome'] = campos.get('FINANCIAMENTO NO NOME DE (somente se a FORMA DE PAGMENTO for FINANCIAMENTO)', None)
        cliente_infos['observacoes_pagamento'] = campos.get('DETALHAMENTO DO PAGAMENTO', None)

        cliente_infos['observacoes_projeto'] = campos.get('OBSERVAÇÕES', None)
        cliente_infos['acesso_local'] = campos.get('ACESSO AO LOCAL (marcar todas as opções aplicáveis)', None)

        return cliente_infos
    
    except requests.exceptions.RequestException as e:
        print(f"[Erro cliente {cliente_id}] {e}")
        return None

try:
    response = requests.get(funil_clientes_path, params=params_isales)
    response.raise_for_status() # obtém o status da requisição, se ocorrer um erro lança uma exceção
    data_funil_clientes = response.json() # armazenamento das informações em formato json

    for cliente in data_funil_clientes['funil_clientes']:
        funil_clientes.append(cliente)

except requests.exceptions.RequestException as e:
    print("Erro ao acessar a API:", e) #exibição da exceção

# filtragem necessária das colunas de interesse - projetos aprovados, aumentos de sistemas e cancelados
projetos_interesse = []
projetos_interesse.extend(list(filter(lambda cliente: cliente['coluna_id'] == 17840 or cliente['coluna_id'] == 20024 or cliente['coluna_id'] == 20363, funil_clientes)))

clientes_completos = []

clientes_interesse = {cli['cliente_id']: cli for cli in projetos_interesse} # dicionário para consulta

"""for i, (chave, valor) in enumerate(clientes_interesse.items()):
    if i>= 5:
        break
    print(f'{chave}: {valor}')"""

# Processamento paralelo
with ThreadPoolExecutor(max_workers=10) as executor:
    futuros = [executor.submit(completar_cliente, cid) for cid in clientes_interesse.keys()]
    for future in tqdm.tqdm(as_completed(futuros), total=len(futuros)):
        cliente_finalizado = future.result()
        if cliente_finalizado:
            clientes_completos.append(cliente_finalizado)

with open('clientes_isales.json', 'w', encoding='utf-8') as f:
    json.dump(clientes_completos, f, ensure_ascii=False, indent=4)