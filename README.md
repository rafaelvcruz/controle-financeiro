# Controle Financeiro Familiar

Projeto inicial executável para controle financeiro familiar, com Angular, FastAPI, PostgreSQL e Docker Compose.

## Escopo desta primeira entrega

- Backend REST com CRUD básico para pessoas, categorias, grupos, subgrupos e contas financeiras.
- PostgreSQL persistente em volume Docker.
- Frontend Angular responsivo com painel inicial e consulta/cadastro de categorias.
- Endpoint de saúde em `/api/health` e documentação OpenAPI em `/docs`.
- Modelo preparado para evolução de lançamentos, orçamentos, cartões e objetivos.

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
3. Implementar lançamentos, transferências e ajustes de saldo com transações atômicas.
4. Implementar orçamento mensal e previsto x realizado.
5. Implementar cartões, faturas e parcelamentos.
6. Implementar backup automatizado com teste de restauração.
