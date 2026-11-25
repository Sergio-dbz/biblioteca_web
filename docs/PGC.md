# Plano de Gerenciamento de Configuração (PGC) — Sistema Web de Biblioteca

* **Projeto:** Sistema Web de Biblioteca (`biblioteca_web`)
* **Fábrica de Software:** Nexo Technology
* **Gerente de Projeto:** Sérgio Fernandes Mar Filho
* **Repositório:** GitHub (`Sergio-dbz/biblioteca_web`)
* **Hospedagem da Aplicação:** Vercel (`https://biblioteca-web-1.vercel.app/`)
* **Hospedagem do Banco:** Railway (MySQL)

---

## Histórico de Revisões

| Data | Versão | Descrição | Autor(es) |
| :--- | :--- | :--- | :--- |
| 01/11/2026 | 1.0 | Elaboração inicial do Plano de Gerenciamento de Configuração | Equipe Nexo Technology |
| 08/11/2026 | 1.1 | Detalhamento dos ambientes, fluxo de branches e controle de mudanças | Equipe Nexo Technology |
| 23/11/2026 | 1.2 | Revisão de consistência e atualização dos registros | Equipe Nexo Technology |
| 25/11/2026 | 1.3 | Alinhamento ao fluxo real de branches, Python 3.13, produção em `https://biblioteca-web-1.vercel.app/` e registro de incidentes recentes | Sérgio Fernandes Mar Filho / Equipe Nexo Technology |

---

## 1. Visão Geral e Escopo

O **Sistema Web de Biblioteca** gerencia acervo, empréstimos, devoluções, reservas e multas, com consulta pública e controle de acesso por perfil (visitante, usuário e administrador).

### Itens de Configuração (ICs)
* **Código-fonte (`SRC`):** `app.py`, `templates/`, `static/`
* **Banco de dados (`BD`):** `sql/schema.sql` e instância MySQL no Railway
* **Configuração e deploy (`CFG`):** `requirements.txt`, `vercel.json`, `.env.example`, `.gitignore`
* **CI/CD (`CI`):** `.github/workflows/ci.yml` e projetos/ambientes na Vercel
* **Testes (`TST`):** `tests/` e validações executadas via `pytest` / `py_compile`
* **Documentação (`DOC`):** `README.md`, `docs/` e este `PGC`

---

## 2. Organização, Papéis e CCB

* **Sérgio Fernandes Mar Filho:** Gerente de Projeto, Gerente de Configuração e membro do CCB.
* **Ivonete Balieiro de Almeida:** Analista de Configuração, Gerente de Mudanças (líder do CCB), Infraestrutura/DevOps e Desenvolvimento.
* **Kaylane Soares Vieira:** Gerente de Qualidade/Testes, UX Designer e membro do CCB.
* **Marcos Correa Alves:** Banco de Dados (MySQL/Railway), Desenvolvimento e membro do CCB.

> **Regra do CCB:** Solicitações de mudança relevantes são avaliadas quanto a impacto, escopo, qualidade e risco, exigindo ao menos duas aprovações e revisão feita por pessoa distinta da implementação.

---

## 3. Branches, Ambientes e CI/CD

### Branches
* **`main`:** Branch de produção, atualizada via Pull Request após validação.
* **`develop`:** Branch principal de integração e desenvolvimento contínuo da equipe.
* **Branches de trabalho (`feature/*`, `fix/*`, `docs/*`):** Criadas a partir de `develop` para novas funcionalidades, correções de bugs ou documentação, integradas via Pull Request.

### Ambientes e Infraestrutura
* **Produção (`main`):** Publicada automaticamente na Vercel em `https://biblioteca-web-1.vercel.app/`, conectada ao banco MySQL no Railway via variáveis de ambiente (`MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`, `SECRET_KEY`).
* **Preview / Desenvolvimento (`develop` e branches em PR):** Implantações de validação geradas pela Vercel para testar mudanças antes da promoção para `main`.
* **Local:** Ambiente individual de cada desenvolvedor com clone do repositório, `.env` local (ignorado pelo `.gitignore`) e dependências instaladas via `pip install -r requirements.txt`.

