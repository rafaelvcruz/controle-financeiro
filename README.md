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

**Validação desta entrega:** sintaxe Python e testes de API com banco SQLite em memória foram executados, incluindo cadastro/edição de conta e transferência com conferência dos saldos. A compilação Angular e a construção/execução integral via Docker ainda não foram validadas neste ambiente.


## Planejamento orçamentário (versão 0.4.0)

A versão 0.4.0 acrescenta planejamento mensal por categoria:
- Cadastro de um orçamento por mês, com receita de referência, descrição e status aberto/encerrado.
- Definição de valor planejado por categoria e percentual opcional.
- Consulta de resumo com total planejado, realizado, disponível e consumo por categoria.
- Alerta textual quando o realizado ultrapassa o limite planejado.
- Itens de orçamento são vinculados a categorias existentes; a mesma categoria não pode ser repetida no mesmo orçamento.

### Regras de apuração

- O realizado considera lançamentos `REALIZADO` do tipo `DESPESA` ou `INVESTIMENTO`, agrupados pela **data de competência** dentro do mês do orçamento.
- Lançamentos `PREVISTO` e `CANCELADO` não entram no realizado.
- Transferências não são lançamentos de despesa e não entram no orçamento.
- O pagamento da fatura não deve ser lançado como nova despesa quando as compras já foram registradas; a estrutura de cartões/faturas ainda será implementada.
- A categoria Extra não recebe percentual automático. Ela pode ser incluída manualmente se fizer sentido no planejamento.
- O orçamento aceita valor planejado diretamente; o percentual é informativo/opcional e não altera automaticamente o valor.

### Endpoints

- `GET /api/budgets`: lista orçamentos.
- `POST /api/budgets`: cria orçamento com seus itens.
- `GET /api/budgets/{id}`: consulta orçamento.
- `PUT /api/budgets/{id}`: substitui os dados e itens do orçamento.
- `DELETE /api/budgets/{id}`: exclui orçamento e seus itens.
- `GET /api/budgets/{id}/summary`: consolida planejado versus realizado por categoria.

A data `reference_month` deve ser sempre o primeiro dia do mês (ex.: `2026-11-01`). O banco impede mais de um orçamento por mês.

### Validação desta versão

Foram executados `compileall` no backend e testes da API com SQLite em memória/arquivo temporário: criação de categoria, criação de orçamento com item, consulta do resumo e rejeição de orçamento duplicado para o mesmo mês. A tentativa de instalar dependências npm excedeu o tempo disponível; portanto, a compilação Angular e o build/execução Docker ainda não foram validados nesta entrega.

## Versão 0.5.0 — Dashboard financeiro

A tela inicial apresenta um resumo mensal das receitas, despesas e investimentos realizados, resultado líquido, maiores despesas classificadas por categoria, fluxo de receitas/despesas dos últimos seis meses e lançamentos recentes. O mês de referência pode ser alterado na própria tela.

Endpoint adicional: `GET /api/dashboard/summary?reference_month=YYYY-MM-01`.

Os indicadores mensais usam a data de competência e consideram somente lançamentos com status `REALIZADO`. Transferências entre contas não entram como receita ou despesa. A lista de movimentações recentes exibe os últimos lançamentos independentemente do mês selecionado.

A compilação Angular e a execução integrada com PostgreSQL/Docker precisam ser verificadas no ambiente de desenvolvimento: nesta geração, a instalação das dependências npm excedeu o tempo disponível.


## Cartões de crédito (v0.6.0)

- Cadastro de cartões com limite, dia de fechamento e vencimento.
- Registro de compras à vista ou parceladas em até 48 vezes.
- Cada parcela é alocada à competência da fatura correspondente; compras após o fechamento entram na fatura seguinte.
- Consulta de faturas por cartão/competência, com total, pagamentos e saldo em aberto.
- Pagamento parcial ou integral vinculado a uma conta financeira. O pagamento reduz o saldo da conta e não gera uma nova despesa.
- Compras classificadas por subgrupo são consideradas no realizado do orçamento e no total de despesas do dashboard, pela competência da fatura.

**Convenção de competência:** a competência da fatura é o mês do ciclo de fechamento; o vencimento é calculado no mês seguinte, limitado ao último dia daquele mês. Ex.: uma compra após o fechamento em novembro vai para a competência dezembro, com vencimento no dia configurado em janeiro.

**Atenção:** esta versão ainda não valida o limite disponível do cartão, não permite estorno/edição/exclusão de compras ou pagamentos e não faz conciliação automática com bancos. Configure o banco de dados com backup antes de usar dados reais.


## Versão 0.7.0 — Gestão e validação de cartões

A versão 0.7.0 complementa o módulo de cartões com controles de manutenção e limite:

- Exibição do limite total, utilizado e disponível por cartão. O limite utilizado é calculado pelas parcelas ainda não pagas, incluindo parcelas futuras.
- Bloqueio de novas compras que ultrapassem o limite disponível.
- Bloqueio de redução do limite cadastrado para valor inferior ao que já está utilizado.
- Edição e exclusão de compras. Para preservar a consistência, uma compra não pode ser alterada/excluída quando houver pagamento registrado em alguma fatura afetada; primeiro ajuste ou exclua o pagamento correspondente.
- Edição e exclusão de pagamentos, com validação para impedir que a soma paga ultrapasse o total da fatura.
- Listagens de compras e pagamentos na interface.
- Correção do resumo de saldos das contas para descontar também pagamentos de faturas, assim como já ocorria na consulta individual do saldo.

### Endpoints adicionais

- `GET /api/credit-cards/summary`: limite, utilização e limite disponível por cartão.
- `GET /api/card-purchases`: lista geral de compras.
- `PUT /api/card-purchases/{id}` e `DELETE /api/card-purchases/{id}`: edição e exclusão de compra, respeitando pagamentos existentes.
- `GET /api/card-payments`: lista pagamentos.
- `PUT /api/card-payments/{id}` e `DELETE /api/card-payments/{id}`: edição e exclusão de pagamento.

### Regras importantes

O limite utilizado corresponde ao valor total das parcelas lançadas menos os pagamentos registrados. Assim, parcelas futuras também comprometem o limite. Pagamentos reduzem o saldo bancário e liberam limite, mas não geram uma segunda despesa. O sistema bloqueia edição/exclusão de compras que afetem faturas com pagamentos, para evitar que a fatura fique inconsistente.

### Validação desta versão

- `python -m compileall` no backend: aprovado.
- Teste de integração da API com SQLite temporário: aprovado para cadastro de conta/cartão/compra, cálculo do limite, pagamento e baixa no saldo da conta, bloqueio de edição de compra com fatura paga, edição/exclusão de pagamento, edição/exclusão de compra e rejeição de compra acima do limite.
- Integridade do ZIP: será verificada na geração do pacote.
- Compilação Angular: aprovada com `npm run build`. A execução integrada Docker/PostgreSQL permanece pendente.
