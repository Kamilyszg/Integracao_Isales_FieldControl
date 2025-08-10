import json
import re
import time
import requests
import mysql.connector
from datetime import datetime
import tqdm

ARQUIVO_ENTRADA = 'clientes_isales.json'
ARQUIVO_SAIDA = 'clientes_processados.json'
ARQUIVO_LOG = 'divergencias_log.txt'

def registrar_log(mensagem):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(ARQUIVO_LOG, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {mensagem}\n")

def expandir_link_google_maps(link):
    try:
        response = requests.get(link, allow_redirects=True, timeout=10)
        time.sleep(1)
        return response.url
    except Exception as e:
        print(f"Erro ao expandir link: {e}")
        return None

def extrair_coords_do_link(link):
    padroes = [
        r'@(-?\d+\.\d+),(-?\d+\.\d+)',
        r'/search/(-?\d+\.\d+),\+(-?\d+\.\d+)',
        r'maps\\?q=(-?\d+\.\d+),(-?\d+\.\d+)',
        r'%40(-?\d+\.\d+),(-?\d+\.\d+)',
        r'%3D(-?\d+\.\d+),(-?\d+\.\d+)',
        r'continue=https[^%]+%40(-?\d+\.\d+),(-?\d+\.\d+)',
        r'continue=https[^%]+%3D(-?\d+\.\d+),(-?\d+\.\d+)',
        r'/maps/search/(-?\d+\.\d+),%2B(-?\d+\.\d+)',
        r'coordinate=(-?\d+\.\d+)%2C(-?\d+\.\d+)',
        r'/maps/place/(-?\d+\.\d+),(-?\d+\.\d+)',
    ]
    for padrao in padroes:
        match = re.search(padrao, link)
        if match:
            return float(match.group(1)), float(match.group(2))
    return None, None

conexao = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='sync_isales_field'
)
cursor = conexao.cursor(dictionary=True)

with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8') as file:
    clientes_coletados = json.load(file)

clientes_processados = []

# Buscar todos os clientes, endereços, os e pagamentos de uma vez
cursor.execute("""
    SELECT c.doc_pessoal, c.id AS cliente_id, e.*, os.*, pgto.*
    FROM cliente c
    LEFT JOIN endereco e ON c.id = e.cliente_id
    LEFT JOIN os ON e.id = os.endereco_id
    LEFT JOIN pagamento pgto ON os.id = pgto.os_id
""")
registros_banco = cursor.fetchall()

# Organizar os registros do banco de dados por doc_pessoal
clientes_por_doc = {}
for row in registros_banco:
    doc = row['doc_pessoal']
    if doc not in clientes_por_doc:
        clientes_por_doc[doc] = []
    clientes_por_doc[doc].append(row)

for cliente in tqdm.tqdm(clientes_coletados, desc="Processando clientes"):
    cliente_doc = cliente.get('doc')
    registros_cliente = clientes_por_doc.get(cliente_doc, []) # se não está no banco, retorna uma lista vazia

    if not registros_cliente: #se não estiver no banco e não for cancelado
        # cliente novo - busca as coordenadas
        endereco = cliente['endereço']
        link = endereco.get('link_localizacao')
        lat, lon = None, None

        if cliente.get('coluna_id') == 20363:  # Cliente cancelado
            clientes_processados.append(cliente)
        
        else:
            if link:
                link_expandido = expandir_link_google_maps(link)
                if link_expandido:
                    lat, lon = extrair_coords_do_link(link_expandido)
                    if lat is not None and lon is not None:
                        endereco['latitude'] = lat
                        endereco['longitude'] = lon
                        clientes_processados.append(cliente)
                    else:
                        mensagem = f"Não foi possível extrair coordenadas do link expandido do cliente {cliente['id']} - {cliente['nome']}, link: {link_expandido}"
                        registrar_log(mensagem)
                else:
                    mensagem = f"Erro ao expandir link do cliente {cliente['id']} - {cliente['nome']}"
                    registrar_log(mensagem)
            else:
                mensagem = f"Cliente {cliente['id']} - {cliente['nome']} não possui link de localização"
                registrar_log(mensagem)

    else: #cliente está no banco - comparar os campos para identificar alteração no projeto/os
        campos = ['logradouro', 'numero', 'bairro', 'cidade', 'estado', 'complemento', 'link_localizacao',
            'modulos', 'inversor1', 'inversor2', 'inversor3','coluna_id', 'tipo_servico', 'forma_pgto', 'responsavel_financiamento', 'valor_seguro']

        isales_id = cliente.get('id')
        projeto_existe = False

        for resultado in registros_cliente:
            if resultado['isales_id'] == isales_id:
                projeto_existe = True

                campos_diferentes = []
                for campo in campos:
                    valor_novo = cliente.get(campo)
                    valor_antigo = resultado.get(campo)
                    if valor_novo != valor_antigo:
                        campos_diferentes.append((campo, valor_antigo, valor_novo))

                if campos_diferentes:
                    mensagem = f"Divergência detectada - Cliente: {cliente['nome']} ({cliente_doc})\n"
                    for campo, antigo, novo in campos_diferentes:
                        mensagem += f" - Campo '{campo}' alterado: '{antigo}' → '{novo}'\n"
                    registrar_log(mensagem.strip())
                    clientes_processados.append(cliente)
                    break

        if not projeto_existe:
            clientes_processados.append(cliente)

# Salva o JSON de saída
with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
    json.dump(clientes_processados, f, ensure_ascii=False, indent=4)

cursor.close()
conexao.close()

print(f"Processamento concluído. {len(clientes_processados)} clientes salvos em {ARQUIVO_SAIDA}.")