### Pipeline CI/CD
* **Integração Contínua (GitHub Actions — `.github/workflows/ci.yml`):** Executa em `push` e `pull_request` nas branches configuradas, configurando Python `3.13`, instalando dependências, verificando sintaxe com `python -m py_compile app.py` e executando `pytest` quando houver testes em `tests/`.
* **Entrega Contínua (Vercel):** Realiza builds e deploys automáticos conforme as alterações integradas no repositório, permitindo acompanhamento de logs e *Instant Rollback* se necessário.

---

## 4. Auditorias, Bugs e Mudanças

### Registro de Defeitos (Bugs)

| ID | Descrição do Defeito | Prioridade | Responsável | Status / Evidência |
| :--- | :--- | :--- | :--- | :--- |
| #1 | Comparação de senha em texto puro no login (`login()` em `app.py`), em desacordo com o requisito de segurança de senhas. | Alta | Sérgio Fernandes Mar Filho | Corrigido via hash de senha (Werkzeug) — registrar commit/PR correspondente. |
| #2 | Fallback de `SECRET_KEY` com valor padrão público quando a variável de ambiente não está definida. | Alta | Ivonete Balieiro de Almeida | Corrigido para exigir variável de ambiente — registrar commit/PR correspondente. |
| #3 | Rota de consulta pública ao acervo exigindo autenticação indevidamente para visitantes. | Média | Kaylane Soares Vieira | Corrigido para permitir acesso público — registrar commit/PR correspondente. |
| #4 | Dependências sem versão fixada em `requirements.txt`, causando variação entre builds. | Média | Marcos Correa Alves | Corrigido com fixação de versões — registrar commit/PR correspondente. |
| #5 | Abertura de conexão com o banco fora de blocos de tratamento em rotas principais, gerando erro 500 sem tratamento em falhas de conexão. | Baixa | Sérgio Fernandes Mar Filho | Tratamento adicionado — registrar commit/PR correspondente. |
| #6 | Divergência entre documentação e nomes de branches no repositório/Vercel. | Baixa | Ivonete Balieiro de Almeida | Alinhado ao fluxo real do repositório (`main`, `develop`, `feature/*`/`fix/*`) e `https://biblioteca-web-1.vercel.app/`. |
| #7 | Erro 500 no login em produção por uso do host interno `*.railway.internal` fora da rede privada do Railway. | Alta | Sérgio Fernandes Mar Filho | Resolvido configurando host e porta públicos (`Public networking` / proxy TCP do Railway) nas variáveis de ambiente da Vercel e fazendo *Redeploy*. |
| #8 | `BuildError` ao renderizar `base.html` (`url_for('emprestimos')` sem endpoint correspondente em `app.py`). | Média | Equipe / Sérgio Fernandes Mar Filho | Ajustar endpoint/rota em `base.html` ou `app.py` via branch/PR e registrar hash do commit/PR. |
| #9 | Conflitos de merge em Pull Request entre branches divergentes. | Média | Equipe | Resolvidos localmente via `git fetch`/`git merge`, ajuste manual no código, commit de merge e `git push`. |

### Registro de Mudanças e Marcos
* **Mudanças principais:** Adequação do PGC à arquitetura Flask/MySQL/Vercel, criação do `.env.example`, adoção de hash de senhas e `SECRET_KEY` por ambiente, liberação da consulta pública ao acervo, fixação de dependências em `requirements.txt`, configuração do workflow de CI e atualização da documentação.
* **Baselines e Marcos:** `BL1` (Planejamento/documentação inicial), `BL2` (Estrutura base da aplicação e configuração), `BL3` (Integração em `develop` e validação em Preview) e `BL4` (Versão estável em `main` / `https://biblioteca-web-1.vercel.app/`, identificada por tag de release como `v1.0.0`).
