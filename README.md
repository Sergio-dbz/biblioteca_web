# Sistema Web de Biblioteca — Gerência de Configuração de Software

Repositório destinado ao desenvolvimento do **Sistema Web de Biblioteca**, desenvolvido como trabalho prático da disciplina de **Gerência de Configuração de Software** (UFAM/ICET) pela fábrica de software **Nexo Technology**.

* **Aplicação em Produção (Vercel):** https://biblioteca-web-1.vercel.app/
* **Plano de Gerenciamento de Configuração (PGC):** [`docs/PGC.md`](docs/PGC.md)

---

## 👥 Integrantes do Grupo

| Nome | Matrícula | Papel Principal |
| :--- | :--- | :--- |
| **Sérgio Fernandes Mar Filho** | 22450190 | Gerente de Projeto / Configuração / Testes |
| **Ivonete Balieiro de Almeida** | 22450581 | Analista de Configuração / Gerente de Mudanças / DevOps |
| **Kaylane Soares Vieira** | 22450510 | Gerente de Qualidade / UX Designer |
| **Marcos Correa Alves** | 22450269 | Banco de Dados (MySQL/Railway) / Desenvolvimento |

---

## 📌 Sobre o Projeto e Stack Tecnológica

Plataforma web para controle de acervo, empréstimos, devoluções, reservas e multas, aplicando na prática os processos de Gerência de Configuração:
- **Back-end e Front-end:** Python 3.13, Flask, Flask-Login, HTML5, CSS3.
- **Banco de Dados:** MySQL hospedado no **Railway**.
- **CI/CD e Hospedagem:** Integração Contínua via **GitHub Actions** (`.github/workflows/ci.yml`) e Entrega Contínua via **Vercel** (ambientes de *Preview* e *Production*).
- **Rastreabilidade:** Commits semânticos, Pull Requests revisados e registro de auditorias/bugs no PGC.

---

## 🌿 Estrutura de Branches e Ambientes

- **`main`**: Branch de produção com a versão estável do sistema (publicada automaticamente em `https://biblioteca-web-1.vercel.app/`).
- **`develop`**: Branch principal de integração das funcionalidades desenvolvidas pela equipe (gera ambiente de *Preview* na Vercel para validação).
- **`feature/*` e `fix/*`**: Branches de trabalho criadas a partir da `develop` para novas funcionalidades, correções de defeitos e ajustes de documentação, integradas via Pull Request após aprovação no CI.

---

## ⚙️ Como Executar Localmente

1. Clone o repositório e acesse a pasta do projeto:
   ```bash
   git clone [https://github.com/Sergio-dbz/biblioteca_web.git](https://github.com/Sergio-dbz/biblioteca_web.git)
   cd biblioteca_web
