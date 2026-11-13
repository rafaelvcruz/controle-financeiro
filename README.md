# Controle Financeiro Familiar

Projeto em evolução para controle financeiro familiar, com Angular, FastAPI, PostgreSQL e Docker Compose.

## Escopo desta primeira entrega

- Backend REST com CRUD básico para pessoas, categorias, grupos, subgrupos e contas financeiras.
- PostgreSQL persistente em volume Docker.
- Frontend Angular responsivo para lançamentos, contas e transferências.
- Endpoint de saúde em `/api/health` e documentação OpenAPI em `/docs`.
- Modelo em evolução para orçamento, cartões e objetivos.

> **Atenção:** esta é uma base de desenvolvimento, não uma instalação pronta para uso com dados financeiros reais. Autenticação, autorização, auditoria completa, política de backup testada, HTTPS e validações financeiras avançadas ainda precisam ser implementadas antes de expor a aplicação ou utilizá-la como sistema oficial.

## Requisitos

- Docker Desktop (Windows/macOS) ou Docker Engine + Compose (Linux).
- 8 GB de RAM recomendados para a máquina hospedeira; o projeto consome bem menos.
- Portas locais 4200 (interface), 8000 (API) e 5432 (PostgreSQL) disponíveis.

## Executar

1. Copie `.env.example` para `.env`.
2. Altere `POSTGRES_PASSWORD` por uma senha forte.
3. Na pasta do projeto, execute:

   ```bash
   docker compose up --build
   ```

4. Acesse:
   - Interface: http://localhost:4200
   - API: http://localhost:8000/api/health
   - Documentação da API: http://localhost:8000/docs

O banco fica em um volume Docker chamado `postgres_data`. **Não execute `docker compose down -v` se quiser preservar o banco**, pois o parâmetro `-v` remove os volumes.

## Acesso pelo celular na mesma rede Wi-Fi

Descubra o endereço IP local do computador servidor (por exemplo, `192.168.1.100`) e abra `http://192.168.1.100:4200` no celular. Configure o firewall para permitir a porta 4200 somente na rede privada. O computador servidor precisa permanecer ligado.

Para acesso fora de casa, não exponha diretamente as portas no roteador. Planeje VPN (por exemplo, Tailscale), HTTPS, autenticação e revisão de segurança antes.

## Estrutura

- `frontend/`: aplicação Angular.
- `backend/app/models/`: entidades SQLAlchemy.
- `backend/app/api/`: endpoints REST.
- `backend/alembic/`: versionamento do esquema.
- `database/`: scripts auxiliares.
- `docker-compose.yml`: serviços locais.

## Banco e migrations

A primeira inicialização cria as tabelas do modelo para facilitar a avaliação do MVP. O Alembic está configurado para versionar evoluções futuras. Para gerar uma migration após alterar modelos:

```bash
docker compose exec api alembic revision --autogenerate -m "descricao da alteracao"
docker compose exec api alembic upgrade head
```

Para um ambiente de produção, substitua a criação automática inicial por uma migration inicial revisada e versionada, e não altere tabelas manualmente.

## Cadastros iniciais

A API disponibiliza CRUD para pessoas, categorias, grupos, subgrupos e contas. As categorias iniciais podem ser cadastradas pela interface ou API. O projeto não importa os lançamentos históricos da planilha e não define saldos financeiros fictícios.

## Próximas etapas recomendadas

1. Revisar os cadastros reais da planilha e fazer a carga seletiva validada.
2. Implementar autenticação e usuários/perfis.
3. Implementar orçamento mensal e previsto x realizado.
4. Implementar cartões, faturas e parcelamentos.
5. Implementar autenticação, auditoria e backup automatizado.
6. Criar e validar migration Alembic inicial e teste de restauração do backup.

## Módulo de lançamentos (versão 0.2.0)

A versão seguinte acrescenta:
- Receitas, despesas e investimentos com data de movimentação e competência.
- Vínculo opcional com pessoa, subgrupo e meio de pagamento; conta financeira obrigatória.
- Status `PREVISTO`, `REALIZADO` e `CANCELADO`. Apenas `REALIZADO` afeta o saldo.
- Transferências entre contas em tabela própria, sem classificá-las como receita ou despesa.
- Consulta de saldo por conta em `GET /api/accounts/{id}/balance`.
- Listagem e cadastro em `GET/POST /api/entries` e `GET/POST /api/transfers`.

A tela inicial agora permite cadastrar e listar receitas, despesas e investimentos. A seleção de grupo e subgrupo depende da categoria escolhida. O cancelamento está disponível na listagem e a API já permite atualizar um lançamento por `PUT /api/entries/{id}`. A edição visual dos lançamentos está disponível na listagem. A tela de contas e transferências está disponível na seção correspondente.

**Regra para saldo inicial:** `balance_date` é a data de abertura do saldo informado. O cálculo soma movimentações realizadas a partir dessa data, incluindo a própria data. Movimentações anteriores à data de abertura não alteram o saldo calculado.

**Observação:** esta versão ainda usa `Base.metadata.create_all` na inicialização para criar tabelas ausentes. Antes de uma utilização continuada com dados importantes, vamos criar e validar uma migration Alembic inicial e configurar backup automatizado.

## Contas, transferências e edição (versão 0.3.0)

A interface agora possui uma seção **Contas e transferências** com:
- Cadastro e edição de contas financeiras, tipo, responsável, saldo inicial e data do saldo inicial.
- Saldo atual por conta e saldo consolidado.
- Registro e consulta de transferências entre contas.
- Validação para impedir transferência entre a mesma conta.

Na seção **Lançamentos**, é possível editar visualmente os registros existentes, além de cancelar lançamentos. A API também disponibiliza `GET /api/accounts/summary` para retornar as contas com seus saldos calculados e `PUT /api/accounts/{id}` para edição de conta.

**Atenção ao editar saldo inicial:** o valor e a data de abertura são a base para o cálculo do saldo atual. Alterá-los pode mudar o resultado apresentado para a conta. O sistema ainda não mantém histórico de versões do saldo inicial.

**Validação desta entrega:** sintaxe Python e testes de API com banco SQLite em memória foram executados, incluindo cadastro/edição de conta e transferência com conferência dos saldos. A compilação Angular e as imagens Docker foram construídas; a execução integrada com PostgreSQL via Docker Compose ainda não foi validada.
