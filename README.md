# Integração iSales → FieldControl com Banco Local

Este projeto realiza a integração entre o sistema CRM **iSales** (formato Kanban) e o sistema ERP **FieldControl**, com persistência em banco de dados local.

---

## 📌 Objetivo

- Automatizar a transferência de dados de projetos aprovados e/ou cancelados entre sistemas.
- Garantir que **nenhuma informação seja perdida**, mesmo se houver alterações de status no projeto.
- Ter controle completo sobre os dados, podendo auditar mudanças e reprocessar eventos.

---

## 🧭 Etapas do processo

| Etapa | Script | Função |
|-------|--------|--------|
| 0️⃣ | `00_schema_banco.py` | Cria o esquema do banco de dados local (cliente, endereço, OS, pagamentos, histórico de status etc.) |
| 1️⃣ | `01_get_projetos_isales.py` | Coleta dados de projetos via API do iSales |
| 2️⃣ | `02_tratar_dados_clientes.py` | Complementa os dados com geolocalização e ajusta o JSON para inserção |
| 3️⃣ | `03_sync_dados_local.py` | Insere ou atualiza dados no banco local, com controle de status e mudanças |
| 4️⃣ | `04_sync_field_api.py` | Realiza o envio para a API do FieldControl, com controle de duplicações e status pendentes |

---

## 💾 Estrutura do banco (relacional)

- Tabelas: `cliente`, `endereco`, `os`, `pagamento`, `os_status_historico`
- Toda mudança relevante de status é registrada.
- OS de cancelamento são criadas apenas quando há um histórico válido anterior.

!['Modelo Entidade Relacionamento'](./Imagens/mer_schema_sync.png)

---

## 👩‍💻 Desenvolvido por

**Kamily Gracia**  
Desenvolvedora Júnior  
Contato: [LinkedIn](https://www.linkedin.com/in/kamily-de-souza-gracia/)

---